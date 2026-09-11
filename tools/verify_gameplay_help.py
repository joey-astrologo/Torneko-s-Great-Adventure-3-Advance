"""Native help pages, status records, order menu and gameplay message fixtures."""
import argparse
from collections import Counter
from pathlib import Path
import struct

import mgba.log
from PIL import ImageChops, Image
from tools import verify_core_gameplay as old
from tools import verify_dungeon_interface as ui
from tools.build_gameplay_help import CATALOG, OUTPUT, encode
from tools.build_first_label import ORIGINAL_ROM, digest
from tools.game_text import GameTextCodec
from tools.translation_pipeline import FontZero, load_json
from tools.verify_expansion import Session
from tools.verify_first_label import require
from tools.verify_items import write_json

STATE = Path('build/core-gameplay/verification/save/world.state')
BASELINE = Path('build/core-gameplay/torneko3-core-gameplay-english.gba')


def source_for(entry, variant, report):
    return (int(entry['offset'], 0) if variant == 'baseline' else
            report['help']['relocated'][entry['id']]['offset']) + 0x08000000


def values_for(core, font, profile):
    values = old.slots(core, font, profile)
    for i in (1, 2):
        values[f'$d{i}'] = '9999' if profile == 'normal' else '-2147483648'
        core.memory.u32[old.NUMBER+4*i] = int(values[f'$d{i}']) & 0xffffffff
    return values


def entry_case(session, state, entry, variant, report, folder, font, codec, profile):
    require(session.core.load_raw_state(state), 'State restore failed')
    core = session.core; values = values_for(core, font, profile)
    source = source_for(entry, variant, report); family = entry['family']
    english = variant == 'english'
    if family == 'help' and profile == 'stress':
        core.memory.u16[0x020014CE] = 1; values['$t'] = 'Tipper'
    trace = ui.InterfaceTrace(core); trace.phase = family
    try:
        cap = {'help': 512, 'status': 64, 'message': 1000}[family]
        raw = old.guarded_format(session, trace, source, cap=cap)
        if english:
            _, metric = encode(entry, ORIGINAL_ROM.read_bytes())
            expected = old.expanded(metric['display_template'], values)
            require(raw == expected.encode()+b'\0', f'Substitution mismatch: {entry["id"]}')
        if family == 'message':
            result = ui.native_step(session, trace, 0x0807ADA4, [source, 0, 0, 0, 0, 0, 0],
                stop=0x0807B044, overrides={0x0807AF76: {'r4': 0}})
            formats = [f for f in trace.formats if f['caller'] == '0x0807AE04']
        elif family == 'help':
            result = ui.native_step(session, trace, 0x08078450, [entry['row']+9, 0], stop=0x08078492)
            formats = [f for f in trace.formats if f['caller'] == '0x0807847A']
            # The original caller enables the completed window after its
            # opening animation, before waiting for A/B.
            ui.native_step(session, trace, 0x0808BB14, [0])
        else:
            ui.native_step(session, trace, 0x0808B60C, [19, 1, 1])
            old.write_bytes(core, 0x02008968, b'\0'*256)
            if 'row' in entry:
                row = entry['row']; dest = 0x02007968+64*row
                old.write_bytes(core, dest-8, old.GUARD+b'\xA5'*64+old.GUARD)
                # Select one table row without inventing a combination of
                # game status flags. Original indexing/formatting/list writes
                # execute; skip the condition switch and finish after one row.
                result = ui.native_step(session, trace, 0x0805E1E0, [], overrides={
                    0x0805E1FE: {'r9': row, 'r10': 64},
                    0x0805E6D6: {'r6': 1}, 0x0805E702: {'r9': 63}})
                require(core.memory.u32[0x02008968] == dest, 'Status list pointer mismatch')
                require(old.cstring(core, dest, 64) == raw, 'Status record truncated or changed')
                # Row 63 ends exactly at the active-pointer list. Its first
                # word is intentionally written by this same native routine.
                after = struct.pack('<I', dest)+old.GUARD[4:] if row == 63 else old.GUARD
                require(bytes(core.memory[dest-8:dest]) == old.GUARD and
                        bytes(core.memory[dest+64:dest+72]) == after, 'Status neighbour overwritten')
                if row == 63: old.write_bytes(core, 0x0200896C, b'\0'*252)
                formats = [f for f in trace.formats if f['caller'] == '0x0805E6F0']
            else:
                # Conditional shop/fallback literals: direct bounded formatter
                # plus the real status row renderer; not shop-condition coverage.
                core.memory.u32[0x02008968] = old.DEST
                result = {'fixture': 'conditional_status_literal'}
                formats = []
            ui.native_step(session, trace, 0x0805DFA8, [])
        if formats:
            require(len(formats) == 1 and int(formats[0]['source'], 0) == source and
                    formats[0]['output_hex'] == raw.hex(), 'Native reader selected another payload')
        else: require(family == 'status' and 'row' not in entry, f'Expected reader was not reached: {family}/{trace.formats}')
        checks = ui.check_glyphs(trace.positions, expected, font) if english else {}
        record = {'id': entry['id'], 'family': family, 'profile': profile, 'source': hex(source),
                  'guarded_capacity': cap, 'formatted_hex': raw.hex(), 'checks': checks,
                  'native': result, 'formats': formats, 'glyphs': trace.positions}
    finally: trace.close()
    session.frames(2); name = f'{entry["id"]}-{profile}'
    session.capture(name); write_json(folder/(name+'.json'), record)
    return record


