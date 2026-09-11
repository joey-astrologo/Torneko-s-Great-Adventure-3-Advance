"""Accept the complete opening section, native branches and save regressions."""
import argparse
import csv
import json
import re
import struct
import subprocess
import sys

from tools.build_opening_story import CATALOG, OUTPUT, OWNERS, build, build_rom, validate_catalog, encode
from tools.build_first_label import ORIGINAL_ROM, ROOT, digest
from tools.translation_pipeline import check, load_json, atomic_write, FontZero
from tools.verify_items import write_json, distinct_glyph_observations

BASELINE = ROOT/'build/ally-nicknames/torneko3-ally-nicknames-english.gba'


def save_regression():
    import mgba.log
    from tools.verify_name_entry import creation, reload_name
    from tools.build_name_entry import compact_name
    mgba.log.silence()
    data = (OUTPUT/'torneko3-opening-story-english.gba').read_bytes()
    out = OUTPUT/'verification/save'
    first, _ = creation(data, out/'create-1', 1)
    second, _ = creation(data, out/'create-2', 2, initial_save=first)
    for slot in (1, 2):
        reload_name(data, second, out/f'reload-{slot}', compact_name('Torneko'),
                    slot=slot, select_slot=slot == 2)
    report = {'rom_sha256': digest(data), 'save_bytes': len(second),
              'first_save_sha256': digest(first), 'final_save_sha256': digest(second),
              'slots': [1, 2], 'name': 'Torneko', 'first_slot_preserved': True,
              'helper_sha256': digest((ROOT/'tools/verify_name_entry.py').read_bytes()),
              'scope': 'Normal joypad entry of all seven letters, native FLASH saves in both Adventure Logs, then fresh-core loading of both slots into the opening story. No RAM/register/record edits. Does not test dungeon suspend saves or rankings.'}
    report['artifacts'] = {str(p.relative_to(out)): digest(p.read_bytes())
                           for p in out.rglob('*') if p.is_file() and p.name in ('trace.json', 'created.sav')}
    write_json(out/'verification.json', report)
    print('Seven-character Torneko: both slots saved and cold-loaded', flush=True)
    return report


