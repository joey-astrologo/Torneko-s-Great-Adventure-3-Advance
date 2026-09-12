"""Complete church pages and original positional source-selection paths."""
import argparse
from pathlib import Path
import struct
import mgba.log
from PIL import Image, ImageChops
from tools import build_church_services as b
from tools import verify_core_gameplay as old
from tools import verify_dungeon_interface as ui
from tools import verify_ally_services as service
from tools.build_first_label import ORIGINAL_ROM, digest
from tools.game_text import GameTextCodec
from tools.translation_pipeline import FontZero, load_json, check
from tools.verify_expansion import Session
from tools.verify_items import write_json

STATE = service.STATE
BASELINE = b.previous.OUTPUT/'torneko3-adventure-results-english.gba'


def source(e, variant, report):
    return 0x08000000+(int(e['offset'], 0) if variant == 'baseline' else report['church']['relocated'][e['id']]['offset'])


def selection(session, variant, report, catalog):
    c = session.core; original = ORIGINAL_ROM.read_bytes()
    entries = {int(e['offset'], 0): e for e in catalog['entries']}
    check(c.load_raw_state(STATE.read_bytes()), 'Church table state')
    words = []
    for word in range(b.TABLE, b.END, 4):
        before = struct.unpack_from('<I', original, word)[0]; e = entries.get(before-0x08000000)
        expected = source(e, variant, report) if e else before
        check(c.memory.u32[word+0x08000000] == expected, 'Church table pointer differs')
        words.append({'word': hex(word), 'source': hex(expected), 'translated_prose': bool(e)})
    cases = []
    for kind, types in (('greeting', (0, 1, 4)), ('save_prompt', range(5)), ('oracle_next', (0, 1, 4)), ('oracle_max', (0, 1, 4))):
        for church_type in types:
            check(c.load_raw_state(STATE.read_bytes()), 'Church selector state')
            c.memory.u32[0x020091C0] = church_type
            trace = ui.InterfaceTrace(c)
            try:
                if kind == 'greeting':
                    r = ui.native_step(session, trace, 0x080787F4, [0, church_type, 0], stop=0x08078842); slot = 0
                elif kind == 'save_prompt':
                    r = ui.native_step(session, trace, 0x0807ABF8, [0, 0x08000000+b.TABLE+church_type*b.STRIDE, 0], stop=0x0807AC14); slot = 2
                else:
                    entry = 0x0807894C if kind == 'oracle_next' else 0x08078968
                    r = ui.native_step(session, trace, entry, [], stop=0x08078978); slot = 8 if kind == 'oracle_next' else 9
                word = b.TABLE+church_type*b.STRIDE+slot*4
                check(r['return_r0'] == c.memory.u32[word+0x08000000], 'Native church selected wrong source')
                cases.append({'kind': kind, 'church_type': church_type, 'slot': slot, 'word': hex(word), 'native_source': hex(r['return_r0'])})
            finally:
                trace.close()
    return words, cases


