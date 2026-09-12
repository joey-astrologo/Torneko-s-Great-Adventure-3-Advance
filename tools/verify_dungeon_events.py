"""Complete dungeon-event pages, native lookups, pause menu and text selection."""
import argparse
from pathlib import Path
import struct
import mgba.log
from tools import build_dungeon_events as b
from tools import verify_core_gameplay as old
from tools import verify_dungeon_interface as ui
from tools import verify_ally_services as service
from tools import verify_arena_services as arena
from tools.build_first_label import ORIGINAL_ROM, digest
from tools.game_text import GameTextCodec
from tools.translation_pipeline import FontZero, load_json, check
from tools.verify_expansion import Session
from tools.verify_items import write_json

STATE = service.STATE
BASELINE = b.previous.OUTPUT/'torneko3-item-display-english.gba'


def source(e, variant, report):
    return 0x08000000+(int(e['offset'], 0) if variant == 'baseline' else report['dungeon_events']['relocated'][e['id']]['offset'])


def entry_case(session, e, variant, report, profile, font, codec):
    c = session.core; check(c.load_raw_state(STATE.read_bytes()), 'Dungeon event page state')
    values = service.set_values(c, font, profile)
    if profile == 'stress': c.memory.u16[0x020014CE] = 1; values['$t'] = 'Tipper'
    at = source(e, variant, report); trace = ui.InterfaceTrace(c)
    try:
        raw = old.guarded_format(session, trace, at, cap=b.encode(e, ORIGINAL_ROM.read_bytes())[1]['capacity'])
        if variant == 'english':
            expected = b.encode(e, ORIGINAL_ROM.read_bytes())[0]
            for key, value in values.items(): expected = expected.replace(key.encode(), value.encode())
            expected = expected.replace(b'$+', b'\x03\x12')
            check(raw == expected, 'Dungeon event formatted bytes differ '+e['id'])
    finally: trace.close()
    name = e['id']+'-'+profile
    if e['family'] == 'message':
        result = service.pages(session, at, name, font)
        check(len(result['formats']) == 1 and result['formats'][0]['output_hex'] == raw.hex(), 'Dungeon event page-engine payload differs')
        if variant == 'english':
            lines = raw[:-1].split(b'\n'); check(len(result['pages']) == (len(lines)+2)//3, 'Incomplete dungeon event pages')
            for page in result['pages']:
                i = page['page']*3; text = old.visible(b'\n'.join(lines[i:i+3])+b'\0', codec)
                page['checks'] = ui.check_glyphs(page['glyphs'], text, font) if text else {'blank': True}
        result['checks'] = [p['checks'] for p in result['pages']]
    else:
        trace = ui.InterfaceTrace(c)
        try:
            ui.native_step(session, trace, 0x0808B60C, [18, 1, 1]); ui.native_step(session, trace, 0x0808BBD8, [0])
            old.write_bytes(c, old.DEST, raw)
            ui.native_step(session, trace, 0x0808CB84, [0, 0, old.DEST, 0, 0]); ui.native_step(session, trace, 0x0808BBF8, [0])
            result = {'glyphs': trace.positions, 'payloads': trace.payloads, 'checks': arena.check_draws(trace, font) if variant == 'english' else [], 'pages': []}
        finally: trace.close()
        session.frames(2); session.capture(name); result['screens'] = [name+'.png']
    result.update(id=e['id'], profile=profile, family=e['family'], formatted_hex=raw.hex(), guards_intact=True)
    write_json(session.output/(name+'.json'), result)
    return {k: v for k, v in result.items() if k not in ('pages', 'formats', 'glyphs', 'payloads')} | {'pages': len(result['pages'])}


def selection(session, catalog, variant, report, cache, original):
    c = session.core; by_at = {int(e['offset'], 0): e for e in catalog['entries']}; words = []; lookups = []; selectors = []
    for e in catalog['entries']:
        for p in e['pointer_owners']:
            expected = source(e, variant, report); word = int(p['offset'], 0)
            check(c.memory.u32[word+0x08000000] == expected, 'Dungeon event pointer owner differs')
            words.append({'word': hex(word), 'target': hex(expected)})
    for row in range(31):
        check(c.load_raw_state(STATE.read_bytes()), 'Dungeon tutorial lookup state')
        key, before = struct.unpack_from('<II', original, b.KEYS+8*row); at = b.KEYS+8*row+0x08000000
        check(c.memory.u32[at] == key, 'Dungeon tutorial identifier changed')
        trace = ui.InterfaceTrace(c)
        try:
            r = ui.native_step(session, trace, 0x0807DC98, [key, b.KEYS+0x08000000])
            expected = source(by_at[before-0x08000000], variant, report)
            check(r['return_r0'] == expected, 'Dungeon tutorial native lookup differs')
            lookups.append({'row': row, 'key': hex(key), 'target': hex(expected)})
        finally: trace.close()
    check(bytes(c.memory[b.KEYS_END-8+0x08000000:b.KEYS_END+0x08000000]) == bytes(8), 'Dungeon tutorial terminator changed')
    for hero in (0, 1):
        for seen in (0, 1):
            check(c.load_raw_state(STATE.read_bytes()), 'Boss selector state')
            c.memory.u8[0x02004FF4] = hero; c.memory.u8[0x02005EE0] = (1 << hero) if seen else 0
            trace = ui.InterfaceTrace(c)
            try:
                saved = service.context(c)
                try:
                    ui.registers(c, {'cpsr': 0xff, 'r4': 0, 'pc': 0x08008616})
                    for steps in range(100):
                        if int(trace.cpu.gprs[15])-2 == 0x08008690: break
                        c.step()
                    else: raise AssertionError('Boss text-selection slice did not finish')
                    actual = [int(trace.cpu.gprs[i]) & 0xffffffff for i in (4, 7)]
                finally: ui.registers(c, saved)
                first, second = ((0, 0xA44FC) if seen else (0xA43C4, 0xA4440)) if hero else ((0, 0xA42F8) if seen else (0xA4108, 0xA4210))
                expected = [source(by_at[a], variant, report) if a else 0 for a in (first, second)]
                check(actual == expected, 'Boss first/repeat text selection differs')
            finally: trace.close()
            selectors.append({'kind': 'boss', 'hero': hero, 'seen': seen, 'expected': expected, 'actual': actual})
    for hero in (0, 1):
        check(c.load_raw_state(STATE.read_bytes()), 'Arena abort selector state'); old.write_bytes(c, 0x02000028, cache); c.memory.u8[0x02009264] = hero
        trace = ui.InterfaceTrace(c)
        try:
            r = ui.native_step(session, trace, 0x08008534, [], stop=0x0800853E, overrides={0x08008534: {'r7': 0x02000028}})
            expected = int.from_bytes(cache[hero*4:hero*4+4], 'little'); check(r['return_r0'] == expected, 'Arena abort selector differs')
            selectors.append({'kind': 'arena_abort', 'hero': hero, 'target': hex(expected)})
        finally: trace.close()
    return words, lookups, selectors


def menu(session, variant, font, original):
    c = session.core; check(c.load_raw_state(STATE.read_bytes()), 'Dungeon pause-menu state'); trace = ui.InterfaceTrace(c)
    try:
        for row in range(3):
            at = b.MENU+row*12
            check(bytes(c.memory[at+0x08000004:at+0x0800000C]) == original[at+4:at+12], 'Arena pause menu fields changed')
        check(c.memory.u32[b.MENU+24+0x08000000] == 0, 'Arena pause menu terminator changed')
        ui.native_step(session, trace, 0x0807B294, [b.MENU+0x08000000, 0, 0, 0], stop=0x0807B3B6)
        check(len(trace.payloads) == 2, 'Arena pause menu row count differs')
        r = {'checks': arena.check_draws(trace, font) if variant == 'english' else [], 'glyphs': trace.positions, 'payloads': trace.payloads, 'original_menu_fields_preserved': True}
    finally: trace.close()
    session.frames(2); session.capture('arena-pause-menu'); r['screens'] = ['arena-pause-menu.png']; write_json(session.output/'arena-pause-menu.json', r)
    return {k: v for k, v in r.items() if k not in ('glyphs', 'payloads')}


def verify(variant, limit=None):
    mgba.log.silence(); rom = BASELINE if variant == 'baseline' else b.OUTPUT/f'torneko3-dungeon-events-{variant}.gba'
    data = rom.read_bytes(); original = ORIGINAL_ROM.read_bytes(); catalog = load_json(b.OUTPUT/'catalog.json')
    report = {} if variant == 'baseline' else load_json(b.OUTPUT/f'{variant}-build.json'); font = FontZero(original); codec = GameTextCodec(original); cases = []
    with Session(data, b.OUTPUT/'verification'/variant) as session:
        session.frames(600); cache = bytes(session.core.memory[0x02000028:0x02000030])
        check(cache == data[b.CACHE:b.CACHE_END], 'Cold arena abort initialization differs')
        words, lookups, selectors = selection(session, catalog, variant, report, cache, original)
        for index, e in enumerate(catalog['entries'][:limit]):
            for profile in ('normal', 'stress') if variant == 'english' else ('normal',): cases.append(entry_case(session, e, variant, report, profile, font, codec))
            if index%10 == 0: print(variant, index+1, 'dungeon event sources', flush=True)
        menus = [] if limit else [menu(session, variant, font, original)]
        result = {'rom_sha256': digest(data), 'source_sha256': digest(original), 'catalog_sha256': digest((b.OUTPUT/'catalog.json').read_bytes()),
            'harness_sha256': digest(Path(__file__).read_bytes()), 'page_helper_sha256': digest(Path(service.__file__).read_bytes()), 'fixture_sha256': digest(STATE.read_bytes()),
            'limited': bool(limit), 'cold_abort_table_hex': cache.hex(), 'pointer_words': words, 'lookups': lookups, 'selectors': selectors, 'cases': cases, 'menus': menus,
            'screens': [s for c in cases+menus for s in c['screens']],
            'scope': 'All 63 sources through original formatter and complete paged engine, 31 native tutorial key lookups, four boss and two arena-abort selector slices, cold abort cache and original two-row menu. Restored-state fixtures explicitly refresh caches. Natural boss/rescue outcomes, arena forfeits and tutorial triggers remain separate.'}
        write_json(session.output/'verification.json', result); print(variant, 'dungeon events passed', len(cases), len(result['screens']), flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('variant', choices=('english', 'japanese', 'baseline')); p.add_argument('--limit', type=int)
    a = p.parse_args(); verify(a.variant, a.limit)
