"""Use a short empty-inventory display in the verified 128px popup."""
import json
import struct
from tools import build_ui_polish as previous
from tools import build_battle_completion as battle
from tools.build_first_label import ROOT, ORIGINAL_ROM, digest
from tools.translation_pipeline import check, load_json, atomic_write, FontZero
from tools.build_enemies import measure
from tools.rom_build import RomBuild

OUTPUT = ROOT/'build/completion/inventory-notice'
CATALOG = ROOT/'translations/inventory-notice.json'
BASELINE = previous.OUTPUT/'torneko3-ui-polish-english.gba'
WORD = 0x20488


def validate(original, catalog):
    check(catalog['base_sha256'] == digest(original) and len(catalog['entries']) == 1,
          'Inventory notice catalog differs')
    e = catalog['entries'][0]
    old = next(x for x in load_json(battle.CATALOG)['entries'] if x['id'] == e['supersedes'])
    check(old['id'] == 'battle.001b98c2' and e['id'] == 'inventory-notice.001b98c2', 'Unreviewed notice')
    check(all(e[k] == old[k] for k in old.keys()-{'id', 'display', 'notes', 'family'}), 'Notice source metadata differs')
    check(e['english'] == 'You are not carrying any items.' and e['display'] == 'No items.'
          and e['family'] == 'popup', 'Notice display authority differs')
    raw = e['display'].encode('ascii')+b'\0'
    width = measure(e['display'], FontZero(original))
    check(width <= 128 and len(raw)+36 <= 256, 'Notice exceeds its native reader')
    return e, raw, {'display_template': e['display'], 'width': width, 'window_width': 128,
        'bytes_including_nul': len(raw), 'native_trailing_spaces': 36, 'printf_bytes_including_nul': len(raw)+36,
        'printf_capacity': 256, 'reader': '0x08020498'}


def build_rom(original, *, build=None):
    b = RomBuild(original) if build is None else build
    baseline, prior = previous.build_rom(original, build=b)
    check(baseline == BASELINE.read_bytes(), 'Earlier cumulative build differs')
    e, raw, metrics = validate(original, load_json(CATALOG))
    old = next(p for p in prior['ledger']['patches'] if p['offset'] == WORD)
    check(old['id'] == 'battle.001b98c2.0x00020488' and old['owner'] == 'battle-completion'
          and old['before'] == 'c2981b08' and old['after'] == '30500609', 'Earlier notice owner differs')
    b.protect_source(e['id'], int(e['offset'], 0), int(e['source_end_exclusive'], 0), 'inventory-notice')
    at = b.allocate(e['id'], raw, 'inventory-notice')
    supersession = b.supersede_patch(e['id']+'.display', old['id'], old['owner'],
        bytes.fromhex(old['after']), struct.pack('<I', at+0x08000000), 'inventory-notice',
        'Fit the native 128px inventory popup; preserve the separate full paged-message source')
    data, ledger = b.finish()
    return data, {'source_sha256': digest(original), 'rom_sha256': digest(data),
        'previous_rom_sha256': digest(baseline), 'language': 'english',
        'inventory_notice': {'resources': 1, 'new_inventory_sources': 0,
            'relocated': {e['id']: {'offset': at, 'metrics': metrics}}, 'supersessions': [supersession]},
        'ledger': ledger}


def build():
    data, report = build_rom(ORIGINAL_ROM.read_bytes())
    atomic_write(OUTPUT/'catalog.json', CATALOG.read_bytes())
    report['catalog_sha256'] = digest(CATALOG.read_bytes())
    atomic_write(OUTPUT/'torneko3-inventory-notice-english.gba', data)
    atomic_write(OUTPUT/'english-build.json', (json.dumps(report, indent=2)+'\n').encode())
    print(report['rom_sha256'], report['inventory_notice']['relocated'], flush=True)


if __name__ == '__main__':
    build()
