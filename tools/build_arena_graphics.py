"""Translate six indexed arena graphic phrases with the original Latin font."""
import argparse
import json
import struct
from tools import build_arena_final as previous
from tools.build_first_label import ORIGINAL_ROM, ROOT, digest
from tools.font_metrics import extract_fonts, measure_line
from tools.rom_build import RomBuild
from tools.translation_pipeline import check, load_json, atomic_write

OUTPUT = ROOT / 'build/completion/arena-graphics'
CATALOG = ROOT / 'translations/arena-graphics.json'
ATLAS = (0x3C8CA0, 0x3C9A20)
ROWS = (
    (0xDC838, 0xDC843, (0x5CB78,), '今回の勝利モンスター', 'Winning monsters'),
    (0xDC843, 0xDC84B, (0x5CF0C,), '今回の対戦結果', 'Battle results'),
    (0xDC84B, 0xDC852, (0x5CF4C, 0x5CF8C), 'ポポロの仲間', "Tipper's allies"),
    (0xDC852, 0xDC85B, (0x5CF90,), '<<<勝利>>>', '<<< Victory >>>'),
    (0xDC85B, 0xDC864, (0x5CF50,), '<<<敗北>>>', '<<< Defeat >>>'),
    (0xDC864, 0xDC86E, (0x5CF28,), '<<<引分け>>>', '<<< Draw >>>'),
)


def extract(original):
    entries = []
    for at, end, words, japanese, english in ROWS:
        raw = original[at:end]
        check(raw[-1] == 0 and all(1 <= x <= 27 for x in raw[:-1]), 'Arena graphic index grammar differs')
        for word in words:
            check(struct.unpack_from('<I', original, word)[0] == at + 0x08000000, 'Arena graphic pointer differs')
        entries.append({'id': f'arena-graphics.{at:08x}', 'family': 'indexed_graphic',
                        'offset': hex(at), 'source_end_exclusive': hex(end), 'source_hex': raw.hex(),
                        'source_tokens': [], 'master_id': None, 'japanese': japanese,
                        'pointer_owners': [{'offset': hex(word), 'evidence': 'native_5d070_indexed_tile_reader'} for word in words],
                        'cells': len(raw) - 1, 'english': english, 'display': None,
                        'notes': 'Transcribed from original indexed graphics and independently translated. Latin glyphs come from original font 0; preserve native cell count, positions and palette.',
                        'references': []})
    check(struct.unpack_from('<I', original, 0x5D0B0)[0] == ATLAS[0] + 0x08000000, 'Arena graphic atlas differs')
    return {'schema': 1, 'base_sha256': digest(original), 'font': 0,
            'source_encoding': 'one-byte indexes into 27 original 16x16 graphic cells; zero terminator',
            'entries': entries}


