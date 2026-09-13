"""Bounded native evidence for unowned gameplay text; no insertion/non-use claim."""
import json
import struct
from pathlib import Path
import mgba.log
from tools.build_first_label import ROOT, ORIGINAL_ROM, digest
from tools.audit_scene_resources import BASELINE
from tools import verify_dungeon_interface as ui, verify_tutorial_gameplay as queue
from tools import verify_core_gameplay as old, verify_system_labels as system
from tools import verify_item_display as items
from tools.verify_items import install_item
from tools.verify_expansion import Session
from tools.translation_pipeline import check, load_json, atomic_write

OUT = ROOT/'build/completion/gameplay-candidates'
TARGETS = (0x1B3F2D,0x1B4495,0x1B449D,0x1B44A1,0x1B44A5,0x1B44AB,0x1B44AF,
           0x1B4563,0x1B530A,0x1B551C,0x1B565D,0x1B5F14,0x1B6B6E,0x1B8A4A,
           0x1B93ED,0xC782E4,0xC7876C)


def run():
    mgba.log.silence(); original=ORIGINAL_ROM.read_bytes(); current=BASELINE.read_bytes()
    catalog=load_json(ROOT/'translations/unowned-text-review.json')
    entries=[]
    for e in catalog['entries']:
        at=int(e['offset'],0)
        if at not in TARGETS: continue
        raw=bytes.fromhex(e['source_hex'])
        check(original[at:at+len(raw)]==current[at:at+len(raw)]==raw,'Candidate bytes changed')
        needle=struct.pack('<I',at+0x08000000); hits=[]; cursor=0
        while (cursor:=original.find(needle,cursor))>=0:
            hits.append(hex(cursor));cursor+=1
        entries.append({'id':e.get('master_id',e['id']),'offset':hex(at),'end_exclusive':hex(at+len(raw)),
                        'source_hex':raw.hex(),'exact_rom_pointer_occurrences':hits,'status':'unresolved_reader'})
    check(len(entries)==17,'Gameplay review selection differs')
    variants=[]
    for variant,data in (('original',original),('english',current)):
        cases={'variant':variant,'rom_sha256':digest(data),'landing':[],'dungeon_names':[],
               'footers':[],'frontend_confirmations':[],'status_prefixes':[]}
        with Session(data,OUT/'native'/variant) as s:
            c=s.core
            def restore():check(c.load_raw_state(items.STATE.read_bytes()),'Native fixture restore failed')
            t=ui.InterfaceTrace(c)
            try:
                for f9 in (0,1):
                    for f8 in (0,1):
                        restore();c.memory.u8[0x020060F8]=f8;c.memory.u8[0x020060F9]=f9
                        before=bytes(c.memory[0x020060F0:0x02006102]);t.phase=f'landing-{f8}-{f9}'
                        r=ui.native_step(s,t,0x080190A0,[])['return_r0']
                        literal=0x190B4 if not f9 else 0x190C8 if f8 else 0x190D4
                        check(r==struct.unpack_from('<I',data,literal)[0],'Landing selection differs')
                        check(before==bytes(c.memory[0x020060F0:0x02006102]),'Landing reader wrote flags or neighbours')
                        cases['landing'].append({'flag_f8':f8,'flag_f9':f9,'literal':hex(literal),'source':hex(r),
                                                 'output_hex':old.cstring(c,r).hex(),'flags_and_neighbours_unchanged':True})
                for row in range(64):
                    restore();c.memory.u32[0x02004F8C]=row//32;t.phase=f'dungeon-{row}'
                    r=ui.native_step(s,t,0x0805F33C,[row%32])['return_r0']
                    expected=struct.unpack_from('<I',data,0x1B3F60+row*4)[0]
                    check(r==expected and r!=0x081B3F2D,'Dungeon selection differs')
                    cases['dungeon_names'].append({'row':row,'word':hex(0x1B3F60+row*4),'source':hex(r)})
                for item in range(370):
                    restore();install_item(c,items.RECORD,item);system.guard(c,old.DEST,1024)
                    before=bytes(c.memory[items.RECORD:items.RECORD+24]);t.phase=f'footer-{item}'
                    ui.native_step(s,t,0x0806E1C0,[old.DEST,items.RECORD])
                    system.guards(c,old.DEST,1024);raw=old.cstring(c,old.DEST,1024)
                    check(bytes(c.memory[items.RECORD:items.RECORD+24])==before,'Footer modified item')
                    weights=[bytes.fromhex(e['source_hex'])[:-1] for e in catalog['entries']
                             if int(e['offset'],0) in TARGETS[1:7]]
                    check(all(w not in raw for w in weights),'Unowned weight appeared in footer')
                    cases['footers'].append({'item':item,'type':original[0xE07F4+item*28],
                                            'output_hex':raw.hex(),'guards_and_record_intact':True})
                    if item%100==99:print(variant,item+1,'native footers',flush=True)
                for choice,stop,literal in ((0,0x08085BC4,0x85BD8),(1,0x08085BE2,0x85BF4),(2,0x08085BFE,0x85C14)):
                    restore();r=queue.select_slice(c,0x08085B88,stop,{'r0':choice,'r5':0},0)
                    check(int(r['source'],0)==struct.unpack_from('<I',data,literal)[0],'Frontend confirmation differs')
                    cases['frontend_confirmations'].append({'choice':choice,'stop_before_call':hex(stop),'literal':hex(literal),**r})
                for flags in (0,0x100000,0x2000,0x102000,0x4000000,0x4100000):
                    restore();install_item(c,items.RECORD,1)
                    c.memory.u32[items.RECORD]|=flags;c.memory.u16[items.OPTIONS]=1
                    old.write_bytes(c,0x020007FC,data[0xCB0684:0xCB06BC]);system.guard(c,old.DEST,100)
                    before=bytes(c.memory[items.RECORD:items.RECORD+24]);t.phase=f'status-{flags:x}'
                    ui.native_step(s,t,0x08080A5C,[items.RECORD,old.DEST,items.OPTIONS,0,0])
                    raw=old.cstring(c,old.DEST,100);system.guards(c,old.DEST,100)
                    check(bytes(c.memory[items.RECORD:items.RECORD+24])==before and c.memory.u16[items.OPTIONS]==1,'Status formatter modified inputs')
                    check(b'\xf8\xa0' not in raw and b'\x81\x9a' not in raw,'Prose star unexpectedly selected')
                    prefix=0x8750+bool(flags&0x100000)+2*bool(flags&0x4002000)
                    check(raw.startswith(prefix.to_bytes(2,'big')),'Status prefix selection differs')
                    cases['status_prefixes'].append({'extra_flags':hex(flags),'output_hex':raw.hex(),'guards_and_inputs_intact':True})
                check(not t.errors,'Native reader trace failed')
            finally:t.close()
        variants.append(cases)
        print(variant,'bounded gameplay readers passed',flush=True)
    report={'status':'bounded_gameplay_readers_verified','source_sha256':digest(original),
            'verified_rom':str(BASELINE.relative_to(ROOT)),'verified_rom_sha256':digest(current),
            'harness_sha256':digest(Path(__file__).read_bytes()),'fixture_sha256':digest(items.STATE.read_bytes()),
            'catalog_sha256':digest((ROOT/'translations/unowned-text-review.json').read_bytes()),
            'helpers':{Path(m.__file__).name:digest(Path(m.__file__).read_bytes()) for m in (ui,queue,old,system,items)},
            'listings':{str(p.relative_to(ROOT)):digest(p.read_bytes()) for p in (OUT/'research').glob('*.txt')},
            'entries':entries,'variants':variants,
            'scope':'Paired controlled native readers: four landing-flag combinations, all 64 dungeon-name rows, all 370 zero-enhancement/no-synthesis item footers, three frontend confirmation pointer selections stopped before consequences, six equipment/status flag combinations. No candidate insertion, no full-program non-use proof, no natural reachability or plating-effect interpretation. Exact pointer search excludes computed/RAM/mirrored addresses.'}
    atomic_write(OUT/'native-verification.json',(json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode())


if __name__=='__main__':run()
