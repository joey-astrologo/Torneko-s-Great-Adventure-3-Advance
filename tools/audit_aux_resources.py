"""Classify typed numeric/name resources with bounded native readers."""
import json
import struct
from pathlib import Path
import mgba.log
from tools import audit_scene_resources as scene
from tools import verify_dungeon_interface as ui, verify_tutorial_gameplay as queue
from tools import verify_core_gameplay as old, verify_system_labels as system
from tools.build_first_label import ORIGINAL_ROM, ROOT, digest
from tools.translation_pipeline import check, load_json, atomic_write
from tools.verify_expansion import Session

OUTPUT=ROOT/'build/completion/aux-resource-audit'
BASELINE=scene.BASELINE


def audit():
    mgba.log.silence(); original=ORIGINAL_ROM.read_bytes(); data=BASELINE.read_bytes()
    master={int(e['offset'],0):e for e in load_json(ROOT/'translations/master.json')['entries']};cases=[];entries=[]
    def add(at,kind,reader,evidence):
        e=master[at];raw=bytes.fromhex(e['source_hex'])
        check(data[at:at+len(raw)]==original[at:at+len(raw)]==raw,'Auxiliary source bytes changed')
        entries.append({'master_id':e['id'],'offset':hex(at),'end_exclusive':hex(at+len(raw)),
            'source_hex':e['source_hex'],'japanese':e['japanese'],'kind':kind,'reader':reader,'case_ids':evidence})
    with Session(data,OUTPUT/'native') as s:
        c=s.core
        def restore():check(c.load_raw_state(system.STATE.read_bytes()),'Auxiliary world restore')
        for word in (0x929F44,0x92A17C,0x92A1EC,0x92A2DC):
            restore(); index=(word-0x929EE8-4)//8; at=struct.unpack_from('<I',original,word)[0]-0x08000000
            ctrl=scene.CONTROLLER;system.guard(c,ctrl,scene.CONTROLLER_BYTES);old.write_bytes(c,ctrl,b'\0'*scene.CONTROLLER_BYTES)
            t=ui.InterfaceTrace(c)
            try:
                ui.native_step(s,t,0x08066EF4,[index],overrides={0x08066F04:{'r2':ctrl}})
                check(c.memory.u32[ctrl+0x24]==at+0x08000000,'Native global-program selection differs')
            finally:t.close()
            result=queue.select_slice(c,0x08064E28,0x08064E60,{'r0':ctrl},0)
            check(c.memory.u32[ctrl+0x34]==at+0x08000000 and c.memory.u32[ctrl+0x24]==at+0x08000008,'Global command cursor differs')
            opcode=original[at];table=struct.unpack_from('<I',original,0x64E64)[0]
            check(int(result['source'],0)==c.memory.u32[table+(opcode-1)*4],'Global dispatch differs')
            system.guards(c,ctrl,scene.CONTROLLER_BYTES)
            ident=f'global_{index}';cases.append({'id':ident,'index':index,'word':hex(word),'command':hex(at),'command_hex':original[at:at+8].hex(),'dispatch':result['source'],'guards_intact':True})
            add(at,'global_event_command','08066EF4 -> 08064488 -> 08064E28',[ident])
            if at==0x9187C4:add(at+4,'global_event_operand','Eight-byte native fetch containment',[ident])
        groups=load_json(scene.OUTPUT/'source-candidates.json')['groups']
        for at,number in ((0x9A8B1C,15),(0x9EC564,22)):
            restore();g=next(g for g in groups if g['scene']==number and g['group']==0 and g['kind']=='actor')
            selected=queue.select_slice(c,0x080690FC,0x08069116,{'r0':number,'r1':0},4)
            check(int(selected['source'],0)==at+0x08000000==int(g['records'],0),'Actor numeric row selection differs')
            result=queue.select_slice(c,0x08069350,0x0806936A,{'r0':0,'r1':at+0x08000000,'r2':0},6)
            check(int(result['source'],0)==original[at]==90,'Actor ID field differs')
            ident=f'actor_{number}';cases.append({'id':ident,'group':g,'record':hex(at),'numeric_actor_id':90})
            add(at,'actor_record_id','080690FC -> 08069368 LDRB',[ident])
        for at,entry,stop,index in ((0x86F698,0x08062D94,0x08062DA8,0),(0x872ABC,0x08063D5C,0x08063D70,0),(0x872AC0,0x08063D5C,0x08063D70,1)):
            restore();a=queue.select_slice(c,entry,stop,{'r0':index},0);b=queue.select_slice(c,entry,stop,{'r0':index},1)
            expected=struct.unpack_from('<hh',original,at);check((int(a['source'],0),int(b['source'],0))==expected,'Native numeric flag parameters differ')
            ident=f'flags_{at:x}';cases.append({'id':ident,'start':hex(at),'end_exclusive':hex(at+4),'index':index,'signed_halfwords':list(expected),'call_stopped_before':'08000660'})
            add(at,'numeric_flag_record',f'{entry:08X} -> signed halfword arguments of 08000660',[ident])
        restore();check(bytes(c.memory[0x020007B8:0x020007E0])==original[0xCB0640:0xCB0668],'Suffix pointer cache differs')
        for index in range(10):
            selected=queue.select_slice(c,0x0807D28C,0x0807D294,{'r0':index},0);at=int(selected['source'],0)-0x08000000
            check(at==struct.unpack_from('<I',original,0xCB0640+index*4)[0]-0x08000000,'Suffix selector differs')
            ident=f'suffix_{index}';cases.append({'id':ident,'index':index,'word':hex(0xCB0640+index*4),'source':hex(at)})
            add(at,'nickname_digit_asset','0807D28C original indexed suffix getter',[ident])
        alphabet=original[0xC46BDC:original.index(0,0xC46BDC)]
        check(len(alphabet)==55 and all(a<b for a,b in zip(alphabet,alphabet[1:])),'Kana conversion alphabet differs')
        for index,code in enumerate(alphabet):
            restore();system.guard(c,old.DEST,3);system.guard(c,0x0203F300,2);old.write_bytes(c,0x0203F300,bytes((code,0)))
            t=ui.InterfaceTrace(c)
            try:ui.native_step(s,t,0x0807D2F8,[old.DEST,0x0203F300])
            finally:t.close()
            output=bytes(c.memory[old.DEST:old.DEST+3]);expected=original[0xC46B6C+index*2:0xC46B6E+index*2]+b'\0'
            check(output==expected,'Native kana conversion differs');system.guards(c,old.DEST,3);system.guards(c,0x0203F300,2)
            cases.append({'id':f'kana_{index}','input_hex':bytes((code,0)).hex(),'output_hex':output.hex(),'map_word':hex(0xC46B6C+index*2),'guards_intact':True})
        add(0xC46BDC,'kana_conversion_alphabet','0807D2F8 half-width to full-width conversion',[f'kana_{i}' for i in range(55)])
    # The accepted seven-letter-name patch deliberately replaces this pointer
    # and index arithmetic. Establish the retired source role on original code.
    with Session(original,OUTPUT/'native-original') as s:
        c=s.core
        for index in range(2):
            check(c.load_raw_state(system.STATE.read_bytes()),'Original name fixture restore');local=0x03007800;c.memory.u8[0x02004F80]=index;system.guard(c,local+8,6)
            t=ui.InterfaceTrace(c)
            try:ui.native_step(s,t,0x080858C4,[],stop=0x080858D8,overrides={0x080858C4:{'sp':local}})
            finally:t.close()
            at=0xC4CE97+index*6;expected=original[at:original.index(0,at)+1]
            check(bytes(c.memory[local+8:local+8+len(expected)])==expected,'Native compact default copy differs');system.guards(c,local+8,6)
            cases.append({'id':f'compact_default_{index}','index':index,'record_start':hex(at),'rom_sha256':digest(original),'copied_hex':expected.hex(),'guards_intact':True})
        add(0xC4CE97,'compact_name_default','080858B4 selection/copy -> compact editor 0807BAD4',['compact_default_0','compact_default_1'])
    result={'status':'auxiliary_resources_native_verified','source_sha256':digest(original),'verified_rom':str(BASELINE.relative_to(ROOT)),'verified_rom_sha256':digest(data),
        'harness_sha256':digest(Path(__file__).read_bytes()),'fixture_sha256':digest(system.STATE.read_bytes()),
        'helper_sha256':{Path(m.__file__).name:digest(Path(m.__file__).read_bytes()) for m in (ui,queue,old,system)},
        'entries':entries,'cases':cases,'scope':'Bounded native resource readers and command fetches; no actions, natural scene reachability, new translation, insertion space or permanent RAM changes.'}
    atomic_write(OUTPUT/'native-verification.json',(json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode())
    print(len(entries),'auxiliary resources classified;',len(cases),'native cases',flush=True)

if __name__=='__main__':audit()
