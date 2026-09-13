"""Run revised prose through established native readers and their layout checks.

Each phase is restartable. Fixtures select known readers; they do not establish
natural story reachability or replace a complete playthrough.
"""
import argparse
from collections import defaultdict
from importlib import import_module
from pathlib import Path
import mgba.log

from tools import build_prose_review as b
from tools.prose_review import save
from tools.build_first_label import ORIGINAL_ROM, ROOT, digest
from tools.translation_pipeline import FontZero, load_json, check
from tools.game_text import GameTextCodec
from tools.verify_expansion import Session
from tools import verify_core_gameplay as core
from tools import verify_tutorial_gameplay as queue
from tools import verify_dungeon_interface as ui
from tools import verify_ally_services as service
from tools import verify_opening_story as opening

OUT = b.OUTPUT/'verification'
STORY = {'opening-story','first-village','early-journey','shared-story','story-completion'}
GROUPS = {
    'story':STORY,
    'special':{'story-special'},
    'dialogue':{'ally-dialogue','companion-dialogue'},
    'items':{'items','item-contexts','enemies','dungeon-interface'},
    'services':{'ally-services','arena-services','merchants','church-services','frontend-completion','dungeon-events','world-completion'},
    'messages':{'core-gameplay','gameplay-help','tutorial-gameplay','battle-completion'},
    'results':{'adventure-results'},
}


def inputs():
    original = ORIGINAL_ROM.read_bytes(); plan = load_json(b.PLAN)
    report = load_json(b.OUTPUT/'english-build.json'); data = b.ROM.read_bytes()
    check(digest(data)==report['rom_sha256'] and digest(b.PLAN.read_bytes())==report['allocation_plan_sha256'], 'Built prose does not match plan')
    groups=defaultdict(list); catalogs={}
    for r,e,new in b.revisions(original):
        groups[r['catalog']].append(new)
        if r['catalog'] not in catalogs:
            catalogs[r['catalog']]=load_json(ROOT/f'translations/{r["catalog"]}.json')
        catalogs[r['catalog']]['entries'][r['index']]=new
    relocated={row['id']:{'offset':row['offset'] if row['changed_rom_text'] else
        int.from_bytes(bytes.fromhex(row['previous_pointer_patches'][0]['after']),'little')-0x08000000,
        'metrics':row['metrics']} for row in plan['entries']}
    native_report={k:{'relocated':relocated} for k in ('dialogue','gameplay','help','tutorials','services','arena','merchants','church','frontend','dungeon_events','world_completion','battle','results')}
    return original,data,plan,groups,catalogs,native_report


