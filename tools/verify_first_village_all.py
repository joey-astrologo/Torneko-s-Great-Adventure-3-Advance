"""Accept all village messages, natural introduction, saves and preservation."""
import argparse
import csv
import json
from pathlib import Path
import re
import struct
import subprocess
import sys
from tools.build_first_village import CATALOG,OUTPUT,OWNERS,extract_catalog,validate_catalog,encode,build,build_rom
from tools.build_first_label import ORIGINAL_ROM,ROOT,digest
from tools.translation_pipeline import load_json,check,atomic_write,FontZero
from tools.verify_items import write_json,distinct_glyph_observations

BASELINE=ROOT/'build/opening-story/torneko3-opening-story-english.gba'


def saves():
    import mgba.log
    from tools.verify_name_entry import creation,reload_name
    from tools.build_name_entry import compact_name
    mgba.log.silence();rom=(OUTPUT/'torneko3-first-village-english.gba').read_bytes();out=OUTPUT/'verification/save'
    first,_=creation(rom,out/'create-1',1)
    second,_=creation(rom,out/'create-2',2,initial_save=first)
    for slot in (1,2):reload_name(rom,second,out/f'reload-{slot}',compact_name('Torneko'),slot=slot,select_slot=slot==2)
    report={'rom_sha256':digest(rom),'save_bytes':len(second),'final_save_sha256':digest(second),'slots':[1,2],
        'name':'Torneko','first_slot_name_preserved':True,'helper_sha256':digest((ROOT/'tools/verify_name_entry.py').read_bytes()),
        'artifacts':{str(p.relative_to(out)):digest(p.read_bytes()) for p in out.rglob('*') if p.is_file() and p.name in ('trace.json','created.sav')},
        'scope':'Normal joypad entry, native FLASH saves in both Adventure Logs, then cold-loading both from the final save into the opening. Seven-character Torneko preserved, including slot one after writing slot two. No record edits; not a dungeon-suspend or ranking test.'}
    write_json(out/'verification.json',report);print('Both Adventure Logs: Torneko saved and cold-loaded',flush=True)
    return report