def verify(variant, limit=None):
    mgba.log.silence()
    rom = BASELINE if variant == 'baseline' else b.OUTPUT/f'torneko3-church-services-{variant}.gba'
    catalog = load_json(b.OUTPUT/'catalog.json'); original = ORIGINAL_ROM.read_bytes()
    report = {} if variant == 'baseline' else load_json(b.OUTPUT/f'{variant}-build.json')
    font = FontZero(original); codec = GameTextCodec(original); cases = []
    with Session(rom.read_bytes(), b.OUTPUT/'verification'/variant) as session:
        words, selectors = selection(session, variant, report, catalog)
        for index, e in enumerate(catalog['entries'][:limit]):
            for profile in ('normal', 'stress') if variant == 'english' else ('normal',):
                c = session.core; check(c.load_raw_state(STATE.read_bytes()), 'Church page state')
                values = service.set_values(c, font, profile)
                if profile == 'stress': c.memory.u16[0x020014CE] = 1; values['$t'] = 'Tipper'
                at = source(e, variant, report); trace = ui.InterfaceTrace(c)
                try:
                    raw = old.guarded_format(session, trace, at, cap=1000)
                    if variant == 'english':
                        expected = b.encode(e, original)[0]
                        for key, value in values.items(): expected = expected.replace(key.encode(), value.encode())
                        expected = expected.replace(b'$+', b'\x03\x12')
                        check(raw == expected, f'Church formatted bytes differ {e["id"]}: {raw!r}/{expected!r}')
                finally:
                    trace.close()
                name = e['id']+'-'+profile
                result = service.pages(session, at, name, font)
                check(len(result['formats']) == 1 and result['formats'][0]['output_hex'] == raw.hex(), 'Church page-engine payload differs')
                if variant == 'english':
                    lines = raw[:-1].split(b'\n')
                    check(len(result['pages']) == (len(lines)+2)//3, 'Incomplete church pages')
                    for page in result['pages']:
                        i = page['page']*3
                        text = old.visible(b'\n'.join(lines[i:i+3])+b'\0', codec)
                        page['checks'] = ui.check_glyphs(page['glyphs'], text, font) if text else {'blank': True}
                result.update(id=e['id'], profile=profile, formatted_hex=raw.hex(), guards_intact=True)
                write_json(session.output/(name+'.json'), result)
                cases.append({k: value for k, value in result.items() if k not in ('pages', 'formats')} | {'pages': len(result['pages']), 'checks': [p['checks'] for p in result['pages']]})
            if index%10 == 0: print(variant, index+1, 'church sources', flush=True)
        result = {'rom_sha256': digest(rom.read_bytes()), 'source_sha256': digest(original),
            'catalog_sha256': digest((b.OUTPUT/'catalog.json').read_bytes()), 'fixture_sha256': digest(STATE.read_bytes()),
            'harness_sha256': digest(Path(__file__).read_bytes()), 'page_helper_sha256': digest(Path(service.__file__).read_bytes()),
            'limited': bool(limit), 'table_words': words, 'native_selections': selectors, 'cases': cases,
            'screens': [s for c in cases for s in c['screens']],
            'scope': 'Every church prose source through the original formatter and complete paged service engine; all 105 table words including unchanged placeholders; 14 native greeting/save/oracle source selections. Type and substitution fixtures are controlled. Natural access, oracle game state, transactions and accepting save prompts remain separate.'}
        write_json(session.output/'verification.json', result)
        print(variant, 'church passed', len(cases), len(result['screens']), flush=True)


def summarize():
    original = ORIGINAL_ROM.read_bytes(); baseline = BASELINE.read_bytes(); out = b.OUTPUT
    catalog = load_json(out/'catalog.json'); check((out/'catalog.json').read_bytes() == b.CATALOG.read_bytes(), 'Church catalog changed')
    prior = load_json(BASELINE.parent/'english-build.json')['ledger']; end = max(a['offset']+a['bytes'] for a in prior['allocations']); proofs = {}
    for variant in ('english', 'japanese', 'baseline'):
        path = out/'verification'/variant/'verification.json'; r = load_json(path)
        data = baseline if variant == 'baseline' else (out/f'torneko3-church-services-{variant}.gba').read_bytes()
        check(r['rom_sha256'] == digest(data) and r['source_sha256'] == digest(original), 'Church proof ROM mismatch')
        check(r['catalog_sha256'] == digest((out/'catalog.json').read_bytes()) and r['harness_sha256'] == digest((out/'verify_church_services.py').read_bytes()), 'Church proof input mismatch')
        check(r['fixture_sha256'] == digest(STATE.read_bytes()) and r['page_helper_sha256'] == digest(Path(service.__file__).read_bytes()), 'Church fixture/helper changed')
        expected = {(e['id'], p) for e in catalog['entries'] for p in (('normal', 'stress') if variant == 'english' else ('normal',))}
        check(not r['limited'] and len(r['cases']) == len(expected) and {(c['id'], c['profile']) for c in r['cases']} == expected, 'Incomplete church cases')
        check(len(r['table_words']) == 105 and {int(w['word'], 0) for w in r['table_words']} == set(range(b.TABLE, b.END, 4)), 'Missing church table word')
        expected_selectors = {(kind, t) for kind in ('greeting', 'save_prompt', 'oracle_next', 'oracle_max') for t in (range(5) if kind == 'save_prompt' else (0, 1, 4))}
        check(len(r['native_selections']) == 14 and {(c['kind'], c['church_type']) for c in r['native_selections']} == expected_selectors, 'Missing church selection')
        check(all(c['guards_intact'] and c['pages'] == len(c['screens']) for c in r['cases']), 'Incomplete church page/guard evidence')
        check(r['screens'] == [s for c in r['cases'] for s in c['screens']] and len(set(r['screens'])) == len(r['screens']), 'Church screen inventory differs')
        check(all((path.parent/s).is_file() for s in r['screens']), 'Church screenshot missing')
        if variant == 'english': check(all(c['checks'] and all(c['checks']) for c in r['cases']), 'Missing church glyph checks')
        if variant != 'baseline':
            report = load_json(out/f'{variant}-build.json'); check(report['previous_rom_sha256'] == digest(baseline), 'Church baseline differs')
            ledger = report['ledger']; rebuilt = bytearray(original+b'\xff'*(len(data)-len(original)))
            for a in ledger['allocations']:
                at = a['offset']; raw = data[at:at+a['bytes']]; check(digest(raw) == a['sha256'], 'Church allocation differs'); rebuilt[at:at+len(raw)] = raw
            for p in ledger['patches']:
                at = p['offset']; before = bytes.fromhex(p['before']); after = bytes.fromhex(p['after']); check(rebuilt[at:at+len(before)] == before, 'Church patch source differs'); rebuilt[at:at+len(after)] = after
            check(bytes(rebuilt) == data and data[0x1000000:end] == baseline[0x1000000:end], 'Unexplained church image changes')
            for p in prior['patches']:
                at = p['offset']; after = bytes.fromhex(p['after']); check(data[at:at+len(after)] == after, 'Earlier church-base patch changed')
            for s in ledger['protected_sources']: check(data[s['start']:s['end_exclusive']] == original[s['start']:s['end_exclusive']], 'Protected Japanese source changed')
        proofs[variant] = {'rom_sha256': digest(data), 'report_sha256': digest(path.read_bytes()), 'cases': len(r['cases']), 'pages': len(r['screens'])}
    a = load_json(out/'verification/japanese/verification.json'); z = load_json(out/'verification/baseline/verification.json')
    check(a['screens'] == z['screens'], 'Church Japanese screenshot sets differ')
    for name in a['screens']:
        with Image.open(out/'verification/japanese'/name) as x, Image.open(out/'verification/baseline'/name) as y:
            check(ImageChops.difference(x.convert('RGB'), y.convert('RGB')).getbbox() is None, 'Church Japanese pixels differ '+name)
    result = {'status': 'church_component_native_checks_passed', 'sources': 62, 'pointer_words': 70, 'table_words_checked': 105,
        'native_selections_per_variant': 14, 'english_cases': 124, 'japanese_pixel_pairs': len(a['screens']), 'proofs': proofs,
        'complete_images_reconstructed_from_ledgers': True, 'previous_patches_and_appended_bytes_preserved': True,
        'scope': a['scope']}
    write_json(out/'component-checkpoint.json', result); print(result['status'], len(a['screens']), 'Japanese pixel pairs', flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('variant', choices=('english', 'japanese', 'baseline', 'summarize')); p.add_argument('--limit', type=int)
    a = p.parse_args(); summarize() if a.variant == 'summarize' else verify(a.variant, a.limit)
