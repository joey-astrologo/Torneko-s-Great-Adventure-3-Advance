"""Export the Japanese dungeon arrival graphics for visual review, without patching."""
from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from tools.build_first_label import ORIGINAL_ROM, ROOT, digest
from tools.translation_pipeline import check, load_json

OUTPUT = ROOT / 'build/arrival-cards'
POINTER_TABLE = 0x3C1450
COUNT_TABLE = 0x3C13D0
PALETTE = 0x3903D0
FLOOR_TILES = 0x3BFFD0
FLOOR_INDEXES = 0x9B6FC
SOURCE_SHA256 = '35bfff00dccd8de1a916b316298219c8c16a8adb0162ffe5056c481e0a8a4d02'
BACKGROUND = (0, 0, 0)


def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def rgb(word):
    # Original palette entries are packed AABBGGRR; the GBA keeps five bits.
    channels = [((word >> shift) & 255) >> 3 for shift in (0, 8, 16)]
    return tuple((value << 3) | (value >> 2) for value in channels)


def palette(original):
    return [rgb(struct.unpack_from('<I', original, PALETTE + i * 4)[0])
            for i in range(16)]


def tile_pixel(tiles, tile, x, y):
    check(tile * 32 + 32 <= len(tiles), 'Tile index leaves its recorded asset')
    return (tiles[tile * 32 + y * 4 + x // 2] >> ((x & 1) * 4)) & 15


def paint_cell(image, xy, tiles, entry, colours):
    tile = entry & 1023
    for y in range(8):
        for x in range(8):
            value = tile_pixel(tiles, tile, 7-x if entry & 1024 else x,
                               7-y if entry & 2048 else y)
            # A zero colour index is transparent, independently of palette RGB.
            if value:
                image.putpixel((xy[0]+x, xy[1]+y), colours[value])


def name_image(original, entry):
    at, count = int(entry['offset'], 0), entry['tile_count']
    tiles = original[at+0x800:at+0x800+count*32]
    image = Image.new('RGB', (240, 160), BACKGROUND)
    colours = palette(original)
    # Native 0800526E copies source rows 0..8, columns 1..29 to BG0 rows 1..9.
    for y in range(9):
        for x in range(1, 30):
            cell = struct.unpack_from('<H', original, at + (y*32+x)*2)[0]
            check(cell in (0, 0xF000) or cell >> 12 == 14,
                  'Unexpected arrival palette bank')
            paint_cell(image, (x*8, (y+1)*8), tiles, cell, colours)
    return image


def floor_glyph(original, glyph):
    check(0 <= glyph < 12, 'Invalid floor glyph')
    start = struct.unpack_from('<I', original, FLOOR_INDEXES + glyph*4)[0]
    width = 2 if glyph < 10 else 3
    # The original copies this 0x1400-byte atlas to tile 160 (buffer +0x1400).
    tiles = original[FLOOR_TILES:FLOOR_TILES+0x1400]
    image = Image.new('RGB', (width*8, 40), BACKGROUND)
    for y in range(5):
        for x in range(width):
            paint_cell(image, (x*8, y*8), tiles, start-160+y*32+x,
                       palette(original))
    return image


def add_floor(image, original, number=1, puzzle=False):
    check(0 <= number <= 99, 'Review samples use one or two digits')
    parts = []
    if puzzle:
        parts = [(11, 16 if number >= 10 else 17)]
        if number >= 10:
            parts += [(number//10, 19), (number%10, 21)]
        else:
            parts += [(number, 20)]
    elif number >= 10:
        parts = [(number//10, 16), (number%10, 18), (10, 20)]
    else:
        parts = [(number, 17), (10, 19)]
    image = image.copy()
    for glyph, x in parts:
        image.paste(floor_glyph(original, glyph), (x*8, 12*8))
    return image


def collect(original):
    check(digest(original) == SOURCE_SHA256, 'Expected the pinned Japanese original')
    source_catalog = ROOT / 'translations/dungeon-interface.json'
    labels = {}
    for e in load_json(source_catalog)['entries']:
        if e['family'] == 'dungeon':
            for row in e['rows']:
                labels[row] = e
    check(set(labels) == set(range(64)), 'Dungeon label table coverage changed')
    by_source = {}
    rows = []
    for row in range(64):
        pointer_word = POINTER_TABLE + row*4
        at = struct.unpack_from('<I', original, pointer_word)[0] - 0x08000000
        count = struct.unpack_from('<h', original, COUNT_TABLE + row*2)[0]
        check(0 < count <= 160, 'Arrival title exceeds the native first 160 tiles')
        end = at + 0x800 + count*32
        check(0 <= at < end <= len(original), 'Arrival asset outside original ROM')
        info = labels[row]
        item = by_source.setdefault(at, {
            'id': f'dungeon-{row:02d}', 'offset': hex(at),
            'end_exclusive': hex(end), 'map_bytes': 0x800,
            'tile_count': count, 'source_sha256': digest(original[at:end]),
            'selectors': [], 'japanese_name_reference': info['japanese'],
            'english_name_reference': info['english'],
            'name_catalog_id': info['id'],
            'name_reference_scope': 'Existing ordinary-text name for the matching selector; graphic transcription reviewed separately.',
            'english_artwork': None,
        })
        check(item['tile_count'] == count and item['name_catalog_id'] == info['id'],
              'Shared asset has mismatched size or ordinary name')
        item['selectors'].append(row)
        rows.append({'selector': row, 'bank': row//32, 'dungeon_id': row%32,
                     'pointer_word': hex(pointer_word),
                     'count_halfword': hex(COUNT_TABLE+row*2), 'asset_id': item['id']})
    entries = list(by_source.values())
    check(len(entries) == 36, 'Review the changed number of distinct arrival graphics')
    occupied = sorted((int(e['offset'], 0), int(e['end_exclusive'], 0)) for e in entries)
    check(all(a[1] == b[0] for a, b in zip(occupied, occupied[1:])),
          'Arrival asset boundaries no longer join exactly')
    check(occupied[0][0] == PALETTE+64 and occupied[-1][1] == FLOOR_TILES,
          'Arrival source envelope changed')
    return {'schema': 1, 'source_rom': str(ORIGINAL_ROM.relative_to(ROOT)),
            'source_sha256': digest(original), 'output_rom': None,
            'scope': 'All 64 selectors / 36 distinct assets in the native dungeon arrival table. No ROM changes, English artwork, or universal town/ending-graphics coverage claim.',
            'name_catalog_sha256': digest(source_catalog.read_bytes()),
            'entries': entries, 'selectors': rows}


def label_font(size):
    # Labels outside each game screen are review furniture, not game artwork.
    return ImageFont.truetype('/System/Library/Fonts/Menlo.ttc', size)


def contact_sheet(cards, entries, scale, path, title):
    cols = 4
    cw, ch = 256*scale, 202*scale
    header = 48*scale
    image = Image.new('RGB', (cols*cw, header+((len(cards)+cols-1)//cols)*ch), '#20232a')
    draw = ImageDraw.Draw(image)
    font, small = label_font(12*scale), label_font(10*scale)
    draw.text((12*scale, 8*scale), title, fill='white', font=font)
    draw.text((12*scale, 27*scale), 'Japanese original | labels below are our existing English name references',
              fill='#b7c1cf', font=small)
    for i, (card, e) in enumerate(zip(cards, entries, strict=True)):
        x, y = (i%cols)*cw+8*scale, header+(i//cols)*ch
        image.paste(card.resize((240*scale, 160*scale), Image.Resampling.NEAREST), (x, y))
        line = e['id'] + '  IDs ' + '/'.join(str(n) for n in e['selectors'])
        draw.text((x, y+164*scale), line, fill='#dce5f3', font=small)
        # Split the explanatory English reference outside the native screen.
        words = e['english_name_reference'].split(); lines = ['']
        for word in words:
            candidate = (lines[-1]+' '+word).strip()
            if draw.textlength(candidate, font=small) > 240*scale:
                lines.append(word)
            else:
                lines[-1] = candidate
        for j, line in enumerate(lines):
            draw.text((x, y+(178+j*11)*scale), line, fill='#b7c1cf', font=small)
    image.save(path)


def export():
    original = ORIGINAL_ROM.read_bytes()
    manifest = collect(original)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    individual = OUTPUT/'japanese'
    individual.mkdir(exist_ok=True)
    cards = []
    for e in manifest['entries']:
        name = name_image(original, e)
        # 25/27 are the two puzzle dungeons; 26 suppresses the floor line.
        dungeon = e['selectors'][0] % 32
        card = name if dungeon == 26 else add_floor(name, original, 1, dungeon in (25, 27))
        path = individual/(e['id']+'.png')
        card.save(path)
        name.save(individual/(e['id']+'-name-only.png'))
        e.update(png=str(path.relative_to(ROOT)), name_ink_bbox=name.getbbox(),
                 png_sha256=digest(path.read_bytes()),
                 sample_floor=None if dungeon == 26 else 1,
                 sample_suffix='none' if dungeon == 26 else 'puzzle' if dungeon in (25, 27) else 'F')
        cards.append(card)
    contact_sheet(cards, manifest['entries'], 2, OUTPUT/'arrival-cards-japanese.png',
                  'Torneko 3 Advance | 36 original dungeon arrival cards / 64 table entries')
    contact_sheet(cards, manifest['entries'], 1, OUTPUT/'arrival-cards-japanese-1x.png',
                  'Torneko 3 Advance | original arrival cards at native scale')
    for page in range(3):
        start, end = page*12, (page+1)*12
        contact_sheet(cards[start:end], manifest['entries'][start:end], 3,
                      OUTPUT/f'arrival-cards-japanese-page-{page+1}.png',
                      f'Torneko 3 Advance | Japanese arrival cards | page {page+1}/3')
    glyph_sheet = Image.new('RGB', (768, 200), '#20232a')
    draw = ImageDraw.Draw(glyph_sheet)
    draw.text((16, 12), 'Original floor artwork: 0-9 / F / puzzle prefix',
              font=label_font(16), fill='white')
    for n in range(12):
        glyph = floor_glyph(original, n)
        glyph.save(individual/f'floor-glyph-{n:02d}.png')
        glyph_sheet.paste(glyph.resize((glyph.width*2, 80), Image.Resampling.NEAREST), (16+n*62, 52))
        draw.text((16+n*62, 140), str(n) if n<10 else 'F' if n==10 else 'puzzle',
                  font=label_font(12), fill='white')
    glyph_sheet.save(OUTPUT/'floor-glyphs-japanese.png')
    manifest['harness_sha256'] = digest(Path(__file__).read_bytes())
    save_json(OUTPUT/'manifest.json', manifest)
    ranges = [
        {'start': hex(PALETTE), 'end_exclusive': hex(PALETTE+64), 'purpose': '16 original packed arrival palette colours'},
        {'start': hex(COUNT_TABLE), 'end_exclusive': hex(COUNT_TABLE+128), 'purpose': '64 native signed tile counts'},
        {'start': hex(POINTER_TABLE), 'end_exclusive': hex(POINTER_TABLE+256), 'purpose': '64 native arrival asset pointers'},
        {'start': hex(FLOOR_TILES), 'end_exclusive': hex(FLOOR_TILES+0x1400), 'purpose': '160-tile floor-number/F/puzzle atlas'},
        {'start': hex(FLOOR_INDEXES), 'end_exclusive': hex(FLOOR_INDEXES+48), 'purpose': '12 native floor glyph starting tile indexes'},
    ]
    ranges += [{'start': e['offset'], 'end_exclusive': e['end_exclusive'],
                'purpose': e['id'], 'sha256': e['source_sha256']} for e in manifest['entries']]
    save_json(OUTPUT/'resource-ranges.json', {
        'source_rom': manifest['source_rom'], 'source_sha256': manifest['source_sha256'],
        'output_rom': None, 'address_space': 'ROM file offsets; exclusive ends',
        'owner': 'original arrival renderer; occupied/protected, no insertion allocation',
        'evidence': 'Native 0800518C and 0800511C listings; exact count-driven adjacent asset boundaries. Native validation is separately reported.',
        'ranges': ranges})
    print('Exported 36 distinct Japanese arrival cards, 64 selector mappings and 12 floor glyphs.')


if __name__ == '__main__':
    argparse.ArgumentParser(description=__doc__).parse_args()
    export()
