"""Verify the tutorial correction through normal pickup, menus and pot use."""
import json
from pathlib import Path
import mgba.log
from mgba._pylib import ffi
from PIL import Image, ImageChops
from tools import build_text_polish as b
from tools.build_first_label import ROOT, ORIGINAL_ROM, digest
from tools.translation_pipeline import check, load_json, atomic_write, FontZero
from tools.game_text import GameTextCodec
from tools.verify_expansion import Session
from tools.verify_natural_cave import CaveTrace, sources
from tools.verify_core_gameplay import visible, command_ink_check
from tools.verify_items import distinct_glyph_observations, coalesce_empty_draw_observations


def save(path, value):
    atomic_write(path, (json.dumps(value, ensure_ascii=False, indent=2)+'\n').encode())


def ledger_check(data, report, baseline):
    original = ORIGINAL_ROM.read_bytes()
    prior = load_json(b.BASELINE.parent/'english-build.json')['ledger']
    ledger = report['ledger']
    check(ledger['allocations'][:-1] == prior['allocations'], 'Earlier allocation ledger differs')
    rebuilt = bytearray(original+b'\xff'*(len(data)-len(original)))
    for a in ledger['allocations']:
        at = a['offset']; raw = data[at:at+a['bytes']]
        check(digest(raw) == a['sha256'], 'Allocation bytes differ')
        rebuilt[at:at+len(raw)] = raw
    for p in ledger['patches']:
        at = p['offset']; before = bytes.fromhex(p['before']); after = bytes.fromhex(p['after'])
        check(rebuilt[at:at+len(before)] == before, 'Patch reconstruction differs')
        rebuilt[at:at+len(after)] = after
    check(bytes(rebuilt) == data, 'ROM contains unexplained writes')
    for p in prior['patches']:
        at = p['offset']; after = bytes.fromhex(p['after'])
        if at != b.WORD:
            check(data[at:at+len(after)] == after, 'Unrelated prior patch changed')
    for p in ledger['protected_sources']:
        check(data[p['start']:p['end_exclusive']] == original[p['start']:p['end_exclusive']],
              'Protected original source changed')
    last = ledger['allocations'][-1]
    expected = bytearray(baseline)
    expected[b.WORD:b.WORD+4] = data[b.WORD:b.WORD+4]
    expected[last['offset']:last['offset']+last['bytes']] = data[last['offset']:last['offset']+last['bytes']]
    check(bytes(expected) == data, 'Correction changed bytes outside its pointer/new payload')
    return {'complete_image_reconstructed': True, 'prior_allocations_preserved': True,
            'other_prior_patches_preserved': True, 'only_changed_pointer': hex(b.WORD),
            'new_allocation': last, 'new_inventory_sources': 0}


def ui_checks(report, original):
    font, codec = FontZero(original), GameTextCodec(original)
    nonempty = [d for d in report['ui_payloads'] if visible(bytes.fromhex(d['raw_hex']), codec)]
    draws, repeats = coalesce_empty_draw_observations(nonempty, report['ui_positions'])
    results = []
    for d in draws:
        text = visible(bytes.fromhex(d['raw_hex']), codec)
        gs = [g for g in report['ui_positions'] if g['draw_serial'] == d['serial']]
        if d['native_queue_draw']:
            gs, reobserved = distinct_glyph_observations(gs)
            check([g['code'] for g in gs] == [font.glyph(c)[0] for c in text], 'Queue glyphs differ')
            for g, char in zip(gs, text, strict=True):
                check(g['font'] == 0 and g['spacing'] == 0 and g['window_origin'] == [16, 120]
                      and g['window_width'] == 208 and g['window_height'] == 40, 'Queue viewport differs')
                check(0 <= g['x'] and g['x']+max(g['advance'], font.glyph(char)[2]) <= 208
                      and g['y'] in (2, 14, 26, 38), 'Queue glyph exceeds native row')
            staged = any(g['y'] == 38 for g in gs)
            scrolls = [s for s in report['scroll_completions'] if s['draw_serial'] == d['serial']]
            check(not staged or scrolls, 'Tutorial row did not complete native scrolling')
            result = {'glyphs': len(gs), 'reobservations': reobserved, 'staged': staged, 'scrolls': scrolls}
        else:
            result = command_ink_check(gs, text, font)
        results.append({'serial': d['serial'], 'text': text, **result})
    return results, repeats


