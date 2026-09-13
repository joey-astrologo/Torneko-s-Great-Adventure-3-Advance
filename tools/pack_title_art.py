"""Compile the approved title raster into native 4bpp tile/palette banks."""
from collections import Counter
from pathlib import Path
import json
import math
import struct
from PIL import Image
from tools.build_first_label import ROOT, ORIGINAL_ROM, digest
from tools.extract_arrival_cards import rgb, save_json
from tools.translation_pipeline import check, load_json, atomic_write

OUT = ROOT/'build/title-insertion'
APPROVAL = ROOT/'assets/title-screen/approved.json'
MAP_SOURCE, TILE_SOURCE, PALETTE_SOURCE = 0xC5151C, 0xC5251C, 0xC5737C
BANKS = 13


def representable(c):
    return tuple((v << 3) | (v >> 2) for v in ((x*31+127)//255 for x in c))


def distance(a, b):
    return sum((x-y)**2 for x, y in zip(a, b))


def palette_for(pixels):
    unique = sorted(set(pixels))
    if len(unique) <= 15:
        return [representable(c) for c in unique]
    im = Image.new('RGB', (len(pixels), 1)); im.putdata(pixels)
    q = im.quantize(colors=15, method=Image.Quantize.MEDIANCUT, kmeans=3)
    pal = q.getpalette()
    return sorted({representable(tuple(pal[i*3:i*3+3])) for _, i in q.getcolors()})


def starting_groups(tiles):
    # Histograms retain a tile's mixed colours (blue/stone/gold edges), unlike
    # average RGB alone. Farthest-first initialization is deterministic.
    image = Image.new('RGB', (64, len(tiles)))
    image.putdata([c for tile in tiles for c in tile])
    coarse = list(image.quantize(colors=32, method=Image.Quantize.MEDIANCUT).get_flattened_data())
    features = []
    for i in range(len(tiles)):
        hist = Counter(coarse[i*64:(i+1)*64]); features.append([hist[j] for j in range(32)])
    centers = [features[0]]
    while len(centers) < BANKS:
        centers.append(max(features, key=lambda h: min(distance(h,c) for c in centers)))
    groups = None
    for _ in range(12):
        new = [min(range(BANKS), key=lambda j: distance(h, centers[j])) for h in features]
        if new == groups: break
        groups = new
        centers = [[sum(features[i][k] for i,g in enumerate(groups) if g==j)/sum(g==j for g in groups)
                    for k in range(32)] if j in groups else centers[j] for j in range(BANKS)]
    return groups


def quantize(tiles):
    groups = starting_groups(tiles)
    unique = sorted({c for tile in tiles for c in tile})
    histories = []; best = None
    for iteration in range(12):
        palettes = [palette_for([c for tile,g in zip(tiles,groups) if g==j for c in tile])
                    if j in groups else [(0,0,0)] for j in range(BANKS)]
        lookups = [{c:min(range(len(p)),key=lambda i:distance(c,p[i])) for c in unique} for p in palettes]
        errors = [{c:distance(c,p[lookup[c]]) for c in unique} for p,lookup in zip(palettes,lookups)]
        costs = [[sum(error[c] for c in tile) for error in errors] for tile in tiles]
        chosen = [min(range(BANKS), key=lambda j: costs[i][j]) for i in range(len(tiles))]
        total = sum(costs[i][g] for i,g in enumerate(chosen))
        histories.append({'iteration':iteration,'squared_rgb_error':total,'bank_tile_counts':[chosen.count(j) for j in range(BANKS)]})
        print('Palette pass',iteration,'RGB RMSE',round(math.sqrt(total/(len(tiles)*64*3)),3),flush=True)
        if best is None or total < best[0]: best = (total, chosen, palettes, lookups)
        if chosen == groups: break
        groups = chosen
    _, groups, palettes, lookups = best
    indexed = [[lookups[g][c]+1 for c in tile] for tile,g in zip(tiles,groups)]
    rendered = [[palettes[g][v-1] for v in tile] for tile,g in zip(indexed,groups)]
    return groups, palettes, indexed, rendered, histories


def decode(maps, tiles, palette):
    colours = [rgb(v) for v in struct.unpack('<240I', palette)] + [(0,0,0)]*16
    out = Image.new('RGB',(240,160))
    for y in range(160):
        for x in range(240):
            color = (0,0,0)
            for layer in (1,0):
                entry = struct.unpack_from('<H',maps,layer*2048+((y//8)*32+x//8)*2)[0]
                xx,yy = (7-x%8 if entry&1024 else x%8),(7-y%8 if entry&2048 else y%8)
                value = (tiles[(entry&1023)*32+yy*4+xx//2] >> (4*(xx&1))) & 15
                if value: color=colours[(entry>>12)*16+value]
            # The original title display clips its leftmost screen column.
            out.putpixel((x,y),color if x else (0,0,0))
    return out


def pack():
    original = ORIGINAL_ROM.read_bytes(); approved=load_json(APPROVAL)
    check(digest(original)==approved['source_rom_sha256'],'Wrong Japanese original')
    check(digest((ROOT/approved['candidate']).read_bytes())==approved['candidate_sha256'],'Approved candidate changed')
    raster=ROOT/approved['raster'];check(digest(raster.read_bytes())==approved['raster_sha256'],'Approved raster changed')
    image=Image.open(raster).convert('RGB');check(image.size==(240,160),'Wrong artwork dimensions')
    oldmaps=original[MAP_SOURCE:TILE_SOURCE]
    oldtiles=original[TILE_SOURCE:PALETTE_SOURCE]
    oldpalette=original[PALETTE_SOURCE:PALETTE_SOURCE+960]
    reference=Image.open(ROOT/'build/title-audition/reference/japanese/title.png').convert('RGB')
    check(decode(oldmaps,oldtiles,oldpalette).tobytes()==reference.tobytes(),'Original native pixel decoder differs')
    check(image.crop((0,142,240,160)).tobytes()==reference.crop((0,142,240,160)).tobytes(),'Approved original prompt strip differs')
    # Reserve original banks 13 (ocean) and 14 (prompt); bank 15 is the native
    # separate font palette. The 540 upper-screen cells use banks 0..12.
    blocks=[list(image.crop((x,y,x+8,y+8)).get_flattened_data()) for y in range(0,144,8) for x in range(0,240,8)]
    groups,palettes,indexed,rendered,history=quantize(blocks)
    patterns=[bytes(32)];by_bytes={patterns[0]:0}
    def add(raw):
        if raw not in by_bytes: by_bytes[raw]=len(patterns);patterns.append(raw)
        return by_bytes[raw]
    def remap(entry):
        source=entry&1023
        return (entry&~1023)|add(oldtiles[source*32:source*32+32])
    maps=bytearray(4096)
    for i in range(1024):
        entry=struct.unpack_from('<H',oldmaps,2048+i*2)[0]
        check(entry>>12 in (0,13),'Unexpected ocean bank')
        if entry>>12==0:check(not any(oldtiles[(entry&1023)*32:(entry&1023)*32+32]),'Nonblank ocean bank 0')
        struct.pack_into('<H',maps,2048+i*2,remap(entry))
    for i in range(18*32,20*32):
        entry=struct.unpack_from('<H',oldmaps,i*2)[0]
        check(entry>>12 in (0,14),'Unexpected prompt bank')
        if entry>>12==0:check(not any(oldtiles[(entry&1023)*32:(entry&1023)*32+32]),'Nonblank prompt bank 0')
        struct.pack_into('<H',maps,i*2,remap(entry))
    retained_patterns=len(patterns)
    for i,(bank,tile) in enumerate(zip(groups,indexed)):
        raw=bytes(tile[j]|(tile[j+1]<<4) for j in range(0,64,2))
        struct.pack_into('<H',maps,((i//30)*32+i%30)*2,(bank<<12)|add(raw))
    check(len(patterns)<=1024,'Title exceeds two native BG character blocks')
    palette=bytearray()
    for bank in palettes:
        words=[0x80000000]+[0x80000000|sum((c>>3)<<(8*j+3) for j,c in enumerate(color)) for color in bank]
        words += [0x80000000]*(16-len(words))
        palette.extend(struct.pack('<16I',*words))
    palette.extend(oldpalette[13*64:15*64])
    tiles=b''.join(patterns)
    decoded=decode(maps,tiles,palette)
    # Deterministic decode also proves palette-bank assignment per cell, not
    # merely that the flattened bitmap uses fewer than 256 colours.
    errors=[abs(a-b) for p,q in zip(image.get_flattened_data(),decoded.get_flattened_data()) for a,b in zip(p,q)]
    mae=sum(errors)/len(errors);rmse=math.sqrt(sum(v*v for v in errors)/len(errors))
    check(decoded.crop((0,144,240,160)).tobytes()==reference.crop((0,144,240,160)).tobytes(),'Prompt/ocean pixels changed')
    OUT.mkdir(parents=True,exist_ok=True)
    atomic_write(OUT/'packed/graphics.bin',bytes(maps)+tiles)
    atomic_write(OUT/'packed/palette.bin',bytes(palette))
    decoded.save(OUT/'packed-preview.png')
    save_json(OUT/'packing.json',{'source_rom':str(ORIGINAL_ROM.relative_to(ROOT)),'source_sha256':digest(original),'output_rom':None,
        'approval_sha256':digest(APPROVAL.read_bytes()),'raster_sha256':approved['raster_sha256'],
        'packer_sha256':digest(Path(__file__).read_bytes()),'tile_count':len(patterns),'retained_patterns':retained_patterns,
        'new_pattern_count':len(patterns)-retained_patterns,'upper_screen_cells':540,'art_palette_banks':list(range(13)),
        'retained_palette_banks':[13,14],'font_palette_bank':15,'quantization_iterations':history,
        'rgb_mae':mae,'rgb_rmse':rmse,'max_channel_error':max(errors),'psnr_db':20*math.log10(255/rmse),
        'prompt_and_visible_ocean_pixels_exact':True,'original_decoder_pixels_exact':True,
        'files':{str(p.relative_to(ROOT)):digest(p.read_bytes()) for p in (OUT/'packed/graphics.bin',OUT/'packed/palette.bin',OUT/'packed-preview.png')},
        'scope':'Approved raster compiled into native 4bpp per-cell palettes. Original ocean map/tiles and prompt cells/tiles are repacked without pixel changes. No insertion.'})
    print('Packed',len(patterns),'tiles; MAE',round(mae,3),'RMSE',round(rmse,3),flush=True)


if __name__=='__main__':pack()
