"""Cold-boot title labels and navigate the native score menus in both directions."""
import json
from pathlib import Path
import mgba.log
from mgba._pylib import ffi
from PIL import Image, ImageChops
from tools import build_ui_polish as b
from tools.build_first_label import ROOT, ORIGINAL_ROM, digest
from tools.translation_pipeline import check, load_json, atomic_write
from tools.verify_expansion import Session
from tools.verify_natural_cave import CaveTrace
from tools.verify_text_polish import ui_checks
from tools.verify_result_runtime import map_errors, ink_pixels
from tools.verify_result_saves import OUTPUT as SCORES
from tools.trace_story_provenance import SAVE


def save(path, value):
    atomic_write(path, (json.dumps(value, ensure_ascii=False, indent=2)+'\n').encode())


def route(data, variant, mode):
    initial = (SCORES/'profile.sav').read_bytes() if mode == 'scores' else SAVE.read_bytes() if mode == 'single-log' else bytes([255])*65536
    folder = b.OUTPUT/'verification'/variant/mode
    with Session(data, folder, initial) as s:
        t = CaveTrace(s.core, data, [], [0x08000000+b.WORD])
        try:
            t.frames(600); t.phase = 'title'; s.press('START', 240, t); s.capture('title')
            detail = None
            if mode == 'scores':
                for name, key, wait in [('down-1', 'DOWN', 30), ('down-2', 'DOWN', 30),
                    ('categories', 'A', 240), ('list', 'A', 240), ('detail', 'A', 240),
                    ('back-list', 'B', 120), ('back-categories', 'B', 120), ('back-title', 'B', 120)]:
                    t.phase = name; s.press(key, wait, t); screen = s.capture(name)
                    if name == 'detail':
                        c = s.core
                        bitmap = bytes(c.memory[0x02035E1C:0x0203977C])
                        rawmap = bytes(c.memory[0x02034DDC:0x020355DC])
                        check(bitmap == bytes(c.memory[0x06000040:0x060039A0]), 'Score bitmap differs')
                        check(rawmap == bytes(c.memory[0x06006000:0x06006800]), 'Score tilemap differs')
                        check(not map_errors(rawmap), 'Score detail map is not 27 by 17')
                        detail = ink_pixels(c, screen)
                        check(detail['white_ink_pixels'] > 500 and detail['mismatched_white_ink_pixels'] == 0,
                              'Score detail visible text differs')
            report = t.report()
            check(not t.errors and not report['versions'], 'Unexpected trace error or story transition')
            if variant == 'baseline':
                # Reproduce this one known clipping defect; all other observed
                # text must pass the normal glyph/layout checks.
                clipped = [d for d in report['ui_payloads'] if bytes.fromhex(d['raw_hex']).split(b'\0')[0] == b'Adventure records']
                check(len(clipped) == (2 if mode == 'scores' else 0), 'Baseline profile-dependent label differs')
                for d in clipped:
                    gs = [g for g in report['ui_positions'] if g['draw_serial'] == d['serial']]
                    check(gs and all(g['window_width'] == 80 and g['window_origin'] == [24, 16] for g in gs), 'Title window differs')
                    check(max(g['x']+g['advance'] for g in gs) > 80, 'Baseline clipping not reproduced')
                filtered = {**report, 'ui_payloads': [d for d in report['ui_payloads'] if d not in clipped]}
                checks, repeats = ui_checks(filtered, ORIGINAL_ROM.read_bytes())
            else:
                checks, repeats = ui_checks(report, ORIGINAL_ROM.read_bytes())
                check(sum(c['text'] == 'Records' for c in checks) == (2 if mode == 'scores' else 0), 'Records profile-dependent display differs')
            pointer_reads = report['source_reads']
            check(bool(pointer_reads) == (mode == 'scores') and
                  all(int(r['address'], 0) == 0x08000000+b.WORD for r in pointer_reads), 'Menu ownership trace differs')
            report.update(checks=checks, duplicate_draws=repeats, detail_pixels=detail,
                inputs=s.frames_recorded, rom_sha256=digest(data), initial_save_sha256=digest(initial),
                scope='Cold boot with a disposable empty, single-log or native-created test score-profile save; normal menu buttons only. Controlled score values are not a natural dungeon outcome.')
            (folder/'final.state').write_bytes(bytes(ffi.buffer(s.core.save_raw_state())))
        finally:
            t.close()
    check(s.disk_save == initial, 'Menu navigation changed cartridge save')
    save(folder/'trace.json', report)
    print(variant, mode, len(checks), 'accepted draws', flush=True)
    return report


