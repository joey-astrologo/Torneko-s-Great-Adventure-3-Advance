"""Accept six graphic phrases with complete native tile-buffer evidence."""
from pathlib import Path
from PIL import Image, ImageChops
from tools import verify_arena_graphics as v
from tools.translation_pipeline import check, load_json
from tools.verify_items import write_json

SCOPE = ('Six indexed graphic phrases outside the ordinary string inventory. '
         'Original font-0 English is packed into native 16x16 graphic cells, '
         'preserving field lengths, caller positions and palette. Native palette '
         'loading, index traversal, tile blits and complete window-buffer '
         'comparisons cover winner/no-winner boards and draw/defeat/victory '
         'branches, including original result status. All prior patches and '
         'appended bytes remain intact. Controlled slices do not establish '
         'natural arena generation, combat or payout behavior.')


def summarize():
    out = v.b.OUTPUT
    original, baseline = v.ORIGINAL_ROM.read_bytes(), v.BASELINE.read_bytes()
    catalog = load_json(out / 'catalog.json')
    prior = load_json(v.BASELINE.parent / 'english-build.json')['ledger']
    end = max(a['offset'] + a['bytes'] for a in prior['allocations'])
    harness = v.digest(Path(v.__file__).read_bytes())
    helpers = {**v.system.helper_hashes(), 'verify_system_labels.py': v.digest(Path(v.system.__file__).read_bytes()),
               'verify_arena_final.py': v.digest(Path(v.arena.__file__).read_bytes())}
    check(v.b.CATALOG.read_bytes() == (out / 'catalog.json').read_bytes() and
          harness == v.digest((out / Path(v.__file__).name).read_bytes()), 'Arena graphic frozen inputs changed')
    reports, proofs = {}, {}
    for variant in ('english', 'japanese', 'baseline'):
        data = baseline if variant == 'baseline' else (out / f'torneko3-arena-graphics-{variant}.gba').read_bytes()
        path = out / 'verification' / variant / 'verification.json'; r = load_json(path)
        check(r['rom_sha256'] == v.digest(data) and r['source_sha256'] == v.digest(original), 'Arena graphic ROM proof changed')
        check(r['catalog_sha256'] == v.digest(v.b.CATALOG.read_bytes()) and r['harness_sha256'] == harness and
              r['helper_sha256'] == helpers and r['fixture_sha256'] == v.digest(v.STATE.read_bytes()), 'Arena graphic proof inputs changed')
        check([c['kind'] for c in r['cases']] == ['winners', 'empty', 'draw', 'defeat', 'victory'], 'Arena graphic cases incomplete')
        check([c['status'] for c in r['cases']] == [None, None, 2, 0, 1], 'Arena native result status changed')
        check(all(c['font_state_intact'] and c['guards_intact'] for c in r['cases']), 'Arena graphic preservation evidence missing')
        selected = set()
        for c in r['cases']:
            graphics = [c['graphics']] if 'whole_buffer_exact' in c['graphics'] else list(c['graphics'].values())
            for g in graphics:
                check(g['whole_buffer_exact'] and g['palette_bank'] == 14 and g['native_blits'] > 0, 'Arena native tile proof absent')
                selected.update(g['sources'])
        check(selected == {e['id'] for e in catalog['entries']}, 'Arena graphic phrase coverage incomplete')
        words = {int(p['offset'], 0) for e in catalog['entries'] for p in e['pointer_owners']} | {0x5D0B0}
        check(len(r['pointer_words']) == 8 and {int(p['word'], 0) for p in r['pointer_words']} == words, 'Arena graphic pointer coverage incomplete')
        for p in r['pointer_words']:
            at = int(p['word'], 0)
            check(int(p['source'], 0) == int.from_bytes(data[at:at + 4], 'little'), 'Arena graphic pointer proof differs')
        check(r['screens'] == [p for c in r['cases'] for p in c['screens']] and len(r['screens']) == 5 and
              all((path.parent / p).is_file() for p in r['screens']), 'Arena graphic screenshots missing')
        if variant != 'baseline':
            build = load_json(out / f'{variant}-build.json')
            check(build['rom_sha256'] == v.digest(data) and build['previous_rom_sha256'] == v.digest(baseline) and
                  build['catalog_sha256'] == v.digest(v.b.CATALOG.read_bytes()), 'Arena graphic build inputs differ')
            ledger = build['ledger']; rebuilt = bytearray(original + b'\xff' * (len(data) - len(original)))
            for a in ledger['allocations']:
                at = a['offset']; raw = data[at:at + a['bytes']]
                check(v.digest(raw) == a['sha256'], 'Arena graphic allocation hash differs'); rebuilt[at:at + len(raw)] = raw
            for p in ledger['patches']:
                at = p['offset']; before, after = bytes.fromhex(p['before']), bytes.fromhex(p['after'])
                check(rebuilt[at:at + len(before)] == before, 'Arena graphic patch original differs'); rebuilt[at:at + len(after)] = after
            check(bytes(rebuilt) == data and data[0x1000000:end] == baseline[0x1000000:end], 'Arena graphic unexplained ROM writes')
            for p in prior['patches']:
                at = p['offset']; raw = bytes.fromhex(p['after'])
                check(data[at:at + len(raw)] == raw, 'Arena graphics changed an earlier patch')
            for p in ledger['protected_sources']:
                check(data[p['start']:p['end_exclusive']] == original[p['start']:p['end_exclusive']], 'Arena graphic protected source changed')
        reports[variant] = r
        proofs[variant] = {'rom_sha256': v.digest(data), 'report_sha256': v.digest(path.read_bytes()), 'cases': 5, 'screens': 5}
    a, z = reports['japanese'], reports['baseline']
    check(a['screens'] == z['screens'], 'Arena graphic control screens differ')
    for c, d in zip(a['cases'], z['cases'], strict=True):
        check(c['graphics'] == d['graphics'] and c['status'] == d['status'] and
              [(h['x'], h['y'], h['indexes_hex']) for h in c['headings']] ==
              [(h['x'], h['y'], h['indexes_hex']) for h in d['headings']], 'Arena graphic Japanese native traversal differs')
    for name in a['screens']:
        with Image.open(out / 'verification/japanese' / name) as x, Image.open(out / 'verification/baseline' / name) as y:
            check(ImageChops.difference(x.convert('RGB'), y.convert('RGB')).getbbox() is None, 'Arena graphic Japanese pixels differ: ' + name)
    result = {'status': 'arena_graphics_native_checks_passed', 'sources': 6, 'new_inventory_sources': 0,
              'reviewed_resources_outside_inventory': 6, 'pointer_words': 8, 'english_cases': 5,
              'english_screens': 5, 'japanese_pixel_pairs': 5, 'proofs': proofs,
              'complete_images_reconstructed_from_ledgers': True, 'previous_patches_preserved': True,
              'previous_appended_bytes_preserved': True, 'scope': SCOPE}
    write_json(out / 'component-checkpoint.json', result); print(result['status'], flush=True)


if __name__ == '__main__':
    summarize()
