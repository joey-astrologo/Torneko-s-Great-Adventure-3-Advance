"""Help, ally orders, status summaries and the next gameplay message block."""
from collections import Counter
import json
import struct

from tools import build_core_gameplay as core
from tools.build_first_label import ORIGINAL_ROM, ROOT, digest
from tools.game_text import GameTextCodec, PRINTF, rebuild
from tools.rom_build import RomBuild
from tools.translation_pipeline import FontZero, atomic_write, check, load_json

CATALOG = ROOT / 'translations/gameplay-help.json'
OUTPUT = ROOT / 'build/gameplay-help'
TABLES = {'help': (0xEA448, 10), 'order': (0x1B4EF0, 7), 'status': (0x1B7CBC, 64)}
STATUS_LITERALS = (0x5E358, 0x5E390, 0x5E3EC, 0x5E744)
ORDER_MESSAGES = (0x1B4F0C, 0xC3E334, 0xC3E360, 0xC3E37C)
# The three strength messages and magic/item cancellation tables above 0xCA0000
# need their readers established separately. $i2 also needs its slot audited.
EXCLUDE = {0x1B5EBF}
SPEED_WORDS = set(range(0xA67E4, 0xA67F4, 4)) | set(range(0xD9304, 0xD9314, 4))


def extract_catalog(original):
    codec = GameTextCodec(original)
    master = load_json(ROOT / 'translations/master.json')
    check(digest(original) == master['base_sha256'], 'Wrong source ROM')
    records = {}
    def add(offset, family, owner, evidence, row=None):
        if offset not in records:
            s = codec.parse(original, offset)
            check(rebuild(s['tokens']) == original[offset:s['end']], 'Source round-trip failed')
            records[offset] = {'id': f'help.{offset:08x}', 'family': family,
                'offset': f'0x{offset:08X}', 'japanese': s['display'],
                'source_hex': s['raw_hex'], 'source_tokens': s['tokens'],
                'pointer_owners': [], 'master_id': f'jp_{offset:08x}',
                'english': None, 'display': None, 'notes': ''}
        check(records[offset]['family'] == family, 'Unexpected shared family')
        records[offset]['pointer_owners'].append({'offset': f'0x{owner:08X}', 'evidence': evidence})
        if row is not None: records[offset]['row'] = row
    for family, (base, count) in TABLES.items():
        for row in range(count):
            p = base + 4 * row
            add(struct.unpack_from('<I', original, p)[0] - 0x08000000, family, p, f'{family}_pointer_table', row)
    for p in STATUS_LITERALS:
        add(struct.unpack_from('<I', original, p)[0] - 0x08000000, 'status', p, 'status_conditional_literal')
    for e in master['entries']:
        o = int(e['offset'], 0)
        if not (0x1B5B1D <= o < 0x1B65CF or o in ORDER_MESSAGES) or o in EXCLUDE: continue
        for word in e['pointer_candidates']:
            p = int(word, 0)
            if p >= 0xF0000: continue
            loads = [i for i in range(max(0, p-1024), p, 2)
                     if original[i+1] & 0xF8 == 0x48 and ((i+4)&~3)+original[i]*4 == p]
            ability = 0xA6C8C <= p <= 0xA7C28 and (p-0xA6C8C) % 36 == 0
            check(loads or ability or p in SPEED_WORDS, f'Unreviewed pointer {p:08x}')
            check(struct.unpack_from('<I', original, p)[0] == o + 0x08000000, 'Pointer mismatch')
            add(o, 'message', p, 'ability_record_plus_8' if ability else
                'speed_result_pointer_table' if p in SPEED_WORDS else 'thumb_literal')
    return {'schema': 1, 'base_sha256': digest(original), 'font': 0,
            'entries': [records[o] for o in sorted(records)]}


def validate_catalog(original, catalog):
    fresh = extract_catalog(original)
    check(all(catalog[k] == fresh[k] for k in ('schema', 'base_sha256', 'font')), 'Catalog header changed')
    entries = {e['id']: e for e in catalog['entries']}
    check(len(entries) == len(catalog['entries']) == len(fresh['entries']), 'Incomplete or duplicate entries')
    for s in fresh['entries']:
        e = entries[s['id']]
        check(all(e[k] == s[k] for k in s.keys()-{'english', 'display', 'notes'}), f'Source changed: {s["id"]}')
        check(isinstance(e['english'], str) and e['english'], 'Missing English')
        check(e['display'] is None or isinstance(e['display'], str) and e['display'], 'Bad display')
    return entries


