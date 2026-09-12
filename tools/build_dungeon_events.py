"""Direct dungeon dialogue, rescued villagers and companion tutorial messages."""
import argparse
import json
import struct
from tools import build_item_display as previous
from tools import build_arena_services as message
from tools.build_first_label import ORIGINAL_ROM, ROOT, digest
from tools.game_text import GameTextCodec, rebuild
from tools.translation_pipeline import atomic_write, load_json, check
from tools.rom_build import RomBuild

CATALOG = ROOT/'translations/dungeon-events.json'
OUTPUT = ROOT/'build/completion/dungeon-events'
MENU, MENU_END = 0xA3FA0, 0xA3FC4
KEYS, KEYS_END = 0xA536C, 0xA546C
CACHE, CACHE_END = 0xCAFEB0, 0xCAFEB8
encode = message.encode


def extract(original):
    codec = GameTextCodec(original); entries = []
    for m in load_json(ROOT/'translations/master.json')['entries']:
        at = int(m['offset'], 0)
        if not 0xA3FC4 <= at <= 0xA5F20 or not any(ord(c) > 127 for c in m['japanese']): continue
        owners = []; excluded = []
        for word in m['pointer_candidates']:
            p = int(word, 0); check(struct.unpack_from('<I', original, p)[0] == at+0x08000000, 'Dungeon event source pointer differs')
            if p >= 0xCE0000:
                excluded.append({'offset': word, 'reason': 'Unreviewed high data array, not established independent reader'}); continue
            kind = ('typed_menu_12_bytes' if p in (MENU, MENU+12) else
                'tutorial_key_value_table' if KEYS+4 <= p < KEYS_END-8 and (p-KEYS)%8 == 4 else
                'initialized_arena_abort_table' if CACHE <= p < CACHE_END else 'thumb_literal')
            loads = [i for i in range(max(0, p-1024), p, 2) if original[i+1]&0xF8 == 0x48 and ((i+4)&~3)+original[i]*4 == p] if kind == 'thumb_literal' else []
            check(kind != 'thumb_literal' or p < 0xA000 and loads, 'Unreviewed dungeon-event owner '+word)
            owners.append({'offset': word, 'evidence': kind, 'loads': [hex(i+0x08000000) for i in loads]})
        check(owners, 'Dungeon event lacks reader'); s = codec.parse(original, at)
        check(rebuild(s['tokens']) == original[at:s['end']], 'Dungeon event source reconstruction')
        entries.append({'id': f'dungeon-event.{at:08x}', 'family': 'menu' if at in (0xA3FC4, 0xA3FCC) else 'message',
            'offset': m['offset'], 'source_end_exclusive': hex(s['end']), 'japanese': s['display'],
            'source_hex': s['raw_hex'], 'source_tokens': s['tokens'], 'master_id': m['id'],
            'pointer_owners': owners, 'excluded_owners': excluded, 'english': None, 'display': None, 'notes': '', 'references': []})
    check(len(entries) == 63, 'Dungeon event source count differs')
    return {'schema': 1, 'base_sha256': digest(original), 'font': 0, 'entries': entries}


def validate(original, catalog):
    fresh = extract(original); entries = {e['id']: e for e in catalog['entries']}
    check(all(catalog[k] == fresh[k] for k in ('schema', 'base_sha256', 'font')), 'Dungeon event header differs')
    check(len(entries) == len(catalog['entries']) == len(fresh['entries']), 'Incomplete dungeon event catalog')
    for e in fresh['entries']:
        a = entries[e['id']]; check(all(a[k] == e[k] for k in e.keys()-{'english', 'display', 'notes', 'references'}), 'Dungeon event metadata differs'); encode(a, original)
    return list(entries.values())


def owners():
    original = ORIGINAL_ROM.read_bytes(); c = extract(original)
    tables = [{'start': hex(a), 'end_exclusive': hex(z), 'purpose': purpose, 'source_hex': original[a:z].hex()} for a, z, purpose in
        ((MENU, MENU_END, 'Arena pause menu, two 12-byte rows plus zero terminator'), (KEYS, KEYS_END, '31 tutorial key/value pairs plus zero terminator'), (CACHE, CACHE_END, 'Two initialized arena abort-message pointers'))]
    atomic_write(OUTPUT/'source-owners.json', (json.dumps({'source_sha256': digest(original), 'entries': c['entries'], 'tables': tables,
        'scope': 'Exact source spans and reviewed pointer words only; keys, menu fields, high data-array references, original source bytes and table storage remain occupied.'}, ensure_ascii=False, indent=2)+'\n').encode())
    print(len(c['entries']), 'dungeon-event sources;', sum(len(e['pointer_owners']) for e in c['entries']), 'pointers', flush=True)


def build_rom(original, language='english', catalog=None, *, build=None):
    check(language in ('english', 'japanese'), 'Invalid dungeon-event language'); b = RomBuild(original) if build is None else build
    _, prior = previous.build_rom(original, build=b); c = load_json(CATALOG) if catalog is None else catalog; entries = validate(original, c); relocated = {}
    for e in entries:
        at = int(e['offset'], 0); source = bytes.fromhex(e['source_hex']); raw, metrics = encode(e, original)
        b.protect_source(e['id'], at, at+len(source), 'dungeon-events'); dest = b.allocate(e['id'], raw if language == 'english' else source, 'dungeon-events')
        for p in e['pointer_owners']:
            b.patch(e['id']+'.'+p['offset'], int(p['offset'], 0), struct.pack('<I', at+0x08000000), struct.pack('<I', dest+0x08000000), 'dungeon-events', p['evidence'])
        relocated[e['id']] = {'offset': dest, 'metrics': metrics}
    data, ledger = b.finish()
    return data, {'source_sha256': digest(original), 'rom_sha256': digest(data), 'previous_rom_sha256': prior['rom_sha256'], 'language': language,
        'dungeon_events': {'entries': len(entries), 'pointer_words': sum(len(e['pointer_owners']) for e in entries), 'relocated': relocated}, 'ledger': ledger}


def build():
    original = ORIGINAL_ROM.read_bytes(); catalog = load_json(CATALOG); atomic_write(OUTPUT/'catalog.json', (json.dumps(catalog, ensure_ascii=False, indent=2)+'\n').encode())
    for language in ('english', 'japanese'):
        data, report = build_rom(original, language, catalog); report['catalog_sha256'] = digest((OUTPUT/'catalog.json').read_bytes())
        atomic_write(OUTPUT/f'torneko3-dungeon-events-{language}.gba', data); atomic_write(OUTPUT/f'{language}-build.json', (json.dumps(report, indent=2)+'\n').encode())
        print(language, report['rom_sha256'], flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('mode', choices=('owners', 'build')); owners() if p.parse_args().mode == 'owners' else build()
