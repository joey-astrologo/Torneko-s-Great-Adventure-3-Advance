"""Rebuild and audit the complete tutorial/gameplay milestone."""
import argparse
import csv
import json
from pathlib import Path
import re
import subprocess
import sys
from tools.build_tutorial_gameplay import CATALOG,OUTPUT,build,build_rom
from tools.build_first_label import ORIGINAL_ROM,ROOT,digest
from tools.translation_pipeline import check,load_json,atomic_write
from tools.verify_items import write_json

FAMILIES={'tutorial':9,'message':165,'joined_damage':5,'object':8,'effect':98}


def summarize():
    original=ORIGINAL_ROM.read_bytes();catalog=load_json(CATALOG);catalog_hash=digest(CATALOG.read_bytes());hashes={}
    check(digest(original)=='35bfff00dccd8de1a916b316298219c8c16a8adb0162ffe5056c481e0a8a4d02','Original ROM changed')
    for v in ('english','japanese'):
        data,report=build_rom(original,v)
        check(data==(OUTPUT/f'torneko3-tutorial-gameplay-{v}.gba').read_bytes(),'ROM differs from rebuild')
        check(report==load_json(OUTPUT/f'{v}-build.json'),'Build ledger stale')
        hashes[v]=digest(data)
        if v=='english':ledger=report['ledger']
    from tools.verify_tutorial_gameplay import BASELINE,STATE,compare
    hashes['baseline']=digest(BASELINE.read_bytes());harness_hash=digest((ROOT/'tools/verify_tutorial_gameplay.py').read_bytes())
    native={v:load_json(OUTPUT/f'verification/{v}/verification.json') for v in hashes}
    expected_ids={e['id'] for e in catalog['entries']}
    check(len(expected_ids)==285,'Catalog count changed')
    for v,r in native.items():
        check(r['rom_sha256']==hashes[v] and r['catalog_sha256']==catalog_hash and r['harness_sha256']==harness_hash,'Stale native artifact')
        check(r['fixture_state_sha256']==digest(STATE.read_bytes()),'Fixture state changed')
        check(not r['limited'] and r['counts']==FAMILIES,'Incomplete families')
        profiles=('normal','stress','narrow') if v=='english' else ('normal',)
        expected={(ident,profile) for ident in expected_ids for profile in profiles}
        check(len(r['cases'])==len(expected) and {(c['id'],c['profile']) for c in r['cases']}==expected,'Incomplete profile coverage')
        check(len(r['cold_initialized_tables'])==4 and len(r['copies'])==108 and len(r['selections'])==77,'Incomplete native tables/copies')
        check(sum('removal_feedback' in c for c in r['copies'])==100,'Effect feedback coverage incomplete')
        check(len(r['joined_damage'])==4 and r['joined_damage'][-1]['pieces'][0]['queue_start']==14 and r['joined_damage'][-1]['pieces'][0]['history_start']==19,'Missing joined/ring-boundary coverage')
        if v=='english':
            check(all(c.get('checks') and len(c['checks'])==len(c['queue']['rows_hex']) for c in r['cases'] if c['profile']!='narrow'),'Missing native glyph/layout checks')
    paired=compare()
    regression={name:load_json(OUTPUT/'verification'/p) for name,p in {'secondary':'secondary-contexts/report.json','items':'items-regression/verification.json','heroes':'hero-details/verification.json','save':'save/verification.json'}.items()}
    check(all(r['rom_sha256']==hashes['english'] for r in regression.values()),'Stale regression')
    r=regression['secondary'];check(len(r['menus'])==14 and len(r['enemy_copy_guards'])==400 and len(r['hero_copy_guards'])==2 and len(r['natural_search'])==2 and r['concealed_trap'],'Incomplete prior UI regression')
    check(regression['items']['item_rows']==[1,64,133,190,247,273,304] and len(regression['heroes']['checks'])==4,'Missing item/hero coverage')
    check(regression['save']['torneko_save_cold_load'] and regression['save']['save_bytes']==65536,'Save/cold-load failed')
    log=(OUTPUT/'unit-tests.log').read_text();match=re.search(r'Ran (\d+) tests',log)
    check(match and int(match[1])>=131 and log.rstrip().endswith('OK'),'Unit tests failed')
    for name in ('items','enemies','item-contexts','dungeon-interface','core-gameplay','gameplay-help','ally-services'):
        check((ROOT/f'translations/{name}.json').read_bytes()==(OUTPUT/f'before/{name}.json').read_bytes(),f'Prior catalog changed: {name}')
    master=load_json(ROOT/'translations/master.json');before=load_json(OUTPUT/'before/master.json');current={e['id']:e for e in master['entries']}
    check(len(current)==len(before['entries'])==9318,'Source inventory count changed')
    for e in before['entries']:check(all(current[e['id']][k]==e[k] for k in ('source_hex','english','notes')),'Prior draft/source changed')
    from tools.extract_master_text import verify_roundtrip
    roundtrip=verify_roundtrip(original,master['entries'])
    glossary=load_json(ROOT/'translations/glossary.json');review=glossary['current_review'];terms={t['id']:t for t in glossary['terms']}
    check(review['id']=='tutorial-gameplay' and review['rom_sha256']==hashes['english'] and review['catalogs']['translations/tutorial-gameplay.json']==catalog_hash,'Terminology snapshot stale')
    for t in load_json(OUTPUT/'before/glossary.json')['terms']:check(all(terms[t['id']][k]==t[k] for k in ('japanese','english','status','sources','notes')),'Existing term changed')
    with (ROOT/'translations/tutorial-gameplay-terminology-review.tsv').open() as f:rows=list(csv.DictReader(f,delimiter='\t'))
    entries={e['id']:e for e in catalog['entries']};check(len(rows)==len(entries) and {r['id'] for r in rows}==entries.keys(),'Review sheet incomplete')
    for row in rows:
        e=entries[row['id']];check(row['full_english']==e['english'].replace('\n','<LF>') and row['display']==(e['display'] or ''),'Review sheet stale')
        check(all(ref in terms for ref in row['glossary_references'].split(',') if ref),'Unknown terminology reference')
    fan=ROOT/'Dragon Quest Characters - Torneko no Daibouken 3 Advance - Fushigi no Dungeon (Japan) [T-En by Sam Steel v0.05] [i].gba';fan_hash=digest(fan.read_bytes())
    check(fan_hash=='e7108d76a0c9c3a40b3eb52dc622cfe9ac9f08e673d3f43e0996815cebf7a93f','Reference ROM changed')
    review['status']='translated_inserted_automated_acceptance_passed'
    for t in glossary['terms']:
        if t.get('batch')=='tutorial-gameplay':
            t['insertion_status']='inserted_controlled_native_verified'
            t['insertion_evidence']={'rom_sha256':hashes['english'],'report':'build/tutorial-gameplay/acceptance.json','scope':'Original effect-table copies, removal-feedback queue/history and isolated display fixtures; natural effect-removal scenarios remain separate.'}
    atomic_write(ROOT/'translations/glossary.json',(json.dumps(glossary,ensure_ascii=False,indent=2)+'\n').encode())
    result={'status':'passed','source_sha256':digest(original),'reference_sha256':fan_hash,'rom_sha256':hashes,'catalog_entries':285,'families':FAMILIES,
            'english_native_cases':len(native['english']['cases']),'english_screens':len(native['english']['screens']),'japanese_pixel_pairs':paired['pixel_pairs'],
            'cold_initialized_pointer_tables_per_variant':4,'guarded_effect_copies_per_variant':100,'effect_removal_feedback_cases_per_variant':100,'guarded_object_copies_per_variant':8,
            'native_pointer_selections_per_variant':{'tutorial':9,'strength':3,'cancellation':25,'trap_context':40},'joined_damage_sequences_per_variant':4,'queue_and_history_wrap_checked':True,
            'unit_tests':int(match[1]),'enemy_copy_guards':400,'hero_copy_guards':2,'secondary_action_menus':14,'item_inventory_information_screens':14,'hero_detail_screens':4,'save_bytes':65536,
            'master_entries':len(current),'master_roundtrip_sha256':roundtrip,'glossary_terms':len(terms),'appended_used_with_padding':ledger['appended_used_with_padding'],'appended_remaining':ledger['appended_remaining'],
            'new_appended_bytes':ledger['appended_used_with_padding']-75729,'allocations':len(ledger['allocations']),'original_patch_ranges':len(ledger['patches']),
            'catalog_file_sha256':{p.name:digest(p.read_bytes()) for p in (ROOT/'translations').glob('*.json')},'harness_sha256':harness_hash,
            'terminology_review_sha256':digest((ROOT/'translations/tutorial-gameplay-terminology-review.tsv').read_bytes()),
            'limits':'Controlled native formatter, queue/history, rendering/scroll and indexed selection/copy fixtures. Live queue permits 80 bytes per row, history only 59 payload bytes; all new English respects both including narrow-character stress. Fixture history backing replaces an absent dungeon structure, queue scheduling is skipped, and renderer frame yields/button waits are bypassed. This does not prove natural tutorial pickup, combat/trap/effect-removal scenarios, all extracted messages, or ranking/history save persistence.'}
    write_json(OUTPUT/'acceptance.json',result);print(json.dumps({k:v for k,v in result.items() if k!='catalog_file_sha256'},indent=2));return result


def verify_all():
    from tools.verify_tutorial_gameplay import verify,STATE
    from tools.verify_dungeon_contexts import verify as secondary
    from tools.verify_enemy_items import verify as items
    from tools.verify_enemies import verify as enemies
    from tools.extract_master_text import extract
    build()
    with (OUTPUT/'unit-tests.log').open('w') as log:subprocess.run([sys.executable,'-m','unittest','discover','-s','tests'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
    for v in ('english','japanese','baseline'):verify(v)
    rom=OUTPUT/'torneko3-tutorial-gameplay-english.gba'
    secondary(rom,OUTPUT/'verification/secondary-contexts',STATE)
    items(rom,OUTPUT/'verification/items-regression','items',state_path=STATE,rows=[1,64,133,190,247,273,304])
    enemies(rom,OUTPUT/'verification/hero-details',state_path=STATE,rows=[0,198])
    items(rom,OUTPUT/'verification/save','save');extract();return summarize()


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--summarize-only',action='store_true')
    summarize() if p.parse_args().summarize_only else verify_all()
