"""Remaining battle feedback, dungeon shops, recruitment and companion actions."""
import argparse
from collections import Counter
import json
import struct
from tools import build_dungeon_events as previous
from tools import build_tutorial_gameplay as queue
from tools import build_arena_services as message
from tools.build_first_label import ORIGINAL_ROM, ROOT, digest
from tools.game_text import GameTextCodec, PRINTF, rebuild
from tools.translation_pipeline import atomic_write, load_json, check, FontZero
from tools.rom_build import RomBuild

CATALOG = ROOT/'translations/battle-completion.json'
OUTPUT = ROOT/'build/completion/battle'
POINTER_TABLES = ((0xDB0FC, 0xDB108), (0x9B660, 0x9B66C), (0xDB15C, 0xDB16C), (0xD95E0, 0xD9600))
INIT_TABLES = ((0xCAFE98, 0xCAFEA4), (0xCB0098, 0xCB00A4))
TYPED = {p for a, z in POINTER_TABLES+INIT_TABLES for p in range(a, z, 4)}
ABILITY = {p for start in (0xA6C8C, 0xA6C90) for p in range(start, 0xA7C8C, 36)}
ICON_LABEL = '⑪'  # Viewing label of original indexed glyph F9 AC, not prose.


def in_scope(at):
    return at == 0x1B4FF0 or 0x1B7DC6 <= at <= 0x1B9DE1 and not 0x1B98D6 <= at < 0x1B997C


def extract(original):
    codec = GameTextCodec(original); entries = []
    for m in load_json(ROOT/'translations/master.json')['entries']:
        at = int(m['offset'], 0)
        if not in_scope(at) or not m['pointer_candidates']: continue
        owners = []
        for word in m['pointer_candidates']:
            p = int(word, 0); check(struct.unpack_from('<I', original, p)[0] == at+0x08000000, 'Battle source pointer differs')
            kind = 'ability_record_text' if p in ABILITY else 'typed_pointer_table' if p in TYPED else 'thumb_literal'
            loads = [i for i in range(max(0, p-1024), p, 2) if original[i+1]&0xF8 == 0x48 and ((i+4)&~3)+original[i]*4 == p] if kind == 'thumb_literal' else []
            check(kind != 'thumb_literal' or p < 0xF0000 and loads, 'Unreviewed battle owner '+word)
            owners.append({'offset': word, 'evidence': kind, 'loads': [hex(i+0x08000000) for i in loads]})
        s = codec.parse(original, at); check(rebuild(s['tokens']) == original[at:s['end']], 'Battle source reconstruction')
        paged = at != 0x1B4FF0 and ('「' in s['display'] or 0x1B977C <= at <= 0x1B9871)
        entries.append({'id': f'battle.{at:08x}', 'family': 'message' if paged else 'queue', 'offset': m['offset'],
            'source_end_exclusive': hex(s['end']), 'japanese': s['display'], 'source_hex': s['raw_hex'], 'source_tokens': s['tokens'],
            'leading_glyph_hex': 'f9ac' if at in (0x1B84D3, 0x1B84FB) else '', 'master_id': m['id'], 'pointer_owners': owners,
            'english': None, 'display': None, 'notes': '', 'references': []})
    check(len(entries) == 298, 'Battle source count differs')
    return {'schema': 1, 'base_sha256': digest(original), 'font': 0, 'entries': entries}


def encode(e, original):
    if e['family'] == 'message': return message.encode(e, original)
    text = e['display'] or e['english']; check(isinstance(text, str) and text and all(32 <= ord(c) < 127 or c == '\n' for c in text), 'Battle English requires printable ASCII/LF')
    check(not any(c in text for c in '{}'), 'Unsupported battle markup')
    source = bytes.fromhex(e['source_hex']); check(text.startswith('!') == source.startswith(b'!'), 'Battle continuation marker differs')
    font = FontZero(original); codec = GameTextCodec(original)
    if e['leading_glyph_hex']:
        check(source.startswith(bytes.fromhex(e['leading_glyph_hex'])), 'Battle leading glyph differs'); text = ICON_LABEL+text
    def byte_bound(line): return queue.line_bytes(line.replace(ICON_LABEL, 'XX'))
    lines = []
    for paragraph in text.split('\n'):
        line = ''
        for word in paragraph.split(' '):
            candidate = line+' '+word if line else word
            if line and (queue.width(candidate, font) > 208 or byte_bound(candidate) > 59): lines.append(line); line = word
            else: line = candidate
            check(queue.width(line, font) <= 208 and byte_bound(line) <= 59, 'Unbreakable battle word '+e['id'])
        lines.append(line)
    check(len(lines) <= 15, 'Battle exceeds original pending queue capacity')
    text = '\n'.join(lines); raw = text.encode('cp932').replace(b'\x87\x4a', b'\xf9\xac')+b'\0'; parsed = codec.parse(raw, 0)
    dollars = lambda ts: Counter(t['text'] for t in ts if t['kind'] == 'dollar_command' and t['text'] != '$x' and not t['text'].startswith('$/'))
    check(dollars(parsed['tokens']) == dollars(e['source_tokens']), 'Battle substitution contract differs')
    check(not PRINTF.findall(source) and not any(t['kind'] == 'binary_control' for t in e['source_tokens']), 'Unreviewed battle source control')
    check(parsed['end'] == len(raw), 'Embedded battle terminator')
    return raw, {'display_template': text, 'line_widths': [queue.width(s, font) for s in lines], 'history_payload_upper_bounds': [byte_bound(s) for s in lines],
        'history_payload_capacity': 59, 'queue_row_capacity': 80, 'pending_queue_rows': len(lines), 'bytes_including_nul': len(raw)}


