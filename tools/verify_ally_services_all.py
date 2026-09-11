"""Reproduce and audit the complete ally/service translation milestone."""
import argparse
import csv
import json
from pathlib import Path
import re
import subprocess
import sys
from PIL import Image,ImageChops
from tools.build_ally_services import CATALOG,OUTPUT,build,build_rom
from tools.build_first_label import ORIGINAL_ROM,ROOT,digest
from tools.translation_pipeline import check,load_json,atomic_write
from tools.verify_items import write_json


def summarize():
    original=ORIGINAL_ROM.read_bytes();catalog_hash=digest(CATALOG.read_bytes());hashes={};ledger=None
    for v in ('english','japanese'):
        data,report=build_rom(original,v)
        check(data==(OUTPUT/f'torneko3-ally-services-{v}.gba').read_bytes(),'ROM differs from rebuild')
        check(report==load_json(OUTPUT/f'{v}-build.json'),'Build ledger stale')
        hashes[v]=digest(data)
        if v=='english':ledger=report['ledger']
    from tools.verify_ally_services import BASELINE,compare
    hashes['baseline']=digest(BASELINE.read_bytes());harness_hash=digest((ROOT/'tools/verify_ally_services.py').read_bytes());screens={}
    for v in hashes:
        reports=[load_json(OUTPUT/f'verification/{v}/verification.json'),load_json(OUTPUT/f'verification/{v}/service-contexts.json'),load_json(OUTPUT/f'verification/routes/{v}/verification.json')]
        for r in reports:check(r['rom_sha256']==hashes[v] and r['catalog_sha256']==catalog_hash and r['harness_sha256']==harness_hash,'Stale native artifact')
        r=reports[0]
        check(not r['limited'] and r['counts']=={'message':94,'menu':16,'label':13,'row':9,'small':4,'stats':2},'Incomplete families')
        check(len(r['cases'])==(276 if v=='english' else 138) and len(r['menus'])==26 and len(r['copies'])==3,'Incomplete native cases')
        check(len(reports[1]['cases'])==(14 if v=='english' else 9),'Incomplete numeric/header checks')
        check([c['kind'] for c in reports[2]['cases']]==['warehouse','bank'],'Missing service routes')
        screens[v]=sum(len(r['screens']) for r in reports)
    paired=compare()['pixel_pairs']
    for rel,reportname in [('', 'service-contexts.json'),('routes/','verification.json')]:
        ja=OUTPUT/f'verification/{rel}japanese';base=OUTPUT/f'verification/{rel}baseline';a=load_json(ja/reportname);b=load_json(base/reportname)
        check(a['screens']==b['screens'],'Control route coverage differs')
        for name in a['screens']:
            with Image.open(ja/name) as x,Image.open(base/name) as y:
                check(ImageChops.difference(x.convert('RGB'),y.convert('RGB')).getbbox() is None,f'Japanese pixels differ: {name}')
            paired+=1
    regression={name:load_json(OUTPUT/'verification'/p) for name,p in {'secondary':'secondary-contexts/report.json','items':'items-regression/verification.json','heroes':'hero-details/verification.json','save':'save/verification.json'}.items()}
    check(all(r['rom_sha256']==hashes['english'] for r in regression.values()),'Stale regression')
    r=regression['secondary'];check(len(r['menus'])==14 and len(r['enemy_copy_guards'])==400 and len(r['hero_copy_guards'])==2 and len(r['natural_search'])==2 and r['concealed_trap'],'Incomplete prior UI regression')
    check(regression['items']['item_rows']==[1,64,133,190,247,273,304] and len(regression['heroes']['checks'])==4,'Missing item/hero coverage')
    check(regression['save']['torneko_save_cold_load'] and regression['save']['save_bytes']==65536,'Save/cold-load failed')
    log=(OUTPUT/'unit-tests.log').read_text();match=re.search(r'Ran (\d+) tests',log);check(match and int(match[1])>=124 and log.rstrip().endswith('OK'),'Tests failed')
    for name in ('items','enemies','item-contexts','dungeon-interface','core-gameplay','gameplay-help'):
        check((ROOT/f'translations/{name}.json').read_bytes()==(OUTPUT/f'before/{name}.json').read_bytes(),f'Prior catalog changed: {name}')
    master=load_json(ROOT/'translations/master.json');before=load_json(OUTPUT/'before/master.json');current={e['id']:e for e in master['entries']}
    check(len(current)==len(before['entries'])==9318,'Source inventory count changed')
    for e in before['entries']:check(all(current[e['id']][k]==e[k] for k in ('source_hex','english','notes')),'Prior draft/source changed')
    from tools.extract_master_text import verify_roundtrip
    roundtrip=verify_roundtrip(original,master['entries'])
    glossary=load_json(ROOT/'translations/glossary.json');review=glossary['current_review'];terms={t['id']:t for t in glossary['terms']}
    check(review['id']=='ally-services' and review['rom_sha256']==hashes['english'] and review['catalogs']['translations/ally-services.json']==catalog_hash,'Terminology snapshot stale')
    for t in load_json(OUTPUT/'before/glossary.json')['terms']:check(all(terms[t['id']][k]==t[k] for k in ('japanese','english','status','sources','notes')),'Existing term changed')
    with (ROOT/'translations/ally-services-terminology-review.tsv').open() as f:rows=list(csv.DictReader(f,delimiter='\t'))
    catalog=load_json(CATALOG);entries={e['id']:e for e in catalog['entries']}
    check(len(rows)==len(entries)==138,'Review sheet incomplete')
    for row in rows:
        e=entries[row['id']];check(row['full_english']==e['english'].replace('\n','<LF>') and row['display']==(e['display'] or ''),'Review sheet stale')
    fan=ROOT/'Dragon Quest Characters - Torneko no Daibouken 3 Advance - Fushigi no Dungeon (Japan) [T-En by Sam Steel v0.05] [i].gba';fan_hash=digest(fan.read_bytes())
    check(fan_hash=='e7108d76a0c9c3a40b3eb52dc622cfe9ac9f08e673d3f43e0996815cebf7a93f','Reference ROM changed')
    review['status']='translated_inserted_automated_acceptance_passed'
    for t in glossary['terms']:
        if t.get('batch')=='ally-services':
            t['insertion_status']='inserted_controlled_native_verified'
            t['insertion_evidence']={'rom_sha256':hashes['english'],'report':'build/ally-services/acceptance.json','scope':'Native service text, menu/copy/header fixtures and controlled-entry warehouse/bank routes; natural recruitment, transactions and scenario-specific uses remain separate.'}
    atomic_write(ROOT/'translations/glossary.json',(json.dumps(glossary,ensure_ascii=False,indent=2)+'\n').encode())
    result={'status':'passed','source_sha256':digest(original),'reference_sha256':fan_hash,'rom_sha256':hashes,'catalog_entries':138,'families':{'message':94,'menu':16,'label':13,'row':9,'small':4,'stats':2},'english_screens':screens['english'],'japanese_pixel_pairs':paired,'unit_tests':int(match[1]),'native_ally_menu_layouts':24,'service_menu_tables':2,'guarded_context_title_copies':3,'numeric_input_units':2,'warehouse_transfer_popups':2,'native_header_cases':10,'controlled_service_routes':['warehouse_help_empty_withdrawal_cancel','bank_empty_balance_cancel'],'enemy_copy_guards':400,'hero_copy_guards':2,'secondary_action_menus':14,'item_inventory_information_screens':14,'hero_detail_screens':4,'save_bytes':65536,'master_entries':len(current),'master_roundtrip_sha256':roundtrip,'appended_used_with_padding':ledger['appended_used_with_padding'],'appended_remaining':ledger['appended_remaining'],'new_appended_bytes':ledger['appended_used_with_padding']-70192,'allocations':len(ledger['allocations']),'original_patch_ranges':len(ledger['patches']),'catalog_file_sha256':{p.name:digest(p.read_bytes()) for p in (ROOT/'translations').glob('*.json')},'harness_sha256':harness_hash,'terminology_review_sha256':digest((ROOT/'translations/ally-services-terminology-review.tsv').read_bytes()),'limits':'All 138 entries have bounded native formatting and display fixtures. Message fixtures execute every page with the original redraw callback but bypass input waits and frame-yield timing. Real service handlers are reached by one fixture redirect, followed by ordinary buttons through warehouse help/empty withdrawal and bank empty/cancel branches. This does not establish every natural NPC, recruitment, registration, transaction, ranking/save or scenario-specific caller.'}
    write_json(OUTPUT/'acceptance.json',result);print(json.dumps({k:v for k,v in result.items() if k!='catalog_file_sha256'},indent=2));return result


def verify_all():
    from tools.verify_ally_services import verify,service_contexts,service_routes,STATE
    from tools.verify_dungeon_contexts import verify as secondary
    from tools.verify_enemy_items import verify as items
    from tools.verify_enemies import verify as enemies
    from tools.extract_master_text import extract
    build()
    with (OUTPUT/'unit-tests.log').open('w') as log:subprocess.run([sys.executable,'-m','unittest','discover','-s','tests'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
    for v in ('english','japanese','baseline'):verify(v);service_contexts(v);service_routes(v)
    rom=OUTPUT/'torneko3-ally-services-english.gba'
    secondary(rom,OUTPUT/'verification/secondary-contexts',STATE)
    items(rom,OUTPUT/'verification/items-regression','items',state_path=STATE,rows=[1,64,133,190,247,273,304])
    enemies(rom,OUTPUT/'verification/hero-details',state_path=STATE,rows=[0,198])
    items(rom,OUTPUT/'verification/save','save');extract();return summarize()

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--summarize-only',action='store_true');summarize() if p.parse_args().summarize_only else verify_all()
