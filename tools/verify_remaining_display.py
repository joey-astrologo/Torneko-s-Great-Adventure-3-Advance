"""Native sound help state machine and live-floor Adventure Log summaries."""
import argparse
import struct
from pathlib import Path
import mgba.log
from tools import build_remaining_display as b,verify_system_labels as system
from tools import verify_dungeon_interface as ui,verify_core_gameplay as old,verify_tutorial_gameplay as queue
from tools.build_first_label import ORIGINAL_ROM,digest
from tools.build_name_entry import compact_name
from tools.game_text import GameTextCodec
from tools.translation_pipeline import check,load_json,FontZero
from tools.verify_expansion import Session
from tools.verify_items import write_json,distinct_glyph_observations
BASELINE=b.previous.OUTPUT/'torneko3-arena-graphics-english.gba'
STATE=system.STATE
HELP=0x02039F90
LOCAL=0x03007800

def helper_hashes():return {Path(m.__file__).name:digest(Path(m.__file__).read_bytes()) for m in (system,ui,old,queue,system.keyboard)}

def sound(s,caches,variant,report,entries):
    results=[];original=ORIGINAL_ROM.read_bytes();font=FontZero(original)
    for row,e in enumerate([e for e in entries if e['family']=='sound_help']):
        queue.restore(s,STATE.read_bytes(),caches);c=s.core;t=ui.InterfaceTrace(c)
        try:
            ui.native_step(s,t,0x08090960,[],stop=0x080909BA)
            before=bytes(c.memory[HELP-8:HELP+28])
            ui.native_step(s,t,0x08090CB4,[],stop=0x08090CD2,overrides={0x08090CB4:{'r5':HELP,'r7':row,'r4':0}})
            expected=0x08000000+(int(e['offset'],0) if variant=='baseline' else report['remaining_display']['relocated'][e['id']]['offset'])
            check(c.memory.u32[HELP+16]==expected and c.memory.u32[HELP+4]==row and c.memory.u32[HELP]==1,'Sound help native selection differs')
            text=old.cstring(c,expected,256);steps=0
            for count in range(256):
                if c.memory.u32[HELP]!=1:break
                call=ui.native_step(s,t,0x08090CD8,[],stop=0x08090D20,overrides={0x08090CD8:{'r5':HELP,'sp':LOCAL}});steps+=call['steps']
            else:raise RuntimeError('Sound help did not terminate')
            check(c.memory.u32[HELP]==2 and c.memory.u32[HELP+16]==expected+len(text),'Sound help final cursor differs')
            check(bytes(c.memory[HELP-8:HELP])==before[:8] and bytes(c.memory[HELP+20:HELP+28])==before[-8:],'Sound help adjacent state changed')
            glyphs,repeats=distinct_glyph_observations([g for g in t.positions if g['caller']=='0x08090D10'])
            check(glyphs and all(g['font']==0 and g['spacing']==0 and g['window_origin']==[16,112] and g['window_width']==208 and g['window_height']==40 for g in glyphs),'Sound help font/window differs')
            p=GameTextCodec(original).parse(text,0);codes=[int.from_bytes(x.encode('cp932'),'big') for x in p['display']]
            # Full native glyph sequence is checked against the original font
            # decoder; ASCII maps through the ROM's single-byte font table.
            if variant=='english':codes=[font.glyph(ch)[0] for ch in e['display'] or e['english']]
            else:
                codes=[];pos=0;codec=GameTextCodec(original)
                while pos<len(text)-1:
                    n=2 if 0x80<=text[pos]<=0x9F or 0xE0<=text[pos]<=0xFE else 1
                    raw=text[pos:pos+n];view,_=codec.glyph(raw,pos);codes.append(int.from_bytes(view.encode('cp932'),'big'));pos+=n
            check([g['code'] for g in glyphs]==codes,'Sound help glyph sequence differs')
            ink=system.keyboard.ink_check(glyphs,original);check(ink['overlapping_ink_pixels']==0,'Sound help ink overlaps')
            x=0
            for g in glyphs:check((g['x'],g['y'])==(x,0),'Sound help cursor position differs');x+=g['advance']
            check(c.memory.u32[HELP+8]==x and c.memory.u32[HELP+12]==0,'Sound help final position differs')
            case={'id':f'sound-{row}','kind':'sound','entry':e['id'],'row':row,'source':hex(expected),'source_hex':text.hex(),'glyphs':glyphs,'checks':[ink],'guards_intact':True,'native_steps':steps,'native_final_cursor':hex(c.memory.u32[HELP+16]),'screens':[f'sound-{row}.png']}
            t.close();s.frames(2);s.capture(f'sound-{row}');write_json(s.output/f'sound-{row}.json',case);results.append({k:v for k,v in case.items() if k!='glyphs'})
        finally:t.close()
    return results

