"""Accept complete item composition fixtures and explain every ROM write."""
from pathlib import Path
from PIL import Image, ImageChops
from tools import verify_item_display as v
from tools.build_first_label import ORIGINAL_ROM, digest
from tools.translation_pipeline import load_json, check
from tools.verify_items import write_json


def summarize():
    out = v.b.OUTPUT; original = ORIGINAL_ROM.read_bytes(); baseline = v.BASELINE.read_bytes()
    catalog = load_json(out/'catalog.json')
    check((out/'catalog.json').read_bytes() == v.b.CATALOG.read_bytes(), 'Item-display catalog changed')
    harness = digest((out/'verify_item_display.py').read_bytes())
    check(harness == digest(Path(v.__file__).read_bytes()), 'Item-display frozen harness differs')
    prior = load_json(v.BASELINE.parent/'english-build.json')['ledger']
    prior_end = max(a['offset']+a['bytes'] for a in prior['allocations']); proofs = {}; reports = {}
    expected = v.scenarios(original)
    for variant in ('english', 'japanese', 'baseline'):
        path = out/'verification'/variant/'verification.json'; r = load_json(path)
        data = baseline if variant == 'baseline' else (out/f'torneko3-item-display-{variant}.gba').read_bytes()
        check(r['rom_sha256'] == digest(data) and r['source_sha256'] == digest(original), 'Item-display proof ROM differs')
        check(r['catalog_sha256'] == digest((out/'catalog.json').read_bytes()) and r['harness_sha256'] == harness, 'Item-display proof inputs differ')
        check(r['fixture_sha256'] == digest(v.STATE.read_bytes()) and r['unknown_helper_sha256'] == digest(Path(v.unknown.__file__).read_bytes()), 'Item-display fixture/helper differs')
        check(not r['limited'] and [c['case'] for c in r['cases']] == expected, 'Incomplete item composition cases')
        check([c['id'] for c in r['previews']] == [e['id'] for e in catalog['entries']], 'Incomplete item resource previews')
        check(all(c['record_and_options_intact'] for c in r['cases']), 'Item source-record evidence missing')
        all_cases = r['cases']+r['previews']
        check(all(c['guards_intact'] for c in all_cases), 'Item output-guard evidence missing')
        check(bytes.fromhex(r['cold_category_table_hex']) == data[v.b.TABLE:v.b.TABLE_END] and r['pointer_words_checked'] == 21, 'Item startup/owner evidence differs')
        check(r['screens'] == [s for c in all_cases for s in c['screens']] and len(set(r['screens'])) == len(r['screens']), 'Item screenshot inventory differs')
        check(all((path.parent/s).is_file() for s in r['screens']), 'Item screenshot missing')
        if variant == 'english':
            check(all(c['checks'] and all(c['checks']) for c in all_cases), 'Item English glyph evidence missing')
            check(all(not c['has_price'] or c['left_advance_right'] <= 130 for c in all_cases), 'Item price-column evidence fails')
        if variant != 'baseline':
            report = load_json(out/f'{variant}-build.json')
            check(report['previous_rom_sha256'] == digest(baseline) and report['catalog_sha256'] == digest((out/'catalog.json').read_bytes()), 'Item build inputs differ')
            ledger = report['ledger']; rebuilt = bytearray(original+b'\xff'*(len(data)-len(original)))
            for a in ledger['allocations']:
                at = a['offset']; raw = data[at:at+a['bytes']]; check(digest(raw) == a['sha256'], 'Item allocation differs'); rebuilt[at:at+len(raw)] = raw
            for p in ledger['patches']:
                at = p['offset']; before = bytes.fromhex(p['before']); after = bytes.fromhex(p['after'])
                check(rebuilt[at:at+len(before)] == before, 'Item patch source differs'); rebuilt[at:at+len(after)] = after
            check(bytes(rebuilt) == data and data[0x1000000:prior_end] == baseline[0x1000000:prior_end], 'Unexplained item-display writes')
            for p in prior['patches']:
                at = p['offset']; after = bytes.fromhex(p['after']); check(data[at:at+len(after)] == after, 'Earlier component patch changed')
            for s in ledger['protected_sources']:
                check(data[s['start']:s['end_exclusive']] == original[s['start']:s['end_exclusive']], 'Protected Japanese source changed')
        proofs[variant] = {'rom_sha256': digest(data), 'report_sha256': digest(path.read_bytes()), 'native_cases': len(r['cases']), 'previews': len(r['previews']), 'screens': len(r['screens'])}; reports[variant] = r
    a, z = reports['japanese'], reports['baseline']; check(a['screens'] == z['screens'], 'Item Japanese screen sets differ')
    check([c['formatted_hex'] for c in a['cases']+a['previews']] == [c['formatted_hex'] for c in z['cases']+z['previews']], 'Japanese item composition differs')
    for name in a['screens']:
        with Image.open(out/'verification/japanese'/name) as x, Image.open(out/'verification/baseline'/name) as y:
            check(ImageChops.difference(x.convert('RGB'), y.convert('RGB')).getbbox() is None, 'Item Japanese pixels differ '+name)
    result = {'status': 'item_display_component_native_checks_passed', 'sources': 20, 'pointer_words': 21,
        'native_composition_cases': len(expected), 'resource_previews': 20, 'english_screens': len(reports['english']['screens']),
        'japanese_pixel_pairs': len(a['screens']), 'proofs': proofs, 'complete_images_reconstructed_from_ledgers': True,
        'previous_patches_and_appended_bytes_preserved': True, 'scope': a['scope']}
    write_json(out/'component-checkpoint.json', result); print(result['status'], len(a['screens']), 'Japanese pixel pairs', flush=True)


if __name__ == '__main__':
    summarize()
