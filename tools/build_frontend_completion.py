"""Remaining owned frontend mode, save warning, help and summary text."""
import argparse
import json
import struct
from tools import build_church_services as previous
from tools import build_arena_services as message
from tools.build_first_label import ORIGINAL_ROM, ROOT, digest
from tools.game_text import GameTextCodec, rebuild
from tools.translation_pipeline import atomic_write, load_json, check, FontZero
from tools.build_enemies import measure
from tools.rom_build import RomBuild

CATALOG = ROOT/'translations/frontend-completion.json'
OUTPUT = ROOT/'build/completion/frontend'
TYPED = {0xC4CD18, 0xC4CD0C, 0xC4CD58, 0xC78294, 0xC7828C}
EXTRA = {0xC4CD30, 0xC4CD38, 0xC4CD98, 0xC4CE90, 0xC4CEA4, 0xC4CEF8, 0xC4CF18, 0xC4CF2C}
LABELS = {0xC4CD30, 0xC4CD38, 0xC4CD98, 0xC78298, 0xC782B0, 0xC783E4, 0xC78408}


def extract(original):
    codec = GameTextCodec(original)
    prior = load_json(previous.OUTPUT/'english-build.json')['ledger']
    owned = {p['offset']: p for p in prior['patches']}; entries = []
    for m in load_json(ROOT/'translations/master.json')['entries']:
        at = int(m['offset'], 0)
        if not (0xC78298 <= at < 0xC78B04 or 0xC7A2E4 <= at < 0xC7ACB0 or at in EXTRA): continue
        owners = []; excluded = []
        for word in m['pointer_candidates']:
            p = int(word, 0)
            if p in owned:
                excluded.append({'offset': word, 'owner': owned[p]['owner'], 'id': owned[p]['id'], 'reason': 'Existing accepted patch preserved'})
                continue
            if p >= 0xF0000 and p not in TYPED:
                excluded.append({'offset': word, 'reason': 'Unreviewed high data-table context; no write authorized'})
                continue
            loads = [i for i in range(max(0, p-1024), p, 2) if original[i+1]&0xF8 == 0x48 and ((i+4)&~3)+original[i]*4 == p]
            check(p in TYPED or loads, 'Unreviewed frontend literal '+word)
            check(struct.unpack_from('<I', original, p)[0] == at+0x08000000, 'Frontend pointer differs')
            owners.append({'offset': word, 'evidence': 'typed_frontend_menu' if p in TYPED else 'thumb_literal', 'loads': [hex(i+0x08000000) for i in loads]})
        if not owners: continue
        s = codec.parse(original, at); check(rebuild(s['tokens']) == original[at:s['end']], 'Frontend source reconstruction')
        family = 'label' if at in LABELS else 'stats' if at == 0xC783CC else 'trip' if at == 0xC4CE90 else 'message'
        entries.append({'id': f'frontend.{at:08x}', 'family': family, 'offset': m['offset'], 'source_end_exclusive': hex(s['end']),
            'japanese': s['display'], 'source_hex': s['raw_hex'], 'source_tokens': s['tokens'], 'master_id': m['id'],
            'pointer_owners': owners, 'excluded_owners': excluded, 'english': None, 'display': None, 'notes': '', 'references': []})
    check(len(entries) == 48, 'Frontend source count differs')
    return {'schema': 1, 'base_sha256': digest(original), 'font': 0, 'entries': entries}


