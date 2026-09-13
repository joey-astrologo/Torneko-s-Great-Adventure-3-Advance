"""Cold-load the naturally earned Mysterious cave clear, records and both Logs."""
from pathlib import Path
import struct
import mgba.log
from mgba._pylib import ffi
from tools import verify_cave_clear as route, verify_roundtrip as trip
from tools import verify_name_entry as names
from tools.verify_result_runtime import map_errors, ink_pixels
from tools.verify_expansion import Session
from tools.verify_natural_cave import sources
from tools.build_name_entry import NAME_RAM
from tools.build_first_label import ROOT, ORIGINAL_ROM, digest
from tools.audit_scene_resources import BASELINE
from tools.translation_pipeline import check, load_json


def cold():
    mgba.log.silence();data=BASELINE.read_bytes();build=load_json(BASELINE.parent/'english-build.json')
    replay=load_json(route.OUT/'replay.json');saved=(route.OUT/'clear-route/latest.sav').read_bytes()
    check(digest(data)==replay['rom_sha256'] and digest(saved)==replay['expected_final_save_sha256'],'Cold cave inputs changed')
    initial=(ROOT/replay['initial_save']).read_bytes()
    check(len(saved)==65536 and saved!=initial,'Clear did not create a native save')
    # Existing Adventure Log layout: two seven-sector blocks followed by profile.
    check(saved[0x7000:0xE000]==initial[0x7000:0xE000],'Saving Log 1 changed Log 2 sectors')
    earned=saved[0xE014:0xE044]
    check(struct.unpack_from('<5H',earned)==(91,0,0,0,0) and int.from_bytes(earned[10:13],'little')==4002
          and earned[25]==3 and earned[26]&63==0,'Saved result is not the earned first-cave clear')
    index,_,_=sources(data,build['ledger']);folder=route.OUT/'cold'
    inputs=[('title','START',240),('down-1','DOWN',30),('down-2','DOWN',30),
            ('categories','A',240),('list','A',240),('detail','A',240),
            ('back-list','B',120),('back-categories','B',120),('history-selected','DOWN',30),
            ('history','A',240),('history-back','B',120),('title-back','B',120),
            ('slots','A',240),('load','A',240),('village','A',600),('welcome-dismissed','A',300),
            ('priest-dismissal','B',180),('world-menu','B',180)]
    with Session(data,folder,saved) as s:
        c=s.core;t=trip.RoundtripTrace(c,data,index,[])
        try:
            t.frames(600);pixels=None
            for phase,key,wait in inputs:
                t.phase=phase;s.press(key,wait,t);screen=s.capture(phase)
                if phase=='detail':
                    check(bytes(c.memory[trip.PROFILE:trip.PROFILE+trip.PROFILE_SIZE])==saved[0xE000:0xFFAC],'Cold profile differs')
                    raw=bytes(c.memory[0x02034DDC:0x020355DC])
                    check(not map_errors(raw) and raw==bytes(c.memory[0x06006000:0x06006800]),'Cold result tilemap differs')
                    check(bytes(c.memory[0x02035E1C:0x0203977C])==bytes(c.memory[0x06000040:0x060039A0]),'Cold result bitmap differs')
                    pixels=ink_pixels(c,screen)
                    check(pixels['white_ink_pixels']>500 and pixels['mismatched_white_ink_pixels']==0,'Cold clear ink differs')
            r=t.report();route.save(folder/'raw-trace.json',r)
            check(not t.errors and pixels is not None,'Cold clear trace failed')
            check(c.memory.u32[0x0200000C]==0 and bytes(c.memory[NAME_RAM:NAME_RAM+8])==trip.EXPECTED_NAME,'Cold village/name differs')
            loads=[e for e in t.save_events if e['pc']=='0x800230a']
            check(loads and all(e['record_name_hex']==trip.EXPECTED_NAME.hex() for e in loads),'Cold native saved name differs')
            checks=trip.language_checks(r,data,index,build['ledger']);strings=[e['text'] for e in checks['whole_string_draws']]
            for text in ('Records','Torneko: High scores','Adventure history','Cleared safely','[Torneko] Barinabo Village'):
                check(text in strings,'Cold clear text missing: '+text)
            (folder/'village.state').write_bytes(bytes(ffi.buffer(c.save_raw_state())))
            r.update(rom_sha256=digest(data),input_save_sha256=digest(saved),checks=checks,detail_pixels=pixels,
                     earned_record_hex=earned.hex(),inputs=s.frames_recorded,
                     scope='Fresh core, native clear save; records/category/list/detail/history then Log 1 load and world menu. No save/state edits.')
            route.save(folder/'trace.json',r)
        finally:t.close()
    check(s.disk_save==saved,'Cold records/load changed save bytes')
    names.reload_name(data,saved,route.OUT/'cold-log-2',trip.EXPECTED_NAME,slot=2,select_slot=True)
    result={'status':'cold_cave_clear_save_verified','source_sha256':digest(ORIGINAL_ROM.read_bytes()),
            'verified_rom':str(BASELINE.relative_to(ROOT)),'verified_rom_sha256':digest(data),
            'harness_sha256':digest(Path(__file__).read_bytes()),'input_save_sha256':digest(saved),
            'earned_record_hex':earned.hex(),'score':4002,'floor':3,'cause':91,'save_bytes':65536,
            'log_2_sectors_unchanged':True,'name':'Torneko','logs_checked':[1,2],
            'detail_pixels':pixels,'whole_string_draws':len(checks['whole_string_draws']),
            'reports':{str(p.relative_to(route.OUT)):digest(p.read_bytes()) for p in (folder/'trace.json',route.OUT/'cold-log-2/trace.json')},
            'scope':'Cold persistence/renderer check of the exploration save. The uninterrupted source route must pass separately before combined acceptance.'}
    route.save(route.OUT/'cold-verification.json',result)
    print(result['status'],flush=True)
    return result


if __name__=='__main__':cold()
