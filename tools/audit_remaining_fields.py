"""Confirm final typed fields and preserve original ASCII startup values."""
import json
import struct
from pathlib import Path
import mgba.log
from tools import audit_scene_resources as scene,verify_dungeon_interface as ui,verify_tutorial_gameplay as queue
from tools import verify_core_gameplay as old,verify_system_labels as system
from tools.build_first_label import ORIGINAL_ROM,ROOT,digest
from tools.translation_pipeline import check,load_json,atomic_write
from tools.verify_expansion import Session
OUTPUT=ROOT/'build/completion/remaining-field-audit'
BASELINE=scene.BASELINE

def audit():
    mgba.log.silence();original=ORIGINAL_ROM.read_bytes();data=BASELINE.read_bytes();master={int(e['offset'],0):e for e in load_json(ROOT/'translations/master.json')['entries']};entries=[];cases=[]
    def add(at,kind,reason,**meta):
        e=master[at];raw=bytes.fromhex(e['source_hex']);check(data[at:at+len(raw)]==original[at:at+len(raw)]==raw,'Remaining field source changed')
        entries.append({'master_id':e['id'],'offset':hex(at),'end_exclusive':hex(at+len(raw)),'source_hex':raw.hex(),'japanese':e['japanese'],'kind':kind,'reason':reason,**meta})
    with Session(data,OUTPUT/'native') as s:
        c=s.core;s.frames(5)
        for word in [0xCAFEB8,*range(0xCB07A0,0xCB07C8,4)]:
            ram=0x02000000+word-0xCAFE88;value=struct.unpack_from('<I',original,word)[0];at=value-0x08000000
            check(data[word:word+4]==original[word:word+4] and c.memory.u32[ram]==value,'Cold original ASCII pointer differs')
            e=master[at];check(e['japanese'].isascii() and bytes.fromhex(e['source_hex'])==e['japanese'].encode()+b'\0','Original ASCII content differs')
            add(at,'original_ascii_startup_value','Original ASCII label/identifier and its cold initialized pointer are confirmed. Later reader/display/lookup use remains unproved; no new English or unused-data claim.',pointer_word=hex(word),ram_pointer=hex(ram),cold_pointer=hex(value))
        check(c.load_raw_state(system.STATE.read_bytes()),'Remaining field state restore')
        selected=queue.select_slice(c,0x0806F34E,0x0806F350,{},4);table=int(selected['source'],0);check(table==0x08C3D8F0,'Item numeric table literal differs')
        values=[]
        for index in range(8):
            result=queue.select_slice(c,0x0806F356,0x0806F35C,{'r0':index,'r4':table},0);value=int(result['source'],0);check(value==struct.unpack_from('<I',original,0xC3D8F0+index*4)[0],'Item numeric field differs');values.append(value)
        cases.append({'id':'numeric_item_arguments','reader':'0806F34E..0806F35C','table':hex(table),'values':values})
        check(values==[500,4000,2500,650,1500,8500,700,200],'Item numeric values changed')
        add(0xC3D90C,'numeric_item_format_argument','Native bounded indexing selects integer 200 from an eight-word table passed to the item formatter.',case_ids=['numeric_item_arguments'])
        check(c.load_raw_state(system.STATE.read_bytes()),'Ally table state restore');at=0x020090C0;size=56;before=bytes(c.memory[at-8:at+size+8]);c.memory.u32[0x02000624]=0;t=ui.InterfaceTrace(c)
        try:ui.native_step(s,t,0x08071294,[],stop=0x080712B4)
        finally:t.close()
        check(bytes(c.memory[at:at+size])==data[0xC3DB78:0xC3DB78+size],'Native ally table copy differs');check(bytes(c.memory[at-8:at])==before[:8] and bytes(c.memory[at+size:at+size+8])==before[-8:],'Ally table copy changed adjacent bytes')
        check(c.memory.u32[at]==100,'Ally first command ID differs');cases.append({'id':'ally_command_table_0','reader':'08071294..080712B4','record_bytes':size,'copied_hex':bytes(c.memory[at:at+size]).hex(),'first_numeric_command':100,'guards_intact':True})
        add(0xC3DB78,'numeric_ally_command_id','Command ID 100, selected/copied with seven typed command/label pairs by the original ally-menu reader. Label relocation ownership remains with the accepted ally component.',case_ids=['ally_command_table_0'])
        offsets=[]
        for index in range(5):
            result=queue.select_slice(c,0x0807C07C,0x0807C086,{'r5':index,'r1':0},6);value=int(result['source'],0);value=value-0x100000000 if value&0x80000000 else value;offsets.append(value)
        check(offsets==[-2,46,86,130,170],'Keyboard X offsets differ');cases.append({'id':'keyboard_x_offsets','reader':'0807C07C..0807C086','values':offsets})
        add(0xC454E4,'numeric_keyboard_coordinate','Native input-cursor indexing identifies the final word as X offset 170, not a kana glyph.',case_ids=['keyboard_x_offsets'])
        coordinates=[]
        for index in range(30):
            check(c.load_raw_state(system.STATE.read_bytes()),'World-coordinate state restore')
            system.guard(c,old.DEST,8);t=ui.InterfaceTrace(c)
            try:result=ui.native_step(s,t,0x08066CE0,[index,old.DEST])
            finally:t.close()
            pair=bytes(c.memory[old.DEST:old.DEST+8]);expected=original[0x872E88+index*12:0x872E90+index*12]
            check(pair==expected,'Native world coordinates differ');system.guards(c,old.DEST,8)
            x,y=struct.unpack('<ii',pair);check(result['return_r0']==int(x>=0),'Coordinate availability flag differs')
            coordinates.append({'row':index,'x':x,'y':y,'available':result['return_r0'],'guards_intact':True})
        check(coordinates[-1]['y']==33,'Final world Y coordinate differs')
        cases.append({'id':'world_label_coordinates','reader':'08066CE0','table':'0x872e84','rows':coordinates})
        add(0x872FE8,'numeric_world_map_coordinate','Y coordinate 33 in the last of thirty label/X/Y records; all pairs pass the original signed-coordinate reader.',case_ids=['world_label_coordinates'])
        check(c.load_raw_state(system.STATE.read_bytes()),'Trigger state restore')
        selected=queue.select_slice(c,0x0806C390,0x0806C3BA,{'r0':5,'r1':27},4)
        record=int(selected['source'],0);check(record==0x08946B00,'Native trigger group/record selection differs')
        system.guard(c,old.DEST,28);t=ui.InterfaceTrace(c)
        try:ui.native_step(s,t,0x0806C47A,[],stop=0x0806C526,overrides={0x0806C47A:{'r2':old.DEST,'r5':0,'r6':27,'r7':record,'r12':0}})
        finally:t.close()
        check(c.memory.u32[old.DEST+24]==0x08946070,'Native trigger descriptor indirection differs');system.guards(c,old.DEST,28)
        cached=bytes(c.memory[0x03000030:0x03000044]);c.memory.u32[0x03000038]=old.DEST
        ctrl=scene.CONTROLLER;system.guard(c,ctrl,scene.CONTROLLER_BYTES);old.write_bytes(c,ctrl,bytes(scene.CONTROLLER_BYTES));t=ui.InterfaceTrace(c)
        try:
            source=ui.native_step(s,t,0x0806C55C,[0])['return_r0'];check(source==0x08946070,'Native trigger getter differs')
            # This is the common activation reached by the reviewed actor
            # wrapper 08069A70. The scratch controller is explicitly supplied.
            ui.native_step(s,t,0x08064488,[ctrl,0,2,source])
        finally:t.close()
        fetched=queue.select_slice(c,0x08064E28,0x08064E60,{'r0':ctrl},0)
        table=struct.unpack_from('<I',original,0x64E64)[0];dispatch=c.memory.u32[table+(0x5A-1)*4]
        check(int(fetched['source'],0)==dispatch and c.memory.u32[ctrl+0x34]==source and c.memory.u32[ctrl+0x24]==source+8 and c.memory.u8[ctrl+0x38]==0x5A,'Trigger command dispatch differs')
        system.guards(c,ctrl,scene.CONTROLLER_BYTES);system.guards(c,old.DEST,28)
        check(bytes(c.memory[0x03000030:0x03000038])==cached[:8] and bytes(c.memory[0x0300003C:0x03000044])==cached[-8:],'Trigger pointer adjacent bytes changed')
        c.memory.u32[0x03000038]=struct.unpack_from('<I',cached,8)[0]
        check(bytes(c.memory[0x03000030:0x03000044])==cached,'Trigger cache restore differs')
        check(data[0x946070:0x946078]==original[0x946070:0x946078],'Original trigger command changed')
        cases.append({'id':'trigger_program','scene':5,'group':27,'record':'0x946b00','group_word':'0x946be4','descriptor':'0x9461dc','program':'0x946070','command_hex':original[0x946070:0x946078].hex(),'dispatch':hex(dispatch),'runtime_trigger_hex':bytes(c.memory[old.DEST:old.DEST+28]).hex(),'guards_intact':True,'cache_restored':True,'scope':'Native group selection, constructor indirection, getter, supplied scratch-controller activation and original fetch. Actor intersection/actions and natural reachability are not executed.'})
        add(0x946070,'trigger_event_command','Opcode 5A reached through scene 5 / trigger group 27, the native trigger constructor and getter, and a bounded native event activation/fetch.',case_ids=['trigger_program'])
        parent_path=scene.OUTPUT/'native-verification.json';parent=load_json(parent_path)
        check(parent['verified_rom_sha256']==digest(data) and parent['harness_sha256']==digest(Path(scene.__file__).read_bytes()),'Scene ancestry proof changed')
        ancestry=next(e for e in parent['entries'] if int(e['offset'],0)==0xB9F01C)
        check(ancestry['opcode']==0x45 and ancestry['dispatch_target']=='0x8065772' and ancestry['guards_intact'],'Missing preceding-command proof')
        check(data[0xB9F01C:0xB9F02C]==original[0xB9F01C:0xB9F02C]==bytes.fromhex('4500000070000000a700000000000000'),'Continuation command bytes differ')
        check(c.load_raw_state(system.STATE.read_bytes()),'Continuation state restore')
        system.guard(c,ctrl,scene.CONTROLLER_BYTES);old.write_bytes(c,ctrl,bytes(scene.CONTROLLER_BYTES));t=ui.InterfaceTrace(c)
        try:ui.native_step(s,t,0x08064488,[ctrl,0,2,0x08B9F01C])
        finally:t.close()
        first=queue.select_slice(c,0x08064E28,0x08064E60,{'r0':ctrl},0)
        check(int(first['source'],0)==0x08065772 and c.memory.u32[ctrl+0x24]==0x08B9F024,'Preceding native fetch differs')
        before=bytes(c.memory[ctrl:ctrl+scene.CONTROLLER_BYTES])
        # The virtual callback at 0806577A is deliberately not executed.
        # Supply the preserved controller registers at its return point.
        second=queue.select_slice(c,0x0806577E,0x08064E60,{'r7':ctrl,'r10':ctrl+0x20,'sp':0x03007800},0)
        expected=bytearray(before);struct.pack_into('<I',expected,0x24,0x08B9F02C);struct.pack_into('<I',expected,0x34,0x08B9F024);expected[0x38]=0xA7
        check(int(second['source'],0)==0x08066492 and bytes(c.memory[ctrl:ctrl+scene.CONTROLLER_BYTES])==expected,'Continuation fetch/dispatch or surrounding controller fields differ')
        end=queue.select_slice(c,0x08066492,0x08066498,{},0)
        check(int(end['source'],0)==0,'A7 epilogue selector differs');system.guards(c,ctrl,scene.CONTROLLER_BYTES)
        cases.append({'id':'following_a7_command','preceding_scene_proof':str(parent_path.relative_to(ROOT)),
            'preceding_scene_proof_sha256':digest(parent_path.read_bytes()),'selected_owner':ancestry['selected_owner'],
            'first_fetch':first,'post_callback_fetch':second,'epilogue_selection':end,
            'source':'0xb9f024','command_hex':'a700000000000000','guards_intact':True,
            'other_controller_bytes_intact':True,'scope':'Native activation/fetch of the previously verified opcode 45, then a separate bounded slice from its callback return to the following A7 dispatch. Controller registers and stack are supplied. The virtual callback, event consequences, epilogue return and natural temple reachability are not executed.'})
        add(0xB9F024,'following_event_command','Opcode A7 follows the reader-confirmed temple command 45; its post-callback branch and native fetch/dispatch establish command bytes rather than a kana string. Callback effects and natural reachability remain untested.',case_ids=['following_a7_command'])
    result={'status':'remaining_fields_native_verified','source_sha256':digest(original),'verified_rom':str(BASELINE.relative_to(ROOT)),'verified_rom_sha256':digest(data),'harness_sha256':digest(Path(__file__).read_bytes()),'fixture_sha256':digest(system.STATE.read_bytes()),'helper_sha256':{Path(m.__file__).name:digest(Path(m.__file__).read_bytes()) for m in (ui,queue,old,system)},'entries':entries,'cases':cases,'scope':'Four numeric fields, one trigger program, one following command through bounded native readers and eleven original ASCII values through cold startup pointers. Later readers of the ASCII values, natural trigger conditions and event actions remain unconfirmed; no displayed-language translation, free space or ROM changes.'}
    check(len(entries)==17,'Remaining field count differs');atomic_write(OUTPUT/'native-verification.json',(json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode());print(len(entries),'remaining fields/ASCII values verified',flush=True)

if __name__=='__main__':audit()
