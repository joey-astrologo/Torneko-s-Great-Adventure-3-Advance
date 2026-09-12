"""Remaining battle messages through native history, scrolls and paged dialogue."""
import argparse
from pathlib import Path
import struct
import mgba.log
from tools import build_battle_completion as b
from tools import verify_core_gameplay as old
from tools import verify_dungeon_interface as ui
from tools import verify_ally_services as service
from tools import verify_tutorial_gameplay as queue
from tools.build_first_label import ORIGINAL_ROM, digest
from tools.game_text import GameTextCodec
from tools.translation_pipeline import FontZero, load_json, check
from tools.verify_expansion import Session
from tools.verify_items import write_json

STATE = service.STATE
BASELINE = b.previous.OUTPUT/'torneko3-dungeon-events-english.gba'


def source(e, variant, report):
    return 0x08000000+(int(e['offset'], 0) if variant == 'baseline' else report['battle']['relocated'][e['id']]['offset'])


def restore(session, caches):
    check(session.core.load_raw_state(STATE.read_bytes()), 'Battle state restore')
    for row in caches: old.write_bytes(session.core, row['ram_start'], bytes.fromhex(row['raw_hex']))


def values(core, font, profile):
    result = queue.set_values(core, font, profile)
    for i in (1, 2):
        result[f'$d{i}'] = '9999' if profile == 'normal' else '-2147483648'; core.memory.u32[old.NUMBER+4*i] = int(result[f'$d{i}']) & 0xffffffff
    if profile == 'stress': core.memory.u16[0x020014CE] = 1; result['$t'] = 'Tipper'
    return result