def summarize():
    from tools.verify_opening_story import STATE, compare
    from tools.verify_story_provenance import check_natural
    from tools.trace_story_provenance import SAVE
    from tools.verify_dungeon_interface import check_glyphs
    from tools.game_text import GameTextCodec
    from tools.extract_master_text import verify_roundtrip
    from tools.audit_text_coverage import translated_ids
    original = ORIGINAL_ROM.read_bytes()
    check(digest(original) == '35bfff00dccd8de1a916b316298219c8c16a8adb0162ffe5056c481e0a8a4d02', 'Original ROM changed')
    catalog = load_json(CATALOG); entries = validate_catalog(original, catalog)
    frozen = load_json(OUTPUT/'before/hashes.json')
    for path, sha in frozen.items():
        if path not in ('translations/master.json', 'translations/glossary.json'):
            check(digest((ROOT/path).read_bytes()) == sha, 'Earlier authored artifact changed: '+path)
    owners = load_json(OWNERS)
    check(owners['source_sha256'] == digest(original) and owners['scope'] == catalog['scope'], 'Stale ownership source/scope')
    check(owners['provenance_sha256'] == digest((ROOT/'build/story-provenance/natural/trace.json').read_bytes()), 'Stale source provenance')
    check(len(owners['entries']) == 46 and {e['id'] for e in owners['entries']} == entries.keys(), 'Incomplete source ownership')
    for owner in owners['entries']:
        e = entries[owner['id']]
        check(all(owner[k] == e[k] for k in owner.keys()-{'end_exclusive'}), 'Source ownership differs from catalog')
        check(int(owner['end_exclusive'], 0) == int(e['offset'], 0)+len(bytes.fromhex(e['source_hex'])), 'Wrong protected source end')
    roms = {'baseline': BASELINE.read_bytes()}; builds = {}
    for variant in ('english', 'japanese'):
        roms[variant], builds[variant] = build_rom(original, variant)
        check(roms[variant] == (OUTPUT/f'torneko3-opening-story-{variant}.gba').read_bytes(), 'Stale/nondeterministic ROM')
        check(builds[variant] == load_json(OUTPUT/f'{variant}-build.json'), 'Stale allocation ledger')
    hashes = {v: digest(r) for v, r in roms.items()}; cat_hash = digest(CATALOG.read_bytes())
    expected_cases = {(e['id'], ev['pointer_offset']) for e in entries.values() for ev in e['events']}
    for variant in roms:
        r = load_json(OUTPUT/f'verification/{variant}/verification.json')
        check(r['rom_sha256'] == hashes[variant] and r['source_sha256'] == digest(original) and r['catalog_sha256'] == cat_hash, 'Stale native ROM/catalog')
        check(r['harness_sha256'] == digest((ROOT/'tools/verify_opening_story.py').read_bytes()) and r['fixture_sha256'] == digest(STATE.read_bytes()), 'Stale native harness/fixture')
        check(not r['limited'] and len(r['cases']) == 52 and {(c['id'], c['pointer_offset']) for c in r['cases']} == expected_cases, 'Incomplete native event coverage')
        for c in r['cases']:
            e = entries[c['id']]; target = struct.unpack_from('<I', roms[variant], int(c['pointer_offset'], 0))[0]
            raw, _ = encode(e, original)
            expected = raw if variant == 'english' or e['reuse'] else bytes.fromhex(e['source_hex'])
            check(int(c['source'], 0) == target and c['guards_intact'] and bytes.fromhex(c['output_hex']) == expected, 'Native pointer/output/guard mismatch')
            check((OUTPUT/f'verification/{variant}'/c['screen']).is_file(), 'Missing native screenshot')
    japanese_pairs = compare()
    master = load_json(ROOT/'translations/master.json'); augmented = list(master['entries'])
    codec = GameTextCodec(roms['english']); font = FontZero(original)
    for e in entries.values():
        at = builds['english']['opening']['relocated'][e['id']]['offset']; p = codec.parse(roms['english'], at)
        augmented.append({'id': e['master_id'], 'offset': hex(at), 'source_hex': p['raw_hex'], 'source_tokens': p['tokens']})
    by_master = {e['master_id']: e for e in entries.values()}; natural = {}
    expected_sources = set(load_json(ROOT/'build/story-provenance/natural-coverage.json')['master_ids'])
    for choice in ('yes', 'no'):
        r = load_json(OUTPUT/f'verification/natural-{choice}/trace.json')
        check(r['rom_sha256'] == hashes['english'] and r['source_sha256'] == digest(original) and r['catalog_sha256'] == cat_hash, 'Stale natural route')
        check(r['harness_sha256'] == digest((ROOT/'tools/trace_opening_story.py').read_bytes()) and r['initial_save_sha256'] == digest(SAVE.read_bytes()), 'Stale natural route harness/save')
        check(r['choice'] == choice and r['inputs'], 'Missing natural button route')
        proof = check_natural(r, roms['english'], augmented)
        check(proof == r['proof'], 'Stale natural provenance proof')
        check(set(proof['master_ids']) == expected_sources | ({'jp_00c2f4a8'} if choice == 'no' else set()), 'Wrong dream branch')
        check(proof['buffer_versions'] == (36 if choice == 'yes' else 37), 'Unexpected opening message sequence')
        checks = []
        for v in r['versions']:
            e = by_master[v['source']['master_id']]; raw, metrics = encode(e, original)
            check(v['output_hex'] == raw.hex(), 'Natural formatter lost text')
            glyphs, _ = distinct_glyph_observations([g for g in r['positions'] if g['version'] == v['serial']])
            checks.append({'version': v['serial'], 'id': e['id'], **check_glyphs(glyphs, metrics['visible'], font)})
        check(checks == r['glyph_checks'], 'Stale natural glyph checks')
        menu_checks = []
        for serial in sorted({g['draw_serial'] for g in r['menu_positions']}):
            gs = [g for g in r['menu_positions'] if g['draw_serial'] == serial]; label = gs[0]['label']
            menu_checks.append({'label': label, **check_glyphs(gs, label, font)})
        check(menu_checks == r['menu_label_checks'] and {c['label'] for c in menu_checks} == {'Yes', 'No'}, 'Incomplete natural choice glyphs')
        check(all((OUTPUT/f'verification/natural-{choice}'/s).is_file() for s in r['screens']), 'Missing route screenshots')
        natural[choice] = proof
    save = load_json(OUTPUT/'verification/save/verification.json')
    check(save['rom_sha256'] == hashes['english'] and save['save_bytes'] == 65536 and save['slots'] == [1, 2] and save['name'] == 'Torneko' and save['first_slot_preserved'], 'Incomplete save regression')
    check(save['helper_sha256'] == digest((ROOT/'tools/verify_name_entry.py').read_bytes()), 'Stale save helper')
    for path, sha in save['artifacts'].items():
        check(digest((OUTPUT/'verification/save'/path).read_bytes()) == sha, 'Changed save trace/output')
    for slot in (1, 2):
        check(f'create-{slot}/trace.json' in save['artifacts'] and f'reload-{slot}/trace.json' in save['artifacts'], 'Missing saved slot evidence')
        check(load_json(OUTPUT/f'verification/save/reload-{slot}/trace.json')['save_sha256'] == save['final_save_sha256'], 'Slot was not cold-loaded from final save')
    old = load_json(ROOT/'build/ally-nicknames/english-build.json')['ledger']; ledger = builds['english']['ledger']
    alloc = {a['id']: a for a in ledger['allocations']}
    for a in old['allocations']:
        check(alloc[a['id']] == a, 'Earlier allocation moved')
        at, size = a['offset'], a['bytes']
        check(roms['english'][at:at+size] == roms['baseline'][at:at+size], 'Earlier payload changed')
    check(ledger['patches'][:len(old['patches'])] == old['patches'], 'Earlier patch ownership changed')
    for patch in old['patches']:
        raw = bytes.fromhex(patch['after']); at = patch['offset']
        check(roms['english'][at:at+len(raw)] == raw, 'Earlier original patch changed')
    new_patches = ledger['patches'][len(old['patches']):]
    wanted = {int(ev['pointer_offset'], 0) for e in entries.values() if not e['reuse'] for ev in e['events']+e.get('choice_owners', [])}
    check(len(new_patches) == 53 and {p['offset'] for p in new_patches} == wanted and all(len(bytes.fromhex(p['after'])) == 4 for p in new_patches), 'Unexpected original ROM edits')
    check(ledger['memory_reservations'] == old['memory_reservations'] and ledger['complete_image_matches_ledger'], 'RAM/save layout or collision regression')
    for e in entries.values():
        at = int(e['offset'], 0); raw = bytes.fromhex(e['source_hex'])
        check(roms['english'][at:at+len(raw)] == raw, 'Original story source overwritten')
        for event in e['events']:
            at = int(event['command_offset'], 0)
            check(roms['english'][at:at+4] == original[at:at+4], 'Event command parameters changed')
        for owner in e.get('choice_owners', []):
            at = int(owner['pointer_offset'], 0)
            check(roms['english'][at+4:at+12] == original[at+4:at+12], 'Choice default/return value changed')
    before = load_json(OUTPUT/'before/master.json'); by_id = {e['id']: e for e in master['entries']}
    check(len(by_id) == len(before['entries']) == 9318, 'Master inventory changed')
    for e in before['entries']:
        check(all(by_id[e['id']][k] == e[k] for k in ('source_hex', 'english', 'notes')), 'Earlier master draft/source changed')
    roundtrip = verify_roundtrip(original, master['entries']); done, families = translated_ids(master['entries'])
    check(len(done) == 4353 and families['opening-story']['new_distinct_ids'] == 45 and 'opening-story.json' in master['english_authority'], 'Stale progress/authority')
    browser = (ROOT/'build/text-extraction/index.html').read_text()
    check(all(e['id'] in browser for e in entries.values()), 'Missing opening browser overlay')
    glossary = load_json(ROOT/'translations/glossary.json'); terms = {t['id']: t for t in glossary['terms']}; review = glossary['current_review']
    old_terms = load_json(OUTPUT/'before/glossary.json')['terms']
    check(len(terms) == 1288 and review['id'] == 'opening-story' and review['catalogs']['translations/opening-story.json'] == cat_hash, 'Stale terminology snapshot')
    for t in old_terms:
        check(all(terms[t['id']][k] == t[k] for k in ('japanese', 'english', 'status', 'sources', 'notes')), 'Earlier terminology changed')
    check(set(terms)-{t['id'] for t in old_terms} == set(review['new_terms']) and len(review['new_terms']) == 5, 'Unexpected new terminology')
    with (ROOT/'translations/opening-story-terminology-review.tsv').open() as f:
        rows = list(csv.DictReader(f, delimiter='\t'))
    check(len(rows) == 46 and {r['id'] for r in rows} == entries.keys(), 'Incomplete terminology review')
    for row in rows:
        e = entries[row['id']]
        check(row['japanese'] == e['japanese'].replace('\n', '<LF>') and row['full_english'] == e['english'].replace('\n', '<LF>') and row['notes'] == e['notes'], 'Review wording differs')
        check([t for t in row['glossary_references'].split(',') if t] == e['references'] and all(t in terms for t in e['references']), 'Missing identity reference')
    log = (OUTPUT/'unit-tests.log').read_text(); m = re.search(r'Ran (\d+) tests', log)
    check(m and int(m[1]) >= 179 and log.rstrip().endswith('OK'), 'Unit tests incomplete/failed')
    fan = ROOT/'Dragon Quest Characters - Torneko no Daibouken 3 Advance - Fushigi no Dungeon (Japan) [T-En by Sam Steel v0.05] [i].gba'
    check(digest(fan.read_bytes()) == 'e7108d76a0c9c3a40b3eb52dc622cfe9ac9f08e673d3f43e0996815cebf7a93f', 'Reference ROM changed')
    review['status'] = 'translated_inserted_automated_acceptance_passed'; review['rom_sha256'] = hashes['english']
    for ident in review['new_terms']:
        terms[ident]['insertion_status'] = 'inserted_native_opening_verified'
        terms[ident]['insertion_evidence'] = {'rom_sha256': hashes['english'], 'report': 'build/opening-story/acceptance.json', 'scope': 'Native opening through both dream responses and English event choices. Naming confidence remains separate; additional rest/return messages have controlled display coverage.'}
    atomic_write(ROOT/'translations/glossary.json', (json.dumps(glossary, ensure_ascii=False, indent=2)+'\n').encode())
    result = {'status': 'passed', 'source_sha256': digest(original), 'reference_sha256': digest(fan.read_bytes()), 'rom_sha256': hashes,
        'catalog_entries': 46, 'story_sources': 44, 'shared_choice_labels': 2, 'new_distinct_translations': 45, 'reused_prior_narrations': 1,
        'native_english_event_operands': 52, 'japanese_pixel_control_pairs': japanese_pairs, 'natural_routes': natural,
        'native_save_slots': 2, 'seven_character_torneko_preserved': True, 'save_bytes': save['save_bytes'],
        'earlier_catalogs_allocations_and_patches_preserved': True, 'original_story_sources_preserved': True, 'ram_and_save_layout_preserved': True,
        'unit_tests': int(m[1]), 'master_entries': len(by_id), 'translated_distinct_sources': len(done), 'remaining_distinct_sources': len(by_id)-len(done),
        'master_roundtrip_sha256': roundtrip, 'glossary_terms': len(terms), 'new_glossary_terms': 5,
        'appended_used_with_padding': ledger['appended_used_with_padding'], 'new_appended_bytes': ledger['appended_used_with_padding']-old['appended_used_with_padding'],
        'appended_remaining': ledger['appended_remaining'], 'new_original_pointer_patches': 53,
        'catalog_file_sha256': {p.name: digest(p.read_bytes()) for p in (ROOT/'translations').glob('*.json')},
        'terminology_review_sha256': digest((ROOT/'translations/opening-story-terminology-review.tsv').read_bytes()),
        'source_ownership_sha256': digest(OWNERS.read_bytes()),
        'tool_sha256': {p.name: digest(p.read_bytes()) for p in (ROOT/'tools').glob('*opening*') if p.is_file()},
        'limits': 'Natural opening covers 37 distinct story sources across Yes/No routes. Seven further return/rest/observation sources and eight additional shared-source operands have controlled native display checks; no natural later-bedroom/rest branch claim. Shared choice labels are checked in the dream menu. Later village/events, endings, rankings and complete-game extraction remain unproven.'}
    write_json(OUTPUT/'acceptance.json', result)
    print(json.dumps({k: v for k, v in result.items() if k not in ('catalog_file_sha256', 'tool_sha256', 'natural_routes')}, indent=2))
    return result


def verify_all():
    from tools.verify_opening_story import verify
    from tools.trace_opening_story import capture
    from tools.extract_master_text import extract
    build()
    with (OUTPUT/'unit-tests.log').open('w') as log:
        subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests'], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)
    for variant in ('english', 'japanese', 'baseline'): verify(variant)
    for choice in ('yes', 'no'): capture(choice)
    save_regression(); extract()
    return summarize()


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    mode = p.add_mutually_exclusive_group()
    mode.add_argument('--summarize-only', action='store_true')
    mode.add_argument('--save-only', action='store_true')
    args = p.parse_args()
    summarize() if args.summarize_only else save_regression() if args.save_only else verify_all()
