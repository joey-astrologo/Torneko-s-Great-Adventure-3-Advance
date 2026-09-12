"""Category prefixes, quantities and special composed item names."""
import argparse
import json
import struct
from tools import build_frontend_completion as previous
from tools.build_first_label import ORIGINAL_ROM, ROOT, digest
from tools.game_text import GameTextCodec, PRINTF, rebuild
from tools.translation_pipeline import atomic_write, load_json, check
from tools.rom_build import RomBuild

CATALOG = ROOT/'translations/item-display.json'
OUTPUT = ROOT/'build/completion/item-display'
TABLE, TABLE_END = 0xCB0684, 0xCB06BC
SOURCES = set(range(0xC4C820, 0xC4C858, 4)) | {0xC4C858, 0xC4C87C, 0xC4C884, 0xC4C88C, 0xC4C8A4, 0xC4C8B4}


def extract(original):
    codec = GameTextCodec(original); entries = []
    for m in load_json(ROOT/'translations/master.json')['entries']:
        at = int(m['offset'], 0)
        if at not in SOURCES: continue
        owners = []
        for word in m['pointer_candidates']:
            p = int(word, 0); typed = TABLE <= p < TABLE_END and p%4 == 0
            loads = [i for i in range(max(0, p-1024), p, 2) if original[i+1]&0xF8 == 0x48 and ((i+4)&~3)+original[i]*4 == p]
            check(typed or p < 0xF0000 and loads, 'Unreviewed item-display reference '+word)
            check(struct.unpack_from('<I', original, p)[0] == at+0x08000000, 'Item-display pointer differs')
            owners.append({'offset': word, 'evidence': 'initialized_category_table' if typed else 'thumb_literal', 'loads': [hex(i+0x08000000) for i in loads]})
        s = codec.parse(original, at); check(rebuild(s['tokens']) == original[at:s['end']], 'Item-display source reconstruction')
        entries.append({'id': f'item-display.{at:08x}', 'family': 'category' if at < 0xC4C858 else 'quantity' if at in (0xC4C87C, 0xC4C884, 0xC4C88C) else 'special',
            'offset': m['offset'], 'source_end_exclusive': hex(s['end']), 'japanese': s['display'], 'source_hex': s['raw_hex'], 'source_tokens': s['tokens'],
            'master_id': m['id'], 'pointer_owners': owners, 'english': None, 'display': None, 'notes': '', 'references': []})
    check(len(entries) == 20, 'Item-display source count differs')
    return {'schema': 1, 'base_sha256': digest(original), 'font': 0, 'entries': entries}


def encode(e, original):
    text = e['display'] or e['english']; check(isinstance(text, str) and text and all(32 <= ord(c) < 127 for c in text), 'Item-display requires printable ASCII')
    raw = text.encode()+b'\0'; check(PRINTF.findall(raw) == PRINTF.findall(bytes.fromhex(e['source_hex'])), 'Item-display printf contract differs')
    cap = 100
    args = (32768, b"Justice's elder brother") if e['family'] == 'quantity' else (b"Justice's elder brother",) if b'%s' in raw else ()
    bound = len(raw % args); check(bound <= cap, 'Item-display formatter bound')
    return raw, {'bytes_including_nul': len(raw), 'capacity': cap, 'sample_formatted_bytes': bound,
        'layout_status': 'Complete original item formatter and actual item/actor/custom-name combinations required'}


def validate(original, catalog):
    fresh = extract(original); entries = {e['id']: e for e in catalog['entries']}
    check(all(catalog[k] == fresh[k] for k in ('schema', 'base_sha256', 'font')), 'Item-display header differs')
    check(len(entries) == len(catalog['entries']) == len(fresh['entries']), 'Incomplete item-display catalog')
    for e in fresh['entries']:
        a = entries[e['id']]; check(all(a[k] == e[k] for k in e.keys()-{'english', 'display', 'notes', 'references'}), 'Item-display metadata differs'); encode(a, original)
    return list(entries.values())


def owners():
    original = ORIGINAL_ROM.read_bytes(); c = extract(original)
    atomic_write(OUTPUT/'source-owners.json', (json.dumps({'source_sha256': digest(original), 'entries': c['entries'],
        'category_table': {'rom_start': hex(TABLE), 'rom_end_exclusive': hex(TABLE_END), 'ram_start': '0x020007FC', 'ram_end_exclusive': '0x02000834'},
        'scope': 'Exact text spans and pointer words only. Original strings, table storage, other formatter controls and surrounding data remain occupied.'}, ensure_ascii=False, indent=2)+'\n').encode())
    print(len(c['entries']), 'item-display sources;', sum(len(e['pointer_owners']) for e in c['entries']), 'pointers', flush=True)


def build_rom(original, language='english', catalog=None, *, build=None):
    check(language in ('english', 'japanese'), 'Invalid item-display language'); b = RomBuild(original) if build is None else build
    _, prior = previous.build_rom(original, build=b); c = load_json(CATALOG) if catalog is None else catalog; entries = validate(original, c); relocated = {}
    for e in entries:
        at = int(e['offset'], 0); source = bytes.fromhex(e['source_hex']); raw, metrics = encode(e, original)
        b.protect_source(e['id'], at, at+len(source), 'item-display'); dest = b.allocate(e['id'], raw if language == 'english' else source, 'item-display')
        for p in e['pointer_owners']:
            b.patch(e['id']+'.'+p['offset'], int(p['offset'], 0), struct.pack('<I', at+0x08000000), struct.pack('<I', dest+0x08000000), 'item-display', p['evidence'])
        relocated[e['id']] = {'offset': dest, 'metrics': metrics}
    data, ledger = b.finish()
    return data, {'source_sha256': digest(original), 'rom_sha256': digest(data), 'previous_rom_sha256': prior['rom_sha256'], 'language': language,
        'item_display': {'entries': len(entries), 'pointer_words': sum(len(e['pointer_owners']) for e in entries), 'relocated': relocated}, 'ledger': ledger}


def build():
    original = ORIGINAL_ROM.read_bytes(); catalog = load_json(CATALOG); atomic_write(OUTPUT/'catalog.json', (json.dumps(catalog, ensure_ascii=False, indent=2)+'\n').encode())
    for language in ('english', 'japanese'):
        data, report = build_rom(original, language, catalog); report['catalog_sha256'] = digest((OUTPUT/'catalog.json').read_bytes())
        atomic_write(OUTPUT/f'torneko3-item-display-{language}.gba', data); atomic_write(OUTPUT/f'{language}-build.json', (json.dumps(report, indent=2)+'\n').encode())
        print(language, report['rom_sha256'], flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('mode', choices=('owners', 'build')); owners() if p.parse_args().mode == 'owners' else build()
