"""Native item-name composition, categories, unknown names and price columns."""
import argparse
from pathlib import Path
import struct
import mgba.log
from tools import build_item_display as b
from tools import verify_core_gameplay as old
from tools import verify_dungeon_interface as ui
from tools import verify_ally_services as service
from tools import verify_arena_services as arena
from tools import verify_item_contexts as unknown
from tools.build_name_entry import compact_name
from tools.build_first_label import ORIGINAL_ROM, digest
from tools.game_text import GameTextCodec, PRINTF
from tools.translation_pipeline import FontZero, load_json, check
from tools.verify_expansion import Session
from tools.verify_items import install_item, write_json

STATE = service.STATE
BASELINE = b.previous.OUTPUT/'torneko3-frontend-completion-english.gba'
RECORD, OPTIONS = 0x0203F000, 0x0203F100


def scenarios(original):
    cases = []
    for mode in ('normal', 'priced'):
        for item in range(370):
            amount = 0 if mode == 'normal' else 99 if item < 116 else 32767 if item <= 132 else 0
            cases.append({'id': f'{mode}-{item:03}', 'kind': mode, 'item': item, 'amount': amount})
    for row in range(246):
        category = struct.unpack_from('<I', original, 0x190808+8*row)[0]
        cases.append({'id': f'unknown-{row:03}', 'kind': 'unknown', 'item': unknown.CATEGORY_ITEMS[category], 'dictionary_row': row, 'amount': 0})
    for row in unknown.UNKNOWN_ROWS:
        category = struct.unpack_from('<I', original, 0x190808+8*row)[0]
        cases.append({'id': f'custom-{row:03}', 'kind': 'custom', 'item': unknown.CATEGORY_ITEMS[category], 'dictionary_row': row, 'amount': 0})
    for actor in range(200): cases.append({'id': f'grave-{actor:03}', 'kind': 'grave', 'item': 349, 'amount': actor})
    for mode in ('outside', 'matching', 'different'):
        cases.append({'id': 'tracks-'+mode, 'kind': 'tracks', 'item': 348, 'amount': 188 if mode != 'different' else 1, 'context': mode})
    for item in (1, 190): cases.append({'id': f'hidden-{item}', 'kind': 'hidden', 'item': item, 'amount': 0})
    return cases


def draw(session, raw, variant, font, codec):
    c = session.core; trace = ui.InterfaceTrace(c)
    try:
        ui.native_step(session, trace, 0x0808B60C, [18, 1, 1]); ui.native_step(session, trace, 0x0808BBD8, [0])
        old.write_bytes(c, old.DEST, raw)
        ui.native_step(session, trace, 0x0808CB84, [0, 0, old.DEST, 0, 0]); ui.native_step(session, trace, 0x0808BBF8, [0])
        checks = arena.check_draws(trace, font) if variant == 'english' else []
        at = raw.find(b'\x03\x09\x82'); glyphs, _ = old.distinct_glyph_observations(trace.positions)
        left = old.visible((raw[:at] if at >= 0 else raw[:-1])+b'\0', codec)
        right = max((g['x']+g['advance'] for g in glyphs[:len(left)]), default=0)
        if variant == 'english' and at >= 0: check(right <= 130, 'Item name overlaps native price column')
        return {'checks': checks, 'glyphs': trace.positions, 'payloads': trace.payloads, 'has_price': at >= 0, 'left_advance_right': right}
    finally:
        trace.close()


def native_case(session, case, table, variant, original, font, codec):
    c = session.core; check(c.load_raw_state(STATE.read_bytes()), 'Item-display state restore')
    old.write_bytes(c, 0x020007FC, table)
    install_item(c, RECORD, case['item'], case['amount'])
    kind = case['kind']; flags = 0x102 if kind in ('priced', 'unknown', 'custom') else 0
    c.memory.u16[OPTIONS] = flags
    if kind in ('unknown', 'custom'):
        unknown.unidentified_state(c, original, case['item'], case['dictionary_row'], 'custom' if kind == 'custom' else 'unknown')
        if kind == 'custom':
            slot = max(0, struct.unpack_from('<h', original, 0xC4C4FC+2*case['item'])[0])
            old.write_bytes(c, 0x0200CA06+slot*8, compact_name('WWWWWWW'))
    root_word = c.memory.u32[0x0200000C]; mode_word = c.memory.u32[0x02000000]
    root_field = bytes(c.memory[0x02010ADC:0x02010ADE])
    if kind == 'tracks':
        c.memory.u32[0x02000000] = int(case['context'] != 'outside')
        c.memory.u32[0x0200000C] = 0x02010A90
        c.memory.u16[0x02010ADC] = 188
    if kind == 'hidden':
        check(original[0xE07F4+28*case['item']+0x13] != 0, 'Hidden-name item lacks source property')
        c.memory.u16[0x02006188] = 1
    before = bytes(c.memory[RECORD:RECORD+24])
    old.write_bytes(c, old.DEST-8, old.GUARD+b'\xA5'*100+old.GUARD); trace = ui.InterfaceTrace(c)
    try:
        ui.native_step(session, trace, 0x08080A5C, [RECORD, old.DEST, OPTIONS, 0, 999999 if flags else 0])
        raw = old.cstring(c, old.DEST, 100)
        check(bytes(c.memory[old.DEST-8:old.DEST]) == old.GUARD and bytes(c.memory[old.DEST+100:old.DEST+108]) == old.GUARD, 'Item name output overrun')
        check(bytes(c.memory[RECORD:RECORD+24]) == before and c.memory.u16[OPTIONS] == flags, 'Item formatter changed source record/options')
    finally:
        trace.close()
        # The synthetic root uses occupied heap storage; restore it before any
        # UI/frame processing that can use the real heap or village context.
        if kind == 'tracks':
            c.memory.u32[0x0200000C] = root_word; c.memory.u32[0x02000000] = mode_word
            old.write_bytes(c, 0x02010ADC, root_field)
    if variant == 'english':
        if kind == 'hidden': check(raw == b'????\0', 'Native hidden-name text differs')
        if kind == 'grave' and case['amount']: check(b'Grave of ' in raw, 'Native grave composition missing')
        if kind == 'tracks' and case['context'] == 'matching': check(b'Monster tracks' in raw, 'Native matching tracks text missing')
        if kind == 'custom': check(b'WWWWWWW' in raw, 'Seven-slot custom width fixture truncated')
    result = draw(session, raw, variant, font, codec)
    result.update(case=case, formatted_hex=raw.hex(), guards_intact=True, record_and_options_intact=True)
    return result


