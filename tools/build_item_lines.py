"""Native item-aware combat joins and narrowly scoped world acquisition joining."""
import argparse
from pathlib import Path
import struct
import subprocess
import tempfile
from tools import build_companion_combat as previous
from tools.build_first_label import ROOT, ORIGINAL_ROM, digest
from tools.rom_build import AppendAllocator, RomBuild
from tools.translation_pipeline import atomic_write, check, load_json
from tools.prose_review import save

OWNER='item-lines'
OUTPUT=ROOT/'build/item-lines'
ROM=OUTPUT/'torneko3-item-lines-english.gba'
BASELINE=previous.ROM
PLAN=OUTPUT/'allocation-plan.json'
ASM=ROOT/'tools/item_lines.asm'


def prepare():
    original=ORIGINAL_ROM.read_bytes();baseline=BASELINE.read_bytes()
    prior=load_json(BASELINE.parent/'english-build.json')
    check(digest(baseline)==prior['rom_sha256'],'Baseline differs')
    allocations={a['id']:a for a in prior['ledger']['allocations']}
    allocator=AppendAllocator(len(original)+prior['ledger']['appended_used_with_padding'])
    at=(allocator.cursor+3)&~3
    constants=dict(CODE_ADDRESS=at+0x08000000,
        WIDTH_TABLE=allocations['rendering-fixes.font-zero-widths']['offset']+0x08000000,
        PREVIOUS_CODE=allocations['companion-combat.combat']['offset']+0x08000001,
        RECORD_TABLE=allocations['combat-lines.sources']['offset']+0x08000000,
        RECORD_COUNT=len(load_json(ROOT/'build/combat-lines/allocation-plan.json')['records']),
        ACQUISITION_SOURCE=struct.unpack_from('<I',baseline,0x62E80)[0])
    check(constants['ACQUISITION_SOURCE']==struct.unpack_from('<I',baseline,0x62F34)[0],'Acquisition sources differ')
    with tempfile.TemporaryDirectory(prefix=OWNER) as folder:
        args=[str(ROOT/'.tools/bin/armips'),str(ASM),'-sym2','symbols.txt']
        for k,v in constants.items():args+=['-equ',k,hex(v)]
        result=subprocess.run(args,cwd=folder,capture_output=True,text=True)
        check(result.returncode==0,result.stdout+result.stderr)
        raw=(Path(folder)/'item-lines.bin').read_bytes()
        symbols=(Path(folder)/'symbols.txt').read_text()
        world=int(next(line.split()[0] for line in symbols.splitlines() if line.lower().endswith(' worldhook')),16)
    check(allocator.allocate(OWNER+'.code',raw,4)==at,'Code moved');allocator.allocations[-1]['owner']=OWNER
    old=next(p for p in prior['ledger']['patches'] if p['id']=='companion-combat.formatter-hook')
    save(PLAN,dict(source_sha256=digest(original),previous_sha256=digest(baseline),
        builder_sha256=digest(Path(__file__).read_bytes()),asm_sha256=digest(ASM.read_bytes()),
        start=allocator.start,end_exclusive=allocator.cursor,allocations=allocator.allocations,
        resources=[dict(id=OWNER+'.code',offset=at,raw_hex=raw.hex())],constants=constants,world_hook=world,
        previous_patch=old,replacement_hex=(bytes.fromhex('9c46014b1847c046')+struct.pack('<I',at+0x08000001)).hex(),
        world_before_hex=original[0x62294:0x6229C].hex(),
        world_after_hex=(bytes.fromhex('004b1847')+struct.pack('<I',world|1)).hex(),new_ram_reservations=[],save_changes=[]))
    print(f'Prepared [{allocator.start:08X},{allocator.cursor:08X}), world hook {world:08X}',flush=True)


def build_rom(original,*,build=None):
    plan=load_json(PLAN)
    check(digest(original)==plan['source_sha256'],'Source differs')
    check(digest(Path(__file__).read_bytes())==plan['builder_sha256'],'Builder changed')
    check(digest(ASM.read_bytes())==plan['asm_sha256'],'Assembler changed')
    check(f'`[{plan["start"]:08X},{plan["end_exclusive"]:08X})`' in (ROOT/'docs/MEMORY_MAP.md').read_text(),'Document allocation first')
    b=RomBuild(original) if build is None else build
    baseline,prior=previous.build_rom(original,build=b)
    check(baseline==BASELINE.read_bytes() and digest(baseline)==plan['previous_sha256'],'Baseline changed')
    check(b.allocator.cursor==plan['start'],'Allocator changed')
    for r in plan['resources']:
        check(b.allocate(r['id'],bytes.fromhex(r['raw_hex']),OWNER,alignment=4)==r['offset'],'Allocation moved')
    old=plan['previous_patch']
    check(next(p for p in b.patches if p['id']==old['id'])==old,'Previous owner differs')
    b.supersede_patch(OWNER+'.formatter-hook',old['id'],old['owner'],bytes.fromhex(old['after']),bytes.fromhex(plan['replacement_hex']),OWNER,
        'Measure native item icons and colour controls in previously approved spans')
    b.patch(OWNER+'.world-hook',0x62294,bytes.fromhex(plan['world_before_hex']),bytes.fromhex(plan['world_after_hex']),OWNER,
        'Only acquisition caller 08062D60 with owned obtained template; replay original prologue for every call')
    data,ledger=b.finish()
    check(ledger['allocations']==prior['ledger']['allocations']+plan['allocations'],'Earlier allocations changed')
    check(ledger['memory_reservations']==prior['ledger']['memory_reservations'],'RAM changed')
    return data,dict(source_rom=str(ORIGINAL_ROM.relative_to(ROOT)),source_sha256=digest(original),output_rom=str(ROM.relative_to(ROOT)),
        rom_sha256=digest(data),previous_rom_sha256=digest(baseline),allocation_plan_sha256=digest(PLAN.read_bytes()),ledger=ledger)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--prepare',action='store_true')
    if p.parse_args().prepare:prepare()
    else:
        data,report=build_rom(ORIGINAL_ROM.read_bytes());atomic_write(ROM,data);save(OUTPUT/'english-build.json',report)
        print('Built',report['rom_sha256'],flush=True)
