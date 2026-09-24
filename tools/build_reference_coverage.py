"""Repair verified duplicate menu and startup-cache references to existing English."""
import struct
from tools import build_dungeon_save_prompt as previous
from tools.build_first_label import ROOT, ORIGINAL_ROM, digest
from tools.rom_build import RomBuild
from tools.translation_pipeline import atomic_write, check
from tools.prose_review import save

OWNER = 'reference-coverage'
OUTPUT = ROOT/'build/reference-coverage'
ROM = OUTPUT/'torneko3-reference-coverage-english.gba'
BASELINE = previous.ROM
# Missing word, existing translated word, original Japanese source, expected English.
# Sharing already owned strings adds no allocations and reuses no source storage.
REFERENCES = (
    (0xC4CD40, 0xC4CDD8, 0xC4CDC8, 'Story mode'),
    (0xC4CD4C, 0xC4CDE4, 0xC4CDB4, 'Extra mode'),
    (0xC4CD64, 0xC4CDFC, 0xC4CD90, 'Help'),
    (0xC4CD70, 0xC4CE08, 0xC4CD88, 'Cancel'),
    (0xCAFEC0, 0x11548, 0x1B4095, 'But nothing happened.'),
    (0xCAFEC4, 0xA653C, 0x1B56AD, '$i0 burned up.'),
    (0xCAFEC8, 0xA6544, 0x1B56CB, '$i0 froze.'),
    (0xCAFECC, 0xA654C, 0x1B56ED, '$i0 was buried\nin sand.'),
    (0xCAFED0, 0xA6554, 0x1B5712, '$i0 was lost\nto the wind.'),
    (0xCAFED4, 0x11548, 0x1B4095, 'But nothing happened.'),
    (0xCAFED8, 0xA6540, 0x1B56B9, '$i0: some\nburned up.'),
    (0xCAFEDC, 0xA6548, 0x1B56D9, '$i0: some\nfroze.'),
    (0xCAFEE0, 0xA6550, 0x1B56FD, '$i0: some\nvanished into the sand.'),
    (0xCAFEE4, 0xA6558, 0x1B5723, '$i0: some were\nlost to the wind.'),
    (0xCB0094, 0x11548, 0x1B4095, 'But nothing happened.'),
)


def build_rom(original, *, build=None):
    b = RomBuild(original) if build is None else build
    baseline, prior = previous.build_rom(original, build=b)
    check(baseline == BASELINE.read_bytes(), 'Reference-coverage baseline changed')
    memory_map = (ROOT/'docs/MEMORY_MAP.md').read_text()
    rows = []
    for word, alias, source, english in REFERENCES:
        check(f'`[{word:08X},{word+4:08X})`' in memory_map, 'Document reference before patching')
        before = struct.pack('<I', 0x08000000+source)
        check(original[alias:alias+4] == before, 'Alias Japanese identity differs')
        target = struct.unpack_from('<I', baseline, alias)[0]-0x08000000
        payload = english.encode()+b'\0'
        check(baseline[target:target+len(payload)] == payload, 'Existing English differs')
        owners = [a for a in b.allocator.allocations if a['offset'] <= target and target+len(payload) <= a['offset']+a['bytes']]
        check(len(owners) == 1, 'English target must have one existing allocation owner')
        b.patch(f'{OWNER}.{word:08x}', word, before, baseline[alias:alias+4], OWNER,
                f'Native reader confirmed; share {owners[0]["id"]} via existing pointer {alias:08X}')
        rows.append(dict(word=word, existing_pointer=alias, japanese_source=source,
                         english_target=target, english=english, allocation_owner=owners[0]['id']))
    data, ledger = b.finish()
    check(ledger['allocations'] == prior['ledger']['allocations'], 'Reference repair allocated storage')
    check(ledger['memory_reservations'] == prior['ledger']['memory_reservations'], 'RAM reservations changed')
    return data, dict(source_rom=str(ORIGINAL_ROM.relative_to(ROOT)), source_sha256=digest(original),
        output_rom=str(ROM.relative_to(ROOT)), rom_sha256=digest(data), previous_rom_sha256=digest(baseline),
        references=rows, ledger=ledger)


if __name__ == '__main__':
    data, report = build_rom(ORIGINAL_ROM.read_bytes())
    atomic_write(ROM, data)
    save(OUTPUT/'english-build.json', report)
    print('Built', report['rom_sha256'])