def paged(s,e,name,report,font,codec,profile):
    # Church entries share this original paged-service engine. Substitutions
    # are independently checked against the revised encoding before rendering.
    check(s.core.load_raw_state(service.STATE.read_bytes()), 'Paged fixture restore')
    values=service.set_values(s.core,font,profile)
    at=report['church']['relocated'][e['id']]['offset']+0x08000000
    t=ui.InterfaceTrace(s.core)
    try:
        raw=core.guarded_format(s,t,at)
        expected=b.encode(name,e,ORIGINAL_ROM.read_bytes())[0]
        for k,v in values.items():expected=expected.replace(k.encode(),v.encode())
        check(raw==expected,'Church formatter differs')
    finally:t.close()
    result=service.pages(s,at,e['id']+'-'+profile,font)
    check(len(result['formats'])==1 and result['formats'][0]['output_hex']==raw.hex(),'Paged output differs')
    lines=raw[:-1].split(b'\n')
    check(len(result['pages'])==(len(lines)+2)//3,'Missing final page')
    for page in result['pages']:
        start=page['page']*3;text=core.visible(b'\n'.join(lines[start:start+3])+b'\0',codec)
        if text:ui.check_glyphs(page['glyphs'],text,font)
    save(s.output/(e['id']+'-'+profile+'.json'),result)
    return {'id':e['id'],'profile':profile,'pages':len(result['pages']),'guards_intact':True}


def verify(phase):
    mgba.log.silence();original,data,plan,groups,catalogs,report=inputs()
    folder=OUT/phase;folder.mkdir(parents=True,exist_ok=True)
    font=FontZero(original);codec=GameTextCodec(original);cases=[]
    entries=[e for name in sorted(GROUPS[phase]) for e in groups[name]]
    if phase=='special':
        from tools import verify_story_special as v
        v.OUTPUT=folder
        save(folder/'catalog.json',{'entries':groups['story-special']})
        link=folder/'torneko3-story-special-english.gba'
        if not link.exists():link.symlink_to(b.ROM)
        cases=v.verify('english')['cases']
    else:
        with Session(data,folder) as s:
            tables=queue.cold_tables(s)
            for name in sorted(GROUPS[phase]):
                es=groups[name]
                print(phase,name,len(es),'revisions',flush=True)
                if phase=='items':
                    state=core.STATE.read_bytes()
                    if name=='items':
                        from tools.verify_items import inventory_checks
                        ids=sorted({i for e in es for i in e['item_indices']})
                        _,checks=inventory_checks(s,state,catalogs[name],'english',folder,ids)
                        cases.append({'catalog':name,'item_ids':ids,'checks':checks})
                    elif name=='item-contexts':
                        from tools.verify_item_contexts import capture_contexts
                        selected=[('synthesis',row,False) for e in es for row in e['rows']]
                        _,checks,wrappers,_=capture_contexts(s,state,original,catalogs[name],'english',folder,selected)
                        cases.append({'catalog':name,'checks':checks,'wrappers':wrappers})
                    elif name=='enemies':
                        from tools.verify_enemies import run_fixture
                        all_entries={e['id']:e for e in catalogs[name]['entries']}
                        for e in es:
                            for screen in ('encounter','ally'):
                                row,_=run_fixture(s,state,e['row'],screen,all_entries,'english',font,folder);cases.append(row)
                    else:
                        for e in es:
                            at=report['gameplay']['relocated'][e['id']]['offset']+0x08000000
                            for hero in (0,1):
                                _,checks=ui.search_case(s,state,e,at,hero,True,font,folder)
                                cases.append({'id':e['id'],'hero':hero,'checks':checks})
                    continue
                for index,e in enumerate(es):
                    if phase=='story':
                        from tools import verify_story_completion as v
                        for event in e['events']:
                            for hero in (('Torneko','Tipper') if '$t' in e['japanese'] else ('Torneko',)):
                                if name=='opening-story':row=opening.case(s,opening.STATE.read_bytes(),tables,e,event,'english',font)
                                else:row=v.case(s,opening.STATE.read_bytes(),tables,e,event,'english',font,hero)
                                cases.append(row)
                    elif phase=='dialogue':
                        from tools import verify_companion_dialogue as v
                        species=load_json(ROOT/'translations/enemies.json')['entries']
                        # set_values expects the selected full species string.
                        species_name=next(x['english'] for x in species if x['id']==f'enemy.name.{e["row"]:03d}')
                        for profile in ('normal','stress','narrow')+(('tipper',) if '$t' in e['japanese'] else ()):
                            cases.append(v.case(s,core.STATE.read_bytes(),tables,e,'english',report,font,profile,species_name,prior_entry=name=='ally-dialogue'))
                    elif phase=='services':
                        v=import_module('tools.verify_'+name.replace('-','_'))
                        for profile in ('normal','stress'):
                            if name=='church-services':row=paged(s,e,name,report,font,codec,profile)
                            elif name=='merchants':row=v.entry_case(s,e,'english',report,profile,tables,font)
                            elif name=='world-completion':row=v.entry_case(s,tables,e,'english',report,profile,font,original)
                            elif name=='ally-services':row=v.entry_case(s,core.STATE.read_bytes(),e,'english',report,font,codec,profile)
                            else:row=v.entry_case(s,e,'english',report,profile,font,codec)
                            cases.append({'catalog':name,**row})
                    elif phase=='messages':
                        v=import_module('tools.verify_'+name.replace('-','_'))
                        if name in ('core-gameplay','gameplay-help'):
                            v.encode=lambda e,o,n=name:b.encode(n,e,o)
                        for profile in ('normal','stress','narrow') if name in ('battle-completion','tutorial-gameplay') else ('normal','stress'):
                            if name=='battle-completion':row=v.entry_case(s,e,'english',report,profile,tables,original,font,codec)
                            elif name=='tutorial-gameplay':row=v.entry_case(s,core.STATE.read_bytes(),tables,e,'english',report,font,codec,profile)
                            elif name=='gameplay-help':row=v.entry_case(s,core.STATE.read_bytes(),e,'english',report,folder,font,codec,profile)
                            else:row=v.message_case(s,core.STATE.read_bytes(),e,'english',report,folder,font,codec,profile)
                            cases.append({'catalog':name,**{k:x for k,x in row.items() if k not in ('glyphs','formats','payloads')}})
                    elif phase=='results':
                        from tools import verify_adventure_results as v
                        if e['id']=='result.000dc668':
                            # This twin belongs to the live dungeon-ending reader,
                            # covered by verify_prose_regressions result, not scores.
                            cases.append({'id':e['id'],'coverage':'verification/result/acceptance.json'})
                            continue
                        expected=report['results']['relocated'][e['id']]['offset']+0x08000000
                        selected=v.scenarios({'entries':[e]}) if e['family']=='cause' else [
                            {'parameters':{'cause':33,'actor':188,'item':327,'hero':h,'stress':True}} for h in (0,1)]
                        for j,case in enumerate(selected):
                            row=v.detail(s,'english',font,**case['parameters'])
                            check(any(int(f['source'],0)==expected for f in row['formats']),
                                  'Result reader did not select revised source: '+e['id'])
                            s.frames(2);s.capture(e['id']+f'-{j}')
                            save(folder/(e['id']+f'-{j}.json'),row)
                            cases.append({'id':e['id'],'parameters':case['parameters'],'checks':row['checks']})
                            for mode in (0,1,2):
                                row=v.list_row(s,'english',font,mode,**case['parameters'])
                                cases.append({'id':e['id'],'mode':mode,'checks':row['checks']})
                    if (index+1)%10==0:print(phase,name,index+1,'passed',flush=True)
            if phase=='messages':
                selections=queue.native_selection(s,core.STATE.read_bytes(),tables,'english',report,font)
                save(folder/'native-label-copies.json',selections)
                cases.append({'native_label_copies':len(selections['copies']),
                              'native_selections':len(selections['selections'])})
    result={'phase':phase,'source_sha256':digest(original),'rom_sha256':digest(data),
        'plan_sha256':digest(b.PLAN.read_bytes()),'harness_sha256':digest(Path(__file__).read_bytes()),
        'reviewed_revision_ids':sorted(e['id'] for e in entries),'cases':cases,
        'scope':'Revised source readers, controlled substitutions and native glyph/layout checks. Natural trigger/outcome and full playthrough coverage remain separate.'}
    save(folder/'acceptance.json',result)
    print(phase,'PASSED',len(entries),'revisions;',len(cases),'case records',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('phase',choices=GROUPS)
    verify(p.parse_args().phase)
