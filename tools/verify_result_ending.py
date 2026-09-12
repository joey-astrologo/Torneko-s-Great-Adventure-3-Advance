"""Controlled native dungeon-ending composition and category selector."""
import argparse
from pathlib import Path
import struct
import mgba.log
from tools import verify_adventure_results as v
from tools import verify_result_saves as saves
from tools import verify_core_gameplay as old
from tools import verify_dungeon_interface as ui
from tools import verify_arena_services as arena
from tools.build_first_label import ORIGINAL_ROM,digest
from tools.translation_pipeline import load_json,FontZero,check
from tools.verify_expansion import Session
from tools.verify_items import write_json


def ending(session,variant,font,cause=33,actor=188,item=327,hero=0,flags=0x200,dungeon=0,ranked=True,score_only=False):
    c=session.core;check(c.load_raw_state(v.STATE.read_bytes()),'Ending state restore')
    heap=bytes(c.memory[0x02010A90:0x02034A90]);selectors={a:bytes(c.memory[a:a+n]) for a,n in ((0x0200000C,4),(0x02004FF0,1),(0x02004FF4,1),(0x020014CE,2),(0x02004F8C,4))}
    root=saves.context(c);player=0x0203F000
    c.memory.u16[root+0x20E64]=cause;c.memory.u16[root+0x20E66]=actor&65535
    c.memory.u16[root+0x20E68]=flags;c.memory.u16[root+0x20E6A]=item
    c.memory.u8[0x02004FF0]=dungeon;c.memory.u8[0x02004FF4]=hero
    c.memory.u32[0x02004F8C]=int(score_only)
    old.write_bytes(c,v.RECORD,bytes(160*48))
    if not ranked:
        for row in range(160):old.write_bytes(c,v.RECORD+row*48+10,(9999999).to_bytes(3,'little'))
    for offset,value in ((0x14C,0),(0x150,0),(0x154,root),(0x158,4),(0x168,0),(0x16C,0),
        (0x170,player),(0x174,v.STACK+0x14C),(0x178,v.STACK+0x150),(0x184,player+0x9C)):
        c.memory.u32[v.STACK+offset]=value
    fonts=bytes(c.memory[0x020398EC:0x020398F8]);trace=ui.InterfaceTrace(c)
    try:
        ui.native_step(session,trace,0x08000EA8,[hero])
        ui.native_step(session,trace,0x0805C0AC,[],stop=0x0805C62A,overrides={0x0805C0AC:{'sp':v.STACK}})
        checks=arena.check_draws(trace,font) if variant=='english' else []
        check(bytes(c.memory[0x020398EC:0x020398F8])==fonts,'Ending window damaged font state')
        ui.native_step(session,trace,0x0808BBF8,[0]);ui.native_step(session,trace,0x0808BB14,[0])
        result={'parameters':{'cause':cause,'actor':actor,'item':item,'hero':hero,'flags':flags,'dungeon':dungeon},
            'ranked':ranked,'score_only':score_only,'checks':checks,'glyphs':trace.positions,'payloads':trace.payloads,'formats':trace.formats,'font_tables_intact':True,
            'native_score':c.memory.u32[v.STACK+0x14C],'native_category':c.memory.u32[v.STACK+0x150]}
    finally:
        trace.close();old.write_bytes(c,0x02010A90,heap)
        for a,raw in selectors.items():old.write_bytes(c,a,raw)
    return result


def probe(variant):
    mgba.log.silence();rom=v.BASELINE if variant=='baseline' else v.b.OUTPUT/f'torneko3-adventure-results-{variant}.gba'
    with Session(rom.read_bytes(),v.b.OUTPUT/'research/ending-probe'/variant) as session:
        r=ending(session,variant,FontZero(ORIGINAL_ROM.read_bytes()));session.frames(2);session.capture('ending')
        write_json(session.output/'probe.json',r);print(variant,'ending probe passed',flush=True)


def categories(session,variant,font,mode):
    c=session.core;check(c.load_raw_state(v.STATE.read_bytes()),'Result category state')
    profile=(saves.OUTPUT/'profile.sav').read_bytes()[0xE000:0xFFAC];old.write_bytes(c,saves.PROFILE,profile)
    trace=ui.InterfaceTrace(c);fonts=bytes(c.memory[0x020398EC:0x020398F8])
    try:
        if mode=='empty':
            old.write_bytes(c,v.RECORD,bytes(160*48));ui.native_step(session,trace,0x080015BC,[saves.PROFILE])
        elif mode=='invalid':c.memory.u32[saves.PROFILE]^=1
        r=ui.native_step(session,trace,0x08085FB0,[])
        expected=list(range(9)) if mode=='all' else [8] if mode=='empty' else [10]
        check(r['return_r0']==len(expected) and bytes(c.memory[0x020105F8:0x020105F8+len(expected)])==bytes(expected),'Category selection differs')
        check(len(trace.payloads)==len(expected),'Missing native category row')
        if mode=='campaign':raise ValueError('Campaign is a direct label check, not this routine\'s selection path')
        checks=arena.check_draws(trace,font) if variant=='english' else []
        check(bytes(c.memory[0x020398EC:0x020398F8])==fonts,'Category buffer damaged font state')
        return {'mode':mode,'selected_rows':expected,'checks':checks,'glyphs':trace.positions,'payloads':trace.payloads,'font_tables_intact':True}
    finally:trace.close()