def previews(session, catalog, table, variant, report, font, codec):
    c = session.core; cases = []
    for e in catalog['entries']:
        check(c.load_raw_state(STATE.read_bytes()), 'Item-display preview state'); old.write_bytes(c, 0x020007FC, table)
        at = 0x08000000+(int(e['offset'], 0) if variant == 'baseline' else report['item_display']['relocated'][e['id']]['offset'])
        source = old.cstring(c, at); args = PRINTF.findall(source); trace = ui.InterfaceTrace(c)
        try:
            old.write_bytes(c, RECORD, b"Justice's elder brother\0")
            old.write_bytes(c, old.DEST-8, old.GUARD+b'\xA5'*100+old.GUARD)
            if args: ui.native_step(session, trace, 0x08096744, [old.DEST, at]+[RECORD if a == b'%s' else 32768 for a in args])
            else: ui.native_step(session, trace, 0x080969A8, [old.DEST, at, 100])
            raw = old.cstring(c, old.DEST, 100)
            check(bytes(c.memory[old.DEST-8:old.DEST]) == old.GUARD and bytes(c.memory[old.DEST+100:old.DEST+108]) == old.GUARD, 'Item preview buffer overrun')
            if variant == 'english':
                pyargs = tuple(b"Justice's elder brother" if a == b'%s' else 32768 for a in args)
                check(raw == b.encode(e, ORIGINAL_ROM.read_bytes())[0] % pyargs, 'Item-display preview bytes differ')
        finally:
            trace.close()
        r = draw(session, raw, variant, font, codec); r.update(id=e['id'], formatted_hex=raw.hex(), guards_intact=True)
        name = 'preview-'+e['id']; session.frames(2); session.capture(name); r['screens'] = [name+'.png']
        write_json(session.output/(name+'.json'), r); cases.append({k: v for k, v in r.items() if k not in ('glyphs', 'payloads')})
    return cases


def verify(variant, limit=None):
    mgba.log.silence(); rom = BASELINE if variant == 'baseline' else b.OUTPUT/f'torneko3-item-display-{variant}.gba'
    data = rom.read_bytes(); original = ORIGINAL_ROM.read_bytes(); font = FontZero(original); codec = GameTextCodec(original)
    catalog = load_json(b.OUTPUT/'catalog.json'); report = {} if variant == 'baseline' else load_json(b.OUTPUT/f'{variant}-build.json'); cases = []
    with Session(data, b.OUTPUT/'verification'/variant) as session:
        session.frames(600); table = bytes(session.core.memory[0x020007FC:0x02000834])
        check(table == data[b.TABLE:b.TABLE_END], 'Cold item-category initialization differs')
        for e in catalog['entries']:
            for p in e['pointer_owners']:
                at = int(e['offset'], 0) if variant == 'baseline' else report['item_display']['relocated'][e['id']]['offset']
                check(session.core.memory.u32[int(p['offset'], 0)+0x08000000] == at+0x08000000, 'Item-display pointer owner differs')
        for index, case in enumerate(scenarios(original)[:limit]):
            r = native_case(session, case, table, variant, original, font, codec)
            name = case['id']; session.frames(2); session.capture(name); r['screens'] = [name+'.png']
            write_json(session.output/(name+'.json'), r); cases.append({k: v for k, v in r.items() if k not in ('glyphs', 'payloads')})
            if index%100 == 0: print(variant, index+1, 'native item contexts', flush=True)
        preview_cases = [] if limit else previews(session, catalog, table, variant, report, font, codec)
        result = {'rom_sha256': digest(data), 'source_sha256': digest(original), 'catalog_sha256': digest((b.OUTPUT/'catalog.json').read_bytes()),
            'harness_sha256': digest(Path(__file__).read_bytes()), 'unknown_helper_sha256': digest(Path(unknown.__file__).read_bytes()), 'fixture_sha256': digest(STATE.read_bytes()),
            'limited': bool(limit), 'cold_category_table_hex': table.hex(), 'pointer_words_checked': 21, 'cases': cases, 'previews': preview_cases,
            'screens': [s for c in cases+preview_cases for s in c['screens']],
            'scope': 'Original 100-byte item formatter and native glyph/price-column checks for all IDs, selected quantity/enhancement fixtures, every existing unknown-name row, six seven-slot custom-name width fixtures, all grave actors, three special item contexts and two hidden-name properties. Cold category initialization plus explicit state-fixture refresh. Natural naming limits, item acquisition and transaction consequences remain separate.'}
        write_json(session.output/'verification.json', result); print(variant, 'item display passed', len(cases), len(preview_cases), flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('variant', choices=('english', 'japanese', 'baseline')); p.add_argument('--limit', type=int)
    a = p.parse_args(); verify(a.variant, a.limit)