def encode(entry, original, message_wrap=None):
    font, codec = FontZero(original), GameTextCodec(original)
    text = entry['display'] or entry['english']
    check(all(32 <= ord(c) < 127 or c == '\n' for c in text), 'ASCII/LF required')
    check(not any(c in text for c in '{}%*'), 'Unsupported English control')
    family = entry['family']
    if family == 'message': text = (message_wrap or core.wrap)(text, font)
    lines = text.split('\n')
    widths = [core.text_width(line, font) for line in lines]
    limit = 120 if family == 'order' else 200 if family == 'status' else 208
    check(max(widths) <= limit, f'Width overflow {entry["id"]}: {widths}')
    check(len(lines) <= {'message': 3, 'order': 1, 'status': 1, 'help': 10}[family], f'Too many lines: {entry["id"]}')
    raw = text.encode() + b'\0'
    parsed = codec.parse(raw, 0)
    def commands(tokens):
        # $x is an indent, $/NNN is a conditional Japanese line break.
        return Counter(t['text'] for t in tokens if t['kind'] == 'dollar_command'
                       and t['text'] != '$x' and not t['text'].startswith('$/'))
    check(commands(parsed['tokens']) == commands(entry['source_tokens']), f'Substitutions changed: {entry["id"]}')
    check(not PRINTF.findall(bytes.fromhex(entry['source_hex'])), 'Unexpected printf')
    check(not any(t['kind'] == 'binary_control' for t in entry['source_tokens']), 'Unreviewed binary control')
    maximum = 0
    for t in parsed['tokens']:
        if t['kind'] == 'dollar_command':
            maximum += 99 if t['text'].startswith('$i') else 29 if t['text'].startswith('$m') else 7 if t['text'] == '$t' else 11
        else: maximum += len(bytes.fromhex(t['raw_hex']))
    cap = {'message': 1000, 'order': 30, 'status': 64, 'help': 512}[family]
    check(maximum <= cap, f'Formatted buffer overflow {entry["id"]}: {maximum}/{cap}')
    return raw, {'display_template': text, 'worst_line_widths': widths,
                 'formatted_byte_upper_bound': maximum, 'capacity': cap,
                 'bytes_including_nul': len(raw)}


def add_help(build, catalog, language='english', message_wrap=None):
    check(language in ('english', 'japanese'), 'Bad language')
    entries = validate_catalog(build.original, catalog); relocated = {}
    for ident, e in entries.items():
        offset = int(e['offset'], 0); source = bytes.fromhex(e['source_hex'])
        build.protect_source(ident, offset, offset+len(source), 'gameplay-help')
        english, metrics = encode(e, build.original, message_wrap)
        raw = english if language == 'english' else source
        target = build.allocate(ident, raw, 'gameplay-help')
        for owner in e['pointer_owners']:
            p = int(owner['offset'], 0)
            build.patch(f'{ident}.{p:08x}', p, struct.pack('<I', offset+0x08000000),
                        struct.pack('<I', target+0x08000000), 'gameplay-help', owner['evidence'])
        relocated[ident] = {'offset': target, 'bytes': len(raw), 'metrics': metrics}
    return {'language': language, 'entries': len(entries), 'relocated': relocated}


def build_rom(original, language='english', catalog=None):
    b = RomBuild(original); core.build_name_rom(original, build=b)
    for module, add in ((core.build_items, core.build_items.add_items),
                        (core.build_item_contexts, core.build_item_contexts.add_contexts),
                        (core.build_enemies, core.build_enemies.add_enemies),
                        (core.build_dungeon_interface, core.build_dungeon_interface.add_interface),
                        (core, core.add_gameplay)):
        add(b, load_json(module.CATALOG), 'english')
    report = add_help(b, load_json(CATALOG) if catalog is None else catalog, language)
    data, ledger = b.finish()
    return data, {'source_sha256': digest(original), 'rom_sha256': digest(data), 'help': report, 'ledger': ledger}


def build():
    for language in ('japanese', 'english'):
        data, report = build_rom(ORIGINAL_ROM.read_bytes(), language)
        atomic_write(OUTPUT / f'torneko3-gameplay-help-{language}.gba', data)
        atomic_write(OUTPUT / f'{language}-build.json', (json.dumps(report, indent=2)+'\n').encode())
        print(language, report['rom_sha256'], report['ledger']['appended_used_with_padding'], flush=True)


if __name__ == '__main__': build()
