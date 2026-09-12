"""Native high-score creation, row shifting and separate profile FLASH storage."""
from pathlib import Path
import struct
import mgba.log
from tools import verify_adventure_results as v
from tools import verify_core_gameplay as old
from tools import verify_dungeon_interface as ui
from tools import verify_name_entry as names
from tools.build_name_entry import compact_name
from tools.build_first_label import ORIGINAL_ROM,digest
from tools.translation_pipeline import check,load_json
from tools.verify_expansion import Session
from tools.verify_first_label import battery_snapshot
from tools.verify_items import write_json

PROFILE=0x02002FD4
SIZE=0x1FAC
INPUT=v.b.ROOT/'build/completion/special/verification/pet-saves/create-2/created.sav'
OUTPUT=v.b.OUTPUT/'verification/profile-saves'


def native_flash(session,trace):
    """Allow native FLASH polling/interrupts a longer bound than UI helpers."""
    c=session.core;cpu=trace.cpu;saved={f'r{i}':int(cpu.gprs[i])&0xffffffff for i in range(15)}
    cpsr=int(cpu.cpsr.packed);pc=(int(cpu.gprs[15])&0xffffffff)-(2 if cpsr&32 else 4)
    ui.registers(c,{'cpsr':0x3F,'sp':0x03007E00,'r6':PROFILE,'r8':0,'r5':0,'lr':0x08000001,'pc':0x08001710})
    try:
        for steps in range(20000000):
            at=(int(cpu.gprs[15])&0xffffffff)-(2 if cpu.cpsr.packed&32 else 4)
            if at==0x0800174C:return {'return_r0':int(cpu.gprs[0])&0xffffffff,'steps':steps,'interrupts_enabled':True}
            c.step()
        raise RuntimeError(f'Native FLASH did not finish at {at:08X}')
    finally:ui.registers(c,{'cpsr':cpsr,**saved,'pc':pc})


def context(core):
    root=0x02010A90;actor=0x0203F000
    check(core.memory.u32[0x0200000C]==0,'Expected a restored village state')
    core.memory.u32[0x0200000C]=root
    old.write_bytes(core,actor,bytes(0x150));core.memory.u16[actor+8]=1
    core.memory.u32[actor+0x54]=42;core.memory.u32[actor+0x58]=100;core.memory.u32[actor+0x9C]=123456
    core.memory.u32[root+0x19EE4]=actor;core.memory.u32[root+0x14E4]=1000000
    core.memory.u16[root+0x150C]=1;core.memory.u32[root+0x14DC]=0
    for offset,value in [(0x20E64,5),(0x20E66,1),(0x20E68,0),(0x20E6A,215),(0x20E6C,1),(0x20E70,99)]:core.memory.u16[root+offset]=value
    return root


