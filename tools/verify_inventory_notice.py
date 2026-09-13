"""Observe the native inventory popup and its original transparent blank fill."""
import json
from pathlib import Path
import mgba.log
from mgba._pylib import ffi, lib
from PIL import ImageChops
from tools import build_inventory_notice as b
from tools.build_first_label import ROOT, ORIGINAL_ROM, digest
from tools.translation_pipeline import check, load_json, atomic_write, FontZero
from tools.verify_result_runtime import ResultTrace
from tools.verify_expansion import Session
from tools.verify_text_polish import ui_checks
from tools.verify_core_gameplay import command_ink_check
from tools.verify_items import distinct_glyph_observations


def save(path, value):
    atomic_write(path, (json.dumps(value, ensure_ascii=False, indent=2)+'\n').encode())


def cstring(core, at, cap=256):
    raw = bytes(core.memory[at:at+cap])
    check(b'\0' in raw, 'Unterminated native notice string')
    return raw[:raw.index(0)+1]


class NoticeTrace(ResultTrace):
    def __init__(self, *args):
        self.notice_formats, self.notice_draws = [], []
        self.pending_notice = None
        super().__init__(*args)
        for address in (0x080204EA, 0x080204EE, 0x080204FA):
            point = ffi.new('struct mBreakpoint*')
            point.address, point.segment, point.type = address, -1, lib.BREAKPOINT_HARDWARE
            check(self.debugger.platform.setBreakpoint(self.debugger.platform, point) >= 0, 'Cannot observe native notice')

    def entered(self, debugger, reason, info):
        try:
            if info != ffi.NULL and reason == lib.DEBUGGER_ENTER_BREAKPOINT:
                regs = [int(r)&0xFFFFFFFF for r in self.cpu.gprs]
                if info.address == 0x080204EA:
                    check(regs[1] == 0x080A69C0 and cstring(self.core, regs[1]) == b'%s'+b' '*36+b'\0',
                          'Native notice padding format differs')
                    self.notice_formats.append({'frame': self.core.frame_counter, 'phase': self.phase,
                        'format': hex(regs[1]), 'source': hex(regs[2]), 'source_hex': cstring(self.core, regs[2]).hex(),
                        'destination': hex(regs[0]), 'stack': hex(regs[13]), 'capacity': 256})
                elif info.address == 0x080204EE:
                    f = self.notice_formats[-1]
                    raw = cstring(self.core, int(f['destination'], 0))
                    check(raw == bytes.fromhex(f['source_hex'])[:-1]+b' '*36+b'\0', 'Native notice printf output differs')
                    f['output_hex'] = raw.hex()
                elif info.address == 0x080204FA:
                    f = self.notice_formats[-1]
                    check(regs[2] == int(f['destination'], 0), 'Native notice draw lost its formatter buffer')
                    self.pending_notice = {'format_serial': len(self.notice_formats)-1, 'address': regs[2],
                        'x': regs[0], 'y': regs[1], 'window': regs[3]}
                elif info.address == 0x0808CBA0 and self.pending_notice is not None:
                    p = self.pending_notice
                    check(regs[2] == p['address'] and regs[0] == p['x'] and regs[1] == p['y'], 'Notice draw context differs')
                    self.notice_draws.append({**p, 'draw_serial': len(self.ui_payloads)})
                    self.pending_notice = None
            super().entered(debugger, reason, info)
        except Exception as error:
            self.errors.append(str(error))
        finally:
            debugger.state = lib.DEBUGGER_RUNNING

    def report(self):
        return {**super().report(), 'notice_formats': self.notice_formats, 'notice_draws': self.notice_draws}


def check_ui(report, *, reproduce_old_notice=False):
    notices = report['notice_draws']
    ids = {d['draw_serial'] for d in notices}
    standard, repeats = ui_checks({**report, 'ui_payloads': [d for d in report['ui_payloads'] if d['serial'] not in ids]},
                                 ORIGINAL_ROM.read_bytes())
    font = FontZero(ORIGINAL_ROM.read_bytes())
    bitmap, _ = font.descriptors[font.glyph(' ')[0]]
    at = bitmap-0x08000000
    check(not any(font.original[at:at+72]), 'Native blank-fill glyph has visible ink')
    special = []
    for d in notices:
        f = report['notice_formats'][d['format_serial']]
        source = bytes.fromhex(f['source_hex'])[:-1].decode('ascii')
        padded = source+' '*36
        gs, reobserved = distinct_glyph_observations([g for g in report['ui_positions'] if g['draw_serial'] == d['draw_serial']])
        check([g['code'] for g in gs] == [font.glyph(c)[0] for c in padded], 'Notice glyph sequence differs')
        check(all(g['font'] == 0 and g['spacing'] == 0 and g['window_width'] == 128
                  and g['window_height'] == 16 for g in gs), 'Notice window/font differs')
        foreground, blanks = gs[:len(source)], gs[len(source):]
        for i, g in enumerate(blanks):
            check(g['code'] == font.glyph(' ')[0] and g['y'] == 2 and
                  g['x'] == foreground[-1]['x']+foreground[-1]['advance']+i*font.glyph(' ')[1],
                  'Native transparent padding progression differs')
        if reproduce_old_notice and source == 'You are not carrying any items.':
            check(max(g['x']+g['advance'] for g in foreground) == 157, 'Old clipping not reproduced')
            metrics = {'known_clipped_source': True, 'source_width': 157}
        else:
            metrics = command_ink_check(foreground, source, font)
        special.append({'serial': d['draw_serial'], 'text': source, 'native_padding_spaces': 36,
            'padding_is_transparent': True, 'reobservations': reobserved, **metrics})
    return sorted(standard+special, key=lambda x: x['serial']), repeats