def summarize():
    from tools.verify_first_village import STATE,compare
    from tools.verify_dungeon_interface import check_glyphs
    from tools.trace_first_village import check_route
    from tools.trace_story_provenance import SAVE
    from tools.extract_master_text import verify_roundtrip
    from tools.audit_text_coverage import translated_ids
    original=ORIGINAL_ROM.read_bytes();catalog=load_json(CATALOG);entries=validate_catalog(original,catalog)
    check(digest(original)=='35bfff00dccd8de1a916b316298219c8c16a8adb0162ffe5056c481e0a8a4d02','Original ROM changed')
    for path,sha in load_json(OUTPUT/'before/hashes.json').items():
        if path not in ('translations/master.json','translations/glossary.json'):
            check(digest((ROOT/path).read_bytes())==sha,'Earlier artifact changed: '+path)
    check(load_json(OWNERS)==extract_catalog(original),'Stale/changed source ownership')
    roms={'baseline':BASELINE.read_bytes()};builds={}
    for v in ('english','japanese'):
        roms[v],builds[v]=build_rom(original,v)
        check(roms[v]==(OUTPUT/f'torneko3-first-village-{v}.gba').read_bytes(),'Stale/nondeterministic village ROM')
        check(builds[v]==load_json(OUTPUT/f'{v}-build.json'),'Stale ledger')
    hashes={v:digest(r) for v,r in roms.items()};cat_hash=digest(CATALOG.read_bytes());font=FontZero(original)
    expected={(e['id'],ev['pointer_offset'],hero) for e in entries.values() for ev in e['events'] for hero in (('Torneko','Tipper') if '$t' in e['japanese'] else ('Torneko',))}
    check(len(expected)==368,'Changed native test scope')
    for v in roms:
        out=OUTPUT/f'verification/{v}';r=load_json(out/'verification.json')
        check(r['rom_sha256']==hashes[v] and r['source_sha256']==digest(original) and r['catalog_sha256']==cat_hash,'Stale native source/catalog')
        check(r['harness_sha256']==digest((ROOT/'tools/verify_first_village.py').read_bytes()) and r['fixture_sha256']==digest(STATE.read_bytes()) and not r['limited'],'Stale/partial native evidence')
        check(len(r['cases'])==len(expected) and {(c['id'],c['pointer_offset'],c['hero']) for c in r['cases']}==expected,'Missing village cases')
        for c in r['cases']:
            e=entries[c['id']];raw,metrics=encode(e,original,c['hero'])
            raw=(raw if v=='english' else bytes.fromhex(e['source_hex'])).replace(b'$t',c['hero'].encode())
            pointer=struct.unpack_from('<I',roms[v],int(c['pointer_offset'],0))[0]
            check(int(c['source'],0)==pointer and bytes.fromhex(c['output_hex'])==raw and c['guards_intact'],'Native source/output/guard mismatch')
            detail=load_json(out/Path(c['screen']).with_suffix('.json'))
            check(all(detail[k]==value for k,value in c.items()) and (out/c['screen']).is_file(),'Native detail/screenshot mismatch')
            if v=='english':check(check_glyphs(detail['glyphs'],metrics['visible'],font)==c['checks'],'Stale glyph result')
    pixel_pairs=compare()
    route=load_json(OUTPUT/'verification/natural/trace.json')
    check(route['rom_sha256']==hashes['english'] and route['catalog_sha256']==cat_hash and route['source_sha256']==digest(original),'Stale natural village route')
    check(route['harness_sha256']==digest((ROOT/'tools/trace_first_village.py').read_bytes()) and route['trace_helper_sha256']==digest((ROOT/'tools/trace_opening_story.py').read_bytes()),'Stale natural route harness')
    check(route['initial_save_sha256']==digest(SAVE.read_bytes()) and route['opening_replay_sha256']==digest((ROOT/'build/opening-story/verification/natural-yes/trace.json').read_bytes()),'Stale natural route input')
    proof,glyphs=check_route(route,roms['english'],builds['english'])
    check(proof==route['proof'] and glyphs==route['glyph_checks'] and route['inputs'],'Stale natural route results')
    save=load_json(OUTPUT/'verification/save/verification.json')
    check(save['rom_sha256']==hashes['english'] and save['save_bytes']==65536 and save['slots']==[1,2] and save['name']=='Torneko' and save['first_slot_name_preserved'],'Save regression incomplete')
    check(save['helper_sha256']==digest((ROOT/'tools/verify_name_entry.py').read_bytes()),'Stale save helper')
    for path,sha in save['artifacts'].items():check(digest((OUTPUT/'verification/save'/path).read_bytes())==sha,'Changed save evidence')
    for slot in (1,2):
        check(f'create-{slot}/trace.json' in save['artifacts'] and f'reload-{slot}/trace.json' in save['artifacts'],'Missing Adventure Log')
        check(load_json(OUTPUT/f'verification/save/reload-{slot}/trace.json')['save_sha256']==save['final_save_sha256'],'Cold load used wrong save')
    old=load_json(ROOT/'build/opening-story/english-build.json')['ledger'];ledger=builds['english']['ledger'];alloc={a['id']:a for a in ledger['allocations']}
    for a in old['allocations']:
        at,size=a['offset'],a['bytes'];check(alloc[a['id']]==a and roms['english'][at:at+size]==roms['baseline'][at:at+size],'Earlier payload/allocation changed')
    check(ledger['patches'][:len(old['patches'])]==old['patches'],'Earlier patch ownership changed')
    for p in old['patches']:
        raw=bytes.fromhex(p['after']);check(roms['english'][p['offset']:p['offset']+len(raw)]==raw,'Earlier original patch changed')
    new=ledger['patches'][len(old['patches']):];wanted={int(ev['pointer_offset'],0) for e in entries.values() for ev in e['events']}
    check(len(new)==367 and {p['offset'] for p in new}==wanted and all(len(bytes.fromhex(p['after']))==4 for p in new),'Unexpected original-ROM patches')
    check(ledger['memory_reservations']==old['memory_reservations'] and ledger['complete_image_matches_ledger'],'RAM/save layout or collision regression')
    for e in entries.values():
        at,end=int(e['offset'],0),int(e['end_exclusive'],0)
        check(roms['english'][at:end]==original[at:end],'Original source changed')
        for ev in e['events']:
            at=int(ev['command_offset'],0);check(roms['english'][at:at+4]==original[at:at+4],'Event header/parameters changed')
    master=load_json(ROOT/'translations/master.json');before=load_json(OUTPUT/'before/master.json');by_id={e['id']:e for e in master['entries']}
    check(len(by_id)==len(before['entries'])==9318,'Master inventory changed')
    for e in before['entries']:check(all(by_id[e['id']][k]==e[k] for k in ('source_hex','english','notes')),'Earlier master draft/source changed')
    roundtrip=verify_roundtrip(original,master['entries']);done,families=translated_ids(master['entries'])
    check(len(done)==4634 and families['first-village']['new_distinct_ids']==281 and 'first-village.json' in master['english_authority'],'Stale progress/authority')
    browser=(ROOT/'build/text-extraction/index.html').read_text();check(all(e['id'] in browser for e in entries.values()),'Missing browser overlay')
    glossary=load_json(ROOT/'translations/glossary.json');terms={t['id']:t for t in glossary['terms']};review=glossary['current_review'];old_terms=load_json(OUTPUT/'before/glossary.json')['terms']
    check(len(terms)==1294 and review['id']=='first-village' and review['catalogs']['translations/first-village.json']==cat_hash,'Stale terminology snapshot')
    for t in old_terms:check(all(terms[t['id']][k]==t[k] for k in ('japanese','english','status','sources','notes')),'Earlier terminology changed')
    check(set(terms)-{t['id'] for t in old_terms}==set(review['new_terms']) and len(review['new_terms'])==6,'Unexpected new terms')
    with (ROOT/'translations/first-village-terminology-review.tsv').open() as f:rows=list(csv.DictReader(f,delimiter='\t'))
    check(len(rows)==281 and {r['id'] for r in rows}==entries.keys(),'Incomplete terminology review')
    for row in rows:
        e=entries[row['id']]
        check(row['japanese']==e['japanese'].replace('\n','<LF>') and row['full_english']==e['english'].replace('\n','<LF>') and row['notes']==e['notes'],'Review wording differs')
        check([t for t in row['glossary_references'].split(',') if t]==e['references'] and all(t in terms for t in e['references']),'Missing identity reference')
    log=(OUTPUT/'unit-tests.log').read_text();m=re.search(r'Ran (\d+) tests',log)
    check(m and int(m[1])>=186 and log.rstrip().endswith('OK'),'Unit tests incomplete/failed')
    fan=ROOT/'Dragon Quest Characters - Torneko no Daibouken 3 Advance - Fushigi no Dungeon (Japan) [T-En by Sam Steel v0.05] [i].gba'
    check(digest(fan.read_bytes())=='e7108d76a0c9c3a40b3eb52dc622cfe9ac9f08e673d3f43e0996815cebf7a93f','Reference ROM changed')
    review['status']='translated_inserted_automated_acceptance_passed';review['rom_sha256']=hashes['english']
    for ident in review['new_terms']:
        terms[ident]['insertion_status']='inserted_controlled_native_verified'
        terms[ident]['insertion_evidence']={'rom_sha256':hashes['english'],'report':'build/first-village/acceptance.json','scope':'All 281 catalog sources have native event/display fixtures; natural route covers the opening, village escort and first chief meeting. Later branch reachability remains separate. Naming confidence remains a project choice.'}
    atomic_write(ROOT/'translations/glossary.json',(json.dumps(glossary,ensure_ascii=False,indent=2)+'\n').encode())
    result={'status':'passed','source_sha256':digest(original),'reference_sha256':digest(fan.read_bytes()),'rom_sha256':hashes,
        'catalog_entries':281,'new_distinct_translations':281,'original_pointer_patches':367,'native_english_cases':368,'japanese_pixel_control_pairs':pixel_pairs,
        'natural_route':proof,'natural_new_village_sources':10,'seven_character_torneko_preserved_in_both_slots':True,'save_bytes':65536,
        'earlier_catalogs_allocations_and_patches_preserved':True,'original_village_sources_preserved':True,'ram_and_save_layout_preserved':True,
        'unit_tests':int(m[1]),'master_entries':len(by_id),'translated_distinct_sources':len(done),'remaining_distinct_sources':len(by_id)-len(done),
        'master_roundtrip_sha256':roundtrip,'glossary_terms':len(terms),'new_glossary_terms':6,
        'appended_used_with_padding':ledger['appended_used_with_padding'],'new_appended_bytes':ledger['appended_used_with_padding']-old['appended_used_with_padding'],
        'appended_remaining':ledger['appended_remaining'],'source_ownership_sha256':digest(OWNERS.read_bytes()),
        'catalog_file_sha256':{p.name:digest(p.read_bytes()) for p in (ROOT/'translations').glob('*.json')},
        'terminology_review_sha256':digest((ROOT/'translations/first-village-terminology-review.tsv').read_bytes()),
        'tool_sha256':{p.name:digest(p.read_bytes()) for p in (ROOT/'tools').glob('*first_village*') if p.is_file()},
        'limits':route['scope']+' Related Torneko return lines are translated but not naturally reached here. Later Tipper, celebration and ending arcs, global place labels, dungeon traversal and complete-game text discovery remain separate.'}
    write_json(OUTPUT/'acceptance.json',result)
    print(json.dumps({k:v for k,v in result.items() if k not in ('catalog_file_sha256','tool_sha256','natural_route')},indent=2));return result


def verify_all():
    from tools.verify_first_village import verify
    from tools.trace_first_village import capture
    from tools.extract_master_text import extract
    build()
    with (OUTPUT/'unit-tests.log').open('w') as log:subprocess.run([sys.executable,'-m','unittest','discover','-s','tests'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
    for v in ('english','japanese','baseline'):verify(v)
    capture();saves();extract();return summarize()


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);mode=p.add_mutually_exclusive_group();mode.add_argument('--summarize-only',action='store_true');mode.add_argument('--save-only',action='store_true');a=p.parse_args()
    summarize() if a.summarize_only else saves() if a.save_only else verify_all()