def verify():
    mgba.log.silence();rom=(v.b.OUTPUT/'torneko3-adventure-results-english.gba').read_bytes();initial=INPUT.read_bytes();check(len(initial)==65536,'Profile input save size')
    cases=[]
    with Session(rom,OUTPUT/'write',initial) as session:
        c=session.core;check(c.load_raw_state(v.STATE.read_bytes()),'Profile write state')
        check(battery_snapshot(c)==initial,'State restore changed cartridge save')
        trace=ui.InterfaceTrace(c)
        try:
            read=ui.native_step(session,trace,0x08087CBC,[14,PROFILE,SIZE]);check(read['return_r0']==1,'Native initial profile read failed')
            original=bytes(c.memory[PROFILE:PROFILE+SIZE]);check(original==initial[0xE000:0xFFAC],'Initial profile differs from native sector read')
            initial_checksum=ui.native_step(session,trace,0x080015E0,[PROFILE])['return_r0']
            if initial_checksum:
                check(original==b'\xff'*SIZE,'Unexpected non-erased invalid input profile')
                # New Adventure Logs have not yet created a score/history profile.
                # The real frontend uses this same native initializer on load.
                ui.native_step(session,trace,0x080011C0,[])
                original=bytes(c.memory[PROFILE:PROFILE+SIZE])
            # Build a controlled board using the real writer, including an insertion
            # that shifts each existing first-place result into second place.
            root=context(c);old.write_bytes(c,v.RECORD,bytes(160*48))
            for pass_index in (1,2):
                c.memory.u32[root+0x14E4]=1000000*pass_index
                for hero in (0,1):
                    for subcategory,dungeon in enumerate((0,20,18,31)):
                        category=4*hero+subcategory;before=bytes(c.memory[v.RECORD:v.RECORD+160*48]);at=category*960
                        old.write_bytes(c,old.DEST-8,old.GUARD+bytes(8)+old.GUARD)
                        call=ui.native_step(session,trace,0x080011F0,[0,hero,dungeon,old.DEST,old.DEST+4])
                        check(call['return_r0']==1 and c.memory.u32[old.DEST+4]==category,'Native score rank/category differs')
                        after=bytes(c.memory[v.RECORD:v.RECORD+160*48]);record=after[at:at+48]
                        check(after[:at]==before[:at] and after[at+960:]==before[at+960:],'Other score category changed')
                        check(after[at+48:at+960]==before[at:at+912],'Native 48-byte row shift differs')
                        check(struct.unpack_from('<5H',record)==(5,1,0,215,1),'Saved cause/actor/item fields differ')
                        check(record[25]==99 and record[26]&63==dungeon and (record[26]>>6)&1==hero,'Saved floor/dungeon/protagonist fields differ')
                        check(int.from_bytes(record[10:13],'little')==100000*pass_index,'Native score computation differs')
                        check(bytes(c.memory[old.DEST-8:old.DEST])==old.GUARD and bytes(c.memory[old.DEST+8:old.DEST+16])==old.GUARD,'Score output overrun')
                        cases.append({'pass':pass_index,'category':category,'hero':hero,'dungeon':dungeon,'record_hex':record.hex(),'score':c.memory.u32[old.DEST],'whole_rows_shifted':True,'other_categories_preserved':True})
            profile=bytes(c.memory[PROFILE:PROFILE+SIZE])
            check(profile[:20]==original[:20] and profile[20+160*48:]==original[20+160*48:],'Record fixture changed non-score profile fields')
        finally:trace.close()
        # Restore the real heap before invoking the native FLASH allocator/driver.
        check(c.load_raw_state(v.STATE.read_bytes()),'Restore real heap before FLASH')
        old.write_bytes(c,PROFILE,profile);trace=ui.InterfaceTrace(c)
        try:
            write=native_flash(session,trace)
            check(write['return_r0']==1,'Native profile FLASH write failed')
            expected=bytes(c.memory[PROFILE:PROFILE+SIZE]);saved=battery_snapshot(c)
            check(len(saved)==65536 and saved[:0xE000]==initial[:0xE000],'Profile write changed Adventure Log sectors')
            check(saved[0xE000:0xFFAC]==expected,'Native profile bytes not present in FLASH')
            sector_source=bytes(c.memory[PROFILE:PROFILE+0x2000])
            check(saved[0xE000:]==sector_source,'Native profile full-sector copy differs')
            check(ui.native_step(session,trace,0x080015E0,[PROFILE])['return_r0']==0,'Native written profile checksum invalid')
        finally:trace.close()
    check(session.disk_save==saved,'Profile save was not persisted to cartridge file')
    (OUTPUT/'profile.sav').write_bytes(saved)
    with Session(rom,OUTPUT/'cold-read',saved) as cold:
        cold.frames(600);c=cold.core;trace=ui.InterfaceTrace(c)
        try:
            read=ui.native_step(cold,trace,0x08087CBC,[14,PROFILE,SIZE]);check(read['return_r0']==1,'Cold native profile read failed')
            check(bytes(c.memory[PROFILE:PROFILE+SIZE])==expected,'Cold core lost high scores/history')
            check(ui.native_step(cold,trace,0x080015E0,[PROFILE])['return_r0']==0,'Cold profile checksum invalid')
        finally:trace.close()
    regressions=[]
    for slot in (1,2):
        names.reload_name(rom,saved,OUTPUT/f'AdventureLog-{slot}',compact_name('Torneko'),slot,select_slot=slot==2)
        regressions.append({'slot':slot,'seven_character_name':'Torneko','cold_load_passed':True})
    result={'status':'native_result_profile_save_checks_passed','rom_sha256':digest(rom),'source_sha256':digest(ORIGINAL_ROM.read_bytes()),
        'harness_sha256':digest(Path(__file__).read_bytes()),'input_save_sha256':digest(initial),'output_save_sha256':digest(saved),
        'initial_profile_was_erased':bool(initial_checksum),
        'fixture_sha256':digest(v.STATE.read_bytes()),'save_bytes':len(saved),'profile_bytes':SIZE,'record_creation':cases,
        'native_checksum_and_sector_roundtrip':True,'cold_core_profile_identical':True,'adventure_log_sectors_unchanged':True,
        'native_flash_call':write,
        'native_sector_copy_bytes':8192,'native_sector_tail_hex':saved[0xFFAC:].hex(),
        'adventure_logs':regressions,'scope':'Controlled native record creation in an explicitly synthetic dungeon context, whole-row shifting in all eight categories, then original checksum/header/FLASH write and fresh-core sector read with restored real heap. Both existing Adventure Logs cold-load Torneko. Natural dungeon outcomes and autosave timing remain separate.'}
    write_json(OUTPUT/'verification.json',result);print(result['status'],flush=True)


if __name__=='__main__':verify()
