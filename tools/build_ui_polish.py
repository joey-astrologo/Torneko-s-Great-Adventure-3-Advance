"""Fit the records title-menu label without changing earlier allocations."""
import json
import struct
from tools import build_result_runtime as previous
from tools import build_frontend_completion as frontend
from tools.build_first_label import ROOT, ORIGINAL_ROM, digest
from tools.translation_pipeline import check, load_json, atomic_write, FontZero
from tools.build_enemies import measure
from tools.rom_build import RomBuild

OUTPUT = ROOT/'build/completion/ui-polish'
CATALOG = ROOT/'translations/ui-polish.json'
BASELINE = previous.OUTPUT/'torneko3-result-runtime-english.gba'
WORD = 0xC7828C


def validate(original, catalog):
    check(catalog['base_sha256'] == digest(original) and len(catalog['entries']) == 1,
          'UI correction catalog differs')
    e = catalog['entries'][0]
    old = next(x for x in load_json(frontend.CATALOG)['entries'] if x['id'] == e['supersedes'])
    check(old['id'] == 'frontend.00c782b0' and e['id'] == 'ui-polish.00c782b0', 'Unreviewed UI correction')
    check(all(e[k] == old[k] for k in old.keys()-{'id', 'display', 'notes'}), 'UI source metadata differs')
    check(e['english'] == 'Adventure records' and e['display'] == 'Records', 'UI display authority differs')
    raw, metrics = frontend.encode(e, original)
    check(raw == b'Records\0' and measure(e['display'], FontZero(original)) == 36, 'UI encoding/width differs')
    return e, raw, metrics


def build_rom(original, *, build=None):
    b = RomBuild(original) if build is None else build
    baseline, prior = previous.build_rom(original, build=b)
    check(baseline == BASELINE.read_bytes(), 'Earlier cumulative build differs')
    e, raw, metrics = validate(original, load_json(CATALOG))
    old = next(p for p in prior['ledger']['patches'] if p['offset'] == WORD)
    check(old['id'] == 'frontend.00c782b0.0x00C7828C' and old['owner'] == 'frontend-completion'
          and old['before'] == 'b082c708' and old['after'] == '88030609', 'Earlier menu pointer differs')
    at = int(e['offset'], 0)
    b.protect_source(e['id'], at, int(e['source_end_exclusive'], 0), 'ui-polish')
    dest = b.allocate(e['id'], raw, 'ui-polish')
    supersession = b.supersede_patch(e['id']+'.display', old['id'], old['owner'],
        bytes.fromhex(old['after']), struct.pack('<I', dest+0x08000000), 'ui-polish',
        'Fit the original 80px title-menu window; retain full Adventure records wording in catalog')
    data, ledger = b.finish()
    return data, {'source_sha256': digest(original), 'rom_sha256': digest(data),
        'previous_rom_sha256': digest(baseline), 'language': 'english',
        'ui_polish': {'resources': 1, 'new_inventory_sources': 0, 'pointer_words': 1,
            'relocated': {e['id']: {'offset': dest, 'metrics': metrics}}, 'supersessions': [supersession]},
        'ledger': ledger}


def build():
    data, report = build_rom(ORIGINAL_ROM.read_bytes())
    atomic_write(OUTPUT/'catalog.json', CATALOG.read_bytes())
    report['catalog_sha256'] = digest(CATALOG.read_bytes())
    atomic_write(OUTPUT/'torneko3-ui-polish-english.gba', data)
    atomic_write(OUTPUT/'english-build.json', (json.dumps(report, indent=2)+'\n').encode())
    print(report['rom_sha256'], report['ui_polish']['relocated'], flush=True)


if __name__ == '__main__':
    build()
