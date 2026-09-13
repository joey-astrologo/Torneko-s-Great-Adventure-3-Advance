"""Match the native ending reveal animation to the existing English panel."""
import json
from tools import build_text_polish as previous
from tools.build_first_label import ROOT, ORIGINAL_ROM, digest
from tools.translation_pipeline import check, atomic_write
from tools.rom_build import RomBuild

OUTPUT = ROOT/'build/completion/result-runtime'
BASELINE = previous.OUTPUT/'torneko3-text-polish-english.gba'
PATCHES = (
    ('clear_x', 0x5C6A8, '051d', '851c'),
    ('clear_width', 0x5C6AE, '1921', '1a21'),
    ('clear_right', 0x5C6B4, '3230', '3430'),
    ('reveal_x', 0x5C6CE, '041d', '841c'),
    ('reveal_width', 0x5C6D8, '1921', '1a21'),
)


def build_rom(original, *, build=None):
    b = RomBuild(original) if build is None else build
    baseline, prior = previous.build_rom(original, build=b)
    check(baseline == BASELINE.read_bytes(), 'Earlier cumulative build differs')
    for name, at, before, after in PATCHES:
        b.patch('result-runtime.'+name, at, bytes.fromhex(before), bytes.fromhex(after),
                'result-runtime', 'Match native ending animation to existing x=1, width=27 result window')
    data, ledger = b.finish()
    check(ledger['allocations'] == prior['ledger']['allocations'], 'Prior allocations differ')
    check(ledger['patches'][:-len(PATCHES)] == prior['ledger']['patches'], 'Prior patches differ')
    return data, {'source_sha256': digest(original), 'rom_sha256': digest(data),
        'previous_rom_sha256': digest(baseline), 'language': 'english',
        'result_runtime': {'new_inventory_sources': 0, 'patch_halfwords': len(PATCHES),
            'tile_origin': [1, 2], 'tile_dimensions': [27, 17],
            'scope': 'Native dungeon-ending reveal animation only; existing descriptor, text, allocation, RAM and save layouts preserved'},
        'ledger': ledger}


def build():
    data, report = build_rom(ORIGINAL_ROM.read_bytes())
    atomic_write(OUTPUT/'torneko3-result-runtime-english.gba', data)
    atomic_write(OUTPUT/'english-build.json', (json.dumps(report, indent=2)+'\n').encode())
    print(report['rom_sha256'], flush=True)


if __name__ == '__main__':
    build()