def encode(e, original):
    if e['family'] not in ('stats', 'trip'):
        return message.encode(e, original)
    # The original summary uses signed 16-bit HP/trip fields and an 8-bit level.
    # Its trip suffix is a 20-byte stack buffer; the joined row has 200 bytes.
    text = e['display'] or e['english']; raw = text.encode('ascii')+b'\0'
    from tools.game_text import PRINTF
    check(PRINTF.findall(raw) == PRINTF.findall(bytes.fromhex(e['source_hex'])), 'Frontend summary printf contract differs')
    args = (-32768,) if e['family'] == 'trip' else (-32768, -32768, 255, b'Trip -32768')
    cap = 20 if e['family'] == 'trip' else 200
    payload = raw % args; check(len(payload) <= cap, 'Frontend summary buffer overflow')
    return raw, {'display_template': text, 'capacity': cap, 'formatted_byte_upper_bound': len(payload),
        'bytes_including_nul': len(raw), 'boundary_width': measure(payload[:-1].decode(), FontZero(original)),
        'layout_status': 'Requires complete native summary-row check'}


def validate(original, catalog):
    fresh = extract(original); entries = {e['id']: e for e in catalog['entries']}
    check(all(catalog[k] == fresh[k] for k in ('schema', 'base_sha256', 'font')), 'Frontend catalog header differs')
    check(len(entries) == len(catalog['entries']) == len(fresh['entries']), 'Incomplete frontend catalog')
    for e in fresh['entries']:
        a = entries[e['id']]
        check(all(a[k] == e[k] for k in e.keys()-{'english', 'display', 'notes', 'references'}), 'Frontend source metadata differs')
        check(isinstance(a['english'], str) and a['english'], 'Missing frontend English'); encode(a, original)
    return list(entries.values())


def owners():
    original = ORIGINAL_ROM.read_bytes(); c = extract(original)
    atomic_write(OUTPUT/'source-owners.json', (json.dumps({'source_sha256': digest(original), 'entries': c['entries'],
        'scope': 'Exact reviewed literal and typed-menu pointer words only. Earlier patch owners, unreferenced sources, high data-table leads and all old source storage remain occupied.'}, ensure_ascii=False, indent=2)+'\n').encode())
    print(len(c['entries']), 'frontend sources;', sum(len(e['pointer_owners']) for e in c['entries']), 'pointers', flush=True)


def build_rom(original, language='english', catalog=None, *, build=None):
    check(language in ('english', 'japanese'), 'Invalid frontend language')
    b = RomBuild(original) if build is None else build
    _, prior = previous.build_rom(original, build=b)
    c = load_json(CATALOG) if catalog is None else catalog; entries = validate(original, c); relocated = {}
    for e in entries:
        at = int(e['offset'], 0); source = bytes.fromhex(e['source_hex']); raw, metrics = encode(e, original)
        b.protect_source(e['id'], at, at+len(source), 'frontend-completion')
        dest = b.allocate(e['id'], raw if language == 'english' else source, 'frontend-completion')
        for p in e['pointer_owners']:
            b.patch(e['id']+'.'+p['offset'], int(p['offset'], 0), struct.pack('<I', at+0x08000000), struct.pack('<I', dest+0x08000000), 'frontend-completion', p['evidence'])
        relocated[e['id']] = {'offset': dest, 'metrics': metrics}
    data, ledger = b.finish()
    return data, {'source_sha256': digest(original), 'rom_sha256': digest(data), 'previous_rom_sha256': prior['rom_sha256'], 'language': language,
        'frontend': {'entries': len(entries), 'pointer_words': sum(len(e['pointer_owners']) for e in entries), 'relocated': relocated}, 'ledger': ledger}


def build():
    original = ORIGINAL_ROM.read_bytes(); catalog = load_json(CATALOG)
    atomic_write(OUTPUT/'catalog.json', (json.dumps(catalog, ensure_ascii=False, indent=2)+'\n').encode())
    for language in ('english', 'japanese'):
        data, report = build_rom(original, language, catalog); report['catalog_sha256'] = digest((OUTPUT/'catalog.json').read_bytes())
        atomic_write(OUTPUT/f'torneko3-frontend-completion-{language}.gba', data)
        atomic_write(OUTPUT/f'{language}-build.json', (json.dumps(report, indent=2)+'\n').encode())
        print(language, report['rom_sha256'], flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('mode', choices=('owners', 'build'))
    owners() if p.parse_args().mode == 'owners' else build()
