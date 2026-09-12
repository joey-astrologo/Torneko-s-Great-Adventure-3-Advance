"""Accept complete frontend pages, menu/summary fixtures and cold loads."""
import json
from pathlib import Path
from PIL import Image, ImageChops
from tools import verify_frontend_completion as v
from tools.build_first_label import ORIGINAL_ROM, digest
from tools.translation_pipeline import load_json, check
from tools.verify_items import write_json


def summarize():
    out = v.b.OUTPUT; original = ORIGINAL_ROM.read_bytes(); baseline = v.BASELINE.read_bytes()
    catalog = load_json(out/'catalog.json')
    check((out/'catalog.json').read_bytes() == v.b.CATALOG.read_bytes(), 'Frontend catalog changed')
    prior = load_json(v.BASELINE.parent/'english-build.json')['ledger']
    prior_end = max(a['offset']+a['bytes'] for a in prior['allocations']); proofs = {}; reports = {}
    for variant in ('english', 'japanese', 'baseline'):
        path = out/'verification'/variant/'verification.json'; r = load_json(path)
        data = baseline if variant == 'baseline' else (out/f'torneko3-frontend-completion-{variant}.gba').read_bytes()
        check(r['rom_sha256'] == digest(data) and r['source_sha256'] == digest(original), 'Frontend proof ROM mismatch')
        check(r['catalog_sha256'] == digest((out/'catalog.json').read_bytes()) and r['harness_sha256'] == digest((out/'verify_frontend_completion.py').read_bytes()), 'Frontend proof inputs differ')
        check(r['fixture_sha256'] == digest(v.STATE.read_bytes()) and r['page_helper_sha256'] == digest(Path(v.service.__file__).read_bytes()), 'Frontend fixture/helper differs')
        expected = {(e['id'], p) for e in catalog['entries'] for p in (('normal', 'stress') if variant == 'english' else ('normal',))}
        check(not r['limited'] and len(r['cases']) == len(expected) and {(c['id'], c['profile']) for c in r['cases']} == expected, 'Incomplete frontend source cases')
        check(all(c['guards_intact'] and (not c['pages'] or c['pages'] == len(c['screens'])) for c in r['cases']), 'Frontend page/guard evidence incomplete')
        check(len(r['menus']) == 3 and {(int(c['base'], 0), c['enabled']) for c in r['menus']} == {(0xC4CD0C, 0), (0xC4CD40, 0), (0xC4CD40, 1)}, 'Incomplete frontend menus')
        summaries = r['summaries']
        check(len(summaries) == 14 and {c['slot'] for c in summaries} == {1, 2}, 'Incomplete frontend summaries')
        parameters = [{json.dumps(c['parameters'], sort_keys=True) for c in summaries if c['slot'] == slot} for slot in (1, 2)]
        check(len(parameters[0]) == 7 and parameters[0] == parameters[1], 'Frontend summary variants differ')
        check(all(c['record_and_guards_intact'] and c['font_tables_intact'] for c in summaries), 'Frontend summary guard/font evidence incomplete')
        all_cases = r['cases']+r['menus']+summaries
        check(r['screens'] == [s for c in all_cases for s in c['screens']] and len(set(r['screens'])) == len(r['screens']), 'Frontend screenshot inventory differs')
        check(all((path.parent/s).is_file() for s in r['screens']), 'Frontend screenshot missing')
        if variant == 'english': check(all(c['checks'] and all(c['checks']) for c in all_cases), 'Frontend English glyph evidence missing')
        if variant != 'baseline':
            report = load_json(out/f'{variant}-build.json')
            check(report['previous_rom_sha256'] == digest(baseline) and report['catalog_sha256'] == digest((out/'catalog.json').read_bytes()), 'Frontend build inputs differ')
            ledger = report['ledger']; rebuilt = bytearray(original+b'\xff'*(len(data)-len(original)))
            for a in ledger['allocations']:
                at = a['offset']; raw = data[at:at+a['bytes']]; check(digest(raw) == a['sha256'], 'Frontend allocation differs'); rebuilt[at:at+len(raw)] = raw
            for p in ledger['patches']:
                at = p['offset']; before = bytes.fromhex(p['before']); after = bytes.fromhex(p['after']); check(rebuilt[at:at+len(before)] == before, 'Frontend patch source differs'); rebuilt[at:at+len(after)] = after
            check(bytes(rebuilt) == data and data[0x1000000:prior_end] == baseline[0x1000000:prior_end], 'Unexplained frontend image changes')
            for p in prior['patches']:
                at = p['offset']; after = bytes.fromhex(p['after']); check(data[at:at+len(after)] == after, 'Earlier frontend-base patch changed')
            for s in ledger['protected_sources']: check(data[s['start']:s['end_exclusive']] == original[s['start']:s['end_exclusive']], 'Protected Japanese source changed')
        proofs[variant] = {'rom_sha256': digest(data), 'report_sha256': digest(path.read_bytes()), 'cases': len(r['cases']), 'screens': len(r['screens'])}; reports[variant] = r
    a, z = reports['japanese'], reports['baseline']; check(a['screens'] == z['screens'], 'Frontend Japanese screen sets differ')
    for name in a['screens']:
        with Image.open(out/'verification/japanese'/name) as x, Image.open(out/'verification/baseline'/name) as y:
            check(ImageChops.difference(x.convert('RGB'), y.convert('RGB')).getbbox() is None, 'Frontend Japanese pixels differ '+name)
    path = out/'verification/cold-loads.json'; loads = load_json(path)
    check(loads['rom_sha256'] == proofs['english']['rom_sha256'] and loads['save_sha256'] == digest(v.SAVEPATH.read_bytes()), 'Frontend cold-load input mismatch')
    check(loads['harness_sha256'] == digest((out/'verify_frontend_completion.py').read_bytes()) and loads['name_helper_sha256'] == digest(Path(v.names.__file__).read_bytes()), 'Frontend cold-load harness mismatch')
    check(len(loads['loads']) == 2 and {c['slot'] for c in loads['loads']} == {1, 2} and all(c['passed'] and c['seven_character_name'] == 'Torneko' for c in loads['loads']), 'Missing frontend Adventure Log load')
    result = {'status': 'frontend_component_native_checks_passed', 'sources': 48, 'pointer_words': 48,
        'english_source_cases': 96, 'english_screens': len(reports['english']['screens']), 'native_menus': 3, 'native_summary_cases': 14,
        'japanese_pixel_pairs': len(a['screens']), 'seven_character_adventure_logs': 2, 'proofs': proofs,
        'cold_load_report_sha256': digest(path.read_bytes()), 'complete_images_reconstructed_from_ledgers': True,
        'previous_patches_and_appended_bytes_preserved': True, 'scope': a['scope']}
    write_json(out/'component-checkpoint.json', result); print(result['status'], len(a['screens']), 'Japanese pixel pairs', flush=True)


if __name__ == '__main__':
    summarize()