def route(data, build, variant):
    folder = b.OUTPUT/'verification'/variant
    replay = load_json(b.OUTPUT/'replay.json')
    state = (ROOT/replay['initial_state']).read_bytes()
    check(digest(state) == replay['initial_state_sha256'], 'Natural floor-two state changed')
    index, _, _ = sources(data, build['ledger'])
    watch = [0x08000000+int(e['offset'], 0) for e in load_json(ROOT/'translations/unowned-text-review.json')['entries']]
    watch.append(b.WORD+0x08000000)
    with Session(data, folder) as s:
        check(s.core.load_raw_state(state), 'Cannot restore natural floor-two checkpoint')
        check(s.core.frame_counter == replay['initial_frame'], 'Natural replay start differs')
        t = CaveTrace(s.core, data, index, watch)
        try:
            for i, row in enumerate(replay['inputs']):
                t.phase = f'input-{i:02d}'; code = getattr(s.core, 'KEY_'+row['key'])
                s.core.set_keys(code); t.frames(row['hold']); s.core.clear_keys(code); t.frames(row['released'])
                check(s.core.frame_counter == row['end_frame'], 'Pot route frame differs')
                s.capture(t.phase)
            s.capture('final')
            report = t.report(); save(folder/'raw-trace.json', report)
            check(not t.errors and not report['versions'], 'Unexpected story event or trace error')
            checks, repeats = ui_checks(report, ORIGINAL_ROM.read_bytes())
            pointer_reads = [r for r in report['source_reads'] if int(r['address'], 0) == b.WORD+0x08000000]
            check(pointer_reads and len(pointer_reads) == len(report['source_reads']), 'Unowned source read or missing tutorial pointer')
            target = int.from_bytes(data[b.WORD:b.WORD+4], 'little')
            formatted = [f for f in report['formats'] if int(f['source'], 0) == target]
            word = 'Push' if variant == 'english' else 'Press'
            expected = f'Choose {word} to restore HP!'
            check(len(formatted) == 1 and bytes.fromhex(formatted[0]['output_hex']) == expected.encode()+b'\0',
                  'Native tutorial selection/output differs')
            for text in (expected, 'Push', 'Torneko pushed', "Torneko's HP was fully", 'restored.'):
                check(any(c['text'] == text for c in checks), 'Missing natural correction/menu/use text: '+text)
            check(all(f['payload_limit'] == 79 and f['written_bytes'] <= 59 for f in report['formats']),
                  'Natural queue/history payload bound differs')
            (folder/'final.state').write_bytes(bytes(ffi.buffer(s.core.save_raw_state())))
            result = {**report, 'rom_sha256': digest(data), 'initial_state_sha256': digest(state),
                'checks': checks, 'empty_duplicate_draws': repeats, 'selected_tutorial_source': hex(target),
                'unowned_japanese_reads': 0, 'pointer_reads': pointer_reads,
                'scope': 'Normal recorded buttons from accepted floor two: pot pickup, tutorial scroll, inventory/Look list, Push action and HP recovery. No altered item/HP/coordinates/flags; no cartridge-save persistence claim.'}
            save(folder/'trace.json', result)
        finally:
            t.close()
    return result


def verify():
    mgba.log.silence()
    report = load_json(b.OUTPUT/'english-build.json')
    data = (b.OUTPUT/'torneko3-text-polish-english.gba').read_bytes()
    baseline = b.BASELINE.read_bytes()
    check(report['rom_sha256'] == digest(data) and report['previous_rom_sha256'] == digest(baseline), 'Correction ROM hashes differ')
    check(report['catalog_sha256'] == digest(b.CATALOG.read_bytes()) == digest((b.OUTPUT/'catalog.json').read_bytes()), 'Correction catalog differs')
    ownership = ledger_check(data, report, baseline)
    old = route(baseline, load_json(b.BASELINE.parent/'english-build.json'), 'baseline')
    new = route(data, report, 'english')
    before = [f['output_hex'] for f in old['formats']]
    after = [f['output_hex'] for f in new['formats']]
    check([bytes.fromhex(x).replace(b'Choose Press', b'Choose Push').hex() for x in before] == after,
          'Unrelated formatter output changed')
    pixel_pairs = 0
    for p in sorted((b.OUTPUT/'verification/english').glob('*.png')):
        a = Image.open(p).convert('RGB')
        z = Image.open(b.OUTPUT/'verification/baseline'/p.name).convert('RGB')
        # Only the tutorial/message viewport may differ during the wording change.
        for region in ((0, 0, 240, 120), (0, 120, 8, 160), (232, 120, 240, 160)):
            check(ImageChops.difference(a.crop(region), z.crop(region)).getbbox() is None,
                  'Correction changed pixels outside the message viewport')
        if ImageChops.difference(a, z).getbbox() is None:
            pixel_pairs += 1
    final = b.OUTPUT/'verification/english/final.png'
    check(ImageChops.difference(Image.open(final).convert('RGB'), Image.open(b.OUTPUT/'expected-final.png').convert('RGB')).getbbox() is None,
          'Pot-use result differs from original exploration')
    result = {'status': 'natural_tutorial_correction_passed', 'rom_sha256': digest(data),
        'baseline_sha256': digest(baseline), 'source_sha256': digest(ORIGINAL_ROM.read_bytes()),
        'harness_sha256': digest(Path(__file__).read_bytes()), 'builder_sha256': digest(Path(b.__file__).read_bytes()),
        'catalog_sha256': digest(b.CATALOG.read_bytes()), 'replay_sha256': digest((b.OUTPUT/'replay.json').read_bytes()),
        'helper_sha256': {name: digest((ROOT/'tools'/name).read_bytes()) for name in (
            'verify_natural_cave.py', 'trace_opening_story.py', 'trace_story_provenance.py', 'trace_text_systems.py',
            'verify_items.py', 'verify_core_gameplay.py', 'verify_expansion.py', 'build_tutorial_gameplay.py')},
        'reports': {v: digest((b.OUTPUT/f'verification/{v}/trace.json').read_bytes()) for v in ('baseline', 'english')},
        'english_draws': len(new['checks']), 'baseline_draws': len(old['checks']), 'unchanged_pixel_pairs': pixel_pairs,
        'all_other_screen_regions_identical': True, 'final_result_identical': True, 'ownership': ownership,
        'scope': 'One existing source corrected; no newly translated inventory entry. Complete ledger reconstruction, exact previous-byte preservation except its one superseded pointer, normal tutorial pickup/scroll/menu/Push use on baseline and corrected ROMs. Graphics, other gameplay branches and cartridge persistence remain separate.'}
    save(b.OUTPUT/'component-checkpoint.json', result)
    print(result['status'], len(new['checks']), 'English draws;', pixel_pairs, 'identical screen pairs', flush=True)


if __name__ == '__main__':
    verify()
