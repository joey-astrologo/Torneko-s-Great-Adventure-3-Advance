"""Reproduce and audit the complete gameplay-help milestone."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
from PIL import Image, ImageChops
from tools.build_gameplay_help import CATALOG, OUTPUT, build, build_rom
from tools.build_first_label import ORIGINAL_ROM, ROOT, digest
from tools.translation_pipeline import check, load_json, atomic_write
from tools.verify_items import write_json


def summarize():
    original = ORIGINAL_ROM.read_bytes(); catalog_hash = digest(CATALOG.read_bytes())
    hashes = {}; ledger = None
    for variant in ('english', 'japanese'):
        data, fresh = build_rom(original, variant)
        check(data == (OUTPUT/f'torneko3-gameplay-help-{variant}.gba').read_bytes(), 'Delivered ROM differs from rebuild')
        report = load_json(OUTPUT/f'{variant}-build.json')
        check(report == fresh, 'Build ledger is stale')
        hashes[variant] = digest(data)
        if variant == 'english': ledger = report['ledger']
    from tools.verify_gameplay_help import BASELINE, compare
    hashes['baseline'] = digest(BASELINE.read_bytes())
    for variant in hashes:
        report = load_json(OUTPUT/f'verification/{variant}/verification.json')
        check(report['rom_sha256'] == hashes[variant] and report['catalog_sha256'] == catalog_hash, 'Native snapshot is stale')
        check(not report['limited'] and report['counts'] == {'help':10,'message':106,'status':68}, 'Incomplete catalog coverage')
        check(report['screens'] == (369 if variant=='english' else 185), 'Incomplete screen coverage')
        check(len(report['orders']['guards']) == 7 and len(report['orders']['payloads']) == 7, 'Incomplete order reader coverage')
        natural = load_json(OUTPUT/f'verification/natural/{variant}/verification.json')
        check(natural['rom_sha256'] == hashes[variant] and natural['catalog_sha256'] == catalog_hash and
              natural['screens'] == 12 and len(natural['help_pages']) == 2, 'Natural route is stale/incomplete')
    paired = compare()['pixel_pairs']
    for i in range(12):
        a = OUTPUT/f'verification/natural/japanese/route-{i:02d}.png'
        b = OUTPUT/f'verification/natural/baseline/route-{i:02d}.png'
        with Image.open(a) as x, Image.open(b) as y:
            check(ImageChops.difference(x.convert('RGB'),y.convert('RGB')).getbbox() is None, 'Natural Japanese route changed')
    regression = {name:load_json(OUTPUT/'verification'/path) for name,path in {
        'secondary':'secondary-contexts/report.json','items':'items-regression/verification.json',
        'heroes':'hero-details/verification.json','save':'save/verification.json'}.items()}
    check(all(r['rom_sha256'] == hashes['english'] for r in regression.values()), 'Regression ROM is stale')
    second = regression['secondary']
    check(len(second['menus'])==14 and len(second['enemy_copy_guards'])==400 and len(second['hero_copy_guards'])==2
          and len(second['natural_search'])==2 and second['concealed_trap'], 'Prior-interface regression incomplete')
    check(regression['items']['item_rows']==[1,64,133,190,247,273,304] and len(regression['heroes']['checks'])==4, 'Missing category coverage')
    check(regression['save']['torneko_save_cold_load'] and regression['save']['save_bytes']==65536, 'Save/cold-load failed')
    log = (OUTPUT/'unit-tests.log').read_text(); match = re.search(r'Ran (\d+) tests',log)
    check(match and int(match[1])>=115 and log.rstrip().endswith('OK'), 'Unit tests did not pass')
    for name in ('items','enemies','item-contexts','dungeon-interface','core-gameplay'):
        check((ROOT/f'translations/{name}.json').read_bytes()==(OUTPUT/f'before/{name}.json').read_bytes(), f'Earlier catalog changed: {name}')
    master = load_json(ROOT/'translations/master.json'); old = load_json(OUTPUT/'before/master.json')
    current = {e['id']:e for e in master['entries']}
    check(len(current)==len(old['entries'])==9318, 'Unexpected source inventory change')
    for e in old['entries']:
        check(all(current[e['id']][k]==e[k] for k in ('source_hex','english','notes')), 'Prior draft/source changed')
    from tools.extract_master_text import verify_roundtrip
    roundtrip = verify_roundtrip(original,master['entries'])
    glossary = load_json(ROOT/'translations/glossary.json'); review = glossary['current_review']
    check(review['id']=='gameplay-help' and review['rom_sha256']==hashes['english'] and
          review['catalogs']['translations/gameplay-help.json']==catalog_hash, 'Terminology snapshot is stale')
    terms = {t['id']:t for t in glossary['terms']}
    for t in load_json(OUTPUT/'before/glossary.json')['terms']:
        check(all(terms[t['id']][k]==t[k] for k in ('japanese','english','status','sources','notes')), 'Existing term changed')
    fan = ROOT/'Dragon Quest Characters - Torneko no Daibouken 3 Advance - Fushigi no Dungeon (Japan) [T-En by Sam Steel v0.05] [i].gba'
    fan_hash = digest(fan.read_bytes())
    check(fan_hash=='e7108d76a0c9c3a40b3eb52dc622cfe9ac9f08e673d3f43e0996815cebf7a93f', 'Reference ROM changed')
    # Mark terminology insertion verified only after every check above passes.
    review['status'] = 'translated_inserted_automated_acceptance_passed'
    for t in glossary['terms']:
        if t.get('batch')=='gameplay-help':
            t['insertion_status']='inserted_controlled_native_verified'
            t['insertion_evidence']={'rom_sha256':hashes['english'],'report':'build/gameplay-help/acceptance.json',
                'scope':'Controlled native display/copy checks; naming evidence and natural mechanics remain separately qualified.'}
    atomic_write(ROOT/'translations/glossary.json',(json.dumps(glossary,ensure_ascii=False,indent=2)+'\n').encode())
    summary = {'status':'passed','source_sha256':digest(original),'reference_sha256':fan_hash,'rom_sha256':hashes,
        'catalog_entries':191,'families':{'help':10,'order':7,'status':68,'message':106},
        'english_screens':381,'japanese_pixel_pairs':paired+12,'native_status_table_rows':64,
        'native_order_rows':7,'conditional_status_literals':4,'unit_tests':int(match[1]),
        'enemy_copy_guards':400,'hero_copy_guards':2,'secondary_action_menus':14,
        'item_inventory_information_screens':14,'hero_detail_screens':4,'save_bytes':65536,
        'master_entries':len(current),'master_roundtrip_sha256':roundtrip,
        'appended_used_with_padding':ledger['appended_used_with_padding'],'appended_remaining':ledger['appended_remaining'],
        'new_appended_bytes':ledger['appended_used_with_padding']-63084,'allocations':len(ledger['allocations']),
        'original_patch_ranges':len(ledger['patches']),
        'catalog_file_sha256':{p.name:digest(p.read_bytes()) for p in (ROOT/'translations').glob('*.json')},
        'terminology_review_sha256':digest((ROOT/'translations/gameplay-help-terminology-review.tsv').read_bytes()),
        'limits':'Controlled native row/message fixtures do not establish every natural status, ally order, shop branch or message caller. Natural world help navigation and save/cold-load are covered. Original duplicate speed summary and reserved status row are documented; no gameplay logic is changed.'}
    write_json(OUTPUT/'acceptance.json',summary)
    print(json.dumps({k:v for k,v in summary.items() if k!='catalog_file_sha256'},indent=2))
    return summary


def verify_all():
    from tools.verify_gameplay_help import verify, natural_routes, STATE
    from tools.verify_dungeon_contexts import verify as secondary
    from tools.verify_enemy_items import verify as items
    from tools.verify_enemies import verify as enemies
    from tools.extract_master_text import extract
    build()
    with (OUTPUT/'unit-tests.log').open('w') as log:
        subprocess.run([sys.executable,'-m','unittest','discover','-s','tests'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
    for variant in ('english','japanese','baseline'):
        verify(variant); natural_routes(variant)
    rom = OUTPUT/'torneko3-gameplay-help-english.gba'
    secondary(rom,OUTPUT/'verification/secondary-contexts',STATE)
    items(rom,OUTPUT/'verification/items-regression','items',state_path=STATE,rows=[1,64,133,190,247,273,304])
    enemies(rom,OUTPUT/'verification/hero-details',state_path=STATE,rows=[0,198])
    items(rom,OUTPUT/'verification/save','save')
    extract()
    return summarize()


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--summarize-only',action='store_true')
    summarize() if p.parse_args().summarize_only else verify_all()