def orders_case(session, state, entries, variant, report, folder, font):
    require(session.core.load_raw_state(state), 'State restore failed')
    trace = ui.InterfaceTrace(session.core); trace.phase = 'orders'
    try:
        guards = []
        for e in entries:
            raw = old.guarded_format(session, trace, source_for(e, variant, report), cap=30)
            if variant == 'english': require(raw == e['english'].encode()+b'\0', 'Order copy differs')
            guards.append({'id': e['id'], 'bytes': len(raw), 'capacity': 30})
        result = ui.native_step(session, trace, 0x08072A78, [0, 0], stop=0x08072B86,
            overrides={0x08072AD2: {'r0': 99}, 0x08072AEE: {'r0': 99}})
        require(len(trace.payloads) == 7, f'Expected all seven order rows, got {len(trace.payloads)}')
        checks = []
        for e, draw in zip(entries, trace.payloads, strict=True):
            require(int(draw['source'], 0) == source_for(e, variant, report), 'Order table reader mismatch')
            if variant == 'english':
                glyphs = [g for g in trace.positions if g['draw_serial'] == draw['serial']]
                checks.append(ui.check_glyphs(glyphs, e['english'], font))
        record = {'guards': guards, 'checks': checks, 'native': result, 'payloads': trace.payloads}
    finally: trace.close()
    session.frames(2); session.capture('orders'); write_json(folder/'orders.json', record)
    return record


def verify(variant='english', limit=None):
    mgba.log.silence()
    rom = BASELINE if variant == 'baseline' else OUTPUT/f'torneko3-gameplay-help-{variant}.gba'
    folder = OUTPUT/'verification'/variant; folder.mkdir(parents=True, exist_ok=True)
    state = STATE.read_bytes()
    with Session(rom.read_bytes(), folder) as session:
        original = ORIGINAL_ROM.read_bytes(); font = FontZero(original); codec = GameTextCodec(original)
        catalog = load_json(CATALOG)
        report = {} if variant == 'baseline' else load_json(OUTPUT/f'{variant}-build.json')
        checks = []; counts = Counter()
        for entry in catalog['entries']:
            family = entry['family']
            if family == 'order' or limit and counts[family] >= limit: continue
            profiles = ('normal', 'stress') if variant == 'english' else ('normal',)
            for profile in profiles:
                checks.append(entry_case(session, state, entry, variant, report, folder, font, codec, profile))
            counts[family] += 1
            if len(checks) % 20 < 2: print(variant, dict(counts), flush=True)
        orders = orders_case(session, state, sorted((e for e in catalog['entries'] if e['family']=='order'), key=lambda e:e['row']), variant, report, folder, font)
        result = {'rom_sha256': digest(rom.read_bytes()), 'catalog_sha256': digest(CATALOG.read_bytes()),
                  'limited': bool(limit), 'counts': dict(counts), 'screens': len(checks)+1,
                  'cases': [{k:v for k,v in c.items() if k not in ('glyphs','formats')} for c in checks], 'orders': orders,
                  'scope': 'Native help reader, forced single-row status table reader and actual status renderer, all-order menu with level-99 fixture, bounded message engine with maximum substitutions. These fixtures do not trigger every natural effect, ally action or shop condition.'}
        write_json(folder/'verification.json', result)
        print(variant, 'passed', result['screens'], flush=True)
        return result


