"""Centre the accepted arrival lettering without changing its raster assets."""
import argparse
from pathlib import Path
import struct
import subprocess
import tempfile

from tools import build_prose_review as previous
from tools import build_arrival_credits as art
from tools.build_first_label import ROOT, ORIGINAL_ROM, digest
from tools.rom_build import AppendAllocator, RomBuild
from tools.translation_pipeline import atomic_write, check, load_json
from tools.prose_review import save

OWNER='arrival-layout'
OUTPUT=ROOT/'build/arrival-layout'
BASELINE=previous.ROM
ROM=OUTPUT/'torneko3-arrival-layout-english.gba'
PLAN=OUTPUT/'allocation-plan.json'
ASM=ROOT/'tools/arrival_layout.asm'


def prepare():
    baseline=BASELINE.read_bytes();prior=load_json(BASELINE.parent/'english-build.json')
    original=ORIGINAL_ROM.read_bytes();assets=load_json(art.OUT/'allocation-plan.json')
    check(digest(baseline)==prior['rom_sha256'],'Baseline differs')
    old=next(p for p in prior['ledger']['patches'] if p['id']=='arrival-credits.map')
    check(old['offset']==0x5298 and old['owner']=='arrival-credits' and
          baseline[0x5298:0x52A0]==bytes.fromhex(old['after']), 'Existing map hook changed')
    allocator=AppendAllocator(len(original)+prior['ledger']['appended_used_with_padding'])
    at=(allocator.cursor+3)&~3
    with tempfile.TemporaryDirectory(prefix='arrival-layout-') as directory:
        result=subprocess.run([str(ROOT/'.tools/bin/armips'),str(ASM),
            '-equ','CODE_ADDRESS',hex(at+0x08000000),
            '-equ','FLOOR_RECORDS',hex(assets['records_at']+0x08000000)],
            cwd=directory,capture_output=True,text=True)
        check(result.returncode==0,result.stdout+result.stderr)
        code=(Path(directory)/'arrival-layout.bin').read_bytes()
    check(allocator.allocate(OWNER+'.renderer',code,4)==at,'Code alignment changed')
    allocator.allocations[-1]['owner']=OWNER
    new=(bytes.fromhex('004b1847')+struct.pack('<I',at+0x08000001)).hex()
    plan={'source_rom':str(ORIGINAL_ROM.relative_to(ROOT)),'source_sha256':digest(original),
        'previous_rom':str(BASELINE.relative_to(ROOT)),'previous_sha256':digest(baseline),
        'output_rom':str(ROM.relative_to(ROOT)),'builder_sha256':digest(Path(__file__).read_bytes()),
        'asm_sha256':digest(ASM.read_bytes()),'art_plan_sha256':digest((art.OUT/'allocation-plan.json').read_bytes()),
        'start':allocator.start,'end_exclusive':allocator.cursor,'allocations':allocator.allocations,
        'code_hex':code.hex(),'previous_patch':old,'replacement_hex':new,
        'title_shift_pixels':32,'arena_title_shift_pixels':48,'floor_shift_pixels':-16,
        'new_ram_reservations':[],'save_changes':[],
        'scope':'Existing title tilemap cells move down; existing floor cells move up. No new artwork, font or text.'}
    save(PLAN,plan)
    print(f'Planned [{allocator.start:08X},{allocator.cursor:08X}), {allocator.cursor-allocator.start} bytes; one exact 8-byte map-hook supersession.',flush=True)


def build_rom(original,*,build=None):
    plan=load_json(PLAN)
    for p,k in ((Path(__file__),'builder_sha256'),(ASM,'asm_sha256'),(art.OUT/'allocation-plan.json','art_plan_sha256')):
        check(digest(p.read_bytes())==plan[k],'Regenerate changed arrival layout plan')
    check(digest(original)==plan['source_sha256'],'Japanese source differs')
    marker=f'`[{plan["start"]:08X},{plan["end_exclusive"]:08X})`'
    check(marker in (ROOT/'docs/MEMORY_MAP.md').read_text(),'Document layout ranges before insertion')
    b=RomBuild(original) if build is None else build
    baseline,prior=previous.build_rom(original,build=b)
    check(baseline==BASELINE.read_bytes() and digest(baseline)==plan['previous_sha256'],'Prior English differs')
    check(b.allocator.cursor==plan['start'],'Allocator start differs')
    at=b.allocate(OWNER+'.renderer',bytes.fromhex(plan['code_hex']),OWNER,alignment=4)
    check(at==plan['allocations'][0]['offset'],'Code position differs')
    old=plan['previous_patch']
    check(next(p for p in b.patches if p['id']==old['id'])==old,'Previous map ownership differs')
    b.supersede_patch(OWNER+'.map',old['id'],old['owner'],bytes.fromhex(old['after']),
                     bytes.fromhex(plan['replacement_hex']),OWNER,'Centre the existing title/floor artwork as a compact group')
    data,ledger=b.finish()
    check(ledger['allocations']==prior['ledger']['allocations']+plan['allocations'],'Earlier allocations changed')
    check(ledger['memory_reservations']==prior['ledger']['memory_reservations'],'RAM ownership changed')
    return data,{'source_rom':plan['source_rom'],'source_sha256':digest(original),
        'output_rom':str(ROM.relative_to(ROOT)),'rom_sha256':digest(data),'previous_rom_sha256':digest(baseline),
        'allocation_plan_sha256':digest(PLAN.read_bytes()),'title_assets':36,'selectors':64,
        'new_bytes_with_padding':plan['end_exclusive']-plan['start'],'ledger':ledger}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--prepare',action='store_true')
    if p.parse_args().prepare:prepare()
    else:
        data,report=build_rom(ORIGINAL_ROM.read_bytes())
        atomic_write(ROM,data);save(OUTPUT/'english-build.json',report)
        print('Built',report['rom_sha256'],flush=True)
