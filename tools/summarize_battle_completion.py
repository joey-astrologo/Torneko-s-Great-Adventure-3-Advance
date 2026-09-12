"""Accept complete battle queue/history, paged dialogue and native table checks."""
from pathlib import Path
from PIL import Image, ImageChops
from tools import verify_battle_completion as v
from tools.build_first_label import ORIGINAL_ROM, digest
from tools.translation_pipeline import load_json, check
from tools.verify_items import write_json


def summarize():
    out = v.b.OUTPUT; original = ORIGINAL_ROM.read_bytes(); baseline = v.BASELINE.read_bytes(); catalog = load_json(out/'catalog.json')
    check((out/'catalog.json').read_bytes() == v.b.CATALOG.read_bytes(), 'Battle catalog changed')
    harness = digest((out/'verify_battle_completion.py').read_bytes()); check(harness == digest(Path(v.__file__).read_bytes()), 'Battle harness changed')
    prior = load_json(v.BASELINE.parent/'english-build.json')['ledger']; end = max(a['offset']+a['bytes'] for a in prior['allocations']); proofs = {}; reports = {}
    expected_selections = ({('obstruction', hex(base), row) for base in (0xDB0FC, 0x9B660) for row in range(3)} |
        {('wind', None, row) for row in range(4)} | {('shop', group, row) for group in (0, 1) for row in range(4)})
    for variant in ('english', 'japanese', 'baseline'):
        path = out/'verification'/variant/'verification.json'; r = load_json(path)
        data = baseline if variant == 'baseline' else (out/f'torneko3-battle-completion-{variant}.gba').read_bytes()
        check(r['rom_sha256'] == digest(data) and r['source_sha256'] == digest(original), 'Battle proof ROM differs')
        check(r['catalog_sha256'] == digest((out/'catalog.json').read_bytes()) and r['harness_sha256'] == harness, 'Battle proof inputs differ')
        check(r['fixture_sha256'] == digest(v.STATE.read_bytes()) and r['page_helper_sha256'] == digest(Path(v.service.__file__).read_bytes()) and r['queue_helper_sha256'] == digest(Path(v.queue.__file__).read_bytes()), 'Battle fixture/helper differs')
        expected = {(e['id'], p) for e in catalog['entries'] for p in (('normal', 'stress', 'narrow') if variant == 'english' and e['family'] == 'queue' else ('normal', 'stress') if variant == 'english' else ('normal',))}
        check(not r['limited'] and len(r['cases']) == len(expected) and {(c['id'], c['profile']) for c in r['cases']} == expected, 'Incomplete battle source cases')
        check(all(c['guards_intact'] and c['slots_intact'] for c in r['cases']), 'Battle guard/slot evidence incomplete')
        for case in r['cases']:
            if case['family'] == 'message': check(case['pages'] == len(case['screens']) and case['pages'] > 0, 'Battle dialogue pages missing')
            else:
                q = case['queue']; check(q['guards_intact'] and q['rows_hex'], 'Battle queue/history guard evidence missing')
                if variant == 'english':
                    for row, record in zip(q['rows_hex'], q['history_hex'], strict=True):
                        raw = bytes.fromhex(row); history = bytes.fromhex(record)
                        check(len(raw) <= 60 and history[3:3+len(raw)] == raw and history[0] == 1 and history[-1] == 0xA5, 'Battle history truncation')
                check(bool(case['screens']) == (case['profile'] != 'narrow'), 'Battle queue screen coverage differs')
        expected_words = {int(p['offset'], 0) for e in catalog['entries'] for p in e['pointer_owners']}
        check(len(r['pointer_words']) == 382 and {int(w['word'], 0) for w in r['pointer_words']} == expected_words, 'Battle pointer evidence incomplete')
        check(len(r['cold_tables']) == 2 and {(t['rom_start'], t['rom_end_exclusive']) for t in r['cold_tables']} == set(v.b.INIT_TABLES), 'Battle cold table coverage differs')
        for t in r['cold_tables']: check(bytes.fromhex(t['raw_hex']) == data[t['rom_start']:t['rom_end_exclusive']], 'Battle cold table bytes differ')
        selected = r['selections']; check(len(selected) == 18 and {(c['kind'], c.get('base', c.get('group')), c['row']) for c in selected} == expected_selections, 'Battle native selections incomplete')
        for c in selected:
            at = int(c['base'], 0)+4*c['row'] if c['kind'] == 'obstruction' else 0xDB15C+4*c['row'] if c['kind'] == 'wind' else 0xD95E0+4*(c['row']+4*c['group'])
            check(int(c['source'], 0) == int.from_bytes(data[at:at+4], 'little'), 'Battle native table result differs')
        check(r['screens'] == [s for c in r['cases'] for s in c['screens']] and len(set(r['screens'])) == len(r['screens']), 'Battle screenshot inventory differs')
        check(all((path.parent/s).is_file() for s in r['screens']), 'Battle screenshot missing')
        if variant == 'english': check(all(c['checks'] and all(c['checks']) for c in r['cases']), 'Battle English glyph/history evidence missing')
        if variant != 'baseline':
            report = load_json(out/f'{variant}-build.json'); check(report['previous_rom_sha256'] == digest(baseline) and report['catalog_sha256'] == r['catalog_sha256'], 'Battle build inputs differ')
            ledger = report['ledger']; rebuilt = bytearray(original+b'\xff'*(len(data)-len(original)))
            for a in ledger['allocations']:
                at = a['offset']; raw = data[at:at+a['bytes']]; check(digest(raw) == a['sha256'], 'Battle allocation differs'); rebuilt[at:at+len(raw)] = raw
            for p in ledger['patches']:
                at = p['offset']; before = bytes.fromhex(p['before']); after = bytes.fromhex(p['after']); check(rebuilt[at:at+len(before)] == before, 'Battle patch source differs'); rebuilt[at:at+len(after)] = after
            check(bytes(rebuilt) == data and data[0x1000000:end] == baseline[0x1000000:end], 'Unexplained battle image writes')
            for p in prior['patches']:
                at = p['offset']; after = bytes.fromhex(p['after']); check(data[at:at+len(after)] == after, 'Earlier battle-base patch changed')
            for s in ledger['protected_sources']: check(data[s['start']:s['end_exclusive']] == original[s['start']:s['end_exclusive']], 'Protected Japanese source changed')
        proofs[variant] = {'rom_sha256': digest(data), 'report_sha256': digest(path.read_bytes()), 'cases': len(r['cases']), 'screens': len(r['screens'])}; reports[variant] = r
    a, z = reports['japanese'], reports['baseline']; check(a['screens'] == z['screens'], 'Battle Japanese screen sets differ')
    check([c['formatted_hex'] for c in a['cases']] == [c['formatted_hex'] for c in z['cases']], 'Battle Japanese formatting differs')
    for x, y in zip(a['cases'], z['cases'], strict=True):
        if x['family'] == 'queue':
            check(all(x['queue'][k] == y['queue'][k] for k in ('rows_hex', 'history_hex', 'queue_start', 'history_start', 'guards_intact')), 'Battle Japanese queue/history differs')
    for name in a['screens']:
        with Image.open(out/'verification/japanese'/name) as x, Image.open(out/'verification/baseline'/name) as y:
            check(ImageChops.difference(x.convert('RGB'), y.convert('RGB')).getbbox() is None, 'Battle Japanese pixels differ '+name)
    result = {'status': 'battle_completion_component_native_checks_passed', 'sources': 298, 'pointer_words': 382, 'queue_sources': 247, 'paged_sources': 51,
        'english_cases': 843, 'english_screens': len(reports['english']['screens']), 'native_table_selections': 18, 'japanese_pixel_pairs': len(a['screens']),
        'proofs': proofs, 'complete_images_reconstructed_from_ledgers': True, 'previous_patches_and_appended_bytes_preserved': True, 'scope': a['scope']}
    write_json(out/'component-checkpoint.json', result); print(result['status'], len(a['screens']), 'Japanese pixel pairs', flush=True)


if __name__ == '__main__': summarize()
