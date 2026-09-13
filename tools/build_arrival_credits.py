"""Pack approved arrival rasters and compose checked native hooks into English."""
import argparse
import json
from pathlib import Path
import struct
import subprocess
import tempfile

from PIL import Image

from tools import build_inventory_notice as previous
from tools.build_first_label import ROOT, ORIGINAL_ROM, digest
from tools.export_approved_arrivals import APPROVAL, OUT
from tools.extract_arrival_cards import collect, save_json, rgb
from tools.rom_build import AppendAllocator, RomBuild
from tools.translation_pipeline import check, load_json, atomic_write

OWNER = 'arrival-credits'
BASELINE = previous.OUTPUT/'torneko3-inventory-notice-english.gba'
ROM = OUT/'torneko3-arrival-credits-english.gba'
ASM = ROOT/'tools/arrival_credits.asm'
SOURCE_RANGES = [(0x3903D0,0x3C1550), (0x9B6FC,0x9B72C)]
HOOKS = [(0x5210,'28492b4ba0277f01'), (0x5298,'30781a2818d10120')]


def read_raster(row, colours):
    path = ROOT/row['file']
    check(digest(path.read_bytes()) == row['sha256'], 'Approved raster changed')
    im = Image.open(path).convert('RGB')
    pixels = [colours.index(tuple(c >> 3 for c in pixel)) for pixel in im.get_flattened_data()]
    return im.size, pixels


def pack_tiles(pixels, width, positions, base):
    tiles = [bytes(32)]; cells = []
    for x0,y0 in positions:
        block = bytes(pixels[(y0+y)*width+x0+x] | pixels[(y0+y)*width+x0+x+1] << 4
                      for y in range(8) for x in range(0,8,2))
        if block not in tiles:
            tiles.append(block)
        cells.append(0xE000 | (base+tiles.index(block)))
    check(len(tiles) <= 160, 'Artwork exceeds its native 160-tile slot')
    return b''.join(tiles), cells


def assemble(address, records):
    with tempfile.TemporaryDirectory(prefix='torneko-arrival-asm-') as directory:
        result = subprocess.run([str(ROOT/'.tools/bin/armips'),str(ASM),
            '-equ','CODE_ADDRESS',hex(address),'-equ','FLOOR_RECORDS',hex(records)],
            cwd=directory,capture_output=True,text=True)
        check(result.returncode == 0, result.stdout+result.stderr)
        return (Path(directory)/'arrival-credits.bin').read_bytes()


