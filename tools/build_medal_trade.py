"""Compact medal-trading action, composed after the combat-line checkpoint."""
import argparse
from pathlib import Path
import struct
from tools import build_combat_lines as previous
from tools.build_first_label import ROOT, ORIGINAL_ROM, digest
from tools.rom_build import AppendAllocator, RomBuild
from tools.translation_pipeline import atomic_write, check, load_json
from tools.prose_review import save

OWNER = 'medal-trade'
OUTPUT = ROOT / 'build/medal-trade'
ROM = OUTPUT / 'torneko3-medal-trade-english.gba'
BASELINE = previous.ROM
PLAN = OUTPUT / 'allocation-plan.json'
POINTER = 0x63A3C


def prepare():
    original = ORIGINAL_ROM.read_bytes()
    baseline = BASELINE.read_bytes()
    prior = load_json(BASELINE.parent / 'english-build.json')
    check(digest(baseline) == prior['rom_sha256'], 'Baseline differs')
    old = next(p for p in prior['ledger']['patches'] if p['offset'] == POINTER)
    before = baseline[POINTER:POINTER+4]
    check(bytes.fromhex(old['after']) == before, 'Pointer owner differs')
    source = struct.unpack('<I', before)[0] - 0x08000000
    check(baseline[source:source+9] == b'Exchange\0', 'Medal label differs')
    allocator = AppendAllocator(len(original) + prior['ledger']['appended_used_with_padding'])
    at = allocator.allocate(OWNER+'.label', b'Trade\0', 4)
    allocator.allocations[-1]['owner'] = OWNER
    save(PLAN, dict(source_sha256=digest(original), previous_sha256=digest(baseline),
        builder_sha256=digest(Path(__file__).read_bytes()), start=allocator.start,
        end_exclusive=allocator.cursor, allocations=allocator.allocations, label_offset=at,
        previous_patch=old, replacement_hex=struct.pack('<I', at+0x08000000).hex(),
        new_ram_reservations=[], save_changes=[]))
    print(f'Prepared [{allocator.start:08X},{allocator.cursor:08X})')


def build_rom(original, *, build=None):
    plan = load_json(PLAN)
    check(digest(original) == plan['source_sha256'], 'Source differs')
    check(digest(Path(__file__).read_bytes()) == plan['builder_sha256'], 'Regenerate medal plan')
    check(f'`[{plan["start"]:08X},{plan["end_exclusive"]:08X})`' in (ROOT/'docs/MEMORY_MAP.md').read_text(), 'Document allocation first')
    b = RomBuild(original) if build is None else build
    baseline, prior = previous.build_rom(original, build=b)
    check(baseline == BASELINE.read_bytes() and digest(baseline) == plan['previous_sha256'], 'Baseline changed')
    check(b.allocator.cursor == plan['start'], 'Allocator changed')
    check(b.allocate(OWNER+'.label', b'Trade\0', OWNER) == plan['label_offset'], 'Label moved')
    old = plan['previous_patch']
    check(next(p for p in b.patches if p['id'] == old['id']) == old, 'Previous owner changed')
    b.supersede_patch(OWNER+'.pointer', old['id'], old['owner'], bytes.fromhex(old['after']),
        bytes.fromhex(plan['replacement_hex']), OWNER, 'Approved Trade action fits the 36px medal popup text region')
    data, ledger = b.finish()
    check(ledger['allocations'] == prior['ledger']['allocations'] + plan['allocations'], 'Earlier allocations changed')
    check(ledger['memory_reservations'] == prior['ledger']['memory_reservations'], 'RAM changed')
    return data, dict(source_rom=str(ORIGINAL_ROM.relative_to(ROOT)), source_sha256=digest(original),
        output_rom=str(ROM.relative_to(ROOT)), rom_sha256=digest(data), previous_rom_sha256=digest(baseline),
        allocation_plan_sha256=digest(PLAN.read_bytes()), ledger=ledger)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare', action='store_true')
    if parser.parse_args().prepare:
        prepare()
    else:
        data, report = build_rom(ORIGINAL_ROM.read_bytes())
        atomic_write(ROM, data)
        save(OUTPUT/'english-build.json', report)
        print('Built', report['rom_sha256'])
