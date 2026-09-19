"""Approved conditional combat sentence joining, composed after menu fixes."""
import argparse
from pathlib import Path
import struct
import subprocess
import tempfile
from tools import build_menu_fixes as previous
from tools.build_first_label import ROOT, ORIGINAL_ROM, digest
from tools.rom_build import AppendAllocator, RomBuild
from tools.translation_pipeline import atomic_write, check, load_json
from tools.prose_review import save

OWNER='combat-lines'
OUTPUT=ROOT/'build/combat-lines'
ROM=OUTPUT/'torneko3-combat-lines-english.gba'
BASELINE=previous.ROM
PLAN=OUTPUT/'allocation-plan.json'
ASM=ROOT/'tools/combat_lines.asm'
AUDIT=ROOT/'build/combat-line-audit/audit.json'
SELECTION=ROOT/'translations/combat-line-joins.json'


def prepare():
    original=ORIGINAL_ROM.read_bytes();baseline=BASELINE.read_bytes()
    prior=load_json(BASELINE.parent/'english-build.json')
    check(digest(baseline)==prior['rom_sha256'],'Baseline differs')
    selection=load_json(SELECTION)
    check(selection['baseline_sha256']==digest(baseline),'Approved baseline differs')
    records=[]
    for m in selection['messages']:
        address=m['address'];raw=bytes.fromhex(m['raw_hex'])
        check(baseline[address-0x08000000:address-0x08000000+len(raw)]==raw,'Approved source changed')
        span=m['span'].encode();start=raw.index(span);end=start+len(span)
        check(raw.count(span)==1 and raw[end] in (0,10),'Ambiguous span/end')
        check(start==0 or raw[start-1] in (10,33),'Span must begin at line start/continuation')
        breaks=span.count(b'\n');check(breaks in (1,2),'Unexpected span size')
        keys={address:(raw[:start].count(b'\n'),0x100 if raw.startswith(b'!') else 0),
              address+start:(0,0)}
        if raw.startswith(b'!'):keys[address+1]=(0,0)
        # Preserve marker flag when the full source and span begin together.
        if start==0:keys[address]=(0,0)
        for key,(skip,flag) in keys.items():
            records.append(dict(id=m['id'],key=key,end=address+end+(raw[end]==10),skip=skip,flags=breaks|flag))
    records.sort(key=lambda r:r['key'])
    check(len({r['key'] for r in records})==len(records),'Duplicate join keys')
    table=b''.join(struct.pack('<4I',r['key'],r['end'],r['skip'],r['flags']) for r in records)
    allocator=AppendAllocator(len(original)+prior['ledger']['appended_used_with_padding'])
    resources=[]
    def resource(ident,raw):
        at=allocator.allocate(OWNER+'.'+ident,raw,4);allocator.allocations[-1]['owner']=OWNER
        resources.append(dict(id=OWNER+'.'+ident,offset=at,raw_hex=raw.hex()));return at
    table_at=resource('sources',table)
    allocations={a['id']:a for a in prior['ledger']['allocations']}
    code_at=(allocator.cursor+3)&~3
    old=next(p for p in prior['ledger']['patches'] if p['id']=='damage-lines.formatter-hook')
    with tempfile.TemporaryDirectory(prefix='combat-lines-') as d:
        args=[str(ROOT/'.tools/bin/armips'),str(ASM),'-equ','CODE_ADDRESS',hex(code_at+0x08000000),
              '-equ','PREVIOUS_CODE',hex(allocations['damage-lines.formatter']['offset']+0x08000001),
              '-equ','RECORD_TABLE',hex(table_at+0x08000000),'-equ','RECORD_COUNT',str(len(records)),
              '-equ','WIDTH_TABLE',hex(allocations['rendering-fixes.font-zero-widths']['offset']+0x08000000)]
        result=subprocess.run(args,cwd=d,capture_output=True,text=True)
        check(result.returncode==0,result.stdout+result.stderr)
        code=(Path(d)/'combat-lines.bin').read_bytes()
    check(resource('formatter',code)==code_at,'Code moved')
    save(PLAN,dict(source_rom=str(ORIGINAL_ROM.relative_to(ROOT)),source_sha256=digest(original),previous_sha256=digest(baseline),
        builder_sha256=digest(Path(__file__).read_bytes()),asm_sha256=digest(ASM.read_bytes()),selection_sha256=digest(SELECTION.read_bytes()),
        start=allocator.start,end_exclusive=allocator.cursor,allocations=allocator.allocations,resources=resources,records=records,
        previous_patch=old,replacement_hex=(bytes.fromhex('9c46014b1847c046')+struct.pack('<I',code_at+0x08000001)).hex(),
        new_ram_reservations=[],save_changes=[],wrapper_stack_bytes=128,join_helper_stack_bytes=32))
    print(f'Prepared [{allocator.start:08X},{allocator.cursor:08X}), {len(records)} source keys',flush=True)


def build_rom(original,*,build=None):
    plan=load_json(PLAN)
    check(digest(original)==plan['source_sha256'],'Source differs')
    for p,k in ((Path(__file__),'builder_sha256'),(ASM,'asm_sha256'),(SELECTION,'selection_sha256')):
        check(digest(p.read_bytes())==plan[k],'Regenerate combat plan')
    check(f'`[{plan["start"]:08X},{plan["end_exclusive"]:08X})`' in (ROOT/'docs/MEMORY_MAP.md').read_text(),'Document allocations first')
    b=RomBuild(original) if build is None else build
    baseline,prior=previous.build_rom(original,build=b)
    check(baseline==BASELINE.read_bytes() and digest(baseline)==plan['previous_sha256'],'Baseline changed')
    check(b.allocator.cursor==plan['start'],'Allocator changed')
    for r in plan['resources']:
        check(b.allocate(r['id'],bytes.fromhex(r['raw_hex']),OWNER)==r['offset'],'Resource moved')
    old=plan['previous_patch']
    check(next(p for p in b.patches if p['id']==old['id'])==old,'Previous hook owner changed')
    b.supersede_patch(OWNER+'.formatter-hook',old['id'],old['owner'],bytes.fromhex(old['after']),bytes.fromhex(plan['replacement_hex']),OWNER,
                     'Join approved sentence spans after bounded native substitution; retain damage/XP fallback')
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
