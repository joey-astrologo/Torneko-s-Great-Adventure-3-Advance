"""Join ordinary received/outgoing damage lines after native substitution when they fit."""
import argparse
from pathlib import Path
import struct
import subprocess
import tempfile
from tools import build_arrival_layout as previous
from tools.build_first_label import ROOT, ORIGINAL_ROM, digest
from tools.rom_build import AppendAllocator, RomBuild
from tools.translation_pipeline import atomic_write, check, load_json
from tools.prose_review import save

OWNER='damage-lines'
OUTPUT=ROOT/'build/damage-lines'
ROM=OUTPUT/'torneko3-damage-lines-english.gba'
BASELINE=previous.ROM
PLAN=OUTPUT/'allocation-plan.json'
ASM=ROOT/'tools/damage_lines.asm'
IDS=('gameplay.001b4dac','tutorial.001b6d7d','tutorial.001b6d93','prose-review.tutorial.001b507e','gameplay.001b4d95')


def prepare():
    original=ORIGINAL_ROM.read_bytes();baseline=BASELINE.read_bytes()
    prior=load_json(BASELINE.parent/'english-build.json')
    check(digest(baseline)==prior['rom_sha256'],'Baseline differs')
    legacy=load_json(ROOT/'build/rendering-fixes/allocation-plan.json')
    sources=[dict(r) for r in legacy['messages']]
    allocations={a['id']:a for a in prior['ledger']['allocations']}
    for ident in IDS:
        a=allocations[ident];address=a['offset']+0x08000000
        raw=baseline[a['offset']:a['offset']+a['bytes']]
        expected = b'Dealt $d0 damage to\n$m1.\0' if ident=='gameplay.001b4d95' else None
        check(raw==expected if expected else b'took' in raw and raw.endswith(b'damage.\0') and raw.count(b'\n')==1,'Damage source changed')
        owners=[p for p in prior['ledger']['patches'] if p['after']==struct.pack('<I',address).hex()]
        check(owners,'No pointer ownership for damage source')
        sources.append(dict(id=ident,address=address,line_address=address,raw_hex=raw.hex(),pointer_patches=owners))
        if raw.startswith(b'!'):
            sources.append(dict(id=ident+'.continuation',address=address+1,line_address=address+1,raw_hex=raw[1:].hex()))
    check(len(sources)==10,'Allowlist size changed')
    for r in sources:
        off=r['address']-0x08000000
        check(baseline[off:off+len(bytes.fromhex(r['raw_hex']))].hex()==r['raw_hex'],'Allowlisted source moved')
    widths=allocations['rendering-fixes.font-zero-widths']
    allocator=AppendAllocator(len(original)+prior['ledger']['appended_used_with_padding'])
    at=(allocator.cursor+3)&~3
    with tempfile.TemporaryDirectory(prefix='damage-lines-') as directory:
        command=[str(ROOT/'.tools/bin/armips'),str(ASM),'-equ','CODE_ADDRESS',hex(at+0x08000000),
                 '-equ','WIDTH_TABLE',hex(widths['offset']+0x08000000)]
        for i,r in enumerate(sources):command+=['-equ',f'MESSAGE_{i}',hex(r['address']),'-equ',f'LINE_{i}',hex(r['line_address'])]
        result=subprocess.run(command,cwd=directory,capture_output=True,text=True)
        check(result.returncode==0,result.stdout+result.stderr)
        code=(Path(directory)/'damage-lines.bin').read_bytes()
    check(allocator.allocate(OWNER+'.formatter',code,4)==at,'Alignment differs')
    allocator.allocations[-1]['owner']=OWNER
    old=next(p for p in prior['ledger']['patches'] if p['id']=='rendering-fixes.numeric-line')
    check(old['offset']==0x7D8CC and len(bytes.fromhex(old['after']))==12,'Formatter hook differs')
    save(PLAN,dict(source_rom=str(ORIGINAL_ROM.relative_to(ROOT)),source_sha256=digest(original),
        previous_sha256=digest(baseline),output_rom=str(ROM.relative_to(ROOT)),
        builder_sha256=digest(Path(__file__).read_bytes()),asm_sha256=digest(ASM.read_bytes()),
        start=allocator.start,end_exclusive=allocator.cursor,allocations=allocator.allocations,
        code_hex=code.hex(),previous_patch=old,replacement_hex=(bytes.fromhex('9c46014b1847c046')+struct.pack('<I',at+0x08000001)).hex(),
        messages=sources,width_table=widths,new_ram_reservations=[],save_changes=[],formatter_extra_stack_bytes=112))
    print(f'Prepared [{allocator.start:08X},{allocator.cursor:08X})',flush=True)


def build_rom(original,*,build=None):
    plan=load_json(PLAN)
    check(digest(original)==plan['source_sha256'],'Source differs')
    for p,k in ((Path(__file__),'builder_sha256'),(ASM,'asm_sha256')):
        check(digest(p.read_bytes())==plan[k],'Regenerate damage plan')
    check(f'`[{plan["start"]:08X},{plan["end_exclusive"]:08X})`' in (ROOT/'docs/MEMORY_MAP.md').read_text(),'Document ranges first')
    b=RomBuild(original) if build is None else build
    baseline,prior=previous.build_rom(original,build=b)
    check(baseline==BASELINE.read_bytes() and digest(baseline)==plan['previous_sha256'],'Prior build differs')
    check(b.allocator.cursor==plan['start'],'Allocator differs')
    at=b.allocate(OWNER+'.formatter',bytes.fromhex(plan['code_hex']),OWNER,alignment=4)
    check(at==plan['allocations'][0]['offset'],'Code moved')
    old=plan['previous_patch']
    check(next(p for p in b.patches if p['id']==old['id'])==old,'Previous ownership differs')
    b.supersede_patch(OWNER+'.formatter-hook',old['id'],old['owner'],bytes.fromhex(old['after']),
        bytes.fromhex(plan['replacement_hex']),OWNER,'Join measured ordinary received/outgoing damage lines; retain XP/level joining')
    data,ledger=b.finish()
    check(ledger['allocations']==prior['ledger']['allocations']+plan['allocations'],'Earlier allocations changed')
    check(ledger['memory_reservations']==prior['ledger']['memory_reservations'],'RAM changed')
    return data,dict(source_rom=plan['source_rom'],source_sha256=digest(original),output_rom=str(ROM.relative_to(ROOT)),
        rom_sha256=digest(data),previous_rom_sha256=digest(baseline),allocation_plan_sha256=digest(PLAN.read_bytes()),ledger=ledger)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--prepare',action='store_true')
    if p.parse_args().prepare:prepare()
    else:
        data,report=build_rom(ORIGINAL_ROM.read_bytes())
        atomic_write(ROM,data);save(OUTPUT/'english-build.json',report)
        print('Built',report['rom_sha256'],flush=True)
