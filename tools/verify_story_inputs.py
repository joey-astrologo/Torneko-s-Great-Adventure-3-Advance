"""Real story-keyboard input, native password results and bounded pet commits."""
from pathlib import Path
import json
import struct
import mgba.log
from tools import build_story_special as b
from tools import verify_dungeon_interface as ui
from tools.verify_story_special import compact
from tools.verify_expansion import Session
from tools.verify_tutorial_gameplay import cold_tables,restore
from tools.verify_opening_story import STATE
from tools.verify_core_gameplay import write_bytes,cstring,DEST,GUARD
from tools.verify_name_entry import EDIT_BUFFER,KEY_PAGE,KEY_SELECTION,NAME_CURSOR,select_character
from tools.translation_pipeline import FontZero,load_json,check
from tools.verify_items import write_json
from tools.build_first_label import ORIGINAL_ROM,digest

CONTROLLER=0x0203F000
INPUT=0x02008BF0


def scenarios(original):
    pets=[('dog',0xA0DF28,0x57,'Biscuit'),('cat-1',0xA744C8,0x5F,'Mittens')]
    catalog=load_json(b.OUTPUT/'catalog.json')
    for e in catalog['entries']:
        if e['english']=='$t decided to name the cat $p2!':
            command=int(e['events'][0]['command_offset'],0)-0x20
            check(struct.unpack_from('<II',original,command)==(0x005F0730,0),'Cat input owner differs')
            if command!=0xA744C8:pets.append((f'cat-{len(pets)}',command,0x5F,'Mittens'))
    check(len(pets)==6,'Incomplete house naming variants')
    rows=[{'id':name+'-seven','command':command,'index':index,'initial':'OLDNAME','typed':name_text,'expected':1} for name,command,index,name_text in pets]
    for name,command,index,old in pets[:2]:
        rows.extend([{'id':name+'-short','command':command,'index':index,'initial':old,'typed':'Bo' if index==0x57 else 'Kit','expected':1},
                     {'id':name+'-cancel','command':command,'index':index,'initial':old,'typed':None,'expected':0}])
    for name,typed,result in (('correct','LETMEIN',1),('wrong','LETMEIX',2),('case','letmein',2),('short','LET',2),('cancel',None,0)):
        rows.append({'id':'password-'+name,'command':0xC1528C,'index':None,'initial':'','typed':typed,'expected':result})
    return rows


