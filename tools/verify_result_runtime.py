"""Verify the real defeat animation, tilemap, pixels and return to town."""
import json
import struct
from pathlib import Path
import mgba.log
from mgba._pylib import ffi, lib
from PIL import Image, ImageChops
from tools import build_result_runtime as b
from tools.build_first_label import ROOT, ORIGINAL_ROM, digest
from tools.translation_pipeline import check, load_json, atomic_write
from tools.verify_expansion import Session
from tools.verify_first_label import battery_snapshot
from tools.verify_natural_cave import CaveTrace, sources
from tools.verify_text_polish import ui_checks
from tools.trace_story_provenance import SAVE

MAP = 0x02034DDC
REPLAY = b.OUTPUT/'research/replay.json'


def save(path, value):
    atomic_write(path, (json.dumps(value, ensure_ascii=False, indent=2)+'\n').encode())


def map_errors(raw, hidden=0):
    errors = []
    for y in range(17):
        for x in range(27):
            actual = struct.unpack_from('<H', raw, (y+2)*64+(x+1)*2)[0]
            expected = 0 if y < hidden else 0xF002+(y-hidden)*27+x
            if actual != expected:
                errors.append({'x': x+1, 'y': y+2, 'expected': expected, 'actual': actual})
    return errors


def outside_window(raw):
    return bytes(byte for i, byte in enumerate(raw)
                 if not (2 <= i//64 < 19 and 2 <= i%64 < 56))


class ResultTrace(CaveTrace):
    def __init__(self, *args):
        self.animation = []
        self.before_map = None
        super().__init__(*args)
        for address in (0x0805C692, 0x0805C6EC):
            point = ffi.new('struct mBreakpoint*')
            point.address, point.segment, point.type = address, -1, lib.BREAKPOINT_HARDWARE
            check(self.debugger.platform.setBreakpoint(self.debugger.platform, point) >= 0,
                  'Cannot observe result animation')

    def entered(self, debugger, reason, info):
        try:
            if info != ffi.NULL and reason == lib.DEBUGGER_ENTER_BREAKPOINT:
                if info.address == 0x0805C692:
                    self.before_map = bytes(self.core.memory[MAP:MAP+0x800])
                elif info.address == 0x0805C6EC:
                    check(self.before_map is not None, 'Animation start not observed')
                    raw = bytes(self.core.memory[MAP:MAP+0x800])
                    hidden = 16-len(self.animation)
                    self.animation.append({'frame': self.core.frame_counter, 'hidden_rows': hidden,
                        'tilemap_hex': raw.hex(), 'mismatches': len(map_errors(raw, hidden)),
                        'outside_window_unchanged': outside_window(raw) == outside_window(self.before_map)})
            super().entered(debugger, reason, info)
        except Exception as error:
            self.errors.append(str(error))
        finally:
            debugger.state = lib.DEBUGGER_RUNNING


def ink_pixels(core, screen):
    bitmap = bytes(core.memory[0x02035E1C:0x0203977C])
    palette = bytes(core.memory[0x050001E0:0x05000200])
    checks = mismatches = 0
    for y in range(136):
        for x in range(216):
            offset = ((y//8)*27+x//8)*32+(y%8)*4+(x%8)//2
            color = (bitmap[offset] >> (4*(x%2))) & 15
            # The observed panel palette has two white text entries. Check
            # actual foreground pixels independently of the glyph trace.
            if color and struct.unpack_from('<H', palette, color*2)[0] == 0x7FFF:
                checks += 1
                mismatches += screen.getpixel((x+8, y+16)) != (255, 255, 255)
    return {'white_ink_pixels': checks, 'mismatched_white_ink_pixels': mismatches}


def route(data, build, variant):
    replay = load_json(REPLAY)
    state = (ROOT/replay['initial_state']).read_bytes()
    check(digest(state) == replay['initial_state_sha256'], 'Natural checkpoint changed')
    index, _, _ = sources(data, build['ledger'])
    watch = [0x08000000+int(e['offset'], 0)
             for e in load_json(ROOT/'translations/unowned-text-review.json')['entries']]
    folder = b.OUTPUT/'verification'/variant
    with Session(data, folder, SAVE.read_bytes()) as s:
        check(s.core.load_raw_state(state), 'Cannot restore natural cave checkpoint')
        check(s.core.frame_counter == replay['initial_frame'], 'Initial frame differs')
        check(battery_snapshot(s.core) == SAVE.read_bytes(), 'Checkpoint changed cartridge save')
        t = ResultTrace(s.core, data, index, watch)
        try:
            for i, row in enumerate(replay['inputs']):
                t.phase = f'input-{i:02d}'
                key = getattr(s.core, 'KEY_'+row['key'])
                s.core.set_keys(key); t.frames(row['hold'])
                s.core.clear_keys(key); t.frames(row['released'])
                check(s.core.frame_counter == row['end_frame'], 'Replay frame differs')
                s.capture(t.phase)
            screen = s.capture('result')
            c = s.core
            rawmap = bytes(c.memory[MAP:MAP+0x800])
            bitmap = bytes(c.memory[0x02035E1C:0x0203977C])
            check(bitmap == bytes(c.memory[0x06000040:0x060039A0]), 'RAM/VRAM bitmap differs')
            check(rawmap == bytes(c.memory[0x06006000:0x06006800]), 'RAM/VRAM tilemap differs')
            check(struct.unpack('<4H', bytes(c.memory[0x02034CD8:0x02034CE0])) == (1, 2, 27, 17),
                  'Result window dimensions differ')
            report = t.report()
            checks, repeats = ui_checks(report, ORIGINAL_ROM.read_bytes())
            report.update(animation=t.animation, ui_checks=checks, duplicate_draws=repeats,
                final_tilemap_mismatches=len(map_errors(rawmap)), pixels=ink_pixels(c, screen),
                bitmap_sha256=digest(bitmap), tilemap_hex=rawmap.hex(),
                score_record_hex=bytes(c.memory[0x02002FE8:0x02003018]).hex(),
                font_state_hex=bytes(c.memory[0x020398EC:0x020398F8]).hex())
            check(len(t.animation) == 17 and not t.errors, 'Missing animation or trace error')
            if variant == 'english':
                check(all(a['mismatches'] == 0 and a['outside_window_unchanged'] for a in t.animation),
                      'Animation uses an incorrect tilemap or touches adjacent cells')
                check(report['final_tilemap_mismatches'] == 0, 'Final result tilemap differs')
                check(report['pixels']['white_ink_pixels'] > 500 and
                      report['pixels']['mismatched_white_ink_pixels'] == 0, 'Displayed result ink differs')
            else:
                check(report['final_tilemap_mismatches'] == 459 and
                      report['pixels']['mismatched_white_ink_pixels'] > 500, 'Defect no longer reproduced')
            (folder/'result.state').write_bytes(bytes(ffi.buffer(c.save_raw_state())))
            (folder/'bitmap.bin').write_bytes(bitmap)
            # Continue naturally past the result panel; no scenario or save
            # state is injected after the initial checkpoint restore.
            for i in range(2):
                t.phase = f'return-{i}'
                s.press('A', 600, t); s.capture(t.phase)
            report['return_trace'] = t.report()
            report['return_frame'] = c.frame_counter
            report['return_root'] = c.memory.u32[0x0200000C]
            report['unowned_source_reads'] = report['return_trace']['source_reads']
            check(not t.errors and not report['unowned_source_reads'], 'Trace error or new unowned source')
            check(report['return_trace']['versions'], 'Expected natural return-to-town dialogue')
            (folder/'returned.state').write_bytes(bytes(ffi.buffer(c.save_raw_state())))
            current_save = battery_snapshot(c)
            (folder/'returned.sav').write_bytes(current_save)
        finally:
            t.close()
    check(s.disk_save == current_save and len(current_save) == 65536, 'Native save file differs')
    report.update(rom_sha256=digest(data), initial_state_sha256=digest(state),
        initial_save_sha256=digest(SAVE.read_bytes()), output_save_sha256=digest(current_save),
        cartridge_save_changed=current_save != SAVE.read_bytes(),
        scope='Normal buttons from the accepted floor-two checkpoint through defeat, the complete native result animation and return dialogue; no HP/item/position/flag/register injection. Save bytes are observed, not proof of a later save prompt or all dungeon outcomes.')
    save(folder/'trace.json', report)
    print(variant, 'result route:', len(checks), 'draws;', report['pixels'], flush=True)
    return report


def verify():
    mgba.log.silence()
    data = (b.OUTPUT/'torneko3-result-runtime-english.gba').read_bytes()
    baseline = b.BASELINE.read_bytes()
    build = load_json(b.OUTPUT/'english-build.json')
    prior = load_json(b.BASELINE.parent/'english-build.json')
    check(build['rom_sha256'] == digest(data) and build['previous_rom_sha256'] == digest(baseline),
          'Build ROM hashes differ')
    expected = bytearray(baseline)
    for _, at, before, after in b.PATCHES:
        check(expected[at:at+2] == bytes.fromhex(before), 'Patch before differs')
        expected[at:at+2] = bytes.fromhex(after)
    check(bytes(expected) == data, 'Unrelated ROM bytes changed')
    check(build['ledger']['allocations'] == prior['ledger']['allocations'] and
          build['ledger']['patches'][:-5] == prior['ledger']['patches'], 'Earlier ownership changed')
    old = route(baseline, prior, 'baseline')
    new = route(data, build, 'english')
    for key in ('ui_payloads', 'ui_positions', 'bitmap_sha256', 'score_record_hex', 'font_state_hex',
                'return_trace', 'output_save_sha256', 'return_frame', 'return_root'):
        check(old[key] == new[key], 'Layout correction changed unrelated behavior: '+key)
    check([a['frame'] for a in old['animation']] == [a['frame'] for a in new['animation']],
          'Animation pacing differs')
    unchanged = []
    for name in [f'input-{i:02d}.png' for i in range(17)]+['return-0.png', 'return-1.png']:
        a = Image.open(b.OUTPUT/'verification/baseline'/name).convert('RGB')
        z = Image.open(b.OUTPUT/'verification/english'/name).convert('RGB')
        check(ImageChops.difference(a, z).getbbox() is None, 'Unrelated gameplay pixels differ: '+name)
        unchanged.append(name)
    report = {'status': 'natural_result_animation_passed', 'source_sha256': digest(ORIGINAL_ROM.read_bytes()),
        'rom_sha256': digest(data), 'baseline_sha256': digest(baseline),
        'builder_sha256': digest(Path(b.__file__).read_bytes()), 'harness_sha256': digest(Path(__file__).read_bytes()),
        'replay_sha256': digest(REPLAY.read_bytes()), 'initial_save_sha256': digest(SAVE.read_bytes()),
        'reports': {v: digest((b.OUTPUT/'verification'/v/'trace.json').read_bytes()) for v in ('baseline', 'english')},
        'only_five_owned_halfwords_changed': True, 'prior_allocations_and_patches_preserved': True,
        'animation_steps': 17, 'correct_tiles_per_step': 459, 'actual_pixels': new['pixels'],
        'draws_per_variant': len(new['ui_checks']), 'unchanged_screens': unchanged,
        'normal_return_and_save_bytes_identical': True, 'cartridge_save_changed': new['cartridge_save_changed'],
        'scope': 'Native floor-two defeat and complete ending reveal/return; a regression of five geometry operands, not full-game or all-score-category acceptance.'}
    save(b.OUTPUT/'component-checkpoint.json', report)
    print(report['status'], flush=True)


if __name__ == '__main__':
    verify()
