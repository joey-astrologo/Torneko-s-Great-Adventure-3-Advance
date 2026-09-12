"""Five original church/save-service tables, with independently authored prose."""
import argparse
import json
import struct
from tools import build_adventure_results as previous
from tools import build_arena_services as message
from tools.build_first_label import ORIGINAL_ROM, ROOT, digest
from tools.game_text import GameTextCodec, rebuild
from tools.translation_pipeline import atomic_write, load_json, check
from tools.rom_build import RomBuild

CATALOG = ROOT/'translations/church-services.json'
OUTPUT = ROOT/'build/completion/church'
TABLE, END, STRIDE = 0xC78B04, 0xC78CA8, 84
encode = message.encode


def extract(original):
    codec = GameTextCodec(original)
    master = {int(e['offset'], 0): e for e in load_json(ROOT/'translations/master.json')['entries']}
    entries = {}
    for word in range(TABLE, END, 4):
        at = struct.unpack_from('<I', original, word)[0]-0x08000000
        s = codec.parse(original, at)
        check(rebuild(s['tokens']) == original[at:s['end']], 'Church source reconstruction')
        if not any(ord(c) > 127 for c in s['display']):
            continue  # Positional identifier placeholders are not displayed prose.
        if at not in entries:
            check(at in master, 'Missing church master source')
            entries[at] = {'id': f'church.{at:08x}', 'family': 'message', 'offset': hex(at),
                'source_end_exclusive': hex(s['end']), 'japanese': s['display'],
                'source_hex': s['raw_hex'], 'source_tokens': s['tokens'],
                'master_id': master[at]['id'], 'pointer_owners': [],
                'english': None, 'display': None, 'notes': '', 'references': []}
        entries[at]['pointer_owners'].append({'offset': hex(word),
            'evidence': 'native_church_type_times_84_plus_service_slot',
            'church_type': (word-TABLE)//STRIDE, 'slot': ((word-TABLE)%STRIDE)//4})
    check(len(entries) == 62, 'Church source count differs')
    return {'schema': 1, 'base_sha256': digest(original), 'font': 0,
        'entries': sorted(entries.values(), key=lambda e: int(e['offset'], 0))}


def validate(original, catalog):
    fresh = extract(original)
    check(all(catalog[k] == fresh[k] for k in ('schema', 'base_sha256', 'font')), 'Church catalog header differs')
    entries = {e['id']: e for e in catalog['entries']}
    check(len(entries) == len(catalog['entries']) == len(fresh['entries']), 'Incomplete church catalog')
    for e in fresh['entries']:
        a = entries[e['id']]
        check(all(a[k] == e[k] for k in e.keys()-{'english', 'display', 'notes', 'references'}), 'Church source metadata differs')
        check(isinstance(a['english'], str) and a['english'], 'Missing church English')
        encode(a, original)
    return list(entries.values())


def owners():
    original = ORIGINAL_ROM.read_bytes(); c = extract(original)
    atomic_write(OUTPUT/'source-owners.json', (json.dumps({'source_sha256': digest(original),
        'table': {'start': hex(TABLE), 'end_exclusive': hex(END), 'type_stride': STRIDE,
            'types': 5, 'slots_per_type': 21, 'source_hex': original[TABLE:END].hex()},
        'entries': c['entries'], 'scope': 'Exact positional text pointer words only. Internal identifier placeholders, source strings, original table storage and gaps remain occupied.'}, ensure_ascii=False, indent=2)+'\n').encode())
    print(len(c['entries']), 'church sources;', sum(len(e['pointer_owners']) for e in c['entries']), 'pointers', flush=True)


def build_rom(original, language='english', catalog=None, *, build=None):
    check(language in ('english', 'japanese'), 'Invalid church language')
    b = RomBuild(original) if build is None else build
    _, prior = previous.build_rom(original, build=b)
    c = load_json(CATALOG) if catalog is None else catalog
    entries = validate(original, c); relocated = {}
    for e in entries:
        at = int(e['offset'], 0); source = bytes.fromhex(e['source_hex']); raw, metrics = encode(e, original)
        b.protect_source(e['id'], at, at+len(source), 'church-services')
        dest = b.allocate(e['id'], raw if language == 'english' else source, 'church-services')
        for p in e['pointer_owners']:
            b.patch(e['id']+'.'+p['offset'], int(p['offset'], 0), struct.pack('<I', at+0x08000000), struct.pack('<I', dest+0x08000000), 'church-services', p['evidence'])
        relocated[e['id']] = {'offset': dest, 'metrics': metrics}
    data, ledger = b.finish()
    return data, {'source_sha256': digest(original), 'rom_sha256': digest(data),
        'previous_rom_sha256': prior['rom_sha256'], 'language': language,
        'church': {'entries': len(entries), 'pointer_words': sum(len(e['pointer_owners']) for e in entries), 'relocated': relocated}, 'ledger': ledger}


def build():
    original = ORIGINAL_ROM.read_bytes(); catalog = load_json(CATALOG)
    atomic_write(OUTPUT/'catalog.json', (json.dumps(catalog, ensure_ascii=False, indent=2)+'\n').encode())
    for language in ('english', 'japanese'):
        data, report = build_rom(original, language, catalog)
        report['catalog_sha256'] = digest((OUTPUT/'catalog.json').read_bytes())
        atomic_write(OUTPUT/f'torneko3-church-services-{language}.gba', data)
        atomic_write(OUTPUT/f'{language}-build.json', (json.dumps(report, indent=2)+'\n').encode())
        print(language, report['rom_sha256'], flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('mode', choices=('owners', 'build'))
    owners() if p.parse_args().mode == 'owners' else build()
