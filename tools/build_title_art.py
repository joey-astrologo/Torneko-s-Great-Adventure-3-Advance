"""Insert the approved title through the original two-layer graphics loader."""
import argparse
from pathlib import Path
import struct
from tools import build_rendering_fixes as previous
from tools.build_first_label import ROOT, ORIGINAL_ROM, digest
from tools.pack_title_art import OUT, APPROVAL
from tools.extract_arrival_cards import save_json
from tools.rom_build import AppendAllocator, RomBuild
from tools.translation_pipeline import check, load_json, atomic_write

OWNER='title-art'
BASELINE=previous.ROM
ROM=OUT/'torneko3-title-english.gba'
RECORD=0xC77BDC
SOURCES=[(0xC5151C,0xC5251C),(0xC5251C,0xC5737C),(0xC5737C,0xC5773C)]


def prepare():
    original=ORIGINAL_ROM.read_bytes();baseline=BASELINE.read_bytes()
    packing=load_json(OUT/'packing.json');prior=load_json(BASELINE.parent/'english-build.json')
    check(digest(original)==packing['source_sha256'],'Wrong source')
    check(digest(BASELINE.read_bytes())==prior['rom_sha256'],'Wrong previous checkpoint')
    check(packing['approval_sha256']==digest(APPROVAL.read_bytes()),'Approved artwork changed')
    check(packing['packer_sha256']==digest((ROOT/'tools/pack_title_art.py').read_bytes()),'Repack changed compiler')
    for name,sha in packing['files'].items():check(digest((ROOT/name).read_bytes())==sha,'Packed asset changed')
    start=0x1000000+prior['ledger']['appended_used_with_padding'];allocator=AppendAllocator(start)
    offsets=[]
    for name in ('graphics','palette'):
        path=OUT/'packed'/f'{name}.bin';raw=path.read_bytes()
        offsets.append(allocator.allocate(OWNER+'.'+name,raw,4))
        allocator.allocations[-1].update(owner=OWNER,file=str(path.relative_to(ROOT)))
    before=original[RECORD:RECORD+12]
    check(before==struct.pack('<III',0x8C5151C,0x8C5737C,627),'Title record source differs')
    check(baseline[RECORD:RECORD+16]==original[RECORD:RECORD+16],'Previous title changed')
    after=struct.pack('<III',0x8000000+offsets[0],0x8000000+offsets[1],packing['tile_count'])
    check(packing['tile_count']<=1024,'Title exceeds BG tile capacity')
    plan={'source_rom':str(ORIGINAL_ROM.relative_to(ROOT)),'source_sha256':digest(original),
        'previous_rom':str(BASELINE.relative_to(ROOT)),'previous_sha256':digest(baseline),'output_rom':None,
        'approval_sha256':digest(APPROVAL.read_bytes()),'packing_sha256':digest((OUT/'packing.json').read_bytes()),
        'builder_sha256':digest(Path(__file__).read_bytes()),'start':start,'end_exclusive':allocator.cursor,
        'new_bytes_with_padding':allocator.cursor-start,'allocations':allocator.allocations,
        'patches':[{'id':OWNER+'.record','offset':RECORD,'before':before.hex(),'after':after.hex(),
                    'reason':'Select appended approved title maps, native 4bpp tiles and palette; retain original two-map mode and reader'}],
        'tile_count':packing['tile_count'],'source_ranges':SOURCES,
        'vram_title_tiles':[0x6008000,0x6008000+packing['tile_count']*32],
        'existing_bg_maps':[[0x6007000,0x6007800],[0x6007800,0x6008000]],
        'vram_context':'Existing title BG2/BG3 character base 2; two 16KiB blocks available before OBJ VRAM at 06010000. '
                       'Maps are below the character region. Reused by later native graphics loads; no permanent reservation.',
        'new_ram_reservations':[],'save_changes':[],'code_patches':[],
        'scope':'Dry shared allocation and original record patch plan, to document before insertion.'}
    save_json(OUT/'allocation-plan.json',plan)
    print(f"Planned [{start:08X},{allocator.cursor:08X}), {allocator.cursor-start:,} bytes; title VRAM end {plan['vram_title_tiles'][1]:08X}.")


def build_rom(original, *, build=None):
    plan=load_json(OUT/'allocation-plan.json');packing=load_json(OUT/'packing.json')
    check(plan['source_sha256']==digest(original),'Wrong Japanese source')
    check(plan['builder_sha256']==digest(Path(__file__).read_bytes()),'Regenerate changed plan')
    check(plan['packing_sha256']==digest((OUT/'packing.json').read_bytes()),'Packed report changed')
    check(packing['packer_sha256']==digest((ROOT/'tools/pack_title_art.py').read_bytes()),'Repack changed compiler')
    check(plan['approval_sha256']==packing['approval_sha256']==digest(APPROVAL.read_bytes()),'Approval differs')
    approved=load_json(APPROVAL)
    check(digest((ROOT/approved['raster']).read_bytes())==approved['raster_sha256'],'Approved raster changed')
    check(digest((ROOT/approved['candidate']).read_bytes())==approved['candidate_sha256'],'Approved candidate changed')
    marker=f"`[{plan['start']:08X},{plan['end_exclusive']:08X})`"
    check(marker in (ROOT/'docs/MEMORY_MAP.md').read_text(),'Document title allocation range before insertion')
    b=RomBuild(original) if build is None else build
    baseline,prior=previous.build_rom(original,build=b)
    check(baseline==BASELINE.read_bytes() and digest(baseline)==plan['previous_sha256'],'Previous cumulative build changed')
    check(b.allocator.cursor==plan['start'],'Title plan no longer follows shared allocator')
    for start,end in SOURCES:b.protect_source(f'{OWNER}.source-{start:08x}',start,end,OWNER)
    for row in plan['allocations']:
        raw=(ROOT/row['file']).read_bytes()
        check(digest(raw)==row['sha256'] and len(raw)==row['bytes'],'Prepared title asset changed')
        check(b.allocate(row['id'],raw,OWNER,alignment=4)==row['offset'],'Title allocation differs')
    for p in plan['patches']:b.patch(p['id'],p['offset'],bytes.fromhex(p['before']),bytes.fromhex(p['after']),OWNER,p['reason'])
    data,ledger=b.finish()
    check(ledger['memory_reservations']==prior['ledger']['memory_reservations'],'Unexpected RAM reservation')
    return data,{'source_rom':str(ORIGINAL_ROM.relative_to(ROOT)),'source_sha256':digest(original),
        'output_rom':str(ROM.relative_to(ROOT)),'rom_sha256':digest(data),'previous_rom_sha256':digest(baseline),
        'allocation_plan_sha256':digest((OUT/'allocation-plan.json').read_bytes()),
        'approval_sha256':digest(APPROVAL.read_bytes()),'packing_sha256':digest((OUT/'packing.json').read_bytes()),
        'tile_count':plan['tile_count'],'new_bytes_with_padding':plan['new_bytes_with_padding'],'ledger':ledger}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--prepare',action='store_true')
    if p.parse_args().prepare:prepare()
    else:
        data,report=build_rom(ORIGINAL_ROM.read_bytes());atomic_write(ROM,data);save_json(OUT/'english-build.json',report)
        print('Built',report['rom_sha256'],flush=True)
