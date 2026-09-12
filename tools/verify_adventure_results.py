"""Native result composition, high-score records and result-detail layout."""
import argparse
from pathlib import Path
import struct
import mgba.log
from tools import build_adventure_results as b
from tools import verify_core_gameplay as old
from tools import verify_dungeon_interface as ui
from tools import verify_ally_services as service
from tools import verify_arena_services as arena
from tools.build_first_label import ORIGINAL_ROM,digest
from tools.translation_pipeline import FontZero,load_json,check
from tools.game_text import GameTextCodec
from tools.verify_expansion import Session
from tools.verify_items import write_json

STATE=service.STATE
BASELINE=b.previous.OUTPUT/'torneko3-adventure-history-english.gba'
RECORD=0x02002FE8
STACK=0x03007A00


def seed_record(core,cause=33,actor=1,item=1,hero=0,flags=0,dungeon=0,stress=False):
    record=bytearray(48)
    struct.pack_into('<5H',record,0,cause,actor&65535,flags,item,1)
    for offset,value in ((10,1234567),(13,999999),(16,9999999),(19,99999)):
        record[offset:offset+3]=value.to_bytes(3,'little')
    record[25:30]=bytes((99,dungeon|(hero<<6),99,99,99))
    if stress:
        for offset in (13,16,19):record[offset:offset+3]=bytes.fromhex('ffffff')
        record[10:13]=(9999999).to_bytes(3,'little')
        record[22:25]=((1023<<10)|1023).to_bytes(3,'little')
        record[25]=255;record[27:30]=bytes((255,255,255))
        record[30:36]=bytes((6,48,183,99,99,99))
    old.write_bytes(core,RECORD,record)
    # The native detail reader calculates its record from these original locals.
    for at,value in ((0x2AC,0),(0x2B0,0),(0x2B4,0),(0x2BC,0)):
        core.memory.u32[STACK+at]=value
    return bytes(record)


def detail(session,variant,font,debug=False,**params):
    c=session.core;check(c.load_raw_state(STATE.read_bytes()),'Result state restore')
    record=seed_record(c,**params);trace=ui.InterfaceTrace(c)
    fonts=bytes(c.memory[0x020398EC:0x020398F8])
    try:
        ui.native_step(session,trace,0x0808651A,[],stop=0x080869F8,overrides={0x0808651A:{'sp':STACK}})
        if debug:write_json(session.output/'last-detail-trace.json',{'parameters':params,'glyphs':trace.positions,'payloads':trace.payloads,'formats':trace.formats})
        checks=arena.check_draws(trace,font) if variant=='english' else []
        check(bytes(c.memory[0x020398EC:0x020398F8])==fonts,'Result window corrupted font descriptors')
        check(bytes(c.memory[RECORD:RECORD+48])==record,'Detail reader changed its score record')
        # The real detail flow reveals its initially hidden tilemap at 086A28.
        ui.native_step(session,trace,0x0808BB14,[0])
        result={'parameters':params,'record_hex':record.hex(),'checks':checks,
            'glyphs':trace.positions,'payloads':trace.payloads,'formats':trace.formats,'record_unchanged':True,'font_tables_intact':True}
    finally:trace.close()
    return result


def probe(variant):
    mgba.log.silence();rom=BASELINE if variant=='baseline' else b.OUTPUT/f'torneko3-adventure-results-{variant}.gba'
    font=FontZero(ORIGINAL_ROM.read_bytes())
    with Session(rom.read_bytes(),b.OUTPUT/'research/window-probe'/variant) as session:
        r=detail(session,variant,font,debug=True,cause=33,actor=188,item=327,hero=0,flags=0x200)
        session.frames(2);session.capture('detail');write_json(session.output/'probe.json',r)
        print(variant,'result detail probe passed',flush=True)


def list_row(session,variant,font,mode,**params):
    c=session.core;check(c.load_raw_state(STATE.read_bytes()),'Score list state')
    record=seed_record(c,**params);trace=ui.InterfaceTrace(c)
    try:
        old.write_bytes(c,old.DEST-8,old.GUARD+b'\xA5'*200+old.GUARD)
        ui.native_step(session,trace,0x0800177C,[0,0,old.DEST,200,mode])
        raw=old.cstring(c,old.DEST,200)
        check(bytes(c.memory[old.DEST-8:old.DEST])==old.GUARD and bytes(c.memory[old.DEST+200:old.DEST+208])==old.GUARD,'Score list overrun')
        ui.native_step(session,trace,0x0808B60C,[20,1,1]);ui.native_step(session,trace,0x0808BBD8,[0])
        ui.native_step(session,trace,0x0808CB84,[4,0,old.DEST,0,0]);ui.native_step(session,trace,0x0808BBF8,[0])
        checks=arena.check_draws(trace,font) if variant=='english' else []
        check(bytes(c.memory[RECORD:RECORD+48])==record,'List reader changed score record')
        return {'parameters':params,'mode':mode,'formatted_hex':raw.hex(),'checks':checks,'glyphs':trace.positions,
            'payloads':trace.payloads,'formats':trace.formats,'guards_intact':True,'record_unchanged':True}
    finally:trace.close()


