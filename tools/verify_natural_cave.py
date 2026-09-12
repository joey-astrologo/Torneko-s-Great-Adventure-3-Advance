"""Replay normal village/rest/tutorial-cave inputs on the current combined ROM."""
import json
import struct
from pathlib import Path

import mgba.log
from mgba._pylib import ffi, lib
from PIL import Image, ImageChops

from tools.audit_scene_resources import BASELINE
from tools.build_first_label import ROOT, ORIGINAL_ROM, digest
from tools import build_opening_story, build_first_village, build_early_journey
from tools import build_story_completion, build_dungeon_events
from tools.game_text import GameTextCodec
from tools.trace_opening_story import OpeningTrace
from tools.verify_story_provenance import check_natural
from tools.verify_expansion import Session
from tools.verify_items import distinct_glyph_observations, coalesce_empty_draw_observations
from tools.verify_dungeon_interface import check_glyphs
from tools.verify_core_gameplay import visible, command_ink_check
from tools.translation_pipeline import check, load_json, atomic_write, FontZero

OUT = ROOT/'build/completion/dungeon-route'
STORY = {
    'opening-story': build_opening_story.encode,
    'first-village': build_first_village.encode,
    'early-journey': build_early_journey.encode,
    'story-completion': build_story_completion.encode,
    'shared-story': build_story_completion.encode,
}


def save(path, data):
    atomic_write(path, (json.dumps(data, ensure_ascii=False, indent=2)+'\n').encode())


def sources(data, ledger):
    index = list(load_json(ROOT/'translations/master.json')['entries'])
    codec = GameTextCodec(data)
    allocations = {a['id']: a for a in ledger['allocations']}
    by_address, hashes = {}, {}
    for family in (*STORY, 'dungeon-events'):
        path = ROOT/f'translations/{family}.json'
        hashes[str(path.relative_to(ROOT))] = digest(path.read_bytes())
        for entry in load_json(path)['entries']:
            a = allocations[entry.get('reuse') or entry['id']]
            parsed = codec.parse(data, a['offset'])
            check(parsed['end'] == a['offset']+a['bytes'], 'Allocation/source boundary differs')
            index.append({'id': entry['master_id'], 'offset': hex(a['offset']),
                          'source_hex': parsed['raw_hex'], 'source_tokens': parsed['tokens']})
            by_address[a['offset']+0x08000000] = (entry, family)
    return index, by_address, hashes


class CaveTrace(OpeningTrace):
    """Observe original story, paged tutorial and whole-string draw paths together."""
    def __init__(self, core, data, index, watch):
        self.ui_payloads, self.ui_positions, self.paged_positions = [], [], []
        self.paged_format = None
        self.pending_queue = None
        self.last_queue_serial = None
        self.scroll_completions = []
        super().__init__(core, data, index)
        for address in (0x0805D55C, 0x0805D63C):
            point = ffi.new('struct mBreakpoint*')
            point.address, point.segment, point.type = address, -1, lib.BREAKPOINT_HARDWARE
            check(self.debugger.platform.setBreakpoint(self.debugger.platform, point) >= 0,
                  'Cannot observe native queue draw/scroll')
        for address in watch:
            point = ffi.new('struct mWatchpoint*')
            point.address, point.segment, point.type = address, -1, lib.WATCHPOINT_READ
            check(self.debugger.platform.setWatchpoint(self.debugger.platform, point) >= 0,
                  'Cannot watch unowned Japanese source')

    def entered(self, debugger, reason, info):
        try:
            if info != ffi.NULL and reason == lib.DEBUGGER_ENTER_BREAKPOINT:
                regs = [int(r)&0xffffffff for r in self.cpu.gprs]
                if info.address == 0x0805D55C:
                    self.pending_queue = {'address': regs[2], 'y': regs[1],
                                          'frame': self.core.frame_counter}
                if info.address == 0x0805D63C:
                    self.scroll_completions.append({'draw_serial': self.last_queue_serial,
                        'frame': self.core.frame_counter, 'pc': '0x0805D63C'})
                if info.address == 0x0807D8CC and (regs[14]&~1)-4 == 0x0807AE04:
                    self.paged_format = len(self.formats)
                if info.address == 0x0808CBA0:
                    queued = self.pending_queue
                    queue_draw = bool(queued and queued['address'] == regs[2] and
                                      queued['y'] == regs[1] and queued['frame'] == self.core.frame_counter)
                    self.ui_payloads.append({'serial': len(self.ui_payloads), 'phase': self.phase,
                        'frame': self.core.frame_counter, 'address': hex(regs[2]),
                        'x': regs[0], 'y': regs[1], 'native_queue_draw': queue_draw,
                        'raw_hex': bytes(self.core.memory[regs[2]:regs[2]+512]).hex()})
                    if queue_draw:
                        self.last_queue_serial = len(self.ui_payloads)-1
                    self.pending_queue = None
                if info.address == 0x0808BC78 and self.glyph_caller != 0x08061B4E:
                    _, code, advance = struct.unpack('<IHh', bytes(self.core.memory[regs[0]:regs[0]+8]))
                    x, y, w, h = struct.unpack('<hhhh', bytes(self.core.memory[regs[4]:regs[4]+8]))
                    glyph = {'frame': self.core.frame_counter, 'phase': self.phase,
                        'caller': hex(self.glyph_caller), 'code': code, 'advance': advance,
                        'x': regs[6], 'y': regs[8], 'font': self.core.memory.u32[0x020398F8],
                        'spacing': self.core.memory.u16[0x020398DC], 'window_origin': [x*8, y*8],
                        'window_width': w*8, 'window_height': h*8}
                    if self.glyph_caller in (0x0808CD04, 0x0808CD38):
                        glyph['draw_serial'] = len(self.ui_payloads)-1
                        self.ui_positions.append(glyph)
                    elif self.glyph_caller == 0x0807AF6A:
                        check(self.paged_format is not None, 'Paged glyph lacks formatter')
                        glyph['draw_serial'] = self.paged_format
                        self.paged_positions.append(glyph)
            super().entered(debugger, reason, info)
        except Exception as error:
            self.errors.append(str(error))
        finally:
            debugger.state = lib.DEBUGGER_RUNNING

    def report(self):
        return {**super().report(), 'ui_payloads': self.ui_payloads,
                'ui_positions': self.ui_positions, 'paged_positions': self.paged_positions,
                'scroll_completions': self.scroll_completions}


