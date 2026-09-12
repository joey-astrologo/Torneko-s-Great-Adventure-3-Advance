"""Accept complete result-screen, relocation and native profile-save evidence."""
from pathlib import Path
from PIL import Image, ImageChops
from tools import verify_adventure_results as v
from tools import verify_result_saves as saves
from tools.build_first_label import ORIGINAL_ROM, digest
from tools.translation_pipeline import load_json, check
from tools.verify_items import write_json


def summarize():
    out = v.b.OUTPUT
    original = ORIGINAL_ROM.read_bytes()
    baseline = v.BASELINE.read_bytes()
    catalog = load_json(out/'catalog.json')
    check((out/'catalog.json').read_bytes() == v.b.CATALOG.read_bytes(), 'Result catalog changed since build')
    prior = load_json(v.BASELINE.parent/'english-build.json')['ledger']
    prior_end = max(a['offset']+a['bytes'] for a in prior['allocations'])
    expected = {c['id']: c for c in v.scenarios(catalog)}
    proofs = {}
    reports = {}
    for variant in ('english', 'japanese', 'baseline'):
        data = baseline if variant == 'baseline' else (out/f'torneko3-adventure-results-{variant}.gba').read_bytes()
        proofs[variant] = {'rom_sha256': digest(data)}
        for kind, directory, harness in (
            ('main', out/'verification'/variant, 'verify_adventure_results.py'),
            ('ending', out/'verification/ending'/variant, 'verify_result_ending.py'),
        ):
            path = directory/'verification.json'
            r = load_json(path)
            check(not r['limited'] and r['rom_sha256'] == digest(data) and r['source_sha256'] == digest(original), 'Result proof ROM mismatch')
            check(r['catalog_sha256'] == digest((out/'catalog.json').read_bytes()) and r['fixture_sha256'] == digest(v.STATE.read_bytes()), 'Result proof input mismatch')
            check(r['harness_sha256'] == digest((out/harness).read_bytes()), 'Result harness mismatch')
            cases = r['details'] if kind == 'main' else r['cases']
            check(len(cases) == len(expected) == 202 and {c['id'] for c in cases} == set(expected), 'Missing result causes/protagonists')
            for c in cases:
                check(c['source_id'] == expected[c['id']]['source_id'] and all(c['parameters'][k] == value for k, value in expected[c['id']]['parameters'].items()), 'Result fixture identity mismatch')
                check(c['font_tables_intact'], 'Result font-state proof missing')
            if kind == 'main':
                check(len(r['lists']) == 606 and {(c['id'], c['mode']) for c in r['lists']} == {(key, mode) for key in expected for mode in (0, 1, 2)}, 'Missing list mode')
                check(all(c['guards_intact'] and c['record_unchanged'] for c in r['lists']) and all(c['record_unchanged'] for c in cases), 'Result record/guard proof missing')
                count = 750 if variant == 'english' else 84
                check(len(r['stress']) == count and {c['id'] for c in r['stress']} == {f'stress-{i:03}' for i in range(count)}, 'Incomplete result boundary cases')
                check(all(c['font_tables_intact'] and c['record_unchanged'] for c in r['stress']), 'Boundary record/font proof missing')
                if variant == 'english':
                    stress = r['stress']
                    check({c['parameters']['actor'] for c in stress[84:284]} == set(range(200)), 'Missing species boundary')
                    check({c['parameters']['item'] for c in stress[284:654]} == set(range(370)), 'Missing item boundary')
                all_cases = cases+r['lists']+r['stress']
            else:
                check(r['context_helper_sha256'] == digest((out/'verify_result_saves.py').read_bytes()), 'Ending context helper mismatch')
                check(len(r['extra_cases']) == 30 and len(r['menus']) == 4, 'Incomplete ending/category cases')
                check({c['mode'] for c in r['menus']} == {'all', 'empty', 'invalid', 'campaign_label_only'}, 'Category fixture mismatch')
                all_cases = cases+r['extra_cases']+r['menus']
            check(r['screens'] == [s for c in all_cases for s in c['screens']] and len(set(r['screens'])) == len(r['screens']), 'Incomplete or duplicate result screenshots')
            check(all((directory/name).is_file() for name in r['screens']), 'Missing result screenshot')
            if variant == 'english':
                check(all(c['checks'] for c in all_cases), 'Missing English glyph/layout proof')
            reports[kind, variant] = r
            proofs[variant][kind] = {'report_sha256': digest(path.read_bytes()), 'screens': len(r['screens'])}
        if variant != 'baseline':
            report = load_json(out/f'{variant}-build.json')
            check(report['previous_rom_sha256'] == digest(baseline) and report['catalog_sha256'] == digest((out/'catalog.json').read_bytes()), 'Result build inputs differ')
            ledger = report['ledger']
            rebuilt = bytearray(original+b'\xff'*(len(data)-len(original)))
            for a in ledger['allocations']:
                at = a['offset']; raw = data[at:at+a['bytes']]
                check(digest(raw) == a['sha256'], 'Result allocation differs')
                rebuilt[at:at+len(raw)] = raw
            for p in ledger['patches']:
                at = p['offset']; before = bytes.fromhex(p['before']); after = bytes.fromhex(p['after'])
                check(rebuilt[at:at+len(before)] == before, 'Result original patch bytes differ')
                rebuilt[at:at+len(after)] = after
            check(bytes(rebuilt) == data and data[0x1000000:prior_end] == baseline[0x1000000:prior_end], 'Unexplained result ROM changes')
            for p in prior['patches']:
                at = p['offset']; after = bytes.fromhex(p['after'])
                check(data[at:at+len(after)] == after, 'Earlier component patch changed')
            for s in ledger['protected_sources']:
                check(data[s['start']:s['end_exclusive']] == original[s['start']:s['end_exclusive']], 'Protected Japanese source changed')
    pairs = {}
    for kind, subdir in (('main', 'verification'), ('ending', 'verification/ending')):
        a, z = reports[kind, 'japanese'], reports[kind, 'baseline']
        check(a['screens'] == z['screens'], 'Japanese result screenshot sets differ')
        for name in a['screens']:
            with Image.open(out/subdir/'japanese'/name) as x, Image.open(out/subdir/'baseline'/name) as y:
                check(ImageChops.difference(x.convert('RGB'), y.convert('RGB')).getbbox() is None, 'Japanese result pixels differ: '+name)
        pairs[kind] = len(a['screens'])
    path = saves.OUTPUT/'verification.json'; saved = load_json(path)
    check(saved['status'] == 'native_result_profile_save_checks_passed' and saved['rom_sha256'] == proofs['english']['rom_sha256'], 'Result save proof ROM mismatch')
    check(saved['source_sha256'] == digest(original) and saved['fixture_sha256'] == digest(v.STATE.read_bytes()) and saved['harness_sha256'] == digest((out/'verify_result_saves.py').read_bytes()), 'Result save proof input mismatch')
    check(saved['input_save_sha256'] == digest(saves.INPUT.read_bytes()) and saved['output_save_sha256'] == digest((saves.OUTPUT/'profile.sav').read_bytes()), 'Result save file mismatch')
    check(len(saved['record_creation']) == 16 and {(c['pass'], c['category']) for c in saved['record_creation']} == {(p, c) for p in (1, 2) for c in range(8)}, 'Incomplete native score writes')
    check(all(c['whole_rows_shifted'] and c['other_categories_preserved'] for c in saved['record_creation']), 'Native score shift proof missing')
    check(saved['save_bytes'] == 65536 and saved['profile_bytes'] == 8108 and saved['native_sector_copy_bytes'] == 8192, 'Native save sizes differ')
    check(all(saved[k] for k in ('native_checksum_and_sector_roundtrip', 'cold_core_profile_identical', 'adventure_log_sectors_unchanged')), 'Native persistence proof missing')
    check(len(saved['adventure_logs']) == 2 and {c['slot'] for c in saved['adventure_logs']} == {1, 2} and all(c['cold_load_passed'] and c['seven_character_name'] == 'Torneko' for c in saved['adventure_logs']), 'Missing seven-character Adventure Log load')
    result = {'status': 'adventure_results_component_native_checks_passed', 'resources': 185, 'inventory_sources': 181, 'text_pointer_words': 284,
        'english_result_cases': 1558, 'english_ending_category_cases': 236, 'japanese_pixel_pairs': pairs,
        'native_record_writes': 16, 'native_profile_flash_roundtrip': True, 'seven_character_adventure_logs': 2,
        'complete_images_reconstructed_from_ledgers': True, 'previous_patches_and_appended_bytes_preserved': True,
        'proofs': proofs, 'save_report_sha256': digest(path.read_bytes()), 'summarizer_sha256': digest(Path(__file__).read_bytes()),
        'scope': 'Controlled native result/list/ending/category composition and record creation, original FLASH persistence and both Adventure Log cold loads. Natural dungeon outcomes, transition timing and achievement triggers remain separate. No ranking/name/save field expansion.'}
    write_json(out/'component-checkpoint.json', result)
    print(result['status'], pairs, flush=True)


if __name__ == '__main__':
    summarize()