def route(data, variant):
    proof = ROOT/'build/completion/roundtrip/research/empty-probe'
    state = (proof/'before.state').read_bytes()
    initial = (ROOT/'build/completion/roundtrip/creation/both-logs.sav').read_bytes()
    inputs = load_json(ROOT/'build/completion/roundtrip/exploration/readers.json')['inputs'][87:89]
    folder = b.OUTPUT/'verification'/variant
    with Session(data, folder, initial) as s:
        check(s.core.load_raw_state(state), 'Cannot restore natural notice checkpoint')
        t = NoticeTrace(s.core, data, [], [0x08000000+b.WORD])
        try:
            for i, a in enumerate(inputs):
                t.phase = f'input-{i}'
                k = getattr(s.core, 'KEY_'+a['key']); s.core.set_keys(k); t.frames(a['hold'])
                s.core.clear_keys(k); t.frames(a['released']); check(s.core.frame_counter == a['end_frame'], 'Notice timing differs')
                s.capture(t.phase)
            screen = s.capture('notice')
            report = t.report()
            check(not t.errors and len(report['notice_formats']) == len(report['notice_draws']) == 1, 'Notice missing or trace error')
            expected = 'No items.' if variant == 'english' else 'You are not carrying any items.'
            check(bytes.fromhex(report['notice_formats'][0]['source_hex']) == expected.encode()+b'\0', 'Wrong native notice selected')
            target = int.from_bytes(data[b.WORD:b.WORD+4], 'little')
            check(int(report['notice_formats'][0]['source'], 0) == target, 'Notice pointer/formatter ownership differs')
            check(report['source_reads'] and all(int(r['address'], 0) == 0x08000000+b.WORD for r in report['source_reads']), 'Owned source word not observed')
            checks, repeats = check_ui(report, reproduce_old_notice=variant == 'baseline')
            report.update(rom_sha256=digest(data), initial_state_sha256=digest(state), initial_save_sha256=digest(initial),
                inputs=inputs, checks=checks, duplicate_draws=repeats, scope='Normal B/A input at the naturally reached empty-inventory checkpoint. Exact getter/printf/draw ownership and original transparent padding; no injected inventory or scenario values.')
            save(folder/'trace.json', report)
        finally:
            t.close()
    check(s.disk_save == initial, 'Popup changed cartridge save')
    return report, screen


def verify():
    mgba.log.silence()
    data = (b.OUTPUT/'torneko3-inventory-notice-english.gba').read_bytes()
    baseline = b.BASELINE.read_bytes()
    build = load_json(b.OUTPUT/'english-build.json'); prior = load_json(b.BASELINE.parent/'english-build.json')
    check(build['rom_sha256'] == digest(data) and build['previous_rom_sha256'] == digest(baseline), 'Notice build hash differs')
    check(build['catalog_sha256'] == digest(b.CATALOG.read_bytes()), 'Notice catalog changed')
    check(build['ledger']['allocations'][:-1] == prior['ledger']['allocations'], 'Earlier allocation metadata changed')
    expected = bytearray(baseline); a = build['ledger']['allocations'][-1]
    expected[b.WORD:b.WORD+4] = data[b.WORD:b.WORD+4]
    expected[a['offset']:a['offset']+a['bytes']] = b'No items.\0'
    check(bytes(expected) == data, 'Unrelated ROM bytes changed')
    for p in prior['ledger']['patches']:
        now = next(q for q in build['ledger']['patches'] if q['offset'] == p['offset'])
        check((now['supersedes'] if p['offset'] == b.WORD else now) == p, 'Prior patch ownership changed')
    old, left = route(baseline, 'baseline'); new, right = route(data, 'english')
    bounds = ImageChops.difference(left, right).getbbox()
    check(bounds is not None and bounds[0] >= 56 and bounds[1] >= 72 and bounds[2] <= 184 and bounds[3] <= 88,
          'Popup changed pixels outside its bitmap')
    result = {'status': 'natural_inventory_notice_passed', 'rom_sha256': digest(data),
        'source_sha256': digest(ORIGINAL_ROM.read_bytes()), 'baseline_sha256': digest(baseline),
        'harness_sha256': digest(Path(__file__).read_bytes()), 'builder_sha256': digest(Path(b.__file__).read_bytes()),
        'catalog_sha256': digest(b.CATALOG.read_bytes()), 'new_allocation': a,
        'only_owned_pointer_and_new_payload_changed': True, 'prior_ownership_preserved': True,
        'pixel_difference_bounds': bounds, 'native_padding_preserved': True,
        'reports': {v: digest((b.OUTPUT/'verification'/v/'trace.json').read_bytes()) for v in ('baseline', 'english')},
        'scope': 'One existing source receives a popup-specific display form; a separate full paged copy remains unchanged. Broader dungeon/save roundtrip acceptance is recorded separately.'}
    save(b.OUTPUT/'component-checkpoint.json', result)
    print(result['status'], bounds, flush=True)


if __name__ == '__main__':
    verify()
