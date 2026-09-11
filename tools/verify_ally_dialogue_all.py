"""Rebuild and audit the complete ally dialogue/history milestone."""
import argparse
import csv
import json
from pathlib import Path
import re
import subprocess
import sys
from tools.build_ally_dialogue import CATALOG,OUTPUT,TABLE,build,build_rom
from tools.build_first_label import ORIGINAL_ROM,ROOT,digest
from tools.translation_pipeline import atomic_write,check,load_json
from tools.verify_items import write_json


def summarize():
    original=ORIGINAL_ROM.read_bytes();catalog=load_json(CATALOG);catalog_hash=digest(CATALOG.read_bytes());hashes={}
    check(digest(original)=='35bfff00dccd8de1a916b316298219c8c16a8adb0162ffe5056c481e0a8a4d02','Original changed')
    for variant in ('english','japanese'):
        data,report=build_rom(original,variant)
        check(data==(OUTPUT/f'torneko3-ally-dialogue-{variant}.gba').read_bytes(),'ROM differs from rebuild')
        check(report==load_json(OUTPUT/f'{variant}-build.json'),'Build ledger stale')
        hashes[variant]=digest(data)
        if variant=='english':english,english_report,ledger=data,report,report['ledger']
    from tools.verify_ally_dialogue import BASELINE,STATE,compare
    hashes['baseline']=digest(BASELINE.read_bytes());harness_hash=digest((ROOT/'tools/verify_ally_dialogue.py').read_bytes())
    helper_hash=digest((ROOT/'tools/verify_tutorial_gameplay.py').read_bytes());state_hash=digest(STATE.read_bytes())
    native={v:load_json(OUTPUT/f'verification/{v}/verification.json') for v in hashes}
    entries={e['id']:e for e in catalog['entries']}
    check(len(entries)==400 and {(e['row'],e['field']) for e in entries.values()}=={(r,f) for r in range(1,51) for f in range(8)},'Incomplete eight-response sets')
    expected_health={(r,hp,rand) for r in range(1,51) for hp in (39,40,79,80) for rand in (0,99)}
    for v,r in native.items():
        check(r['rom_sha256']==hashes[v] and r['catalog_sha256']==catalog_hash and r['harness_sha256']==harness_hash,'Stale native artifact')
        check(r['page_helper_sha256']==helper_hash and r['fixture_state_sha256']==state_hash and not r['limited'],'Stale/limited fixture')
        expected={(ident,p) for ident in entries for p in (('normal','stress','narrow') if v=='english' else ('normal',))}
        check(len(r['cases'])==len(expected) and {(c['id'],c['profile']) for c in r['cases']}==expected,'Incomplete dialogue profiles')
        check(len(r['cold_initialized_tables'])==4,'Missing cold pointer tables')
        health=r['health_selectors']
        check(len(health)==400 and {(c['row'],c['hp'],c['controlled_random_result']) for c in health}==expected_health,'Incomplete HP/choice boundaries')
        for c in health:
            check(c['max_hp']==100 and c['response']==(4 if c['hp']<40 else 2 if c['hp']<80 else 0)+(c['controlled_random_result']<50),'Wrong health response')
        for c in r['cases']:
            check(c['guards_intact'] and c['selector']['source']==c['source'],'Missing guarded native selector')
            if c['profile']!='narrow':
                check(c['native_stack_flags']==[0,1,1] and c['pages']>=1,'Wrong ally wrapper layout')
                if v=='english':
                    detail=load_json(OUTPUT/f'verification/{v}/{c["id"]}-{c["profile"]}.json')
                    check(len(detail['pages'])==c['pages'] and all(p['checks'] for p in detail['pages']),'Missing English glyph checks')
        check(all((OUTPUT/f'verification/{v}'/s).is_file() for s in r['screens']),'Missing native screen')
    pairs=compare()
    history=english_report['history'];changed=set(history['changed_ids'])
    expected_old={e['id'] for e in load_json(ROOT/'build/tutorial-gameplay/research/earlier-history-audit.json')['lines']}
    check(len(history['messages'])==311 and changed==expected_old and len(changed)==16,'History audit scope changed')
    expected={(e['id'],p) for e in history['messages'] for p in ('normal','stress','narrow')}
    cases=native['english']['history_cases']
    check(len(cases)==933 and {(c['id'],c['profile']) for c in cases}==expected,'Incomplete earlier history profiles')
    for c in cases:
        check(c['queue']['guards_intact'] and c['changed']==(c['id'] in changed),'History guard/change mismatch')
        for raw_hex,hist_hex in zip(c['queue']['rows_hex'],c['queue']['history_hex'],strict=True):
            row=bytes.fromhex(raw_hex);record=bytes.fromhex(hist_hex)
            check(len(row)<=60 and record[3:].split(b'\0')[0]+b'\0'==row,'History lost payload')
        if c['changed'] and c['profile']!='narrow':check(c['checks'] and c['screens'],'Missing reflow display check')
    for e in history['messages']:
        check(e['display_template'].split()==e['old_display'].split(),'Reflow changed wording')
        check(len(bytes.fromhex(e['raw_hex']))==len(bytes.fromhex(e['old_raw_hex'])),'Reflow moved an allocation')
        check(all(n<=59 for n in e['history_payload_upper_bounds']),'History bound exceeds capacity')
    before=load_json(OUTPUT/'verification/history-before/verification.json')
    check(before['rom_sha256']==hashes['baseline'] and before['fixed_rom_sha256']==hashes['english'] and before['fixture_state_sha256']==state_hash,'Stale before/fixed comparison')
    check(len(before['cases'])==16 and {c['id'] for c in before['cases']}==changed and all(c['truncated_rows'] for c in before['cases']),'Old truncation not reproduced')
    prior=load_json(ROOT/'build/tutorial-gameplay/english-build.json');old=BASELINE.read_bytes();allocations={a['id']:a for a in ledger['allocations']}
    for a in prior['ledger']['allocations']:
        n=allocations[a['id']];at,size=a['offset'],a['bytes']
        check((n['offset'],n['bytes'],n['owner'])==(at,size,a['owner']),'Earlier ownership/address changed')
        check((english[at:at+size]!=old[at:at+size])==(a['id'] in changed),'Unexpected prior payload revision')
    for p in prior['ledger']['patches']:
        at=p['offset'];raw=bytes.fromhex(p['after']);check(english[at:at+len(raw)]==raw,'Earlier original patch changed')
    owned={int(e['pointer_offset'],0) for e in entries.values()}
    for at in range(TABLE,TABLE+200*80,4):
        if at not in owned:check(english[at:at+4]==old[at:at+4],'Unowned ally pointer changed')
    check(ledger['memory_reservations']==prior['ledger']['memory_reservations'],'RAM/save reservations changed')
    regression={name:load_json(OUTPUT/'verification'/p) for name,p in {'secondary':'secondary-contexts/report.json','items':'items-regression/verification.json','heroes':'hero-details/verification.json','save':'save/verification.json'}.items()}
    check(all(r['rom_sha256']==hashes['english'] for r in regression.values()),'Stale prior UI/save regression')
    r=regression['secondary'];check(len(r['menus'])==14 and len(r['enemy_copy_guards'])==400 and len(r['hero_copy_guards'])==2 and len(r['natural_search'])==2 and r['concealed_trap'],'Incomplete prior UI checks')
    check(regression['items']['item_rows']==[1,64,133,190,247,273,304] and len(regression['heroes']['checks'])==4,'Missing item/hero checks')
    check(regression['save']['torneko_save_cold_load'] and regression['save']['save_bytes']==65536,'Save/cold-load failed')
    log=(OUTPUT/'unit-tests.log').read_text();match=re.search(r'Ran (\d+) tests',log)
    check(match and int(match[1])>=141 and log.rstrip().endswith('OK'),'Unit tests failed')
    for name in ('items','enemies','item-contexts','dungeon-interface','core-gameplay','gameplay-help','ally-services','tutorial-gameplay'):
        check((ROOT/f'translations/{name}.json').read_bytes()==(OUTPUT/f'before/{name}.json').read_bytes(),f'Prior catalog changed: {name}')
    master=load_json(ROOT/'translations/master.json');before=load_json(OUTPUT/'before/master.json');current={e['id']:e for e in master['entries']}
    check(len(current)==len(before['entries'])==9318,'Source inventory count changed')
    for e in before['entries']:check(all(current[e['id']][k]==e[k] for k in ('source_hex','english','notes')),'Prior source/draft changed')
    from tools.extract_master_text import verify_roundtrip
    roundtrip=verify_roundtrip(original,master['entries'])
    check('ally-dialogue.json' in master['english_authority'],'Missing new insertion authority')
    browser=(ROOT/'build/text-extraction/index.html').read_text()
    check(all(e['id'] in browser for e in entries.values()),'Missing dialogue browser overlay')
    glossary=load_json(ROOT/'translations/glossary.json');review=glossary['current_review'];terms={t['id']:t for t in glossary['terms']}
    check(len(terms)==1085 and review['id']=='ally-dialogue' and review['rom_sha256']==hashes['english'] and review['catalogs']['translations/ally-dialogue.json']==catalog_hash,'Terminology snapshot stale')
    for t in load_json(OUTPUT/'before/glossary.json')['terms']:check(all(terms[t['id']][k]==t[k] for k in ('japanese','english','status','sources','notes')),'Existing term identity/confidence changed')
    with (ROOT/'translations/ally-dialogue-terminology-review.tsv').open() as f:rows=list(csv.DictReader(f,delimiter='\t'))
    check(len(rows)==len(entries) and {r['id'] for r in rows}==entries.keys(),'Review sheet incomplete')
    for row in rows:
        e=entries[row['id']];check(row['japanese']==e['japanese'] and row['full_english']==e['english'].replace('\n','<LF>') and row['display']==(e['display'] or ''),'Review sheet stale')
        check(row['glossary_references'] and all(ref in terms for ref in row['glossary_references'].split(',')),'Unknown terminology reference')
    with (ROOT/'translations/ally-dialogue-history-review.tsv').open() as f:rows=list(csv.DictReader(f,delimiter='\t'))
    check(len(rows)==16 and {r['id'] for r in rows}==changed,'History review incomplete')
    fan=ROOT/'Dragon Quest Characters - Torneko no Daibouken 3 Advance - Fushigi no Dungeon (Japan) [T-En by Sam Steel v0.05] [i].gba';fan_hash=digest(fan.read_bytes())
    check(fan_hash=='e7108d76a0c9c3a40b3eb52dc622cfe9ac9f08e673d3f43e0996815cebf7a93f','Reference ROM changed')
    review['status']='translated_inserted_automated_acceptance_passed'
    atomic_write(ROOT/'translations/glossary.json',(json.dumps(glossary,ensure_ascii=False,indent=2)+'\n').encode())
    result={'status':'passed','source_sha256':digest(original),'reference_sha256':fan_hash,'rom_sha256':hashes,
        'catalog_entries':400,'complete_species_sets':50,'responses_per_species':8,'remaining_extracted_dialogue_entries':1224,
        'english_native_dialogue_cases':len(native['english']['cases']),'english_dialogue_screens':sum(len(c['screens']) for c in native['english']['cases']),
        'english_total_screens':len(native['english']['screens']),'japanese_pixel_pairs':pairs,'native_health_boundary_choices_per_variant':400,
        'cold_initialized_pointer_tables_per_variant':4,'earlier_history_messages':311,'earlier_history_native_cases':933,'history_reflowed_messages':16,
        'before_truncation_reproductions':16,'earlier_allocations_and_patches_preserved':True,'unit_tests':int(match[1]),
        'enemy_copy_guards':400,'hero_copy_guards':2,'secondary_action_menus':14,'natural_ground_search_routes':2,'item_inventory_information_screens':14,'hero_detail_screens':4,'save_bytes':65536,
        'master_entries':len(current),'master_roundtrip_sha256':roundtrip,'glossary_terms':len(terms),
        'appended_used_with_padding':ledger['appended_used_with_padding'],'appended_remaining':ledger['appended_remaining'],
        'new_appended_bytes':ledger['appended_used_with_padding']-prior['ledger']['appended_used_with_padding'],'allocations':len(ledger['allocations']),'original_patch_ranges':len(ledger['patches']),
        'catalog_file_sha256':{p.name:digest(p.read_bytes()) for p in (ROOT/'translations').glob('*.json')},'harness_sha256':harness_hash,
        'terminology_review_sha256':digest((ROOT/'translations/ally-dialogue-terminology-review.tsv').read_bytes()),
        'history_review_sha256':digest((ROOT/'translations/ally-dialogue-history-review.tsv').read_bytes()),
        'limits':'Controlled native ally pointer selection, HP thresholds and paged rendering with caller flags. Speaker slots are supplied, random results controlled, waits/frame yield bypassed; no assertion of natural recruitment, special abilities, nickname copying or level transitions. All 311 earlier core/help messages have bounded native history checks, including synthetic narrow 48-byte item names. Their natural reachability, history navigation and ranking/save persistence remain separate.'}
    write_json(OUTPUT/'acceptance.json',result);print(json.dumps({k:v for k,v in result.items() if k!='catalog_file_sha256'},indent=2));return result


def verify_all():
    from tools.verify_ally_dialogue import verify,STATE
    from tools.verify_dungeon_contexts import verify as secondary
    from tools.verify_enemy_items import verify as items
    from tools.verify_enemies import verify as enemies
    from tools.extract_master_text import extract
    build()
    with (OUTPUT/'unit-tests.log').open('w') as log:subprocess.run([sys.executable,'-m','unittest','discover','-s','tests'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
    for variant in ('english','japanese','baseline'):verify(variant)
    rom=OUTPUT/'torneko3-ally-dialogue-english.gba'
    secondary(rom,OUTPUT/'verification/secondary-contexts',STATE)
    items(rom,OUTPUT/'verification/items-regression','items',state_path=STATE,rows=[1,64,133,190,247,273,304])
    enemies(rom,OUTPUT/'verification/hero-details',state_path=STATE,rows=[0,198])
    items(rom,OUTPUT/'verification/save','save');extract();return summarize()


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--summarize-only',action='store_true')
    summarize() if p.parse_args().summarize_only else verify_all()
