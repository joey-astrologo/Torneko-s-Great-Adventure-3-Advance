"""Complete nickname milestone: rebuild, native readers/editor/saves and audit."""
import argparse
import csv
import json
import re
import string
import struct
import subprocess
import sys
from tools.build_ally_nicknames import CATALOG,OUTPUT,TABLE,build,build_rom,validate_catalog,expected_compact
from tools.build_first_label import ORIGINAL_ROM,ROOT,digest
from tools.translation_pipeline import check,load_json,atomic_write
from tools.verify_items import write_json

BASELINE=ROOT/'build/companion-dialogue/torneko3-companion-dialogue-english.gba'


def summarize():
    from tools.verify_ally_nicknames import STATE
    from tools.extract_master_text import verify_roundtrip
    from tools.audit_text_coverage import translated_ids
    original=ORIGINAL_ROM.read_bytes();catalog=load_json(CATALOG);entries=validate_catalog(original,catalog)
    frozen=load_json(OUTPUT/'before/hashes.json')
    check(digest(original)=='35bfff00dccd8de1a916b316298219c8c16a8adb0162ffe5056c481e0a8a4d02','Source ROM changed')
    for path,sha in frozen.items():
        if path not in ('translations/master.json','translations/glossary.json'):
            check(digest((ROOT/path).read_bytes())==sha,'Earlier authored artifact changed: '+path)
    roms={'baseline':BASELINE.read_bytes()};reports={}
    for v in ('english','japanese'):
        roms[v],reports[v]=build_rom(original,v)
        check(roms[v]==(OUTPUT/f'torneko3-ally-nicknames-{v}.gba').read_bytes(),'Nondeterministic/stale ROM')
        check(reports[v]==load_json(OUTPUT/f'{v}-build.json'),'Stale ledger')
    hashes={v:digest(b) for v,b in roms.items()};catalog_hash=digest(CATALOG.read_bytes())
    native={v:load_json(OUTPUT/f'verification/{v}/verification.json') for v in hashes}
    for v,r in native.items():
        check(r['rom_sha256']==hashes[v] and r['source_sha256']==digest(original) and r['catalog_sha256']==catalog_hash,'Stale native source/catalog')
        check(r['harness_sha256']==digest((ROOT/'tools/verify_ally_nicknames.py').read_bytes()) and r['fixture_sha256']==digest(STATE.read_bytes()) and not r['limited'],'Stale/partial native run')
        expected={(e['id'],suffix) for e in entries.values() for suffix in (range(10) if v=='english' else (0,1,9))}
        check(len(r['cases'])==len(expected) and {(c['id'],c['suffix']) for c in r['cases']}==expected,'Incomplete native row/suffix coverage')
        check(len(r['cold_initialized_tables'])==4 and len(r['other_encoder_callers'])==6,'Missing initialization/fallback checks')
        for c in r['cases']:
            e=entries[c['id']];pointer=struct.unpack_from('<I',roms[v],int(e['pointer_offset'],0))[0]
            check(int(c['source'],0)==pointer and c['guards_intact'] and c['record_guards_intact'],'Native reader/record guard missing')
            raw=bytes.fromhex(c['compact_hex']);stored=bytes.fromhex(c['stored_hex'])
            check(len(raw)==6 and b'\0' in raw and stored==raw.split(b'\0')[0].ljust(6,b'\0'),'Compact field/record mismatch')
            check(len(c['formatters'])==3 and all(x['guards_intact'] for x in c['formatters']),'Incomplete name consumers')
            if v=='english':
                compact,text=expected_compact(e['display'] or e['english'],c['suffix'])
                check(raw.startswith(compact) and c['decoded_hex']==(text.encode()+b'\0').hex(),'English native name/suffix differs')
    for a,b in zip(native['japanese']['cases'],native['baseline']['cases'],strict=True):
        check(all(a[k]==b[k] for k in ('id','row','suffix','source_hex','combined_hex','compact_hex','decoded_hex','stored_hex')),'Japanese relocation/codec regression')
        check([f['raw_hex'] for f in a['formatters']]==[f['raw_hex'] for f in b['formatters']],'Japanese name consumers changed')
    for v in ('japanese','english'):
        for a,b in zip(native[v]['other_encoder_callers'],native['baseline']['other_encoder_callers'],strict=True):
            check(all(a[k]==b[k] for k in ('type','source_hex','output_hex')),'Non-recruitment encoder behavior changed')
    editor=load_json(OUTPUT/'verification/editor/verification.json');save=load_json(OUTPUT/'verification/nickname-saves/verification.json')
    for r,tool in ((editor,'verify_nickname_editor.py'),(save,'verify_nickname_saves.py')):
        check(r['rom_sha256']==hashes['english'] and r['catalog_sha256']==catalog_hash and r['harness_sha256']==digest((ROOT/'tools'/tool).read_bytes()),'Stale editor/save evidence')
    check(not editor['limited'] and len(editor['cases'])==200 and {c['id'] for c in editor['cases']}==entries.keys(),'Incomplete nickname displays')
    check(editor['capacity']==5 and editor['guards_intact'] and editor['entry_default']=='Goot1','Editor capacity/default regression')
    from tools.build_name_entry import compact_name
    check(editor['editor_returns'][-1]=={'return':1,'source_hex':compact_name('RobbX').hex()},'Editor Done changed or truncated nickname')
    check(editor['fixture_sha256']==digest(STATE.read_bytes()),'Stale editor fixture')
    check(''.join(editor['alphabet'])==string.ascii_uppercase+string.ascii_lowercase+string.digits,'Missing Latin editor IDs')
    for c in editor['cases']:
        e=entries[c['id']];compact,text=expected_compact(e['display'] or e['english'],9)
        check(c['text']==text and c['compact_hex']==compact.hex() and c['checks'] and (OUTPUT/'verification/editor'/c['screen']).is_file(),'Missing/stale editor display')
    check(save['save_bytes']==65536 and save['all_200_defaults_cold_loaded'] and save['first_slot_preserved'] and save['torneko_seven_character_regression'],'Save/cold-load regression')
    check(save['custom_character_ids']==62 and save['legacy_japanese_names']==3 and len(save['cases'])==2,'Incomplete save variants')
    check(save['name_helper_sha256']==digest((ROOT/'tools/verify_name_entry.py').read_bytes()),'Stale native save helper')
    seeded=[e for c in save['cases'] for e in c['names']]
    check({e['id'] for e in seeded if e['id'].startswith('ally.nickname.')}==entries.keys(),'Save coverage omits defaults')
    for c in save['cases']:
        path=OUTPUT/f'verification/nickname-saves/create-{c["slot"]}/created.sav'
        check(digest(path.read_bytes())==c['save_sha256'] and c['whole_ally_block_identical'],'Changed native FLASH output')
        body=[e for e in c['events'] if e['phase']=='serialize'][-1]['pool_hex']
        loaded=[e for e in c['cold_load_events'] if e['phase']=='restore'][0]['pool_hex']
        check(body==loaded and len(bytes.fromhex(body))==130*32,'Save record block differs')
        for i,e in enumerate(c['names']):
            payload=bytes.fromhex(e['compact_hex']).split(b'\0')[0].ljust(6,b'\0')
            check(bytes.fromhex(body)[32*i+4:32*i+10]==payload,'Save block omits seeded name')
            if e['id'] in entries:
                entry=entries[e['id']];compact,_=expected_compact(entry['display'] or entry['english'],9)
                check(payload==compact.ljust(6,b'\0'),'Saved default differs from catalog')
    old=load_json(ROOT/'build/companion-dialogue/english-build.json');ledger=reports['english']['ledger'];alloc={a['id']:a for a in ledger['allocations']}
    for a in old['ledger']['allocations']:
        check(alloc[a['id']]==a,'Earlier allocation moved');at,size=a['offset'],a['bytes']
        check(roms['english'][at:at+size]==roms['baseline'][at:at+size],'Earlier payload changed')
    check(ledger['patches'][:len(old['ledger']['patches'])]==old['ledger']['patches'],'Prior patch ownership changed')
    for p in old['ledger']['patches']:
        raw=bytes.fromhex(p['after']);check(roms['english'][p['offset']:p['offset']+len(raw)]==raw,'Prior original patch changed')
    new_patches=ledger['patches'][len(old['ledger']['patches']):]
    check(len(new_patches)==201 and {p['offset'] for p in new_patches}==set(range(TABLE,TABLE+800,4))|{0x7D29C},'Unexpected new original patches')
    check(ledger['memory_reservations']==old['ledger']['memory_reservations'] and ledger['complete_image_matches_ledger'],'Save/RAM layout or collision check changed')
    for e in entries.values():
        at=int(e['offset'],0);raw=bytes.fromhex(e['source_hex'])
        check(roms['english'][at:at+len(raw)]==raw,'Original nickname bytes overwritten')
    master=load_json(ROOT/'translations/master.json');before=load_json(OUTPUT/'before/master.json');by_id={e['id']:e for e in master['entries']}
    check(len(by_id)==len(before['entries'])==9318,'Master inventory changed')
    for e in before['entries']:check(all(by_id[e['id']][k]==e[k] for k in ('source_hex','english','notes')),'Earlier master source/draft changed')
    roundtrip=verify_roundtrip(original,master['entries']);done,families=translated_ids(master['entries'])
    check(len(done)==4308 and families['ally-nicknames']['new_distinct_ids']==198 and 'ally-nicknames.json' in master['english_authority'],'Progress/authority stale')
    browser=(ROOT/'build/text-extraction/index.html').read_text();check(all(e['id'] in browser for e in entries.values()),'Missing browser overlay')
    glossary=load_json(ROOT/'translations/glossary.json');terms={t['id']:t for t in glossary['terms']};review=glossary['current_review']
    old_terms=load_json(OUTPUT/'before/glossary.json')['terms']
    check(len(terms)==1283 and review['id']=='ally-nicknames' and review['catalogs']['translations/ally-nicknames.json']==catalog_hash,'Terminology snapshot stale')
    for t in old_terms:check(all(terms[t['id']][k]==t[k] for k in ('japanese','english','status','sources','notes')),'Prior terminology changed')
    check(set(terms)-{t['id'] for t in old_terms}==set(review['new_terms']) and len(review['new_terms'])==194,'Unexpected new identities')
    with (ROOT/'translations/ally-nickname-terminology-review.tsv').open() as f:rows=list(csv.DictReader(f,delimiter='\t'))
    check(len(rows)==200 and {r['id'] for r in rows}==entries.keys(),'Incomplete terminology review')
    for r in rows:
        e=entries[r['id']]
        check(r['japanese']==e['japanese'] and r['full_english']==e['english'] and r['display']==(e['display'] or '') and r['notes']==e['notes'],'Review wording differs')
        check(r['glossary_references'].split(',')==e['references'] and all(x in terms for x in e['references']),'Missing nickname identity')
        check(all(s in glossary['sources'] for s in r['source_ids'].split(',') if s),'Unrecorded naming source')
    log=(OUTPUT/'unit-tests.log').read_text();m=re.search(r'Ran (\d+) tests',log)
    check(m and int(m[1])>=171 and log.rstrip().endswith('OK'),'Unit tests incomplete/failed')
    fan=ROOT/'Dragon Quest Characters - Torneko no Daibouken 3 Advance - Fushigi no Dungeon (Japan) [T-En by Sam Steel v0.05] [i].gba'
    check(digest(fan.read_bytes())=='e7108d76a0c9c3a40b3eb52dc622cfe9ac9f08e673d3f43e0996815cebf7a93f','Technical reference ROM changed')
    review['status']='translated_inserted_automated_acceptance_passed';review['rom_sha256']=hashes['english']
    for ident in review['new_terms']:
        terms[ident]['insertion_status']='inserted_controlled_native_verified'
        terms[ident]['insertion_evidence']={'rom_sha256':hashes['english'],'report':'build/ally-nicknames/acceptance.json','scope':'Bounded default generation, native editor display/joypad controls and seeded ally records through actual FLASH save/cold load. Reserved rows have no natural-recruitment claim. Official-name confidence remains separate.'}
    atomic_write(ROOT/'translations/glossary.json',(json.dumps(glossary,ensure_ascii=False,indent=2)+'\n').encode())
    result={'status':'passed','source_sha256':digest(original),'reference_sha256':digest(fan.read_bytes()),'rom_sha256':hashes,
        'catalog_rows':200,'distinct_sources':198,'native_english_generation_cases':2000,'japanese_control_pairs':600,'name_formatter_calls':9600,
        'other_encoder_cases_per_variant':6,'editor_display_rows':200,'joypad_character_ids':62,'nickname_capacity':5,'compact_record_bytes':6,
        'native_save_slots':2,'save_default_names':200,'legacy_japanese_save_names':3,'save_custom_character_ids':62,'save_bytes':65536,
        'seven_character_player_name_preserved':True,'earlier_catalogs_allocations_and_patches_preserved':True,'original_nickname_sources_preserved':True,
        'ram_and_save_layout_preserved':True,'unit_tests':int(m[1]),'master_entries':len(by_id),'translated_distinct_sources':len(done),'remaining_distinct_sources':len(by_id)-len(done),
        'master_roundtrip_sha256':roundtrip,'glossary_terms':len(terms),'new_glossary_terms':194,
        'appended_used_with_padding':ledger['appended_used_with_padding'],'new_appended_bytes':ledger['appended_used_with_padding']-old['ledger']['appended_used_with_padding'],
        'appended_remaining':ledger['appended_remaining'],'new_original_patch_ranges':201,
        'catalog_file_sha256':{p.name:digest(p.read_bytes()) for p in (ROOT/'translations').glob('*.json')},
        'terminology_review_sha256':digest((ROOT/'translations/ally-nickname-terminology-review.tsv').read_bytes()),
        'tool_sha256':{p.name:digest(p.read_bytes()) for p in (ROOT/'tools').glob('*nickname*') if p.is_file()},
        'limits':native['english']['scope']+' '+editor['scope']+' '+save['scope']}
    write_json(OUTPUT/'acceptance.json',result)
    print(json.dumps({k:v for k,v in result.items() if k not in ('catalog_file_sha256','tool_sha256')},indent=2));return result


def verify_all():
    from tools.verify_ally_nicknames import verify
    from tools.verify_nickname_editor import verify as editor
    from tools.verify_nickname_saves import verify as saves
    from tools.extract_master_text import extract
    build()
    with (OUTPUT/'unit-tests.log').open('w') as log:subprocess.run([sys.executable,'-m','unittest','discover','-s','tests'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
    for v in ('english','japanese','baseline'):verify(v)
    editor();saves();extract();return summarize()

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--summarize-only',action='store_true')
    summarize() if p.parse_args().summarize_only else verify_all()