def entry_case(session, e, variant, report, profile, caches, original, font, codec):
    restore(session, caches); c = session.core; substitutions = values(c, font, profile); at = source(e, variant, report)
    before = bytes(c.memory[old.ITEM:old.ACTOR+90]); trace = ui.InterfaceTrace(c)
    try:
        raw = old.guarded_format(session, trace, at, cap=1000)
        if variant == 'english':
            expected = b.encode(e, original)[0]
            for k, value in substitutions.items(): expected = expected.replace(k.encode(), value.encode())
            check(raw == expected, 'Battle formatted payload differs '+e['id'])
        if e['family'] == 'queue':
            queue.prepare_queue(session, trace); queued = queue.enqueue(session, trace, at, raw if variant == 'english' else None)
            check(len([f for f in trace.formats if f['caller'] == '0x0805D45C']) == len(queued['rows_hex']), 'Battle queue formatter count differs')
        check(bytes(c.memory[old.ITEM:old.ACTOR+90]) == before, 'Battle formatter changed item/actor slots')
    finally: trace.close()
    name = e['id']+'-'+profile
    if e['family'] == 'message':
        result = service.pages(session, at, name, font)
        check(len(result['formats']) == 1 and result['formats'][0]['output_hex'] == raw.hex(), 'Battle paged payload differs')
        if variant == 'english':
            lines = raw[:-1].split(b'\n'); check(len(result['pages']) == (len(lines)+2)//3, 'Incomplete battle dialogue pages')
            for page in result['pages']:
                i = page['page']*3; text = old.visible(b'\n'.join(lines[i:i+3])+b'\0', codec)
                page['checks'] = ui.check_glyphs(page['glyphs'], text, font) if text else {'blank': True}
        result['checks'] = [p['checks'] for p in result['pages']]
    else:
        result = {'queue': queued, 'screens': [], 'checks': []}
        if profile != 'narrow':
            rendered = queue.render_queue(session, name, font, queued['rows_hex'], False)
            if variant == 'english':
                text = ''.join(old.visible(bytes.fromhex(row), codec) for row in queued['rows_hex']); gs = rendered['glyphs']
                check([g['code'] for g in gs] == [font.glyph(c)[0] for c in text], 'Battle queue glyph sequence differs '+e['id'])
                for g, ch in zip(gs, text, strict=True):
                    check(g['font'] == 0 and g['spacing'] == 0 and g['window_width'] == 208 and g['window_height'] == 40, 'Battle queue font/window differs')
                    check(0 <= g['x'] and g['x']+max(g['advance'], font.glyph(ch)[2]) <= 208 and g['y'] in (2, 14, 26, 38), 'Battle queue clipping')
                rendered['checks'] = [{'glyphs': len(gs), 'max_right': max((g['x']+g['advance'] for g in gs), default=0), 'native_scroll_rows_verified': True}]
            result.update(rendered)
        else: result['checks'] = [{'history_payloads_match_queue': True, 'narrow_name_byte_stress': True}]
    result.update(id=e['id'], profile=profile, family=e['family'], formatted_hex=raw.hex(), guards_intact=True, slots_intact=True)
    write_json(session.output/(name+'.json'), result)
    return {k: v for k, v in result.items() if k not in ('pages', 'formats', 'glyphs', 'payloads')} | {'pages': len(result.get('pages', []))}


def selections(session, caches, original):
    c = session.core; cases = []
    for base in (0xDB0FC, 0x9B660):
        for row, entry in enumerate((0x08025278, 0x08025256, 0x08025270)):
            restore(session, caches); result = queue.select_slice(c, entry, entry+2, {'r6': base+0x08000000}, 0)
            expected = c.memory.u32[base+0x08000000+4*row]; check(int(result['source'], 0) == expected, 'Battle obstruction pointer selection differs')
            cases.append({'kind': 'obstruction', 'base': hex(base), 'row': row, **result})
    for row in range(4):
        restore(session, caches); c.memory.u32[0x03007D98] = 4*row
        result = queue.select_slice(c, 0x0805A8BC, 0x0805A8C4, {'sp': 0x03007C00}, 0)
        check(int(result['source'], 0) == c.memory.u32[0x080DB15C+4*row], 'Battle wind pointer selection differs')
        cases.append({'kind': 'wind', 'row': row, **result})
    for group in (0, 1):
        for row in range(4):
            restore(session, caches)
            queue.select_slice(c, 0x08044196, 0x080441A6, {'sp': 0x03007C00}, 0)
            check(bytes(c.memory[0x03007C00:0x03007C20]) == bytes(c.memory[0x080D95E0:0x080D9600]), 'Battle shop table copy differs')
            start, stop = (0x080441C0, 0x080441C6) if group == 0 else (0x080441DE, 0x080441E6)
            result = queue.select_slice(c, start, stop, {'sp': 0x03007C00, 'r5': row}, 1)
            check(int(result['source'], 0) == c.memory.u32[0x080D95E0+4*(row+4*group)], 'Battle shop prompt selection differs')
            cases.append({'kind': 'shop', 'group': group, 'row': row, 'table_copy_intact': True, **result})
    return cases


def verify(variant, limit=None):
    mgba.log.silence(); rom = BASELINE if variant == 'baseline' else b.OUTPUT/f'torneko3-battle-completion-{variant}.gba'
    data = rom.read_bytes(); original = ORIGINAL_ROM.read_bytes(); catalog = load_json(b.OUTPUT/'catalog.json')
    report = {} if variant == 'baseline' else load_json(b.OUTPUT/f'{variant}-build.json'); font = FontZero(original); codec = GameTextCodec(original); cases = []
    with Session(data, b.OUTPUT/'verification'/variant) as session:
        session.frames(600); caches = []
        for a, z in b.INIT_TABLES:
            ram = 0x02000000+a-0xCAFE88; raw = bytes(session.core.memory[ram:ram+z-a]); check(raw == data[a:z], 'Battle cold initialized pointers differ')
            caches.append({'rom_start': a, 'rom_end_exclusive': z, 'ram_start': ram, 'raw_hex': raw.hex()})
        pointers = []
        for e in catalog['entries']:
            for p in e['pointer_owners']:
                at = int(p['offset'], 0); expected = source(e, variant, report); check(session.core.memory.u32[at+0x08000000] == expected, 'Battle pointer owner differs')
                pointers.append({'word': hex(at), 'source': hex(expected)})
        selected = selections(session, caches, original)
        for index, e in enumerate(catalog['entries'][:limit]):
            profiles = ('normal', 'stress', 'narrow') if variant == 'english' and e['family'] == 'queue' else ('normal', 'stress') if variant == 'english' else ('normal',)
            for profile in profiles: cases.append(entry_case(session, e, variant, report, profile, caches, original, font, codec))
            if index%20 == 0: print(variant, index+1, 'battle sources', flush=True)
        result = {'rom_sha256': digest(data), 'source_sha256': digest(original), 'catalog_sha256': digest((b.OUTPUT/'catalog.json').read_bytes()),
            'harness_sha256': digest(Path(__file__).read_bytes()), 'page_helper_sha256': digest(Path(service.__file__).read_bytes()), 'queue_helper_sha256': digest(Path(queue.__file__).read_bytes()), 'fixture_sha256': digest(STATE.read_bytes()),
            'limited': bool(limit), 'cold_tables': caches, 'pointer_words': pointers, 'selections': selected, 'cases': cases, 'screens': [s for c in cases for s in c['screens']],
            'scope': '298 reviewed sources: 247 native queue/history messages with normal/wide/narrow English substitutions, 51 complete paged dialogue sources with normal/stress substitutions, all pointer words, cold initialization and 18 original obstruction/wind/shop selection slices. Natural effects, recruitment, shop transactions and save persistence remain separate.'}
        write_json(session.output/'verification.json', result); print(variant, 'battle completion passed', len(cases), len(result['screens']), flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('variant', choices=('english', 'japanese', 'baseline')); p.add_argument('--limit', type=int)
    a = p.parse_args(); verify(a.variant, a.limit)
