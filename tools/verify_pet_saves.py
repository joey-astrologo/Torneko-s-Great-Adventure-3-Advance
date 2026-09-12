"""Native FLASH persistence of the existing seven-halfword pet name variables."""
from pathlib import Path
import mgba.log
from mgba._pylib import ffi,lib
from tools import verify_name_entry as names
from tools import build_story_special as b
from tools.verify_story_special import compact
from tools.build_name_entry import compact_name
from tools.build_first_label import ORIGINAL_ROM,digest
from tools.verify_core_gameplay import write_bytes
from tools.verify_items import write_json
from tools.translation_pipeline import load_json,check

VARIABLES=0x020010C0
SIZE=0x400
RECORD=0x1B88


class SaveTrace(names.NameEntryTrace):
    def __init__(self,core,seeds,events):
        self.seeds=seeds;self.save_events=events
        super().__init__(core)
        for address in (0x08002012,0x08002016,0x08002390):
            p=ffi.new('struct mBreakpoint*');p.address=address;p.segment=-1;p.type=lib.BREAKPOINT_HARDWARE
            check(self.debugger.platform.setBreakpoint(self.debugger.platform,p)>=0,'Pet save breakpoint failed')
    def entered(self,debugger,reason,info):
        try:
            if info!=ffi.NULL and reason==lib.DEBUGGER_ENTER_BREAKPOINT and info.address in (0x08002012,0x08002016,0x08002390):
                at=int(info.address);base=int(self.cpu.gprs[6])&0xffffffff
                if at==0x08002012:
                    before=bytes(self.core.memory[VARIABLES:VARIABLES+SIZE]);expected=bytearray(before)
                    if self.seeds is not None:
                        for index,raw in self.seeds.items():
                            check(len(raw)==14,'Wrong pet save seed size');write_bytes(self.core,VARIABLES+index*2,raw);expected[index*2:index*2+14]=raw
                    after=bytes(self.core.memory[VARIABLES:VARIABLES+SIZE]);check(after==bytes(expected),'Save fixture altered non-pet variables')
                    self.save_events.append({'phase':'seed','record_base':hex(base),'variables_hex':after.hex(),'only_pet_fields_changed':True})
                else:
                    live=bytes(self.core.memory[VARIABLES:VARIABLES+SIZE]);record=bytes(self.core.memory[base+RECORD:base+RECORD+SIZE])
                    check(live==record,'Native pet variable serialization/restore differs')
                    self.save_events.append({'phase':'serialize' if at==0x08002016 else 'restore','record_base':hex(base),'variables_hex':record.hex()})
                return
            super().entered(debugger,reason,info)
        except Exception as error:self.errors.append(str(error))
        finally:debugger.state=lib.DEBUGGER_RUNNING


def with_probe(seeds,events,operation):
    original=names.attach;traces=[]
    def attach(session):
        trace=SaveTrace(session.core,seeds,events);frames=session.frames;traces.append(trace)
        session.frames=lambda n,unused=None:trace.frames(n)
        return trace,frames
    names.attach=attach
    try:
        result=operation();check(traces and all(not t.errors for t in traces),str([t.errors for t in traces]));return result
    finally:names.attach=original


def verify():
    mgba.log.silence();rom=b.OUTPUT/'torneko3-story-special-english.gba';data=rom.read_bytes();original=ORIGINAL_ROM.read_bytes();out=b.OUTPUT/'verification/pet-saves'
    proof_path=b.OUTPUT/'verification/inputs/verification.json';proof=load_json(proof_path);check(proof['rom_sha256']==digest(data),'Pet input proof has different ROM')
    inputs={e['id']:e for e in proof['cases']}
    legacy=b''.join(i.to_bytes(2,'little') for i in compact('あああああああ',original))
    groups=[{0x57:bytes.fromhex(inputs['dog-seven']['stored_hex']),0x5F:bytes.fromhex(inputs['cat-1-seven']['stored_hex'])},
            {0x57:bytes.fromhex(inputs['dog-short']['stored_hex']),0x5F:legacy}]
    initial=None;cases=[]
    for slot,seeds in enumerate(groups,1):
        events=[]
        save,_=with_probe(seeds,events,lambda:names.creation(data,out/f'create-{slot}',slot,initial_save=initial))
        serialized=[e for e in events if e['phase']=='serialize'];check(serialized and len(save)==65536,'Missing native pet save')
        block=bytes.fromhex(serialized[-1]['variables_hex'])
        for index,raw in seeds.items():check(block[index*2:index*2+14]==raw,'Saved pet name differs')
        loaded=[];with_probe(None,loaded,lambda:names.reload_name(data,save,out/f'load-{slot}',compact_name('Torneko'),slot,select_slot=slot==2))
        restored=[e for e in loaded if e['phase']=='restore'];check(restored and restored[0]['variables_hex']==serialized[-1]['variables_hex'],'Cold load lost pet variables')
        cases.append({'slot':slot,'seeds':{hex(i):raw.hex() for i,raw in seeds.items()},'save_sha256':digest(save),'events':events,'cold_load_events':loaded,'whole_variable_block_identical':True})
        initial=save;print('pet save slot',slot,'passed',flush=True)
    loaded=[];with_probe(None,loaded,lambda:names.reload_name(data,initial,out/'reload-first-with-both-slots',compact_name('Torneko')))
    restored=[e for e in loaded if e['phase']=='restore'];first=[e for e in cases[0]['events'] if e['phase']=='serialize'][-1]
    check(restored and restored[0]['variables_hex']==first['variables_hex'],'Second slot overwrote first pet names')
    result={'rom_sha256':digest(data),'source_sha256':digest(original),'catalog_sha256':digest((b.OUTPUT/'catalog.json').read_bytes()),'harness_sha256':digest(Path(__file__).read_bytes()),'name_helper_sha256':digest(Path(names.__file__).read_bytes()),'input_proof_sha256':digest(proof_path.read_bytes()),'save_bytes':65536,'cases':cases,'first_slot_preserved':True,'torneko_seven_character_regression':True,'scope':'Only existing pet-name variables seeded immediately before native serialization, using actual native keyboard/commit results plus a legacy Japanese fixture. Normal Adventure Log creation, native FLASH writes and fresh-core button-driven cold loads. Entire 1,024-byte variable block compared, including non-name fields. Does not establish natural adoption or dungeon suspend/ranking behavior.'}
    write_json(out/'verification.json',result);return result


if __name__=='__main__':verify()