def verify():
    mgba.log.silence();original=ORIGINAL_ROM.read_bytes();rom=b.OUTPUT/'torneko3-story-special-english.gba';data=rom.read_bytes();out=b.OUTPUT/'verification/inputs';results=[]
    with Session(data,out) as s:
        tables=cold_tables(s);state=STATE.read_bytes()
        for row in scenarios(original):
            restore(s,state,tables);core=s.core;trace=ui.InterfaceTrace(core);frames=s.frames;s.frames=lambda n,unused=None:trace.frames(n)
            try:
                trace.phase=row['id'];index=row['index'];at=0x020010C0+2*index if index is not None else None
                if at is not None:
                    ids=compact(row['initial'],original)
                    for i in range(7):core.memory.u16[at+2*i]=ids[i] if i<len(ids) else 0
                    prior=bytes(core.memory[at:at+14]);neighbors=bytes(core.memory[at-2:at])+bytes(core.memory[at+14:at+16])
                adjacent=bytes(core.memory[INPUT-8:INPUT])+bytes(core.memory[INPUT+8:INPUT+16])
                write_bytes(core,CONTROLLER,b'\0'*128);core.memory.u32[CONTROLLER+0x24]=row['command']+0x08000000
                dispatch=ui.native_step(s,trace,0x08064E28,[CONTROLLER],stop=0x0806566E)
                root=core.memory.u32[0x03000010];check(core.memory.u32[root+0x48C]==7,'Native input limit changed')
                s.frames(120)
                initial=bytes(core.memory[EDIT_BUFFER:EDIT_BUFFER+8]).split(b'\0',1)[0]
                check(initial==bytes(compact(row['initial'],original)),'Native initial pet name differs')
                for _ in initial:s.press('B',15)
                if row['typed'] is None:
                    s.press('B',60)
                else:
                    for c in row['typed']:select_character(s,c);s.press('A',15)
                    ids=bytes(compact(row['typed'],original));check(bytes(core.memory[EDIT_BUFFER:EDIT_BUFFER+len(ids)+1])==ids+b'\0','Story joypad input differs')
                    check(bytes(core.memory[EDIT_BUFFER+8:EDIT_BUFFER+32])==b'\0'*24,'Story input exceeded its buffer')
                    if len(ids)==7:check(core.memory.u32[KEY_SELECTION]==4,'Seven characters did not select Done')
                    s.capture(row['id']+'-typed');s.press('R',15);s.press('A',60)
                editor_result=core.memory.u32[root+0x498]
                check(editor_result==(0 if row['typed'] is None else 1),f'Native editor result differs: {row["id"]}: {editor_result}')
                result={**row,'command':hex(row['command']),'dispatch':dispatch,'editor_result':editor_result,'input_hex':bytes(core.memory[INPUT:INPUT+8]).hex()}
                check(adjacent==bytes(core.memory[INPUT-8:INPUT])+bytes(core.memory[INPUT+8:INPUT+16]),'Input write crossed eight-byte buffer')
                if index is None:
                    callback=ui.native_step(s,trace,0x08064BAE,[],stop=0x08064C0A,overrides={0x08064BAE:{'r7':CONTROLLER,'sp':0x03007C00}})
                    observed=core.memory.u32[0x03007C7C];check(observed==row['expected'],'Native password accept/reject/cancel differs')
                    result.update(callback=callback,native_result=observed)
                    if row['typed'] is not None:
                        converted=cstring(core,0x03007C04,16);check(converted==row['typed'].encode()+b'\0','Password conversion changed typed text');result['converted_hex']=converted.hex()
                else:
                    commit=ui.native_step(s,trace,0x08064B70,[],stop=0x08064B98,overrides={0x08064B70:{'r7':CONTROLLER,'sp':0x03007C00}})
                    expected=prior if row['typed'] is None else b''.join(i.to_bytes(2,'little') for i in compact(row['typed'],original)).ljust(14,b'\0')
                    check(bytes(core.memory[at:at+14])==expected,'Pet commit failed or cancellation changed name')
                    check(neighbors==bytes(core.memory[at-2:at])+bytes(core.memory[at+14:at+16]),'Pet commit crossed seven variables')
                    write_bytes(core,DEST-len(GUARD),GUARD+b'\xcc'*15+GUARD)
                    read=ui.native_step(s,trace,0x08000888,[index,DEST,7]);value=row['initial'] if row['typed'] is None else row['typed']
                    check(cstring(core,DEST,15)==value.encode()+b'\0','Native pet getter changed stored name')
                    check(bytes(core.memory[DEST-len(GUARD):DEST])==GUARD and bytes(core.memory[DEST+15:DEST+15+len(GUARD)])==GUARD,'Pet getter overflowed')
                    result.update(commit=commit,stored_hex=expected.hex(),getter=read,visible_name=value)
                check(not trace.errors,str(trace.errors));result['guards_intact']=True;results.append(result)
                write_json(out/(row['id']+'.json'),result);print(row['id'],'passed',flush=True)
            finally:s.frames=frames;trace.close()
    report={'rom_sha256':digest(data),'source_sha256':digest(original),'catalog_sha256':digest((b.OUTPUT/'catalog.json').read_bytes()),'harness_sha256':digest(Path(__file__).read_bytes()),'fixture_sha256':digest(STATE.read_bytes()),'cases':results,'scope':'Controlled actual name/password commands, native story keyboard and real joypad input. All six pet contexts, seven-slot commits, short-name zero fill and cancellation; native password exact/case/typo/short/cancel results. Input buffer, pet neighbors and getter guards checked. Original downstream event branch code is preserved; natural adoption, door traversal and saves are separate coverage.'}
    write_json(out/'verification.json',report);return report


if __name__=='__main__':verify()