def validate(original, catalog):
    fresh = extract(original); entries = {e['id']: e for e in catalog['entries']}
    check(all(catalog[k] == fresh[k] for k in ('schema', 'base_sha256', 'font')), 'Battle header differs')
    check(len(entries) == len(catalog['entries']) == len(fresh['entries']), 'Incomplete battle catalog')
    for e in fresh['entries']:
        a = entries[e['id']]; check(all(a[k] == e[k] for k in e.keys()-{'english', 'display', 'notes', 'references'}), 'Battle source metadata differs'); encode(a, original)
    return list(entries.values())


def owners():
    original = ORIGINAL_ROM.read_bytes(); c = extract(original)
    tables = [{'start': hex(a), 'end_exclusive': hex(z), 'source_hex': original[a:z].hex(), 'initialized': (a, z) in INIT_TABLES} for a, z in POINTER_TABLES+INIT_TABLES]
    excluded = [e for e in load_json(ROOT/'translations/master.json')['entries'] if in_scope(int(e['offset'], 0)) and not e['pointer_candidates']]
    atomic_write(OUTPUT/'source-owners.json', (json.dumps({'source_sha256': digest(original), 'entries': c['entries'], 'tables': tables,
        'unreferenced_prose_leads_excluded': [{k: e[k] for k in ('id', 'offset', 'japanese', 'source_hex')} for e in excluded],
        'scope': 'Exact occupied source spans and text pointers only. Ability callbacks, typed table shapes, old strings and unreferenced leads remain protected from unreviewed writes.'}, ensure_ascii=False, indent=2)+'\n').encode())
    print(len(c['entries']), 'battle sources;', sum(len(e['pointer_owners']) for e in c['entries']), 'pointers;', Counter(e['family'] for e in c['entries']), flush=True)


def build_rom(original, language='english', catalog=None, *, build=None):
    check(language in ('english', 'japanese'), 'Invalid battle language'); b = RomBuild(original) if build is None else build
    _, prior = previous.build_rom(original, build=b); c = load_json(CATALOG) if catalog is None else catalog; entries = validate(original, c); relocated = {}
    for e in entries:
        at = int(e['offset'], 0); source = bytes.fromhex(e['source_hex']); raw, metrics = encode(e, original)
        b.protect_source(e['id'], at, at+len(source), 'battle-completion'); dest = b.allocate(e['id'], raw if language == 'english' else source, 'battle-completion')
        for p in e['pointer_owners']:
            b.patch(e['id']+'.'+p['offset'], int(p['offset'], 0), struct.pack('<I', at+0x08000000), struct.pack('<I', dest+0x08000000), 'battle-completion', p['evidence'])
        relocated[e['id']] = {'offset': dest, 'metrics': metrics}
    data, ledger = b.finish()
    return data, {'source_sha256': digest(original), 'rom_sha256': digest(data), 'previous_rom_sha256': prior['rom_sha256'], 'language': language,
        'battle': {'entries': len(entries), 'pointer_words': sum(len(e['pointer_owners']) for e in entries), 'relocated': relocated}, 'ledger': ledger}


def build():
    original = ORIGINAL_ROM.read_bytes(); catalog = load_json(CATALOG); atomic_write(OUTPUT/'catalog.json', (json.dumps(catalog, ensure_ascii=False, indent=2)+'\n').encode())
    for language in ('english', 'japanese'):
        data, report = build_rom(original, language, catalog); report['catalog_sha256'] = digest((OUTPUT/'catalog.json').read_bytes())
        atomic_write(OUTPUT/f'torneko3-battle-completion-{language}.gba', data); atomic_write(OUTPUT/f'{language}-build.json', (json.dumps(report, indent=2)+'\n').encode())
        print(language, report['rom_sha256'], flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('mode', choices=('owners', 'build')); owners() if p.parse_args().mode == 'owners' else build()
