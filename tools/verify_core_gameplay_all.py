"""Reproduce or audit the complete core-gameplay milestone."""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

from tools.build_core_gameplay import CATALOG,OUTPUT,ROOT,ORIGINAL_ROM,build,build_rom
from tools.build_first_label import digest,load_manifest
from tools.translation_pipeline import check,load_json
from tools.verify_items import write_json


def summarize():
    original=ORIGINAL_ROM.read_bytes();check(digest(original)==load_manifest()['base_sha256'],'Source ROM changed')
    catalog=load_json(CATALOG);cat_hash=digest(CATALOG.read_bytes());hashes={};reports={}
    for variant in ('english','japanese'):
        expected,report=build_rom(original,variant,catalog)
        actual=(OUTPUT/f'torneko3-core-gameplay-{variant}.gba').read_bytes()
        check(expected==actual,'Delivered ROM differs from a clean shared-ledger build')
        saved=load_json(OUTPUT/f'{variant}-build.json')
        check(saved==report,'Build ledger/report is stale')
        hashes[variant]=digest(actual)
        if variant=='english':ledger=report['ledger']
    baseline=ROOT/'build/dungeon-interface/torneko3-dungeon-interface-english.gba'
    hashes['baseline']=digest(baseline.read_bytes())
    check(hashes['baseline']=='d9aebbd3d0753bbd16e2e95680a058dc6440c4df10e867ec7f9f5426a6d2131c','Historical baseline changed')
    for variant in ('english','japanese','baseline'):
        r=load_json(OUTPUT/f'verification/{variant}/verification.json');reports[variant]=r
        check(r['rom_sha256']==hashes[variant] and r['catalog_sha256']==cat_hash,'Native snapshot is stale')
        check(not r['limited'] and r['entries']==262 and r['row_cases']==24 and r['settings_cases']==37 and
              r['fixed_command_cases']==4 and r['natural_route_inputs']==8,'Incomplete native menu coverage')
        check(r['message_cases']==(410 if variant=='english' else 205),'Incomplete message coverage')
        check(r['screens']==(483 if variant=='english' else 278),'Incomplete screenshot coverage')
    from tools.verify_core_gameplay import compare
    compare()
    choice=load_json(OUTPUT/'verification/fixed-choices/report.json')
    check(len(choice['cases'])==9 and choice['rom_sha256']==hashes,'Stale/missing fixed-choice reader checks')
    regression={name:load_json(OUTPUT/'verification'/path) for name,path in {
        'secondary':'secondary-contexts/report.json','items':'items-regression/verification.json',
        'heroes':'hero-details/verification.json','save':'save/verification.json'}.items()}
    check(all(r['rom_sha256']==hashes['english'] for r in regression.values()),'Regression ROM snapshot is stale')
    second=regression['secondary']
    check(len(second['menus'])==14 and len(second['enemy_copy_guards'])==400 and len(second['hero_copy_guards'])==2
          and len(second['natural_search'])==2 and second['concealed_trap'],'Incomplete prior-interface regression')
    check(regression['items']['item_rows']==[1,64,133,190,247,273,304] and len(regression['heroes']['checks'])==4,'Missing item/hero category coverage')
    check(regression['save']['torneko_save_cold_load'] and regression['save']['save_bytes']==65536,'Save/cold-load failed')
    log=(OUTPUT/'unit-tests.log').read_text();match=re.search(r'Ran (\d+) tests',log)
    check(match and int(match[1])>=108 and log.rstrip().endswith('OK'),'Unit suite did not pass')
    for name in ('items.json','enemies.json','item-contexts.json','dungeon-interface.json'):
        check((ROOT/'translations'/name).read_bytes()==(OUTPUT/'before'/name).read_bytes(),f'Earlier catalog changed: {name}')
    master=load_json(ROOT/'translations/master.json');old=load_json(OUTPUT/'before/master.json')
    current={e['id']:e for e in master['entries']}
    for e in old['entries']:
        check(all(current[e['id']][k]==e[k] for k in ('source_hex','english','notes')),'Existing master draft/source changed')
    check(len(current)==9318 and len(current)-len(old['entries'])==5,'Computed-source extraction count differs')
    from tools.extract_master_text import verify_roundtrip
    roundtrip=verify_roundtrip(original,master['entries'])
    glossary=load_json(ROOT/'translations/glossary.json');review=glossary['current_review']
    check(review['id']=='core-gameplay' and review['rom_sha256']==hashes['english'] and
          review['catalogs']['translations/core-gameplay.json']==cat_hash,'Terminology snapshot is stale')
    oldgloss=load_json(OUTPUT/'before/glossary.json');terms={e['id']:e for e in glossary['terms']}
    for t in oldgloss['terms']:
        check(all(terms[t['id']][k]==t[k] for k in ('japanese','english','status','sources','notes')),'Existing glossary term was changed')
    fan=ROOT/'Dragon Quest Characters - Torneko no Daibouken 3 Advance - Fushigi no Dungeon (Japan) [T-En by Sam Steel v0.05] [i].gba'
    fan_hash=digest(fan.read_bytes());check(fan_hash=='e7108d76a0c9c3a40b3eb52dc622cfe9ac9f08e673d3f43e0996815cebf7a93f','Reference ROM changed')
    summary={'status':'passed','source_sha256':digest(original),'reference_sha256':fan_hash,'rom_sha256':hashes,
             'catalog_entries':262,'new_entries':259,'shared_curated_entries':3,'message_templates':205,
             'english_message_cases':410,'english_screens':483,'japanese_pixel_pairs':278,'native_choice_reader_calls':9,
             'unit_tests':int(match[1]),'enemy_copy_guards':400,'hero_copy_guards':2,'secondary_action_menus':14,
             'natural_ground_search_protagonists':2,'item_inventory_information_screens':14,'hero_detail_screens':4,
             'save_bytes':65536,'master_entries':len(current),'new_master_sources':5,'master_roundtrip_sha256':roundtrip,
             'appended_used_with_padding':ledger['appended_used_with_padding'],'appended_remaining':ledger['appended_remaining'],
             'new_appended_bytes':ledger['appended_used_with_padding']-56195,'allocations':len(ledger['allocations']),
             'original_patch_ranges':len(ledger['patches']),
             'catalog_file_sha256':{p.name:digest(p.read_bytes()) for p in (ROOT/'translations').glob('*.json')},
             'terminology_review_sha256':digest((ROOT/'translations/core-gameplay-terminology-review.tsv').read_bytes()),
             'limits':reports['english']['scope']+' Direct label/choice rows do not exercise all original caller layouts or actions. Help bodies, other message blocks, story, shops and natural effect progression remain separate.'}
    write_json(OUTPUT/'acceptance.json',summary)
    print(json.dumps({k:v for k,v in summary.items() if k!='catalog_file_sha256'},indent=2))
    return summary


def verify_all():
    from tools.verify_core_gameplay import verify,verify_choice_readers,STATE
    from tools.verify_dungeon_contexts import verify as secondary
    from tools.verify_enemy_items import verify as items
    from tools.verify_enemies import verify as enemies
    from tools.extract_master_text import extract
    build()
    with (OUTPUT/'unit-tests.log').open('w') as log:
        subprocess.run([sys.executable,'-m','unittest','discover','-s','tests'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
    for variant in ('english','japanese','baseline'):verify(variant)
    verify_choice_readers()
    rom=OUTPUT/'torneko3-core-gameplay-english.gba'
    secondary(rom,OUTPUT/'verification/secondary-contexts',STATE)
    items(rom,OUTPUT/'verification/items-regression','items',state_path=STATE,rows=[1,64,133,190,247,273,304])
    enemies(rom,OUTPUT/'verification/hero-details',state_path=STATE,rows=[0,198])
    items(rom,OUTPUT/'verification/save','save')
    extract()
    return summarize()


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--summarize-only',action='store_true')
    summarize() if p.parse_args().summarize_only else verify_all()
