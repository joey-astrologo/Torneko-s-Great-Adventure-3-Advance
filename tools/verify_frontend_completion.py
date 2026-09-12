"""Frontend messages, help pages, real menus and 92-byte log summaries."""
import argparse
from pathlib import Path
import struct
import mgba.log
from tools import build_frontend_completion as b
from tools import verify_church_services as church
from tools import verify_ally_services as service
from tools import verify_core_gameplay as old
from tools import verify_dungeon_interface as ui
from tools import verify_arena_services as arena
from tools import verify_name_entry as names
from tools.build_name_entry import compact_name
from tools.build_first_label import ORIGINAL_ROM, digest
from tools.game_text import GameTextCodec, PRINTF
from tools.translation_pipeline import FontZero, load_json, check
from tools.verify_expansion import Session
from tools.verify_items import write_json

STATE = service.STATE
BASELINE = b.previous.OUTPUT/'torneko3-church-services-english.gba'
SAVEPATH = b.ROOT/'build/completion/results/verification/profile-saves/profile.sav'
RECORD = 0x0203F000


def source(e, variant, report):
    return 0x08000000+(int(e['offset'], 0) if variant == 'baseline' else report['frontend']['relocated'][e['id']]['offset'])


def entry_case(session, e, variant, report, profile, font, codec):
    c = session.core; check(c.load_raw_state(STATE.read_bytes()), 'Frontend page state')
    values = service.set_values(c, font, profile)
    c.memory.u8[0x02004F80] = int(profile == 'stress'); values['$j0'] = '２' if profile == 'stress' else '１'
    # These frontend $d0 fields are the Adventure Log ordinal, always 1 or 2.
    values['$d0'] = '2' if profile == 'stress' else '1'; c.memory.u32[old.NUMBER] = int(values['$d0'])
    at = source(e, variant, report); trace = ui.InterfaceTrace(c); cap = b.encode(e, ORIGINAL_ROM.read_bytes())[1]['capacity']
    try:
        raw_source = old.cstring(c, at); expected = b.encode(e, ORIGINAL_ROM.read_bytes())[0]
        if e['family'] in ('trip', 'stats'):
            trip = (b'Trip -32768' if variant == 'english' else b'-32768') if profile == 'stress' else b''
            old.write_bytes(c, RECORD, trip+b'\0')
            pyargs = (-32768 if profile == 'stress' else 1,) if e['family'] == 'trip' else ((-32768, -32768, 255, trip) if profile == 'stress' else (50, 100, 1, trip))
            args = [RECORD if f == b'%s' else v for f, v in zip(PRINTF.findall(raw_source), pyargs, strict=True)]
            old.write_bytes(c, old.DEST-8, old.GUARD+b'\xA5'*cap+old.GUARD)
            ui.native_step(session, trace, 0x08096744, [old.DEST, at]+args)
            raw = old.cstring(c, old.DEST, cap); expected = expected % pyargs
            check(bytes(c.memory[old.DEST-8:old.DEST]) == old.GUARD and bytes(c.memory[old.DEST+cap:old.DEST+cap+8]) == old.GUARD, 'Frontend printf overrun')
        else:
            raw = old.guarded_format(session, trace, at, cap=cap)
            for key, value in values.items(): expected = expected.replace(key.encode(), value.encode('cp932'))
            expected = expected.replace(b'$+', b'\x03\x12')
        if variant == 'english': check(raw == expected, f'Frontend formatted bytes differ {e["id"]}: {raw!r}/{expected!r}')
    finally:
        trace.close()
    name = e['id']+'-'+profile
    if e['family'] == 'message':
        result = service.pages(session, at, name, font)
        check(len(result['formats']) == 1 and result['formats'][0]['output_hex'] == raw.hex(), 'Frontend page-engine payload differs')
        if variant == 'english':
            lines = raw[:-1].split(b'\n'); check(len(result['pages']) == (len(lines)+2)//3, 'Incomplete frontend pages')
            for page in result['pages']:
                i = page['page']*3; text = old.visible(b'\n'.join(lines[i:i+3])+b'\0', codec)
                page['checks'] = ui.check_glyphs(page['glyphs'], text, font) if text else {'blank': True}
        result['checks'] = [p['checks'] for p in result['pages']]
    else:
        trace = ui.InterfaceTrace(c)
        try:
            ui.native_step(session, trace, 0x0808B60C, [18, 1, 1]); ui.native_step(session, trace, 0x0808BBD8, [0])
            # These separate previews retain bytes; actual menu default handling
            # is verified below through the original typed-menu reader.
            old.write_bytes(c, old.DEST, raw)
            ui.native_step(session, trace, 0x0808CB84, [0, 0, old.DEST, 0, 0]); ui.native_step(session, trace, 0x0808BBF8, [0])
            result = {'glyphs': trace.positions, 'payloads': trace.payloads, 'checks': arena.check_draws(trace, font) if variant == 'english' else [], 'pages': []}
        finally:
            trace.close()
        session.frames(2); session.capture(name); result['screens'] = [name+'.png']
    result.update(id=e['id'], profile=profile, family=e['family'], formatted_hex=raw.hex(), guards_intact=True)
    write_json(session.output/(name+'.json'), result)
    return {k: v for k, v in result.items() if k not in ('pages', 'formats', 'glyphs', 'payloads')} | {'pages': len(result['pages'])}


def menus(session, variant, font):
    c = session.core; records = []; original = ORIGINAL_ROM.read_bytes()
    for base, count, enabled in ((0xC4CD0C, 2, 0), (0xC4CD40, 5, 0), (0xC4CD40, 5, 1)):
        check(c.load_raw_state(STATE.read_bytes()), 'Frontend menu state'); c.memory.u32[0x02002FE4] = enabled
        trace = ui.InterfaceTrace(c)
        try:
            for row in range(count+1):
                at = base+12*row
                check(bytes(c.memory[at+0x08000004:at+0x0800000C]) == original[at+4:at+12], 'Frontend menu flags/return values changed')
            check(c.memory.u32[base+count*12+0x08000000] == 0, 'Frontend menu terminator changed')
            ui.native_step(session, trace, 0x0807B294, [base+0x08000000, 0, 0, 0], stop=0x0807B3B6)
            check(len(trace.payloads) == count, 'Frontend menu row count')
            r = {'base': hex(base), 'enabled': enabled, 'rows': count, 'checks': arena.check_draws(trace, font) if variant == 'english' else [], 'glyphs': trace.positions, 'payloads': trace.payloads}
        finally:
            trace.close()
        name = f'menu-{base:08x}-{enabled}'; session.frames(2); session.capture(name); r['screens'] = [name+'.png']
        write_json(session.output/(name+'.json'), r); records.append({k: v for k, v in r.items() if k not in ('glyphs', 'payloads')})
    return records


def summaries(session, variant, font):
    c = session.core; records = []
    cases = [dict(mode=0, suspended=0, hp=50, max_hp=100, trips=1, level=1),
        dict(mode=0, suspended=0, hp=1023, max_hp=1023, trips=32767, level=99),
        dict(mode=0, suspended=0, hp=-32768, max_hp=-32768, trips=-32768, level=255),
        dict(mode=0, suspended=0, hp=0, max_hp=0, trips=0, level=1),
        dict(mode=0, suspended=1, hp=50, max_hp=100, trips=99, level=1),
        dict(mode=1, suspended=0, hp=50, max_hp=100, trips=99, level=1),
        dict(mode=1, suspended=1, hp=50, max_hp=100, trips=99, level=1)]
    for slot in (0, 1):
        for index, params in enumerate(cases):
            check(c.load_raw_state(STATE.read_bytes()), 'Frontend summary state'); raw = bytearray(184)
            for row in (0, 1):
                p = row*92; raw[p:p+8] = compact_name('Torneko')
                struct.pack_into('<hhh', raw, p+12, params['hp'], params['max_hp'], params['trips'])
                raw[p+20:p+23] = bytes((params['level'], params['suspended'], params['mode']))
            old.write_bytes(c, RECORD-8, old.GUARD+raw+old.GUARD)
            c.memory.u32[0x020105E0] = 0; c.memory.u32[0x020105E4] = 0
            fonts = bytes(c.memory[0x020398EC:0x020398F8]); trace = ui.InterfaceTrace(c)
            try:
                ui.native_step(session, trace, 0x0806C7F8, [0, 1, 1])
                ui.native_step(session, trace, 0x080853E0, [3, 0, RECORD], stop=0x08085718,
                    overrides={0x080853E0: {'sp': 0x03007C00}, 0x080854F8: {'r8': slot}})
                check(bytes(c.memory[RECORD:RECORD+184]) == raw and bytes(c.memory[RECORD-8:RECORD]) == old.GUARD and bytes(c.memory[RECORD+184:RECORD+192]) == old.GUARD, 'Frontend summary changed record/guards')
                check(bytes(c.memory[0x020398EC:0x020398F8]) == fonts, 'Frontend summary changed font state')
                checks = arena.check_draws(trace, font) if variant == 'english' else []
                if variant == 'english':
                    rows = [bytes.fromhex(d['raw_hex']).split(b'\0', 1)[0] for d in trace.payloads if d['y'] == 12 and d['x'] == 16]
                    if params['suspended'] and not params['mode']: expected = b'Not suspended correctly'
                    elif params['suspended'] or not params['max_hp']: expected = b''
                    else:
                        trip = f'Trip {params["trips"]}' if params['trips'] and not params['mode'] else ''
                        expected = f'HP {params["hp"]}/{params["max_hp"]} Lv{params["level"]} {trip}'.encode()
                    check(rows == [expected], 'Native summary composition differs')
                r = {'slot': slot+1, 'parameters': params, 'checks': checks, 'glyphs': trace.positions, 'payloads': trace.payloads, 'formats': trace.formats, 'record_and_guards_intact': True, 'font_tables_intact': True}
            finally:
                trace.close()
            name = f'summary-{slot+1}-{index}'; session.frames(2); session.capture(name); r['screens'] = [name+'.png']
            write_json(session.output/(name+'.json'), r); records.append({k: v for k, v in r.items() if k not in ('glyphs', 'payloads', 'formats')})
    return records


def verify(variant, limit=None):
    mgba.log.silence(); rom = BASELINE if variant == 'baseline' else b.OUTPUT/f'torneko3-frontend-completion-{variant}.gba'
    data = rom.read_bytes(); catalog = load_json(b.OUTPUT/'catalog.json'); original = ORIGINAL_ROM.read_bytes(); font = FontZero(original); codec = GameTextCodec(original)
    report = {} if variant == 'baseline' else load_json(b.OUTPUT/f'{variant}-build.json'); cases = []
    with Session(data, b.OUTPUT/'verification'/variant) as session:
        for index, e in enumerate(catalog['entries'][:limit]):
            for profile in ('normal', 'stress') if variant == 'english' else ('normal',):
                cases.append(entry_case(session, e, variant, report, profile, font, codec))
            if index%10 == 0: print(variant, index+1, 'frontend sources', flush=True)
        menu_cases = [] if limit else menus(session, variant, font)
        summary_cases = [] if limit else summaries(session, variant, font)
        result = {'rom_sha256': digest(data), 'source_sha256': digest(original), 'catalog_sha256': digest((b.OUTPUT/'catalog.json').read_bytes()),
            'harness_sha256': digest(Path(__file__).read_bytes()), 'page_helper_sha256': digest(Path(service.__file__).read_bytes()), 'fixture_sha256': digest(STATE.read_bytes()),
            'limited': bool(limit), 'cases': cases, 'menus': menu_cases, 'summaries': summary_cases,
            'screens': [s for c in cases+menu_cases+summary_cases for s in c['screens']],
            'scope': 'Controlled original formatter and complete paged messages/help, typed menu flags/defaults/return values, and original 92-byte log summary reader with both slots and stated field bounds. Natural mode transitions and save recovery consequences remain separate.'}
        write_json(session.output/'verification.json', result); print(variant, 'frontend passed', len(cases), len(result['screens']), flush=True)
    if variant == 'english' and not limit:
        save = SAVEPATH.read_bytes(); loads = []
        for slot in (1, 2):
            names.reload_name(data, save, b.OUTPUT/f'verification/cold-load-{slot}', compact_name('Torneko'), slot, select_slot=slot == 2)
            loads.append({'slot': slot, 'seven_character_name': 'Torneko', 'passed': True})
        write_json(b.OUTPUT/'verification/cold-loads.json', {'rom_sha256': digest(data), 'save_sha256': digest(save), 'harness_sha256': digest(Path(__file__).read_bytes()), 'name_helper_sha256': digest(Path(names.__file__).read_bytes()), 'loads': loads})
        print('Both frontend Adventure Log cold loads passed', flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('variant', choices=('english', 'japanese', 'baseline')); p.add_argument('--limit', type=int)
    a = p.parse_args(); verify(a.variant, a.limit)