def validate(report, data, ledger, index, by_address):
    original = ORIGINAL_ROM.read_bytes()
    font, codec = FontZero(original), GameTextCodec(original)
    proof = check_natural(report, data, index)
    story_checks, paged_checks, ui_checks = [], [], []
    for v in report['versions']:
        e, family = by_address[int(v['source']['address'], 0)]
        raw, metrics = STORY[family](e, original)
        check(v['output_hex'] == raw.replace(b'$t', b'Torneko').hex(), 'Natural story bytes differ')
        gs = [g for g in report['positions'] if g['version'] == v['serial']]
        story_checks.append({'id': e['id'], 'version': v['serial'],
                             **check_glyphs(gs, metrics['visible'], font)})
    for serial, f in enumerate(report['formats']):
        if f['caller'] != '0x0807AE04':
            continue
        e, family = by_address[int(f['source'], 0)]
        check(family == 'dungeon-events', 'Unreviewed natural paged source')
        raw, _ = build_dungeon_events.encode(e, original)
        check(f['output_hex'] == raw.hex(), 'Natural tutorial formatter bytes differ')
        gs = [g for g in report['paged_positions'] if g['draw_serial'] == serial]
        paged_checks.append({'id': e['id'], 'format_serial': serial,
                            **check_glyphs(gs, visible(raw, codec), font)})
    nonempty = [d for d in report['ui_payloads'] if visible(bytes.fromhex(d['raw_hex']), codec)]
    draws, duplicate_draws = coalesce_empty_draw_observations(nonempty, report['ui_positions'])
    for d in draws:
        text = visible(bytes.fromhex(d['raw_hex']), codec)
        gs = [g for g in report['ui_positions'] if g['draw_serial'] == d['serial']]
        if d['native_queue_draw']:
            distinct, repeated = distinct_glyph_observations(gs)
            check([g['code'] for g in distinct] == [font.glyph(c)[0] for c in text], 'Queue glyphs differ')
            for g, char in zip(distinct, text, strict=True):
                check(g['font'] == 0 and g['spacing'] == 0 and g['window_origin'] == [16, 120]
                      and g['window_width'] == 208 and g['window_height'] == 40,
                      'Native queue font/viewport differs')
                check(0 <= g['x'] and g['x']+max(g['advance'], font.glyph(char)[2]) <= 208,
                      'Queue glyph clipped horizontally')
                check(g['y'] in (2, 14, 26, 38), 'Queue row differs')
            staged = any(g['y'] == 38 for g in distinct)
            scrolls = [x for x in report['scroll_completions'] if x['draw_serial'] == d['serial']]
            check(not staged or scrolls, 'Staged queue row did not complete native scroll')
            measurement = {'glyphs': len(distinct), 'reobservations': repeated,
                           'native_scroll_staging_row': staged, 'scroll_completions': scrolls}
        else:
            measurement = command_ink_check(gs, text, font)
        ui_checks.append({'draw_serial': d['serial'], 'text': text,
                          **measurement})
    check(not report['source_reads'], 'Unowned Japanese source was read; review its actual caller')
    required = ('Copper sword', 'Wooden shield', 'Slime was defeated.', '2 XP.', 'Stairs down')
    check(all(any(t in d['text'] for d in ui_checks) for t in required), 'Missing natural cave milestone')
    check(len(paged_checks) == 2, 'Both floor tutorials were not reached')
    return {'story_provenance': proof, 'story_checks': story_checks,
            'paged_tutorial_checks': paged_checks, 'ui_checks': ui_checks,
            'empty_duplicate_draw_observations': duplicate_draws,
            'unowned_japanese_source_reads': 0}


