"""Seed existing ally-name fields, run native FLASH saves and cold-load both slots."""
from pathlib import Path
import mgba.log
from mgba._pylib import ffi,lib
from tools import verify_name_entry as names
from tools.build_ally_nicknames import OUTPUT,CATALOG
from tools.build_first_label import ORIGINAL_ROM,digest
from tools.build_name_entry import compact_name,LATIN
from tools.translation_pipeline import check,load_json
from tools.verify_items import write_json
from tools.verify_core_gameplay import write_bytes

POOL=0x0200EE80

class SaveTrace(names.NameEntryTrace):
    def __init__(self,core,seed,events):
        self.seed=seed;self.save_events=events
        super().__init__(core)
        for address in (0x08002184,0x080021BE,0x0800253A):
            p=ffi.new('struct mBreakpoint*');p.address=address;p.segment=-1;p.type=lib.BREAKPOINT_HARDWARE
            check(self.debugger.platform.setBreakpoint(self.debugger.platform,p)>=0,'Save probe failed')
    def entered(self,debugger,reason,info):
        try:
            if info!=ffi.NULL and reason==lib.DEBUGGER_ENTER_BREAKPOINT and info.address in (0x08002184,0x080021BE,0x0800253A):
                at=int(info.address);base=int(self.cpu.gprs[6])&0xffffffff
                if at==0x08002184:
                    before=bytes(self.core.memory[POOL:POOL+130*32]);expected=bytearray(before)
                    if self.seed is not None:
                        for i,e in enumerate(self.seed):
                            payload=bytes.fromhex(e['compact_hex']).split(b'\0')[0].ljust(6,b'\0')
                            write_bytes(self.core,POOL+32*i+4,payload);expected[32*i+4:32*i+10]=payload
                    after=bytes(self.core.memory[POOL:POOL+130*32]);check(after==bytes(expected),'Save fixture altered non-name fields')
                    self.save_events.append({'phase':'seed','record_base':hex(base),'pool_hex':after.hex(),'only_nickname_fields_changed':True})
                elif at==0x080021BE:
                    observed=bytes(self.core.memory[base+0x4490:base+0x54D0]);pool=bytes(self.core.memory[POOL:POOL+130*32])
                    check(observed==pool,'Native Adventure Log serializer changed ally records')
                    self.save_events.append({'phase':'serialize','record_base':hex(base),'pool_hex':observed.hex()})
                else:
                    observed=bytes(self.core.memory[POOL:POOL+130*32]);record=bytes(self.core.memory[base+0x4490:base+0x54D0])
                    check(observed==record,'Native cold-load inverse changed ally records')
                    self.save_events.append({'phase':'restore','record_base':hex(base),'pool_hex':observed.hex()})
                return
            super().entered(debugger,reason,info)
        except Exception as error:self.errors.append(str(error))
        finally:debugger.state=lib.DEBUGGER_RUNNING


def with_probe(seed,events,operation):
    original=names.attach;traces=[]
    def attach(session):
        trace=SaveTrace(session.core,seed,events);frames=session.frames
        traces.append(trace)
        session.frames=lambda n,unused=None:trace.frames(n)
        return trace,frames
    names.attach=attach
    try:
        result=operation()
        check(traces and all(not t.errors for t in traces),str([t.errors for t in traces]))
        return result
    finally:names.attach=original


def verify():
    mgba.log.silence();rom=OUTPUT/'torneko3-ally-nicknames-english.gba';data=rom.read_bytes();out=OUTPUT/'verification/nickname-saves'
    native=load_json(OUTPUT/'verification/english/verification.json')
    seeds=[{'id':c['id'],'compact_hex':c['stored_hex']} for c in native['cases'] if c['suffix']==9]
    japanese=load_json(OUTPUT/'verification/baseline/verification.json')
    seeds += [{'id':'legacy-'+c['id'],'compact_hex':c['stored_hex']} for c in japanese['cases'] if c['row'] in (3,18,21) and c['suffix']==1]
    import string
    chars=string.ascii_uppercase+string.ascii_lowercase+string.digits
    seeds += [{'id':'custom-'+chars[i:i+5],'compact_hex':compact_name(chars[i:i+5]).hex()} for i in range(0,len(chars),5)]
    groups=[seeds[:130],seeds[130:]];saves=[];cases=[];initial=None
    for slot,group in enumerate(groups,1):
        events=[]
        save,report=with_probe(group,events,lambda:names.creation(data,out/f'create-{slot}',slot,initial_save=initial))
        check(len(save)==65536,'FLASH size changed')
        serialized=[e for e in events if e['phase']=='serialize'];check(serialized,'Normal save route skipped ally serializer')
        for i,e in enumerate(group):check(bytes.fromhex(serialized[-1]['pool_hex'])[32*i+4:32*i+10]==bytes.fromhex(e['compact_hex']).split(b'\0')[0].ljust(6,b'\0'),'Saved ally name differs')
        loaded=[]
        with_probe(None,loaded,lambda:names.reload_name(data,save,out/f'load-{slot}',compact_name('Torneko'),slot,select_slot=slot==2))
        restored=[e for e in loaded if e['phase']=='restore'];check(restored and restored[0]['pool_hex']==serialized[-1]['pool_hex'],'Cold cartridge load lost ally block')
        cases.append({'slot':slot,'names':group,'save_sha256':digest(save),'events':events,'cold_load_events':loaded,'whole_ally_block_identical':True})
        saves.append(save);initial=save
        print('nickname save slot',slot,'passed',len(group),'names',flush=True)
    # Loading slot 1 from the final two-slot FLASH file must still restore its
    # original ally block, independently of slot 2's seeded nickname fields.
    loaded=[]
    with_probe(None,loaded,lambda:names.reload_name(data,saves[-1],out/'reload-first-with-both-slots',compact_name('Torneko')))
    restored=[e for e in loaded if e['phase']=='restore']
    first=[e for e in cases[0]['events'] if e['phase']=='serialize'][-1]
    check(restored and restored[0]['pool_hex']==first['pool_hex'],'Saving second slot changed first ally block')
    result={'rom_sha256':digest(data),'catalog_sha256':digest(CATALOG.read_bytes()),'harness_sha256':digest(Path(__file__).read_bytes()),'name_helper_sha256':digest(Path(names.__file__).read_bytes()),'source_sha256':digest(ORIGINAL_ROM.read_bytes()),'save_bytes':65536,'cases':cases,'first_slot_preserved':True,'all_200_defaults_cold_loaded':True,'custom_character_ids':len(chars),'legacy_japanese_names':3,'torneko_seven_character_regression':True,'scope':'Only nickname fields of existing 32-byte records seeded immediately before original serializer. Normal Adventure Log creation, native FLASH persistence and fresh-core button-driven load; full 130-record blocks compared. Does not establish natural recruitment, active-party eligibility, dungeon suspend-save or ranking behavior.'}
    write_json(out/'verification.json',result);return result

if __name__=='__main__':verify()