def floors(s,caches,variant):
    results=[];c=s.core
    for row in range(64):
        for floor in (0,255):
            queue.restore(s,STATE.read_bytes(),caches);t=ui.InterfaceTrace(c)
            try:
                guard_before=bytes(c.memory[0x02004FE8:0x02004FFA]);c.memory.u8[0x02004FF0]=row;c.memory.u8[0x02004FF1]=floor
                system.guard(c,old.DEST,64)
                ui.native_step(s,t,0x080029C6,[],stop=0x080029E2,overrides={0x080029C6:{'r6':old.DEST-0x27}})
                system.guards(c,old.DEST,64)
                check(bytes(c.memory[0x02004FE8:0x02004FF0])==guard_before[:8] and bytes(c.memory[0x02004FF2:0x02004FFA])==guard_before[10:],'Dungeon/floor adjacent bytes changed')
                name=ui.native_step(s,t,0x0805F33C,[row])['return_r0'];template=old.cstring(c,c.memory.u32[0x080029F0]);title=old.cstring(c,old.DEST,64)
                check(title==template%(old.cstring(c,name)[:-1],floor),'Native live-floor format differs')
                record=bytearray(184)
                for slot in (0,1):
                    at=slot*92;record[at:at+8]=compact_name('WWWWWWW');struct.pack_into('<hhh',record,at+12,50,100,1);record[at+20]=1;record[at+23:at+23+len(title)]=title
                old.write_bytes(c,system.RECORD-8,old.GUARD+record+old.GUARD);c.memory.u32[0x020105E0]=0;c.memory.u32[0x020105E4]=0;fonts=bytes(c.memory[0x020398EC:0x020398F8])
                ui.native_step(s,t,0x0806C7F8,[0,1,1]);ui.native_step(s,t,0x080853E0,[3,0,system.RECORD],stop=0x08085718,overrides={0x080853E0:{'sp':0x03007C00},0x080854F8:{'r8':row%2}})
                check(bytes(c.memory[system.RECORD:system.RECORD+184])==record and bytes(c.memory[0x020398EC:0x020398F8])==fonts,'Floor summary record/font table changed');system.guards(c,system.RECORD,184)
                check(any(title[:-1] in bytes.fromhex(d['raw_hex']).split(b'\0',1)[0] for d in t.payloads),'Floor summary title never displayed')
                results.append(system.record(s,t,f'floor-{row:02d}-{floor}',variant,kind='floor',dungeon=row,floor=floor,title_hex=title.hex(),record_and_guards_intact=True,font_tables_intact=True))
            finally:t.close()
    return results

def verify(variant):
    mgba.log.silence();rom=BASELINE if variant=='baseline' else b.OUTPUT/f'torneko3-remaining-display-{variant}.gba';data=rom.read_bytes();report={} if variant=='baseline' else load_json(b.OUTPUT/f'{variant}-build.json');entries=load_json(b.OUTPUT/'catalog.json')['entries'];words=[]
    with Session(data,b.OUTPUT/'verification'/variant) as s:
        s.frames(5);raw=bytes(s.core.memory[0x02000964:0x02000974]);check(raw==data[0xCB07EC:0xCB07FC],'Cold sound help cache differs')
        caches=[{'ram_start':0x02000964,'raw_hex':raw.hex()}]
        for e in entries:
            for p in e['pointer_owners']:
                at=int(p['offset'],0);target=0x08000000+(int(e['offset'],0) if variant=='baseline' else report['remaining_display']['relocated'][e['id']]['offset']);check(s.core.memory.u32[at+0x08000000]==target,'Remaining display pointer differs');words.append({'word':hex(at),'target':hex(target)})
        cases=sound(s,caches,variant,report,entries)+floors(s,caches,variant)
        result={'variant':variant,'rom_sha256':digest(data),'source_sha256':digest(ORIGINAL_ROM.read_bytes()),'catalog_sha256':digest((b.OUTPUT/'catalog.json').read_bytes()),'harness_sha256':digest(Path(__file__).read_bytes()),'helper_sha256':helper_hashes(),'fixture_sha256':digest(STATE.read_bytes()),'pointer_words':words,'cold_sound_cache_hex':raw.hex(),'cases':cases,'screens':[p for c in cases for p in c['screens']]};write_json(s.output/'verification.json',result);print(variant,len(cases),'remaining display cases passed',flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('variant',choices=('english','japanese','baseline'));verify(p.parse_args().variant)
