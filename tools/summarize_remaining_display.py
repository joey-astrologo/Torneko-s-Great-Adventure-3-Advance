"""Validate remaining display proofs and reconstruct both complete ROMs."""
from pathlib import Path
from PIL import Image, ImageChops
from tools import verify_remaining_display as v
from tools.translation_pipeline import check, load_json
from tools.verify_items import write_json

SCOPE = ('Four sound-test help resources and one live-dungeon floor summary. '
         'Native startup cache, all four help selectors and per-character '
         'state-machine rendering; 64 dungeon names at unsigned-byte floor '
         'bounds 0/255 displayed in both Adventure Log slots with seven-letter '
         'names. Controlled early-world fixtures; no natural debug-menu entry, '
         'audio playback, dungeon progression or additional save writes.')


def summarize():
    out = v.b.OUTPUT
    original, baseline = v.ORIGINAL_ROM.read_bytes(), v.BASELINE.read_bytes()
    catalog = load_json(out / 'catalog.json')
    prior = load_json(v.BASELINE.parent / 'english-build.json')['ledger']
    end = max(a['offset'] + a['bytes'] for a in prior['allocations'])
    harness = v.digest(Path(v.__file__).read_bytes())
    helpers = v.helper_hashes()
    words = {int(p['offset'], 0) for e in catalog['entries'] for p in e['pointer_owners']}
    check(v.b.CATALOG.read_bytes() == (out / 'catalog.json').read_bytes() and
          harness == v.digest((out / Path(v.__file__).name).read_bytes()),
          'Remaining display frozen inputs changed')
    reports, proofs = {}, {}
    for variant in ('english', 'japanese', 'baseline'):
        data = baseline if variant == 'baseline' else (out / f'torneko3-remaining-display-{variant}.gba').read_bytes()
        path = out / 'verification' / variant / 'verification.json'
        r = load_json(path)
        check(r['rom_sha256'] == v.digest(data) and r['source_sha256'] == v.digest(original), 'Remaining display ROM proof changed')
        check(r['catalog_sha256'] == v.digest(v.b.CATALOG.read_bytes()) and
              r['harness_sha256'] == harness and r['helper_sha256'] == helpers and
              r['fixture_sha256'] == v.digest(v.STATE.read_bytes()), 'Remaining display proof tooling changed')
        cases = r['cases']
        check(len(cases) == 132 and [c['row'] for c in cases[:4]] == list(range(4)), 'Sound help coverage incomplete')
        check([(c['dungeon'],c['floor']) for c in cases[4:]] == [(row,floor) for row in range(64) for floor in (0,255)], 'Floor summary coverage incomplete')
        check(all(c['guards_intact'] for c in cases), 'Remaining display guards missing')
        check(r['cold_sound_cache_hex'] == data[0xCB07EC:0xCB07FC].hex(), 'Cold sound cache proof differs')
        if variant == 'english':
            check(all(c['checks'] for c in cases), 'Remaining display English glyph evidence missing')
        check(len(r['pointer_words']) == 5 and {int(p['word'], 0) for p in r['pointer_words']} == words, 'Remaining display pointer coverage incomplete')
        for p in r['pointer_words']:
            at = int(p['word'], 0)
            check(int(p['target'], 0) == int.from_bytes(data[at:at + 4], 'little'), 'Remaining display pointer proof differs')
        check(r['screens'] == [p for c in cases for p in c['screens']] and len(r['screens']) == 132 and
              all((path.parent / p).is_file() for p in r['screens']), 'Remaining display screenshots missing')
        if variant != 'baseline':
            build = load_json(out / f'{variant}-build.json')
            check(build['rom_sha256'] == v.digest(data) and build['previous_rom_sha256'] == v.digest(baseline) and
                  build['catalog_sha256'] == v.digest(v.b.CATALOG.read_bytes()), 'Remaining display build inputs differ')
            ledger = build['ledger']
            rebuilt = bytearray(original + b'\xff' * (len(data) - len(original)))
            for a in ledger['allocations']:
                at = a['offset']; raw = data[at:at + a['bytes']]
                check(v.digest(raw) == a['sha256'], 'Remaining display allocation hash differs')
                rebuilt[at:at + len(raw)] = raw
            for p in ledger['patches']:
                at = p['offset']; before, after = bytes.fromhex(p['before']), bytes.fromhex(p['after'])
                check(rebuilt[at:at + len(before)] == before, 'Remaining display patch original differs')
                rebuilt[at:at + len(after)] = after
            check(bytes(rebuilt) == data and data[0x1000000:end] == baseline[0x1000000:end], 'Remaining display unexplained ROM writes')
            for p in prior['patches']:
                at = p['offset']; raw = bytes.fromhex(p['after'])
                check(data[at:at + len(raw)] == raw, 'Remaining display changed an earlier patch')
            for p in ledger['protected_sources']:
                check(data[p['start']:p['end_exclusive']] == original[p['start']:p['end_exclusive']], 'Remaining display protected source changed')
        reports[variant] = r
        proofs[variant] = {'rom_sha256': v.digest(data), 'report_sha256': v.digest(path.read_bytes()), 'cases': 132, 'screens': 132}
    a, z = reports['japanese'], reports['baseline']
    def comparable(cases):
        return [{k:val for k,val in c.items() if k not in ('source','native_final_cursor')} for c in cases]
    check(comparable(a['cases']) == comparable(z['cases']) and a['screens'] == z['screens'], 'Remaining display Japanese native outputs differ')
    for name in a['screens']:
        with Image.open(out / 'verification/japanese' / name) as x, Image.open(out / 'verification/baseline' / name) as y:
            check(ImageChops.difference(x.convert('RGB'), y.convert('RGB')).getbbox() is None, 'Remaining display Japanese pixels differ: ' + name)
    result = {'status': 'remaining_display_native_checks_passed', 'sources': 5, 'pointer_words': 5,
              'english_cases': 132, 'english_screens': 132, 'japanese_pixel_pairs': 132,
              'proofs': proofs, 'complete_images_reconstructed_from_ledgers': True,
              'previous_patches_preserved': True, 'previous_appended_bytes_preserved': True, 'scope': SCOPE}
    write_json(out / 'component-checkpoint.json', result)
    print(result['status'], flush=True)


if __name__ == '__main__':
    summarize()