def prepare():
    """Dry allocation plan, written and documented before any insertion build."""
    original = ORIGINAL_ROM.read_bytes(); approved = load_json(APPROVAL)
    rasters = load_json(OUT/'rasters.json'); source = collect(original)
    check(approved['source_rom_sha256'] == digest(original) == rasters['source_sha256'], 'Source differs')
    check(rasters['approval_sha256'] == digest(APPROVAL.read_bytes()), 'Approval differs from rasters')
    check(len(rasters['titles']) == 36 and len(rasters['floors']) == 512, 'Incomplete raster export')
    prior = load_json(previous.OUTPUT/'english-build.json')
    check(digest(BASELINE.read_bytes()) == prior['rom_sha256'], 'Earlier build changed')
    start = 0x1000000+prior['ledger']['appended_used_with_padding']
    allocator = AppendAllocator(start)
    payloads = []

    def allocate(ident, data):
        at = allocator.allocate(OWNER+'.'+ident,data,4)
        path = OUT/'packed'/f'{ident}.bin'; atomic_write(path,data)
        allocator.allocations[-1].update(owner=OWNER,file=str(path.relative_to(ROOT)))
        payloads.append(data)
        return at

    colours = [tuple(c) for c in rasters['rgb555_colours']]
    check(colours[0] == (0,0,0) and len(colours) <= 16, 'Palette exceeds 4bpp without additional quantization')
    words = [0x80000000 | r*8 | g*8 << 8 | b*8 << 16 for r,g,b in colours]
    words += [0x80000000]*(16-len(words))
    palette_at = allocate('palette',struct.pack('<16I',*words))
    titles = []
    for row, approval, src in zip(rasters['titles'],approved['cards'],source['entries'],strict=True):
        check(row['id'] == approval['id'] == src['id'] and row['selectors'] == approval['selectors'] == src['selectors']
              and row['text'] == approval['text'], 'Card identity or approved wording changed')
        size, pixels = read_raster(row,colours)
        check(size == (240,160), 'Title dimensions changed')
        check(all(v == 0 or (8 <= i%240 < 240 and 8 <= i//240 < 80) for i,v in enumerate(pixels)), 'Title outside native copy')
        tiles,cells = pack_tiles(pixels,240,[(x*8,y*8) for y in range(1,10) for x in range(1,30)],0)
        tilemap = bytearray(0x800)
        for i,cell in enumerate(cells):
            struct.pack_into('<H',tilemap,((i//29)*32+i%29+1)*2,cell)
        at = allocate(row['id'],bytes(tilemap)+tiles)
        titles.append({**row,'offset':at,'end_exclusive':at+len(tilemap)+len(tiles),'tile_count':len(tiles)//32})
    pointers = [0]*64; counts = [0]*64
    for row in titles:
        for selector in row['selectors']:
            check(pointers[selector] == 0,'Duplicate card selector')
            pointers[selector] = 0x8000000+row['offset']; counts[selector] = row['tile_count']
    check(all(pointers) and all(counts),'Missing card selector')
    pointers_at = allocate('pointers',struct.pack('<64I',*pointers))
    counts_at = allocate('counts',struct.pack('<64h',*counts))
    floor_blob = bytearray(); floors = []
    for i,row in enumerate(rasters['floors']):
        check(row['number'] == i%256 and row['kind'] == ('F' if i<256 else 'puzzle'),'Floor table order changed')
        size,pixels = read_raster(row,colours)
        check(size == (240,32),'Floor dimensions changed')
        tiles,cells = pack_tiles(pixels,240,[(x*8,y*8) for y in range(4) for x in range(30)],160)
        map_offset = len(floor_blob)
        floor_blob.extend(struct.pack('<120H',*cells)); tile_offset = len(floor_blob); floor_blob.extend(tiles)
        floors.append({**row,'index':i,'map_relative':map_offset,'tiles_relative':tile_offset,'tile_count':len(tiles)//32})
    floor_at = allocate('floor-art',bytes(floor_blob))
    records = bytearray()
    for row in floors:
        row.update(map_offset=floor_at+row['map_relative'],tiles_offset=floor_at+row['tiles_relative'])
        records.extend(struct.pack('<III',0x8000000+row['tiles_offset'],0x8000000+row['map_offset'],row['tile_count']*8))
    records_at = allocate('floor-records',bytes(records))
    code_at = (allocator.cursor+3)&~3
    code = assemble(0x8000000+code_at,0x8000000+records_at)
    check(allocate('renderer',code) == code_at,'Code alignment changed')
    patches = []
    for name,at,expected,new in [('pointers',0x52A4,0x83C1450,pointers_at),
        ('counts',0x52B0,0x83C13D0,counts_at),('palette',0x52B8,0x83903D0,palette_at)]:
        patches.append(dict(id=OWNER+'.'+name,offset=at,before=struct.pack('<I',expected).hex(),
                            after=struct.pack('<I',0x8000000+new).hex(),reason='Select approved appended '+name))
    for i,(at,expected) in enumerate(HOOKS):
        patches.append(dict(id=OWNER+'.'+('upload' if i==0 else 'map'),offset=at,before=expected,
            after=(bytes.fromhex('004b1847')+struct.pack('<I',0x8000001+code_at+i*4)).hex(),
            reason='Use bounded proportional floor art; preserve native upload and suppression logic'))
    for p in patches:
        check(original[p['offset']:p['offset']+len(bytes.fromhex(p['before']))] == bytes.fromhex(p['before']),'Hook source changed')
    plan = dict(source_rom=str(ORIGINAL_ROM.relative_to(ROOT)),source_sha256=digest(original),output_rom=None,
        previous_rom=str(BASELINE.relative_to(ROOT)),previous_sha256=prior['rom_sha256'],
        approval_sha256=digest(APPROVAL.read_bytes()),rasters_sha256=digest((OUT/'rasters.json').read_bytes()),
        builder_sha256=digest(Path(__file__).read_bytes()),asm_sha256=digest(ASM.read_bytes()),
        start=start,end_exclusive=allocator.cursor,new_bytes_with_padding=allocator.cursor-start,
        allocations=allocator.allocations,patches=patches,titles=titles,floors=floors,
        palette_words=words,palette_rgb=[rgb(w) for w in words],palette_at=palette_at,
        pointers_at=pointers_at,counts_at=counts_at,records_at=records_at,code_at=code_at,
        new_ram_reservations=[],save_changes=[],scope='Dry plan; not an insertion result. Offsets are exclusive-ended ROM file offsets.')
    save_json(OUT/'allocation-plan.json',plan)
    print(f'Planned [{start:08X},{allocator.cursor:08X}), {allocator.cursor-start:,} bytes; {len(allocator.allocations)} allocations; 28 checked source bytes.')


def build_rom(original, *, build=None):
    plan = load_json(OUT/'allocation-plan.json')
    check(plan['builder_sha256'] == digest(Path(__file__).read_bytes()) and plan['asm_sha256'] == digest(ASM.read_bytes()), 'Regenerate and document changed plan')
    check(plan['approval_sha256'] == digest(APPROVAL.read_bytes()) and plan['rasters_sha256'] == digest((OUT/'rasters.json').read_bytes()),'Planned approval changed')
    marker = f"`[{plan['start']:08X},{plan['end_exclusive']:08X})`"
    check(marker in (ROOT/'docs/MEMORY_MAP.md').read_text(), 'Document exact allocation range before insertion')
    b = RomBuild(original) if build is None else build
    baseline, prior = previous.build_rom(original,build=b)
    check(baseline == BASELINE.read_bytes() and digest(baseline) == plan['previous_sha256'], 'Previous cumulative build differs')
    check(b.allocator.cursor == plan['start'],'Plan no longer follows shared allocator')
    for start,end in SOURCE_RANGES:
        b.protect_source(f'{OWNER}.original-{start:08x}',start,end,OWNER)
    for row in plan['allocations']:
        raw = (ROOT/row['file']).read_bytes()
        check(digest(raw) == row['sha256'] and len(raw) == row['bytes'],'Planned resource changed')
        check(b.allocate(row['id'],raw,OWNER,alignment=4) == row['offset'],'Allocation differs from plan')
    for p in plan['patches']:
        b.patch(p['id'],p['offset'],bytes.fromhex(p['before']),bytes.fromhex(p['after']),OWNER,p['reason'])
    data,ledger = b.finish()
    check(ledger['memory_reservations'] == prior['ledger']['memory_reservations'],'Unexpected RAM allocation')
    return data,dict(source_rom=str(ORIGINAL_ROM.relative_to(ROOT)),source_sha256=digest(original),
        output_rom=str(ROM.relative_to(ROOT)),rom_sha256=digest(data),previous_rom_sha256=digest(baseline),
        allocation_plan_sha256=digest((OUT/'allocation-plan.json').read_bytes()),
        approval_sha256=digest(APPROVAL.read_bytes()),title_assets=36,selectors=64,floor_variants=512,
        new_bytes_with_padding=plan['new_bytes_with_padding'],ledger=ledger)


def build():
    data,report = build_rom(ORIGINAL_ROM.read_bytes())
    atomic_write(ROM,data); save_json(OUT/'english-build.json',report)
    print('Built',ROM.relative_to(ROOT),report['rom_sha256'],flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--prepare',action='store_true')
    args = parser.parse_args()
    prepare() if args.prepare else build()
