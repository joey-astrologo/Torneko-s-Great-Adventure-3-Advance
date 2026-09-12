"""Validate arena result text proofs and reconstruct both complete ROMs."""
from pathlib import Path
from PIL import Image, ImageChops
from tools import verify_arena_final as v
from tools.translation_pipeline import check, load_json
from tools.verify_items import write_json

SCOPE = ('Three arena result text resources, preserving native colour and column '
         'controls, 200-byte formatting, all 200 accepted actor names, both colours, '
         'eight-row boards, generated odds bounds and no-winner/more-winners labels. '
         'Controlled native instruction slices do not establish natural arena '
         'outcomes or actor-record generation. The separate graphic heading remains '
         'Japanese and is tracked for further work.')


def summarize():
    out = v.b.OUTPUT
    original, baseline = v.ORIGINAL_ROM.read_bytes(), v.BASELINE.read_bytes()
    catalog = load_json(out / 'catalog.json')
    prior = load_json(v.BASELINE.parent / 'english-build.json')['ledger']
    end = max(a['offset'] + a['bytes'] for a in prior['allocations'])
    harness = v.digest(Path(v.__file__).read_bytes())
    helpers = {**v.system.helper_hashes(),
               'verify_system_labels.py': v.digest(Path(v.system.__file__).read_bytes())}
    words = {int(p['offset'], 0) for e in catalog['entries'] for p in e['pointer_owners']}
    check(v.b.CATALOG.read_bytes() == (out / 'catalog.json').read_bytes() and
          harness == v.digest((out / Path(v.__file__).name).read_bytes()),
          'Arena frozen inputs changed')
    reports, proofs = {}, {}
    for variant in ('english', 'japanese', 'baseline'):
        data = baseline if variant == 'baseline' else (out / f'torneko3-arena-final-{variant}.gba').read_bytes()
        path = out / 'verification' / variant / 'verification.json'
        r = load_json(path)
        check(r['rom_sha256'] == v.digest(data) and r['source_sha256'] == v.digest(original), 'Arena ROM proof changed')
        check(r['catalog_sha256'] == v.digest(v.b.CATALOG.read_bytes()) and
              r['harness_sha256'] == harness and r['helper_sha256'] == helpers and
              r['fixture_sha256'] == v.digest(v.STATE.read_bytes()), 'Arena proof tooling changed')
        cases = r['cases']
        check(len(cases) == 205 and [c['actor'] for c in cases[:200]] == list(range(200)), 'Arena actor coverage incomplete')
        check([(c['colour'], c['odds_tenths']) for c in cases[200:204]] ==
              [(colour, odds) for colour in (5, 7) for odds in (10, 9999)] and
              cases[-1]['kind'] == 'empty', 'Arena outcome coverage incomplete')
        check(all(c['guards_intact'] for c in cases) and
              all(len(c['rows']) == 8 and all(x['guards_intact'] for x in c['rows']) for c in cases[200:204]), 'Arena guard evidence missing')
        if variant == 'english':
            check(all(c['checks'] for c in cases), 'Arena English glyph evidence missing')
        check(len(r['pointer_words']) == 3 and {int(p['word'], 0) for p in r['pointer_words']} == words, 'Arena pointer coverage incomplete')
        for p in r['pointer_words']:
            at = int(p['word'], 0)
            check(int(p['source'], 0) == int.from_bytes(data[at:at + 4], 'little'), 'Arena pointer proof differs')
        check(r['screens'] == [p for c in cases for p in c['screens']] and len(r['screens']) == 205 and
              all((path.parent / p).is_file() for p in r['screens']), 'Arena screenshots missing')
        if variant != 'baseline':
            build = load_json(out / f'{variant}-build.json')
            check(build['rom_sha256'] == v.digest(data) and build['previous_rom_sha256'] == v.digest(baseline) and
                  build['catalog_sha256'] == v.digest(v.b.CATALOG.read_bytes()), 'Arena build inputs differ')
            ledger = build['ledger']
            rebuilt = bytearray(original + b'\xff' * (len(data) - len(original)))
            for a in ledger['allocations']:
                at = a['offset']; raw = data[at:at + a['bytes']]
                check(v.digest(raw) == a['sha256'], 'Arena allocation hash differs')
                rebuilt[at:at + len(raw)] = raw
            for p in ledger['patches']:
                at = p['offset']; before, after = bytes.fromhex(p['before']), bytes.fromhex(p['after'])
                check(rebuilt[at:at + len(before)] == before, 'Arena patch original differs')
                rebuilt[at:at + len(after)] = after
            check(bytes(rebuilt) == data and data[0x1000000:end] == baseline[0x1000000:end], 'Arena unexplained ROM writes')
            for p in prior['patches']:
                at = p['offset']; raw = bytes.fromhex(p['after'])
                check(data[at:at + len(raw)] == raw, 'Arena changed an earlier patch')
            for p in ledger['protected_sources']:
                check(data[p['start']:p['end_exclusive']] == original[p['start']:p['end_exclusive']], 'Arena protected source changed')
        reports[variant] = r
        proofs[variant] = {'rom_sha256': v.digest(data), 'report_sha256': v.digest(path.read_bytes()), 'cases': 205, 'screens': 205}
    a, z = reports['japanese'], reports['baseline']
    check(a['cases'] == z['cases'] and a['screens'] == z['screens'], 'Arena Japanese native outputs differ')
    for name in a['screens']:
        with Image.open(out / 'verification/japanese' / name) as x, Image.open(out / 'verification/baseline' / name) as y:
            check(ImageChops.difference(x.convert('RGB'), y.convert('RGB')).getbbox() is None, 'Arena Japanese pixels differ: ' + name)
    result = {'status': 'arena_final_native_checks_passed', 'sources': 3, 'pointer_words': 3,
              'english_cases': 205, 'english_screens': 205, 'japanese_pixel_pairs': 205,
              'proofs': proofs, 'complete_images_reconstructed_from_ledgers': True,
              'previous_patches_preserved': True, 'previous_appended_bytes_preserved': True, 'scope': SCOPE}
    write_json(out / 'component-checkpoint.json', result)
    print(result['status'], flush=True)


if __name__ == '__main__':
    summarize()