def scenarios(catalog):
    cases=[]
    for e in catalog['entries']:
        if e['family']!='cause':continue
        for p in e['pointer_owners']:
            key=p['key'];cause=int(key[7:9]);special=key.endswith('b')
            for hero in (0,1):
                cases.append({'id':key+'-'+str(hero),'source_id':e['id'],'key_offset':p['key_offset'],
                    'parameters':{'cause':cause,'actor':(198 if hero else 0) if special else 1,'item':215,'hero':hero}})
    return cases


def verify(variant,limit=None):
    mgba.log.silence();rom=BASELINE if variant=='baseline' else b.OUTPUT/f'torneko3-adventure-results-{variant}.gba'
    original=ORIGINAL_ROM.read_bytes();font=FontZero(original);catalog=load_json(b.OUTPUT/'catalog.json')
    entries={e['id']:e for e in catalog['entries']};report={} if variant=='baseline' else load_json(b.OUTPUT/f'{variant}-build.json')
    all_cases=scenarios(catalog);details=[];lists=[];stress=[]
    with Session(rom.read_bytes(),b.OUTPUT/'verification'/variant) as session:
        def save(name,result):
            session.frames(2);session.capture(name);result['screens']=[name+'.png'];write_json(session.output/(name+'.json'),result)
            return {k:v for k,v in result.items() if k not in ('glyphs','payloads','formats')}
        for index,case in enumerate(all_cases[:limit]):
            result=detail(session,variant,font,**case['parameters']);e=entries[case['source_id']]
            expected=0x08000000+(int(e['offset'],0) if variant=='baseline' else report['results']['relocated'][e['id']]['offset'])
            check(int(result['formats'][-1]['source'],0)==expected,'Native result selected the wrong cause '+case['id'])
            result['id']=case['id'];result['source_id']=e['id'];result['native_source']=hex(expected)
            details.append(save('detail-'+case['id'],result))
            for mode in (0,1,2):
                r=list_row(session,variant,font,mode,**case['parameters']);r['id']=case['id'];lists.append(save(f'list-{case["id"]}-{mode}',r))
            if index%20==0:print(variant,index+1,'result key/hero contexts',flush=True)
        if not limit:
            # Original note-priority branches, unknown actors, every dungeon label,
            # then independently enumerate species and the entire item table at
            # their respective maximum-width partner. These are controlled inputs.
            fixtures=[dict(cause=5,actor=1,hero=h,flags=f) for h in (0,1) for f in (1,0x20,0x100,0x400,0x800,0x921)]
            fixtures += [dict(cause=c,actor=-1,hero=h) for c in (5,33,55,77) for h in (0,1)]
            fixtures += [dict(cause=33,actor=188,item=327,flags=0x200,dungeon=d,stress=True) for d in range(64)]
            if variant=='english':
                fixtures += [dict(cause=33,actor=a,item=327,flags=0x200,stress=True) for a in range(200)]
                fixtures += [dict(cause=33,actor=188,item=i,flags=0x200,stress=True) for i in range(370)]
                fixtures += [dict(cause=int(p['key'][7:9]),actor=188,item=327,flags=0x200) for e in catalog['entries'] if e['family']=='cause' for p in e['pointer_owners'] if not p['key'].endswith('b')]
            for index,params in enumerate(fixtures):
                r=detail(session,variant,font,**params);r['id']=f'stress-{index:03}';stress.append(save(r['id'],r))
                if index%100==0:print(variant,index+1,'result boundary contexts',flush=True)
        result={'rom_sha256':digest(rom.read_bytes()),'source_sha256':digest(original),'catalog_sha256':digest((b.OUTPUT/'catalog.json').read_bytes()),
            'harness_sha256':digest(Path(__file__).read_bytes()),'fixture_sha256':digest(STATE.read_bytes()),'limited':bool(limit),
            'details':details,'lists':lists,'stress':stress,'screens':[n for x in details+lists+stress for n in x['screens']],
            'scope':'Controlled native score-record readers and their exact cause selection, original list shortening, result detail constructor/draw/reveal, known optional-note branches and stated field bounds. Natural end-of-dungeon transitions and save persistence remain separate.'}
        write_json(session.output/'verification.json',result);print(variant,'passed',len(details),len(lists),len(stress),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('variant',choices=('english','japanese','baseline'));p.add_argument('--probe',action='store_true');p.add_argument('--limit',type=int);a=p.parse_args();probe(a.variant) if a.probe else verify(a.variant,a.limit)
