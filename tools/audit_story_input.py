"""Audit native story password/pet keyboard paths on disposable states."""
import json
import mgba.log
from tools.build_first_label import ROOT,ORIGINAL_ROM,digest
from tools.verify_expansion import Session
from tools.verify_tutorial_gameplay import cold_tables,restore
from tools.verify_opening_story import STATE
from tools import verify_dungeon_interface as ui
from tools.verify_core_gameplay import write_bytes,cstring,DEST,GUARD
from tools.verify_name_entry import EDIT_BUFFER,KEY_PAGE,KEY_SELECTION,select_character
from tools.build_name_entry import compact_name
from tools.translation_pipeline import check,atomic_write

OUTPUT=ROOT/'build/completion/input-audit'
ROM=ROOT/'build/completion/checkpoints/story-pages/torneko3-story-completion-english.gba'
CONTROLLER=0x0203F000
INPUT=0x02008BF0


def audit():
    mgba.log.silence();results=[]
    with Session(ROM.read_bytes(),OUTPUT) as s:
        tables=cold_tables(s);state=STATE.read_bytes()
        for name,command,text in (('password',0xC1528C,'LETMEIN'),('dog',0xA0DF28,'Biscuit'),('cat',0xA744C8,'Mittens')):
            restore(s,state,tables);core=s.core;trace=ui.InterfaceTrace(core);frames=s.frames
            s.frames=lambda n,unused=None:trace.frames(n)
            try:
                write_bytes(core,CONTROLLER,b'\0'*128);core.memory.u32[CONTROLLER+0x24]=command+0x08000000
                trace.phase=name+'-dispatch';dispatch=ui.native_step(s,trace,0x08064E28,[CONTROLLER],stop=0x08065666)
                root=core.memory.u32[0x03000010]
                print(name,'root',hex(root),'mode',core.memory.u32[root],'limit',core.memory.u32[root+0x48C],flush=True)
                trace.phase=name+'-keyboard';s.frames(120);s.capture(name+'-initial')
                print('keyboard',core.memory.u32[KEY_PAGE],core.memory.u32[KEY_SELECTION],bytes(core.memory[EDIT_BUFFER:EDIT_BUFFER+8]).hex(),flush=True)
                initial=bytes(core.memory[EDIT_BUFFER:EDIT_BUFFER+8]).split(b'\0',1)[0]
                for _ in initial:s.press('B',15)
                for c in text:select_character(s,c);s.press('A',15)
                check(bytes(core.memory[EDIT_BUFFER:EDIT_BUFFER+8])==compact_name(text),'Story keyboard compact result differs')
                s.capture(name+'-entered');s.press('R',15);s.press('A',60);s.capture(name+'-done')
                result={'case':name,'command_offset':hex(command),'typed':text,'dispatch':dispatch,'root':hex(root),
                    'input_hex':bytes(core.memory[INPUT:INPUT+8]).hex(),'result':core.memory.u32[root+0x498],
                    'story_state':core.memory.u32[root],'source_rom_sha256':digest(ORIGINAL_ROM.read_bytes()),'rom_sha256':digest(ROM.read_bytes())}
                check(result['input_hex']==compact_name(text).hex() and result['result']==1,'Native keyboard commit failed')
                if name=='password':
                    comparison=ui.native_step(s,trace,0x08064BAE,[],stop=0x08064C0A,
                        overrides={0x08064BAE:{'r7':CONTROLLER,'sp':0x03007C00}})
                    result.update(comparison=comparison,comparison_result=core.memory.u32[0x03007C7C],
                        converted_hex=cstring(core,0x03007C04,16).hex())
                    check(result['comparison_result']==2,'English input must fail against original Japanese keyword')
                    check(result['converted_hex']==(text.encode()+b'\0').hex(),'Password conversion changed Latin input')
                else:
                    index=0x57 if name=='dog' else 0x5F;at=0x020010C0+2*index
                    before=bytes(core.memory[at-2:at])+bytes(core.memory[at+14:at+16])
                    commit=ui.native_step(s,trace,0x08064B70,[],stop=0x08064B98,
                        overrides={0x08064B70:{'r7':CONTROLLER,'sp':0x03007C00}})
                    stored=[core.memory.u16[at+2*i] for i in range(7)]
                    check(stored==list(compact_name(text)[:7]),'Native pet writer changed compact IDs')
                    check(before==bytes(core.memory[at-2:at])+bytes(core.memory[at+14:at+16]),'Pet commit crossed seven variables')
                    write_bytes(core,DEST-GUARD.__len__(),GUARD+b'\xcc'*15+GUARD)
                    read=ui.native_step(s,trace,0x08000888,[index,DEST,7])
                    check(cstring(core,DEST,15)==text.encode()+b'\0','Pet getter changed Latin name')
                    check(bytes(core.memory[DEST-len(GUARD):DEST])==GUARD and bytes(core.memory[DEST+15:DEST+15+len(GUARD)])==GUARD,'Pet getter exceeded 15 bytes')
                    result.update(commit=commit,stored_ids=stored,read=read,guards_intact=True)
                print(result,flush=True);results.append(result)
            finally:s.frames=frames;trace.close()
    atomic_write(OUTPUT/'keyboard-probe.json',(json.dumps({'scope':'Controlled actual command dispatch, native story keyboard and real joypad input. Native pet commit/getter with adjacent-field guards; native password conversion/comparison rejects English against the original Japanese keyword. No save persistence or natural scene reachability claim.','cases':results},indent=2)+'\n').encode())


if __name__=='__main__':audit()
