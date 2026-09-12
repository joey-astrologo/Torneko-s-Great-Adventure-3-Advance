"""Apply gameplay wording corrections with explicit existing patch ownership."""
import json
import struct
from tools import build_remaining_display as previous
from tools import build_tutorial_gameplay as tutorial
from tools.build_first_label import ROOT, ORIGINAL_ROM, digest
from tools.translation_pipeline import check, load_json, atomic_write
from tools.rom_build import RomBuild

OUTPUT = ROOT/'build/completion/text-polish'
CATALOG = ROOT/'translations/text-polish.json'
BASELINE = previous.OUTPUT/'torneko3-remaining-display-english.gba'
WORD = 0x1B4B08


def validate(original, catalog):
    check(catalog['base_sha256'] == digest(original) and len(catalog['entries']) == 1,
          'Text correction catalog differs')
    e = catalog['entries'][0]
    old = next(x for x in load_json(tutorial.CATALOG)['entries'] if x['id'] == e['supersedes'])
    check(old['id'] == 'tutorial.001b492f' and e['id'] == 'text-polish.001b492f',
          'Unreviewed text correction')
    check(all(e[k] == old[k] for k in old.keys()-{'id', 'english', 'notes'}),
          'Text correction changed source/reader metadata')
    check(e['english'] == old['english'].replace('Choose Press', 'Choose Push') and
          old['english'].count('Choose Press') == 1, 'Unexpected wording correction')
    tutorial.encode(e, original)
    return e


def build_rom(original, *, build=None):
    b = RomBuild(original) if build is None else build
    baseline, prior = previous.build_rom(original, build=b)
    check(baseline == BASELINE.read_bytes(), 'Earlier cumulative build differs')
    e = validate(original, load_json(CATALOG))
    old = next(p for p in prior['ledger']['patches'] if p['offset'] == WORD)
    check(old['id'] == 'tutorial.001b492f.001b4b08' and old['owner'] == 'tutorial-gameplay'
          and old['before'] == '2f491b08' and old['after'] == '34290109',
          'Prior tutorial pointer owner differs')
    check(next(p for p in b.patches if p['id'] == old['id']) == old,
          'Earlier tutorial patch metadata differs')
    at = int(e['offset'], 0)
    source = bytes.fromhex(e['source_hex'])
    b.protect_source(e['id'], at, at+len(source), 'text-polish')
    raw, metrics = tutorial.encode(e, original)
    dest = b.allocate(e['id'], raw, 'text-polish')
    supersession = b.supersede_patch(e['id']+'.correction', old['id'], old['owner'],
        bytes.fromhex(old['after']), struct.pack('<I', dest+0x08000000), 'text-polish',
        'Match Recovery pot tutorial command name to the native Push action menu')
    data, ledger = b.finish()
    return data, {'source_sha256': digest(original), 'rom_sha256': digest(data),
        'previous_rom_sha256': digest(baseline), 'language': 'english',
        'text_polish': {'resources': 1, 'new_inventory_sources': 0, 'pointer_words': 1,
            'relocated': {e['id']: {'offset': dest, 'metrics': metrics}},
            'supersessions': [supersession]}, 'ledger': ledger}


def build():
    data, report = build_rom(ORIGINAL_ROM.read_bytes())
    atomic_write(OUTPUT/'catalog.json', CATALOG.read_bytes())
    report['catalog_sha256'] = digest(CATALOG.read_bytes())
    atomic_write(OUTPUT/'torneko3-text-polish-english.gba', data)
    atomic_write(OUTPUT/'english-build.json', (json.dumps(report, indent=2)+'\n').encode())
    print(report['rom_sha256'], report['text_polish']['relocated'], flush=True)


if __name__ == '__main__':
    build()