def compare():
    japanese = OUTPUT/'verification/japanese'; baseline = OUTPUT/'verification/baseline'
    a = load_json(japanese/'verification.json'); b = load_json(baseline/'verification.json')
    require(not a['limited'] and not b['limited'], 'Limited controls')
    names = [f'{c["id"]}-{c["profile"]}.png' for c in a['cases']] + ['orders.png']
    for name in names:
        with Image.open(japanese/name) as x, Image.open(baseline/name) as y:
            require(ImageChops.difference(x.convert('RGB'), y.convert('RGB')).getbbox() is None, f'Japanese control changed: {name}')
    result = {'pixel_pairs': len(names), 'japanese_sha256': a['rom_sha256'], 'baseline_sha256': b['rom_sha256']}
    write_json(OUTPUT/'verification/japanese-control.json', result)
    return result


def natural_routes(variant):
    mgba.log.silence()
    rom = BASELINE if variant == 'baseline' else OUTPUT/f'torneko3-gameplay-help-{variant}.gba'
    report = {} if variant == 'baseline' else load_json(OUTPUT/f'{variant}-build.json')
    folder = OUTPUT/'verification/natural'/variant
    entries = load_json(CATALOG)['entries']
    expected_entries = [next(e for e in entries if e['family']=='help' and e['row']==row) for row in (0,4)]
    with Session(rom.read_bytes(), folder) as session:
        require(session.core.load_raw_state(STATE.read_bytes()), 'Cannot restore world')
        trace = ui.InterfaceTrace(session.core)
        try:
            keys = ('B','RIGHT','DOWN','A','DOWN','A','A','B','DOWN','A','B','B')
            for i, key in enumerate(keys):
                trace.phase = str(i); session.press(key,100,trace); session.capture(f'route-{i:02d}')
            formats = [f for f in trace.formats if f['caller']=='0x0807847A']
            require([int(f['source'],0) for f in formats] == [source_for(e,variant,report) for e in expected_entries],
                    'Natural help navigation selected other pages')
            if variant == 'english':
                font = FontZero(ORIGINAL_ROM.read_bytes())
                for e, f in zip(expected_entries, formats, strict=True):
                    raw = bytes.fromhex(f['output_hex'])
                    require(raw == encode(e, ORIGINAL_ROM.read_bytes())[0], 'Natural help text differs')
                    glyphs = [g for g in trace.positions if g['phase']==f['phase']]
                    ui.check_glyphs(glyphs,e['english'],font)
            require(not trace.errors, 'Natural trace failed')
            result = {'rom_sha256':digest(rom.read_bytes()),'catalog_sha256':digest(CATALOG.read_bytes()),
                      'inputs':list(keys),'help_pages':[e['id'] for e in expected_entries], 'screens':len(keys),
                      'formats':formats,'scope':'Unmodified button route: Tactics > How to play, world controls, B return, multiple-item transfer help, B return.'}
            write_json(folder/'verification.json',result)
        finally: trace.close()
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('variant', choices=('english', 'japanese', 'baseline', 'compare', 'routes'), nargs='?', default='english')
    p.add_argument('--limit', type=int)
    args = p.parse_args()
    if args.variant == 'routes':
        for variant in ('english','japanese','baseline'): natural_routes(variant)
    elif args.variant == 'compare': compare()
    else: verify(args.variant, args.limit)
