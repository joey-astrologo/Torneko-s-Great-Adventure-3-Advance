"""Compose control-aware companion combat joiners without moving existing text."""
import argparse
from pathlib import Path
import struct
import subprocess
import tempfile
from tools import build_medal_trade as previous
from tools.build_first_label import ROOT, ORIGINAL_ROM, digest
from tools.rom_build import AppendAllocator, RomBuild
from tools.translation_pipeline import atomic_write, check, load_json
from tools.prose_review import save

OWNER='companion-combat'
OUTPUT=ROOT/'build/companion-combat'
ROM=OUTPUT/'torneko3-companion-combat-english.gba'
BASELINE=previous.ROM
PLAN=OUTPUT/'allocation-plan.json'
ASMS=(ROOT/'tools/companion_damage.asm',ROOT/'tools/companion_combat.asm')


def prepare():
    original=ORIGINAL_ROM.read_bytes(); baseline=BASELINE.read_bytes()
    prior=load_json(BASELINE.parent/'english-build.json')
    check(digest(baseline)==prior['rom_sha256'],'Baseline differs')
    damage=load_json(ROOT/'build/damage-lines/allocation-plan.json')
    combat=load_json(ROOT/'build/combat-lines/allocation-plan.json')
    allocations={a['id']:a for a in prior['ledger']['allocations']}
    allocator=AppendAllocator(len(original)+prior['ledger']['appended_used_with_padding'])
    resources=[]
    constants={'WIDTH_TABLE':allocations['rendering-fixes.font-zero-widths']['offset']+0x08000000}
    for i,m in enumerate(damage['messages']):
        constants[f'MESSAGE_{i}']=m['address'];constants[f'LINE_{i}']=m['line_address']
    for asm,name in zip(ASMS,('damage','combat')):
        at=(allocator.cursor+3)&~3
        constants['CODE_ADDRESS']=at+0x08000000
        if name=='combat':
            constants.update(PREVIOUS_CODE=resources[0]['offset']+0x08000001,
                RECORD_TABLE=allocations['combat-lines.sources']['offset']+0x08000000,RECORD_COUNT=len(combat['records']))
        with tempfile.TemporaryDirectory(prefix=OWNER) as folder:
            args=[str(ROOT/'.tools/bin/armips'),str(asm)]
            for k,v in constants.items():args+=['-equ',k,hex(v)]
            result=subprocess.run(args,cwd=folder,capture_output=True,text=True)
            check(result.returncode==0,result.stdout+result.stderr)
            raw=(Path(folder)/f'companion-{name}.bin').read_bytes()
        check(allocator.allocate(OWNER+'.'+name,raw,4)==at,'Code moved')
        allocator.allocations[-1]['owner']=OWNER
        resources.append(dict(id=OWNER+'.'+name,offset=at,raw_hex=raw.hex()))
    old=next(p for p in prior['ledger']['patches'] if p['id']=='combat-lines.formatter-hook')
    save(PLAN,dict(source_sha256=digest(original),previous_sha256=digest(baseline),
        builder_sha256=digest(Path(__file__).read_bytes()),asm_hashes={str(p.relative_to(ROOT)):digest(p.read_bytes()) for p in ASMS},
        start=allocator.start,end_exclusive=allocator.cursor,allocations=allocator.allocations,resources=resources,
        previous_patch=old,replacement_hex=(bytes.fromhex('9c46014b1847c046')+struct.pack('<I',resources[-1]['offset']+0x08000001)).hex(),
        new_ram_reservations=[],save_changes=[]))
    print(f'Prepared [{allocator.start:08X},{allocator.cursor:08X})',flush=True)


def build_rom(original,*,build=None):
    plan=load_json(PLAN)
    check(digest(original)==plan['source_sha256'],'Source differs')
    check(digest(Path(__file__).read_bytes())==plan['builder_sha256'],'Builder changed')
    for path,h in plan['asm_hashes'].items():check(digest((ROOT/path).read_bytes())==h,'Assembler source changed')
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
        'Preserve native ally colour controls while measuring approved combat joins')
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
