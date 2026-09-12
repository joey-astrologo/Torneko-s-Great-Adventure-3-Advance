"""Native arena outcome formatting, columns and complete eight-row presentation."""
import argparse
from pathlib import Path
import mgba.log
from tools import build_arena_final as b,verify_system_labels as system
from tools import verify_core_gameplay as old,verify_dungeon_interface as ui
from tools.build_first_label import ORIGINAL_ROM,digest
from tools.translation_pipeline import check,load_json
from tools.verify_expansion import Session
from tools.verify_items import write_json
BASELINE=b.previous.OUTPUT/'torneko3-encounter-ui-english.gba'
STATE=system.STATE
LOCAL=0x03007B00
DEST=LOCAL+0x14


def setup(s):
    check(s.core.load_raw_state(STATE.read_bytes()),'Arena-final state restore');t=ui.InterfaceTrace(s.core)
    try:ui.native_step(s,t,0x0805CB1E,[],stop=0x0805CB52,overrides={0x0805CB1E:{'sp':LOCAL}})
    finally:t.close()


def row(s,t,name,index,odds,colour,displayrow,ystart):
    c=s.core;old.write_bytes(c,old.ACTOR,name+b'\0');neighbours=bytes(c.memory[old.ACTOR+30:old.ACTOR+90]);system.guard(c,DEST,200);c.memory.u32[0x02009228+4*index]=odds
    ui.native_step(s,t,0x0805CC16,[],stop=0x0805CC58,overrides={0x0805CC16:{'sp':LOCAL,'r4':index,'r6':colour,'r7':displayrow,'r8':DEST,'r9':ystart,'r10':old.ACTOR}})
    system.guards(c,DEST,200);raw=old.cstring(c,DEST,200);expected=old.cstring(c,c.memory.u32[0x0805CC8C])%(colour,index+1,name,odds//10,odds%10);check(raw==expected,'Arena-final native printf differs');check(old.cstring(c,old.ACTOR,30)==name+b'\0' and bytes(c.memory[old.ACTOR+30:old.ACTOR+90])==neighbours,'Arena-final actor slots changed')
    return {'name_hex':name.hex(),'index':index,'odds_tenths':odds,'colour':colour,'displayrow':displayrow,'ystart':ystart,'formatted_hex':raw.hex(),'guards_intact':True}


def finish(s,t,name,variant,**data):
    c=s.core;ui.native_step(s,t,0x0808BBF8,[0]);ui.native_step(s,t,0x0808BB14,[0]);r=system.record(s,t,name,variant,**data);return r


def verify(variant):
    mgba.log.silence();rom=BASELINE if variant=='baseline' else b.OUTPUT/f'torneko3-arena-final-{variant}.gba';data=rom.read_bytes();report={} if variant=='baseline' else load_json(b.OUTPUT/f'{variant}-build.json');entries=load_json(b.OUTPUT/'catalog.json')['entries'];cases=[];words=[]
    with Session(data,b.OUTPUT/'verification'/variant) as s:
        for e in entries:
            for p in e['pointer_owners']:
                at=int(p['offset'],0);target=0x08000000+(int(e['offset'],0) if variant=='baseline' else report['arena_final']['relocated'][e['id']]['offset']);check(s.core.memory.u32[at+0x08000000]==target,'Arena-final pointer differs');words.append({'word':hex(at),'source':hex(target)})
        for e in b.names():
            setup(s);c=s.core;t=ui.InterfaceTrace(c);name=(e['display'] or e['english']).encode()
            try:
                args=row(s,t,name,e['row']%10,(10,11,123,9999)[e['row']%4],5 if e['row']%2 else 7,e['row']%8,20);cases.append(finish(s,t,f'actor-{e["row"]:03d}',variant,kind='actor',actor=e['row'],**args))
            finally:t.close()
        # Both colours, every display row and both extremal stored odds.
        for colour in (5,7):
            for odds in (10,9999):
                setup(s);t=ui.InterfaceTrace(s.core);rows=[]
                try:
                    for index in range(8):rows.append(row(s,t,b'WWWWWWW',index,odds,colour,index,20))
                    ui.native_step(s,t,0x0805CB80,[],stop=0x0805CB92,overrides={0x0805CB80:{'r7':8,'r4':13,'r9':20,'r5':0}});cases.append(finish(s,t,f'board-{colour}-{odds}',variant,kind='board',rows=rows,colour=colour,odds_tenths=odds))
                finally:t.close()
        setup(s);t=ui.InterfaceTrace(s.core)
        try:
            ui.native_step(s,t,0x0805CB58,[],stop=0x0805CB92,overrides={0x0805CB58:{'r0':0}});cases.append(finish(s,t,'no-winner',variant,kind='empty'))
        finally:t.close()
        r={'variant':variant,'rom_sha256':digest(data),'source_sha256':digest(ORIGINAL_ROM.read_bytes()),'catalog_sha256':digest((b.OUTPUT/'catalog.json').read_bytes()),'harness_sha256':digest(Path(__file__).read_bytes()),'helper_sha256':{**system.helper_hashes(),'verify_system_labels.py':digest(Path(system.__file__).read_bytes())},'fixture_sha256':digest(STATE.read_bytes()),'pointer_words':words,'cases':cases,'screens':[p for c in cases for p in c['screens']]};write_json(s.output/'verification.json',r);print(variant,len(cases),'arena-final cases passed',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('variant',choices=('english','japanese','baseline'));a=p.parse_args();verify(a.variant)