def render(e, font):
    """Pack a font-0 phrase into native GBA tiles, preserving its whole field."""
    text = e['display'] or e['english']
    check(isinstance(text, str) and text and all(32 <= ord(ch) < 127 for ch in text), 'Arena graphics require literal ASCII')
    width = e['cells'] * 16
    metrics = measure_line(font, text)
    check(metrics['advance'] <= width and metrics['ink_right'] <= width, 'Arena graphic phrase is too wide')
    x = (width - metrics['advance']) // 2
    pixels = [[0] * width for _ in range(16)]
    for ch in text:
        g = font['glyphs'][ch]
        for gy, row in enumerate(g['pixels']):
            for gx, value in enumerate(row):
                if value:
                    check(0 <= x + gx < width and pixels[gy + 2][x + gx] == 0, 'Arena graphic glyph collision')
                    pixels[gy + 2][x + gx] = value
        x += g['advance']
    packed = bytearray()
    for cell in range(e['cells']):
        for ty in (0, 8):
            for tx in (0, 8):
                for y in range(ty, ty + 8):
                    for xx in range(tx, tx + 8, 2):
                        xx += cell * 16
                        packed.append(pixels[y][xx] | pixels[y][xx + 1] << 4)
    check(len(packed) == e['cells'] * 128, 'Arena graphic tile size differs')
    return bytes(packed), {**metrics, 'field_width': width, 'height': 16,
                           'text_origin': [(width - metrics['advance']) // 2, 2],
                           'glyph_pixels_sha256': digest(bytes(v for row in pixels for v in row))}


def prepare():
    original = ORIGINAL_ROM.read_bytes(); c = extract(original)
    old = {e['id']: e for e in load_json(CATALOG)['entries']} if CATALOG.exists() else {}
    font = extract_fonts(original)[0]
    for e in c['entries']:
        if e['id'] in old:
            for k in ('english', 'display', 'notes', 'references'): e[k] = old[e['id']][k]
        render(e, font)
    atomic_write(CATALOG, (json.dumps(c, ensure_ascii=False, indent=2) + '\n').encode())
    atomic_write(OUTPUT / 'source-owners.json', (json.dumps(extract(original), ensure_ascii=False, indent=2) + '\n').encode())
    print('Prepared six indexed graphic phrases outside ordinary inventory', flush=True)


def validate(original, catalog):
    fresh = extract(original)
    check(all(catalog[k] == fresh[k] for k in ('schema', 'base_sha256', 'font', 'source_encoding')) and
          len(catalog['entries']) == 6, 'Arena graphic catalog header/count differs')
    for e, f in zip(catalog['entries'], fresh['entries'], strict=True):
        check(all(e[k] == f[k] for k in f.keys() - {'english', 'display', 'notes', 'references'}), 'Arena graphic source metadata changed')
    return catalog['entries']


def build_rom(original, language='english', catalog=None, *, build=None):
    check(language in ('english', 'japanese'), 'Arena graphic language')
    b = RomBuild(original) if build is None else build
    _, prior = previous.build_rom(original, build=b)
    c = load_json(CATALOG) if catalog is None else catalog
    entries = validate(original, c); font = extract_fonts(original)[0]
    atlas = bytearray(); indexes = {}; metrics = {}
    for e in entries:
        raw, metrics[e['id']] = render(e, font)
        first = len(atlas) // 128 + 1
        indexes[e['id']] = bytes(range(first, first + e['cells'])) + b'\0'
        atlas.extend(raw)
    check(len(atlas) // 128 <= 255, 'Arena graphic atlas index overflow')
    b.protect_source('arena-graphics.original-atlas', *ATLAS, 'arena-graphics')
    b.protect_source('arena-graphics.original-palette', 0x3C9CA0, 0x3C9CE0, 'arena-graphics')
    atlas_at = b.allocate('arena-graphics.atlas', bytes(atlas) if language == 'english' else original[slice(*ATLAS)], 'arena-graphics')
    b.patch('arena-graphics.atlas-literal', 0x5D0B0, struct.pack('<I', ATLAS[0] + 0x08000000), struct.pack('<I', atlas_at + 0x08000000), 'arena-graphics', 'Relocated 16x16 indexed atlas for native renderer')
    relocated = {}
    for e in entries:
        at = int(e['offset'], 0); source = bytes.fromhex(e['source_hex'])
        b.protect_source(e['id'], at, at + len(source), 'arena-graphics')
        dest = b.allocate(e['id'], indexes[e['id']] if language == 'english' else source, 'arena-graphics')
        for p in e['pointer_owners']:
            b.patch(e['id'] + '.' + p['offset'], int(p['offset'], 0), struct.pack('<I', at + 0x08000000), struct.pack('<I', dest + 0x08000000), 'arena-graphics', p['evidence'])
        relocated[e['id']] = {'offset': dest, 'metrics': metrics[e['id']]}
    data, ledger = b.finish()
    return data, {'source_sha256': digest(original), 'rom_sha256': digest(data), 'previous_rom_sha256': prior['rom_sha256'],
                  'language': language, 'arena_graphics': {'resources': 6, 'outside_inventory': 6, 'pointer_words': 8,
                  'atlas_offset': atlas_at, 'atlas_bytes': len(atlas) if language == 'english' else ATLAS[1]-ATLAS[0], 'relocated': relocated}, 'ledger': ledger}


def build():
    original = ORIGINAL_ROM.read_bytes(); c = load_json(CATALOG)
    atomic_write(OUTPUT / 'catalog.json', (json.dumps(c, ensure_ascii=False, indent=2) + '\n').encode())
    for language in ('english', 'japanese'):
        data, r = build_rom(original, language, c)
        r['catalog_sha256'] = digest((OUTPUT / 'catalog.json').read_bytes())
        atomic_write(OUTPUT / f'torneko3-arena-graphics-{language}.gba', data)
        atomic_write(OUTPUT / f'{language}-build.json', (json.dumps(r, indent=2) + '\n').encode())
        print(language, r['rom_sha256'], flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('mode', choices=('prepare', 'build'))
    prepare() if p.parse_args().mode == 'prepare' else build()
