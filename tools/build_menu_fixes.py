"""Keep widened menus consistent across cached submenus and clipping tables."""
import argparse
from pathlib import Path
import struct
from tools import build_damage_lines as previous
from tools.build_first_label import ROOT, ORIGINAL_ROM, digest
from tools.rom_build import AppendAllocator, RomBuild
from tools.translation_pipeline import atomic_write, check, load_json
from tools.prose_review import save

OWNER='menu-fixes'
OUTPUT=ROOT/'build/menu-fixes'
BASELINE=previous.ROM
ROM=OUTPUT/'torneko3-menu-fixes-english.gba'
PLAN=OUTPUT/'allocation-plan.json'
PROFILES=(1,4,5,6,7,8,9,10)


def prepare():
    original=ORIGINAL_ROM.read_bytes();baseline=BASELINE.read_bytes()
    prior=load_json(BASELINE.parent/'english-build.json');check(digest(baseline)==prior['rom_sha256'],'Baseline differs')
    allocator=AppendAllocator(len(original)+prior['ledger']['appended_used_with_padding'])
    resources=[];patches=[]
    def resource(name,raw):
        at=allocator.allocate(OWNER+'.'+name,raw,4);allocator.allocations[-1]['owner']=OWNER
        resources.append(dict(id=OWNER+'.'+name,offset=at,raw_hex=raw.hex()));return at
    def patch(name,at,before,after,reason):
        check(baseline[at:at+len(before)]==before,'Source mismatch '+name)
        old=next((p for p in prior['ledger']['patches'] if p['offset']==at),None)
        if old:check(bytes.fromhex(old['after'])==before,'Wrong whole-patch supersession')
        else:check(original[at:at+len(before)]==before,'Unowned previous change')
        patches.append(dict(id=OWNER+'.'+name,offset=at,before=before.hex(),after=after.hex(),previous_patch=old,reason=reason))
    for n in range(5,11):
        at=0xCA2874+n*64
        patch(f'profile-{n}-command',at+4,struct.pack('<H',9),struct.pack('<H',10),'Preserve English command bitmap stride on submenu transition')
        if n%2:
            patch(f'profile-{n}-location',at+16,struct.pack('<3H',13,3,15),struct.pack('<3H',14,3,14),'Preserve English location position, stride and following buffer offsets')
    for n in PROFILES:
        start=0xCA2DB4+n*322
        for y in range(17,55):
            at=start+y*2;word=struct.unpack_from('<H',baseline,at)[0]
            if (word&255) not in (94,95):continue
            check(word>>8 in (9,10),'Unexpected clipping interval')
            patch(f'clip-{n}-{y}',at,struct.pack('<H',word),struct.pack('<H',word+8),'Extend command-only scanline shade to widened border; preserve corner inset')
    word=0x75750;source=struct.unpack_from('<I',baseline,word)[0]-0x08000000
    desc=bytearray(baseline[source:source+64]);check(struct.unpack_from('<3H',desc,16)==(23,14,6),'Warehouse descriptor changed')
    check(struct.unpack_from('<3H',desc,32)==(23,3,6),'Warehouse action changed')
    struct.pack_into('<H',desc,20,5)
    dest=resource('warehouse-descriptor',desc)
    patch('warehouse-pointer',word,baseline[word:word+4],struct.pack('<I',dest+0x08000000),'Preserve cached counter width5; retain action width6')
    for ident,word,expected,text in [('ground',0x201FC,b"There's nothing at your feet.\0",b'Nothing at your feet.\0'),('casino',0x77AD8,b'Exchange\0',b'Trade\0')]:
        source_at=struct.unpack_from('<I',baseline,word)[0]-0x08000000
        check(baseline[source_at:source_at+len(expected)]==expected,'Display source differs')
        dest=resource(ident,text)
        patch(ident+'-pointer',word,baseline[word:word+4],struct.pack('<I',dest+0x08000000),'Measured compact display wording')
    save(PLAN,dict(source_rom=str(ORIGINAL_ROM.relative_to(ROOT)),source_sha256=digest(original),previous_sha256=digest(baseline),
        builder_sha256=digest(Path(__file__).read_bytes()),start=allocator.start,end_exclusive=allocator.cursor,
        allocations=allocator.allocations,resources=resources,patches=patches,warehouse_source=[source,source+64],
        new_ram_reservations=[],save_changes=[]))
    print(f'Prepared [{allocator.start:08X},{allocator.cursor:08X}), {len(patches)} patches',flush=True)


def build_rom(original,*,build=None):
    plan=load_json(PLAN)
    check(digest(original)==plan['source_sha256'] and digest(Path(__file__).read_bytes())==plan['builder_sha256'],'Regenerate changed menu plan')
    check(f'`[{plan["start"]:08X},{plan["end_exclusive"]:08X})`' in (ROOT/'docs/MEMORY_MAP.md').read_text(),'Document allocations first')
    b=RomBuild(original) if build is None else build
    baseline,prior=previous.build_rom(original,build=b)
    check(baseline==BASELINE.read_bytes() and digest(baseline)==plan['previous_sha256'],'Baseline changed')
    check(b.allocator.cursor==plan['start'],'Allocator changed')
    for r in plan['resources']:
        check(b.allocate(r['id'],bytes.fromhex(r['raw_hex']),OWNER)==r['offset'],'Resource moved')
    for p in plan['patches']:
        old=p['previous_patch']
        if old:
            check(next(q for q in b.patches if q['id']==old['id'])==old,'Previous patch owner changed')
            b.supersede_patch(p['id'],old['id'],old['owner'],bytes.fromhex(p['before']),bytes.fromhex(p['after']),OWNER,p['reason'])
        else:b.patch(p['id'],p['offset'],bytes.fromhex(p['before']),bytes.fromhex(p['after']),OWNER,p['reason'])
    data,ledger=b.finish()
    check(ledger['allocations']==prior['ledger']['allocations']+plan['allocations'],'Earlier allocations changed')
    check(ledger['memory_reservations']==prior['ledger']['memory_reservations'],'RAM changed')
    return data,dict(source_rom=plan['source_rom'],source_sha256=digest(original),output_rom=str(ROM.relative_to(ROOT)),rom_sha256=digest(data),
        previous_rom_sha256=digest(baseline),allocation_plan_sha256=digest(PLAN.read_bytes()),ledger=ledger)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--prepare',action='store_true')
    if p.parse_args().prepare:prepare()
    else:
        data,report=build_rom(ORIGINAL_ROM.read_bytes());atomic_write(ROM,data);save(OUTPUT/'english-build.json',report)
        print('Built',report['rom_sha256'],flush=True)