def verify(variant,limit=None):
    mgba.log.silence();rom=v.BASELINE if variant=='baseline' else v.b.OUTPUT/f'torneko3-adventure-results-{variant}.gba'
    original=ORIGINAL_ROM.read_bytes();font=FontZero(original);catalog=load_json(v.b.OUTPUT/'catalog.json')
    build={} if variant=='baseline' else load_json(v.b.OUTPUT/f'{variant}-build.json');entries={e['id']:e for e in catalog['entries']}
    cases=[];menus=[];extras=[]
    with Session(rom.read_bytes(),v.b.OUTPUT/'verification/ending'/variant) as session:
        def save(name,r):
            session.frames(2);session.capture(name);r['screens']=[name+'.png'];write_json(session.output/(name+'.json'),r)
            return {k:v for k,v in r.items() if k not in ('glyphs','payloads','formats')}
        for index,case in enumerate(v.scenarios(catalog)[:limit]):
            r=ending(session,variant,font,**case['parameters']);e=entries[case['source_id']]
            expected=0x08000000+(int(e['offset'],0) if variant=='baseline' else build['results']['relocated'][e['id']]['offset'])
            check(int(r['formats'][-1]['source'],0)==expected,'Ending selected wrong native cause '+case['id'])
            r['id']=case['id'];r['source_id']=e['id'];r['native_source']=hex(expected);cases.append(save('ending-'+case['id'],r))
            if index%25==0:print(variant,index+1,'native ending cases',flush=True)
        if not limit:
            variants=[dict(cause=5,actor=188,flags=flags,hero=h) for h in (0,1) for flags in (1,0x20,0x100,0x400,0x800)]
            variants += [dict(cause=33,actor=188,item=327,flags=0x200,hero=h,dungeon=d,ranked=ranked)
                for h in (0,1) for d in (0,20,18,31) for ranked in (True,False)]
            variants += [dict(cause=5,hero=h,score_only=True) for h in (0,1)]
            variants += [dict(cause=33,actor=-1,hero=h) for h in (0,1)]
            for index,params in enumerate(variants):extras.append(save(f'extra-{index:02}',ending(session,variant,font,**params)))
            for mode in ('all','empty','invalid'):menus.append(save('categories-'+mode,categories(session,variant,font,mode)))
            c=session.core;check(c.load_raw_state(v.STATE.read_bytes()),'Campaign label state');trace=ui.InterfaceTrace(c)
            try:
                # The array label exists; this does not invent a reachable menu entry.
                ui.native_step(session,trace,0x0808B60C,[20,1,1]);ui.native_step(session,trace,0x0808BBD8,[0])
                source=c.memory.u32[0x08C4CF8C];ui.native_step(session,trace,0x0808CB84,[4,3,source,0,0]);ui.native_step(session,trace,0x0808BBF8,[0])
                checks=arena.check_draws(trace,font) if variant=='english' else []
                r={'mode':'campaign_label_only','checks':checks,'glyphs':trace.positions,'payloads':trace.payloads,'selection_path_established':False}
            finally:trace.close()
            menus.append(save('campaign-label',r))
        result={'rom_sha256':digest(rom.read_bytes()),'source_sha256':digest(original),'catalog_sha256':digest((v.b.OUTPUT/'catalog.json').read_bytes()),
            'harness_sha256':digest(Path(__file__).read_bytes()),'context_helper_sha256':digest(Path(saves.__file__).read_bytes()),'fixture_sha256':digest(v.STATE.read_bytes()),
            'limited':bool(limit),'cases':cases,'extra_cases':extras,'menus':menus,'screens':[n for r in cases+extras+menus for n in r['screens']],
            'scope':'Native dungeon-ending constructor/record creation/display segment in a documented synthetic dungeon context, stopped before gameplay consequences; exact original table lookup. Native category selector with occupied/empty/invalid profile and a separate direct Campaign label check. Natural ending transitions remain separate.'}
        write_json(session.output/'verification.json',result);print(variant,'ending passed',len(cases),len(extras),len(menus),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('variant',choices=('english','japanese','baseline'));p.add_argument('--probe',action='store_true');p.add_argument('--limit',type=int);a=p.parse_args();probe(a.variant) if a.probe else verify(a.variant,a.limit)
