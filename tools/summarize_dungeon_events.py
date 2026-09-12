"""Accept complete native dungeon-event pages, readers and ledger reconstruction."""
from pathlib import Path
from PIL import Image, ImageChops
from tools import verify_dungeon_events as v
from tools.build_first_label import ORIGINAL_ROM, digest
from tools.translation_pipeline import load_json, check
from tools.verify_items import write_json


def summarize():
    out = v.b.OUTPUT; original = ORIGINAL_ROM.read_bytes(); baseline = v.BASELINE.read_bytes(); catalog = load_json(out/'catalog.json')
    check((out/'catalog.json').read_bytes() == v.b.CATALOG.read_bytes(), 'Dungeon event catalog changed')
    harness = digest((out/'verify_dungeon_events.py').read_bytes()); check(harness == digest(Path(v.__file__).read_bytes()), 'Dungeon event harness changed')
    prior = load_json(v.BASELINE.parent/'english-build.json')['ledger']; end = max(a['offset']+a['bytes'] for a in prior['allocations']); proofs = {}; reports = {}
    for variant in ('english', 'japanese', 'baseline'):
        path = out/'verification'/variant/'verification.json'; r = load_json(path)
        data = baseline if variant == 'baseline' else (out/f'torneko3-dungeon-events-{variant}.gba').read_bytes()
        check(r['rom_sha256'] == digest(data) and r['source_sha256'] == digest(original), 'Dungeon event proof ROM differs')
        check(r['catalog_sha256'] == digest((out/'catalog.json').read_bytes()) and r['harness_sha256'] == harness, 'Dungeon event proof inputs differ')
        check(r['fixture_sha256'] == digest(v.STATE.read_bytes()) and r['page_helper_sha256'] == digest(Path(v.service.__file__).read_bytes()), 'Dungeon event fixture/helper differs')
        expected = {(e['id'], p) for e in catalog['entries'] for p in (('normal', 'stress') if variant == 'english' else ('normal',))}
        check(not r['limited'] and len(r['cases']) == len(expected) and {(c['id'], c['profile']) for c in r['cases']} == expected, 'Incomplete dungeon event source cases')
        check(all(c['guards_intact'] and (not c['pages'] or c['pages'] == len(c['screens'])) for c in r['cases']), 'Dungeon event guard/page evidence incomplete')
        expected_words = {int(p['offset'], 0) for e in catalog['entries'] for p in e['pointer_owners']}
        check(len(r['pointer_words']) == 82 and {int(w['word'], 0) for w in r['pointer_words']} == expected_words, 'Incomplete dungeon event pointer evidence')
        check(len(r['lookups']) == 31 and {c['row'] for c in r['lookups']} == set(range(31)), 'Incomplete dungeon tutorial lookups')
        check(bytes.fromhex(r['cold_abort_table_hex']) == data[v.b.CACHE:v.b.CACHE_END], 'Dungeon event cold cache differs')
        selectors = r['selectors']; boss = [c for c in selectors if c['kind'] == 'boss']; abort = [c for c in selectors if c['kind'] == 'arena_abort']
        check(len(selectors) == 6 and {(c['hero'], c['seen']) for c in boss} == {(h, s) for h in (0, 1) for s in (0, 1)}, 'Incomplete boss selector evidence')
        check(all(c['actual'] == c['expected'] for c in boss) and len(abort) == 2 and {c['hero'] for c in abort} == {0, 1}, 'Dungeon event selector mismatch')
        check(len(r['menus']) == 1 and r['menus'][0]['original_menu_fields_preserved'], 'Missing dungeon pause menu')
        all_cases = r['cases']+r['menus']
        check(r['screens'] == [s for c in all_cases for s in c['screens']] and len(set(r['screens'])) == len(r['screens']), 'Dungeon event screenshot inventory differs')
        check(all((path.parent/s).is_file() for s in r['screens']), 'Dungeon event screenshot missing')
        if variant == 'english': check(all(c['checks'] and all(c['checks']) for c in all_cases), 'Dungeon event English glyph evidence missing')
        if variant != 'baseline':
            report = load_json(out/f'{variant}-build.json'); check(report['previous_rom_sha256'] == digest(baseline) and report['catalog_sha256'] == r['catalog_sha256'], 'Dungeon event build inputs differ')
            ledger = report['ledger']; rebuilt = bytearray(original+b'\xff'*(len(data)-len(original)))
            for a in ledger['allocations']:
                at = a['offset']; raw = data[at:at+a['bytes']]; check(digest(raw) == a['sha256'], 'Dungeon event allocation differs'); rebuilt[at:at+len(raw)] = raw
            for p in ledger['patches']:
                at = p['offset']; before = bytes.fromhex(p['before']); after = bytes.fromhex(p['after']); check(rebuilt[at:at+len(before)] == before, 'Dungeon event patch source differs'); rebuilt[at:at+len(after)] = after
            check(bytes(rebuilt) == data and data[0x1000000:end] == baseline[0x1000000:end], 'Unexplained dungeon event image writes')
            for p in prior['patches']:
                at = p['offset']; after = bytes.fromhex(p['after']); check(data[at:at+len(after)] == after, 'Earlier dungeon-event-base patch changed')
            for s in ledger['protected_sources']: check(data[s['start']:s['end_exclusive']] == original[s['start']:s['end_exclusive']], 'Protected Japanese source changed')
        proofs[variant] = {'rom_sha256': digest(data), 'report_sha256': digest(path.read_bytes()), 'cases': len(r['cases']), 'screens': len(r['screens'])}; reports[variant] = r
    a, z = reports['japanese'], reports['baseline']; check(a['screens'] == z['screens'], 'Dungeon event Japanese screenshot sets differ')
    check([c['formatted_hex'] for c in a['cases']] == [c['formatted_hex'] for c in z['cases']], 'Dungeon event Japanese formatting differs')
    for name in a['screens']:
        with Image.open(out/'verification/japanese'/name) as x, Image.open(out/'verification/baseline'/name) as y:
            check(ImageChops.difference(x.convert('RGB'), y.convert('RGB')).getbbox() is None, 'Dungeon event Japanese pixels differ '+name)
    result = {'status': 'dungeon_events_component_native_checks_passed', 'sources': 63, 'pointer_words': 82,
        'english_source_cases': 126, 'english_screens': len(reports['english']['screens']), 'native_menus': 1, 'native_tutorial_lookups': 31, 'native_selector_cases': 6,
        'japanese_pixel_pairs': len(a['screens']), 'proofs': proofs, 'complete_images_reconstructed_from_ledgers': True,
        'previous_patches_and_appended_bytes_preserved': True, 'scope': a['scope']}
    write_json(out/'component-checkpoint.json', result); print(result['status'], len(a['screens']), 'Japanese pixel pairs', flush=True)


if __name__ == '__main__': summarize()