def verify():
    mgba.log.silence()
    baseline = b.BASELINE.read_bytes()
    data = (b.OUTPUT/'torneko3-ui-polish-english.gba').read_bytes()
    build = load_json(b.OUTPUT/'english-build.json')
    prior = load_json(b.BASELINE.parent/'english-build.json')
    check(build['rom_sha256'] == digest(data) and build['previous_rom_sha256'] == digest(baseline), 'Build hashes differ')
    check(build['catalog_sha256'] == digest(b.CATALOG.read_bytes()), 'Catalog changed')
    check(build['ledger']['allocations'][:-1] == prior['ledger']['allocations'], 'Earlier allocation ledger changed')
    newest = build['ledger']['allocations'][-1]
    expected = bytearray(baseline)
    expected[b.WORD:b.WORD+4] = data[b.WORD:b.WORD+4]
    expected[newest['offset']:newest['offset']+newest['bytes']] = b'Records\0'
    check(bytes(expected) == data, 'Unrelated ROM bytes changed')
    patch = next(p for p in build['ledger']['patches'] if p['offset'] == b.WORD)
    check(patch['supersedes'] == next(p for p in prior['ledger']['patches'] if p['offset'] == b.WORD), 'Ownership history differs')
    for p in prior['ledger']['patches']:
        if p['offset'] != b.WORD:
            check(p in build['ledger']['patches'], 'Unrelated patch metadata differs')
    results = {}
    for mode in ('scores', 'single-log', 'empty'):
        old = route(baseline, 'baseline', mode)
        new = route(data, 'english', mode)
        a = [bytes.fromhex(d['raw_hex']).split(b'\0')[0] for d in old['ui_payloads']]
        z = [bytes.fromhex(d['raw_hex']).split(b'\0')[0] for d in new['ui_payloads']]
        check([b'Records' if x == b'Adventure records' else x for x in a] == z, 'Unrelated menu text changed')
        check(old['inputs'] == new['inputs'], 'Navigation frame timing differs')
        same = []
        for p in sorted((b.OUTPUT/'verification/english'/mode).glob('*.png')):
            left = Image.open(b.OUTPUT/'verification/baseline'/mode/p.name).convert('RGB')
            right = Image.open(p).convert('RGB')
            bounds = ImageChops.difference(left, right).getbbox()
            if bounds is None:
                same.append(p.name)
            else:
                check(bounds[0] >= 24 and bounds[1] >= 16 and bounds[2] <= 104 and bounds[3] <= 64,
                      'Difference outside title label area')
        results[mode] = {'english_draws': len(new['checks']), 'unchanged_screens': same,
            'detail_pixels': new['detail_pixels'], 'cartridge_save_unchanged': True,
            'reports': {v: digest((b.OUTPUT/'verification'/v/mode/'trace.json').read_bytes()) for v in ('baseline', 'english')}}
    result = {'status': 'native_title_menu_display_passed', 'rom_sha256': digest(data),
        'source_sha256': digest(ORIGINAL_ROM.read_bytes()), 'baseline_sha256': digest(baseline),
        'builder_sha256': digest(Path(b.__file__).read_bytes()), 'harness_sha256': digest(Path(__file__).read_bytes()),
        'catalog_sha256': digest(b.CATALOG.read_bytes()), 'prior_allocations_preserved': True,
        'only_owned_pointer_and_new_payload_changed': True, 'new_allocation': newest, 'cases': results,
        'scope': 'One compact title-menu display form. Three cold-boot save contexts; normal score menu/list/detail/back navigation on a controlled native-created score profile. No new master source or save-layout change.'}
    save(b.OUTPUT/'component-checkpoint.json', result)
    print(result['status'], flush=True)


if __name__ == '__main__':
    verify()