def verify():
    mgba.log.silence()
    data = BASELINE.read_bytes()
    replay_path = OUT/'replay.json'
    replay = load_json(replay_path)
    check(digest(data) == replay['rom_sha256'], 'Replay requires its pinned combined ROM')
    state_path = ROOT/replay['initial_state']
    state = state_path.read_bytes()
    check(digest(state) == replay['initial_state_sha256'], 'Natural checkpoint changed')
    build = load_json(BASELINE.parent/'english-build.json')
    check(build['rom_sha256'] == digest(data), 'Build ledger belongs to another ROM')
    check(digest((OUT/'expected-final.png').read_bytes()) == replay['expected_final_png_sha256'],
          'Exploration reference image changed')
    index, by_address, catalogs = sources(data, build['ledger'])
    watch = [0x08000000+int(e['offset'], 0) for e in
             load_json(ROOT/'translations/unowned-text-review.json')['entries']]
    folder = OUT/'verification'
    with Session(data, folder) as s:
        check(s.core.load_raw_state(state), 'Cannot restore accepted natural checkpoint')
        check(s.core.frame_counter == replay['initial_frame'], 'Initial frame differs')
        trace = CaveTrace(s.core, data, index, watch)
        try:
            for i, row in enumerate(replay['inputs']):
                trace.phase = f'input-{i:03d}'
                code = getattr(s.core, 'KEY_'+row['key'])
                s.core.set_keys(code)
                trace.frames(row['hold'])
                s.core.clear_keys(code)
                trace.frames(row['released'])
                check(s.core.frame_counter == row['end_frame'], 'Replay frame sequence differs')
                if i % 25 == 24:
                    print('Cave replay', i+1, '/', len(replay['inputs']), flush=True)
                s.capture(trace.phase)
            check(s.core.frame_counter == replay['expected_final_frame'], 'Final frame differs')
            final = s.capture('final')
            reference = Image.open(OUT/'expected-final.png').convert('RGB')
            report = trace.report()
            save(folder/'raw-trace.json', report)
            check(ImageChops.difference(final, reference).getbbox() is None, 'Replay final pixels differ')
            check(not trace.errors, str(trace.errors))
            checks = validate(report, data, build['ledger'], index, by_address)
            (folder/'final.state').write_bytes(bytes(ffi.buffer(s.core.save_raw_state())))
            save(folder/'trace.json', {**report, 'checks': checks})
        finally:
            trace.close()
    result = {'status': 'natural_cave_route_passed', 'rom_sha256': digest(data),
        'source_sha256': digest(ORIGINAL_ROM.read_bytes()),
        'harness_sha256': digest(Path(__file__).read_bytes()), 'catalog_sha256': catalogs,
        'helper_sha256': {name: digest((ROOT/'tools'/name).read_bytes()) for name in (
            'trace_opening_story.py', 'trace_story_provenance.py', 'trace_text_systems.py',
            'verify_story_provenance.py', 'verify_items.py', 'verify_dungeon_interface.py',
            'verify_core_gameplay.py', 'verify_expansion.py', 'game_text.py', 'translation_pipeline.py')},
        'replay_sha256': digest(replay_path.read_bytes()), 'initial_state_sha256': digest(state),
        'prior_natural_regression_sha256': digest((state_path.parent.parent/'verification.json').read_bytes()),
        'trace_sha256': digest((folder/'trace.json').read_bytes()),
        'final_png_sha256': digest((folder/'final.png').read_bytes()),
        'normal_inputs': len(replay['inputs']), 'final_frame': replay['expected_final_frame'],
        'story_messages': len(checks['story_checks']), 'paged_tutorials': len(checks['paged_tutorial_checks']),
        'whole_string_draws': len(checks['ui_checks']), 'unowned_japanese_source_reads': 0,
        'scope': 'Normal inputs from the accepted naturally reached chief checkpoint, through Tessie rest, second chief, first cave entry, sword/shield equipment, Slime combat and stairs to floor two. Exact story provenance/output/glyphs, both paged tutorials and observed whole-string glyphs/ink are checked. No scenario, coordinate, register or RAM edits after checkpoint restore. The final screen matches exploration. This does not prove later floors, shrine access, every cave branch, cartridge suspend/save persistence or full-game coverage.'}
    save(OUT/'verification.json', result)
    print(result['story_messages'], 'story messages;', result['paged_tutorials'], 'tutorials;',
          result['whole_string_draws'], 'whole-string draws passed', flush=True)


if __name__ == '__main__':
    verify()
