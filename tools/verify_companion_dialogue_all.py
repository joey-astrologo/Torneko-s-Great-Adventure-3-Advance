"""Rebuild and audit complete companion dialogue with earlier UI/save regressions."""
import argparse
import csv
import json
import re
import struct
import subprocess
import sys
from tools import build_ally_dialogue as prior
from tools.build_companion_dialogue import CATALOG,OUTPUT,TABLE,ALTERNATES,build,build_rom,validate_catalog
from tools.build_first_label import ORIGINAL_ROM,ROOT,digest
from tools.translation_pipeline import atomic_write,check,load_json
from tools.verify_items import write_json


def summarize():
    from tools.verify_companion_dialogue import BASELINE,STATE,compare,profiles
    original=ORIGINAL_ROM.read_bytes();catalog=load_json(CATALOG);entries=validate_catalog(original,catalog)
    catalog_hash=digest(CATALOG.read_bytes());hashes={}
    check(digest(original)=='35bfff00dccd8de1a916b316298219c8c16a8adb0162ffe5056c481e0a8a4d02','Original changed')
    for variant in ('english','japanese'):
        data,report=build_rom(original,variant)
        check(data==(OUTPUT/f'torneko3-companion-dialogue-{variant}.gba').read_bytes(),'ROM differs from rebuild')
        check(report==load_json(OUTPUT/f'{variant}-build.json'),'Build ledger stale')
        hashes[variant]=digest(data)
        if variant=='english':english,english_report,ledger=data,report,report['ledger']
    hashes['baseline']=digest(BASELINE.read_bytes())
    helpers={k:digest((ROOT/'tools'/p).read_bytes()) for k,p in {
        'harness_sha256':'verify_companion_dialogue.py','page_helper_sha256':'verify_ally_dialogue.py',
        'queue_helper_sha256':'verify_tutorial_gameplay.py'}.items()}
    state_hash=digest(STATE.read_bytes());native={v:load_json(OUTPUT/f'verification/{v}/verification.json') for v in hashes}
    expected_health={(r,hp,counter,rand) for r in range(200) for hp in (39,40,79,80)
        for counter in ((0,3,4) if r in (191,192) else (0,))
        for rand in ((0,) if counter==4 else range(5) if r in (191,192) else (0,99))}
    expected_levels={(r,entry,rand) for r in range(200) for entry in ('0x8025eda','0x80378c0')
        for rand in range(4 if r in (191,192) else 2)}
    expected_overrides={(f,flag) for f in (*range(20),-1,20) for flag in (False,True) if flag or 0<=f<20}
    for variant,r in native.items():
        check(r['source_sha256']==digest(original) and r['rom_sha256']==hashes[variant] and r['catalog_sha256']==catalog_hash,'Stale native artifact')
        check(all(r[k]==v for k,v in helpers.items()) and r['fixture_state_sha256']==state_hash and not r['limited'],'Stale/limited fixture')
        expected={(e['id'],p) for e in entries.values() for p in profiles(e,variant)}
        check(len(r['cases'])==len(expected) and {(c['id'],c['profile']) for c in r['cases']}==expected,'Incomplete dialogue profiles')
        check(len(r['cold_initialized_tables'])==4,'Missing cold pointer tables')
        rules=r['response_rules'];health=rules['health'];levels=rules['level_up'];alternates=rules['rosa_overrides']
        check(len(health)==1672 and {(c['row'],c['hp'],c['counter_before'],c['random_value']) for c in health}==expected_health,'Incomplete HP/counter/choice boundaries')
        for c in health:
            special=c['row'] in (191,192);counter=c['counter_before'];band=2 if c['hp']<40 else 1 if c['hp']<80 else 0
            expected=(19 if counter==4 else band*5+c['random_value']) if special else band*2+(c['random_value']<50)
            check(c['max_hp']==100 and c['response']==expected and c['counter_after']==counter+int(special),'Wrong response/counter')
            check(len(c['random_calls'])==(0 if counter==4 else 1),'Wrong native PRNG use')
        check(len(levels)==808 and {(c['row'],c['entry'],c['random_value']) for c in levels}==expected_levels,'Incomplete level-up choices')
        check(all(c['response']==(15 if c['row'] in (191,192) else 6)+c['random_value'] for c in levels),'Wrong level-up response')
        check(len(alternates)==42 and {(c['response'],c['controlled_rosa_flag']) for c in alternates}==expected_overrides,'Incomplete Rosa condition/clamp')
        rom=(BASELINE if variant=='baseline' else OUTPUT/f'torneko3-companion-dialogue-{variant}.gba').read_bytes()
        for c in alternates:
            at=ALTERNATES+max(0,min(2,int(c['response']/5)))*4 if c['controlled_rosa_flag'] else TABLE+191*80+c['response']*4
            check(int(c['source'],0)==struct.unpack_from('<I',rom,at)[0],'Wrong Rosa pointer')
        for c in r['cases']:
            e=entries[c['id']];expected=struct.unpack_from('<I',rom,int(e['pointer_offset'],0))[0]
            check(c['guards_intact'] and int(c['source'],0)==expected and c['selector']['source']==c['source'],'Missing guarded native selector')
            if c['profile']!='narrow':
                check(c['native_stack_flags']==[0,1,1] and c['pages']>=1,'Wrong dialogue caller layout')
                detail=load_json(OUTPUT/f'verification/{variant}/{c["id"]}-{c["profile"]}.json')
                check(len(detail['pages'])==c['pages'] and len(c['screens'])==c['pages'],'Incomplete display pages')
                if variant=='english':check(all(p['checks'] for p in detail['pages']),'Missing English glyph checks')
        check(all((OUTPUT/f'verification/{variant}'/s).is_file() for s in r['screens']),'Missing native screen')
    pairs=compare()
    history=english_report['history'];changed=set(history['changed_ids'])
    check(len(history['messages'])==311 and len(changed)==16,'Prior history scope changed')
    expected={(e['id'],p) for e in history['messages'] for p in ('normal','stress','narrow')}
    cases=native['english']['history_cases']
    check(len(cases)==933 and {(c['id'],c['profile']) for c in cases}==expected,'Incomplete earlier history profiles')
    for c in cases:
        check(c['queue']['guards_intact'] and c['changed']==(c['id'] in changed),'History guard/change mismatch')
        for raw_hex,hist_hex in zip(c['queue']['rows_hex'],c['queue']['history_hex'],strict=True):
            row=bytes.fromhex(raw_hex);record=bytes.fromhex(hist_hex)
            check(len(row)<=60 and record[3:].split(b'\0')[0]+b'\0'==row,'History lost payload')
        if c['changed'] and c['profile']!='narrow':check(c['checks'] and c['screens'],'Missing history reflow display')
    old_cases=native['english']['prior_dialogue_cases']
    check(len(old_cases)==8 and {(c['row'],c['field']) for c in old_cases}=={(r,f) for r in (1,18,35,50) for f in (0,7)} and all(c['guards_intact'] and c['pages']==1 for c in old_cases),'Missing prior dialogue regression')
    old_report=load_json(prior.OUTPUT/'english-build.json');old=BASELINE.read_bytes();allocations={a['id']:a for a in ledger['allocations']}
    for a in old_report['ledger']['allocations']:
        check(allocations[a['id']]==a,'Prior allocation changed');at,size=a['offset'],a['bytes']
        check(english[at:at+size]==old[at:at+size],'Prior payload changed')
    check(ledger['patches'][:len(old_report['ledger']['patches'])]==old_report['ledger']['patches'],'Prior patch ledger changed')
    for p in old_report['ledger']['patches']:
        at=p['offset'];raw=bytes.fromhex(p['after']);check(english[at:at+len(raw)]==raw,'Prior original patch changed')
    owned={int(e['pointer_offset'],0) for e in entries.values()}
    old_owned={int(e['pointer_offset'],0) for e in load_json(prior.CATALOG)['entries']}
    expected={p for p in range(TABLE,TABLE+200*80,4) if struct.unpack_from('<I',original,p)[0]}
    check(len(expected)==1624 and not owned&old_owned and owned|old_owned==expected|set(range(ALTERNATES,ALTERNATES+12,4)),'Combined dialogue ownership incomplete')
    for at in range(TABLE,TABLE+200*80,4):
        if at not in owned:check(english[at:at+4]==old[at:at+4],'Unowned/null dialogue word changed')
    check(ledger['memory_reservations']==old_report['ledger']['memory_reservations'],'RAM/save reservations changed')
    check(english_report['history']==old_report['history'] and english_report['prior_dialogue']==old_report['dialogue'],'Prior component reports changed')
    regression={name:load_json(OUTPUT/'verification'/p) for name,p in {'secondary':'secondary-contexts/report.json','items':'items-regression/verification.json','heroes':'hero-details/verification.json','save':'save/verification.json'}.items()}
    check(all(r['rom_sha256']==hashes['english'] for r in regression.values()),'Stale UI/save regression')
    r=regression['secondary'];check(len(r['menus'])==14 and len(r['enemy_copy_guards'])==400 and len(r['hero_copy_guards'])==2 and len(r['natural_search'])==2 and r['concealed_trap'],'Incomplete prior UI checks')
    check(regression['items']['item_rows']==[1,64,133,190,247,273,304] and len(regression['heroes']['checks'])==4,'Missing item/hero checks')
    check(regression['save']['torneko_save_cold_load'] and regression['save']['save_bytes']==65536,'Save/cold-load failed')
    log=(OUTPUT/'unit-tests.log').read_text();match=re.search(r'Ran (\d+) tests',log)
    check(match and int(match[1])>=150 and log.rstrip().endswith('OK'),'Unit tests failed')
    frozen=[]
    for p in (OUTPUT/'before').glob('*.json'):
        if p.name in ('master.json','glossary.json'):continue
        check((ROOT/'translations'/p.name).read_bytes()==p.read_bytes(),f'Prior catalog changed: {p.name}');frozen.append(p.name)
    master=load_json(ROOT/'translations/master.json');before=load_json(OUTPUT/'before/master.json');current={e['id']:e for e in master['entries']}
    check(len(current)==len(before['entries'])==9318,'Source inventory count changed')
    for e in before['entries']:check(all(current[e['id']][k]==e[k] for k in ('source_hex','english','notes')),'Prior master source/draft changed')
    from tools.extract_master_text import verify_roundtrip
    roundtrip=verify_roundtrip(original,master['entries'])
    check('companion-dialogue.json' in master['english_authority'],'Missing new insertion authority')
    browser=(ROOT/'build/text-extraction/index.html').read_text()
    check(all(e['id'] in browser for e in entries.values()),'Missing dialogue browser overlay')
    glossary=load_json(ROOT/'translations/glossary.json');review=glossary['current_review'];terms={t['id']:t for t in glossary['terms']}
    check(len(terms)==1089 and review['id']=='companion-dialogue' and review['rom_sha256']==hashes['english'] and review['catalogs']['translations/companion-dialogue.json']==catalog_hash,'Terminology snapshot stale')
    old_terms=load_json(OUTPUT/'before/glossary.json')['terms']
    for t in old_terms:check(all(terms[t['id']][k]==t[k] for k in ('japanese','english','status','sources','notes')),'Existing term identity/confidence changed')
    check(set(terms)-{t['id'] for t in old_terms}==set(review['new_terms'])=={'spell.kazap','ability.blade_of_ultimate_power','character.estark','placeholder.paulo'},'New term scope differs')
    with (ROOT/'translations/companion-dialogue-terminology-review.tsv').open() as f:rows=list(csv.DictReader(f,delimiter='\t'))
    check(len(rows)==len(entries) and {r['id'] for r in rows}==entries.keys(),'Review sheet incomplete')
    for row in rows:
        e=entries[row['id']];check(row['japanese']==e['japanese'] and row['full_english']==e['english'].replace('\n','<LF>') and row['display']==(e['display'] or ''),'Review sheet stale')
        check(row['glossary_references'] and all(ref in terms for ref in row['glossary_references'].split(',')),'Unknown terminology reference')
    fan=ROOT/'Dragon Quest Characters - Torneko no Daibouken 3 Advance - Fushigi no Dungeon (Japan) [T-En by Sam Steel v0.05] [i].gba';fan_hash=digest(fan.read_bytes())
    check(fan_hash=='e7108d76a0c9c3a40b3eb52dc622cfe9ac9f08e673d3f43e0996815cebf7a93f','Reference ROM changed')
    review['status']='translated_inserted_automated_acceptance_passed'
    for ident in review['new_terms']:
        terms[ident]['insertion_status']='inserted_controlled_native_verified'
        terms[ident]['insertion_evidence']={'rom_sha256':hashes['english'],'report':'build/companion-dialogue/acceptance.json',
            'scope':'Native source selection, guarded substitution and page rendering. Official-name confidence remains separate; reserved/test source reachability is unverified.'}
    atomic_write(ROOT/'translations/glossary.json',(json.dumps(glossary,ensure_ascii=False,indent=2)+'\n').encode())
    result={'status':'passed','source_sha256':digest(original),'reference_sha256':fan_hash,'rom_sha256':hashes,
        'catalog_entries':1227,'new_main_table_entries':1224,'rosa_alternatives':3,'combined_main_table_entries':1624,'remaining_main_table_entries':0,
        'main_table_rows':200,'reserved_test_style_sources':48,'untranslated_distinct_default_nicknames':198,
        'english_native_dialogue_cases':len(native['english']['cases']),'english_dialogue_screens':sum(len(c['screens']) for c in native['english']['cases']),
        'english_total_screens':len(native['english']['screens']),'japanese_pixel_pairs':pairs,
        'native_health_counter_choices_per_variant':1672,'native_level_up_choices_per_variant':808,'rosa_override_choices_per_variant':42,
        'cold_initialized_pointer_tables_per_variant':4,'earlier_history_messages':311,'earlier_history_native_cases':933,'history_reflowed_messages':16,'earlier_dialogue_display_cases':8,
        'earlier_allocations_payloads_and_patches_preserved':True,'frozen_prior_catalogs':sorted(frozen),'unit_tests':int(match[1]),
        'enemy_copy_guards':400,'hero_copy_guards':2,'secondary_action_menus':14,'natural_ground_search_routes':2,'item_inventory_information_screens':14,'hero_detail_screens':4,'save_bytes':65536,
        'master_entries':len(current),'master_roundtrip_sha256':roundtrip,'glossary_terms':len(terms),
        'appended_used_with_padding':ledger['appended_used_with_padding'],'appended_remaining':ledger['appended_remaining'],
        'new_appended_bytes':ledger['appended_used_with_padding']-old_report['ledger']['appended_used_with_padding'],'allocations':len(ledger['allocations']),'original_patch_ranges':len(ledger['patches']),
        'catalog_file_sha256':{p.name:digest(p.read_bytes()) for p in (ROOT/'translations').glob('*.json')},**helpers,'fixture_state_sha256':state_hash,
        'terminology_review_sha256':digest((ROOT/'translations/companion-dialogue-terminology-review.tsv').read_bytes()),
        'limits':native['english']['scope']+' The 48 reserved/test-style sources are preserved without claiming natural use. Default nicknames remain Japanese; supplied species slots do not establish nickname copying or save/ranking compatibility.'}
    write_json(OUTPUT/'acceptance.json',result);print(json.dumps({k:v for k,v in result.items() if k!='catalog_file_sha256'},indent=2));return result


def verify_all():
    from tools.verify_companion_dialogue import verify,STATE
    from tools.verify_dungeon_contexts import verify as secondary
    from tools.verify_enemy_items import verify as items
    from tools.verify_enemies import verify as enemies
    from tools.extract_master_text import extract
    build()
    with (OUTPUT/'unit-tests.log').open('w') as log:subprocess.run([sys.executable,'-m','unittest','discover','-s','tests'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
    for variant in ('english','japanese','baseline'):verify(variant)
    rom=OUTPUT/'torneko3-companion-dialogue-english.gba'
    secondary(rom,OUTPUT/'verification/secondary-contexts',STATE)
    items(rom,OUTPUT/'verification/items-regression','items',state_path=STATE,rows=[1,64,133,190,247,273,304])
    enemies(rom,OUTPUT/'verification/hero-details',state_path=STATE,rows=[0,198])
    items(rom,OUTPUT/'verification/save','save');extract();return summarize()


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--summarize-only',action='store_true')
    summarize() if p.parse_args().summarize_only else verify_all()
