"""Inventory storage evidence without treating padding patterns as proven free space."""

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import struct

from tools.build_first_label import ORIGINAL_ROM, digest, load_manifest
from tools.build_expansion_probe import OUTPUT, EXPANDED_SIZE


def uniform_runs(data, minimum=256):
    runs = []
    for value in (0, 255):
        for match in re.finditer(re.escape(bytes([value])) + b"{" + str(minimum).encode() + b",}", data):
            runs.append({"start": match.start(), "end": match.end(),
                         "bytes": match.end() - match.start(), "fill": value})
    return sorted(runs, key=lambda run: run["start"])


def audit(rom=ORIGINAL_ROM, output=OUTPUT):
    rom, output = Path(rom).resolve(), Path(output).resolve()
    data = rom.read_bytes()
    if digest(data) != load_manifest()["base_sha256"]:
        raise ValueError("Storage audit requires the verified Japanese original.")
    runs = uniform_runs(data)
    # These are candidates only: graphics and compressed data can resemble pointers.
    pointer_candidates = []
    for source in range(0, len(data) - 3, 4):
        value = struct.unpack_from("<I", data, source)[0]
        if 0x08000000 <= value < 0x0E000000:
            pointer_candidates.append((source, value, (value - 0x08000000) % EXPANDED_SIZE))
    largest = sorted(runs, key=lambda run: run["bytes"], reverse=True)[:20]
    for run in largest:
        refs = [(source, value) for source, value, target in pointer_candidates
                if run["start"] <= target < run["end"]]
        run["pointer_like_words_into_region"] = len(refs)
        run["pointer_like_examples"] = [{"source": f"0x{s:08X}", "value": f"0x{v:08X}"}
                                        for s, v in refs[:8]]
    blocks = []
    for start in range(0, len(data), 0x40000):
        block = data[start:start + 0x40000]
        counts = Counter(block)
        blocks.append({"start": f"0x{start:08X}", "bytes": len(block),
                       "zero_bytes": counts[0], "ff_bytes": counts[255],
                       "distinct_byte_values": len(counts)})
    # Conservative checkpoints from direct observations, not a complete asset map.
    regions = [
        {"start": "0x00000000", "end": "0x000000C0", "role": "Cartridge header and entry instruction"},
        {"start": "0x00084A10", "end": "0x00084E80", "role": "Contains traced title-menu code; end is an inspection boundary"},
        {"start": "0x0008BC4C", "end": "0x0008CD70", "role": "Contains traced text/glyph routines and literal data"},
        {"start": "0x00C78280", "end": "0x00C782E4", "role": "Verified menu pointer table and six strings"},
        {"start": "0x00C7C100", "end": "0x00C7DBB8", "role": "Font 0 printable ASCII bitmap slots"},
        {"start": "0x00C93B4C", "end": "0x00C97A58", "role": "Font 0 glyph descriptor table (1,345 x 12 bytes)"},
        {"start": "0x00D00000", "end": "0x00FD7AF4", "role": "Content-bearing region; asset types not yet identified"},
    ]
    footer = next(run for run in runs if run["end"] == len(data) and run["fill"] == 255)
    report = {
        "source_sha256": digest(data), "rom_bytes": len(data),
        "normal_gba_rom_capacity_bytes": EXPANDED_SIZE,
        "potential_expansion_bytes": EXPANDED_SIZE - len(data),
        "verified_reusable_bytes_inside_original": 0,
        "verified_reusable_bytes_note": "No original regions approved for allocation; zero means unverified, not necessarily unavailable.",
        "trailing_ff_candidate": footer,
        "uniform_ff_candidate_bytes": sum(run["bytes"] for run in runs if run["fill"] == 255),
        "uniform_zero_bytes_not_counted_as_free": sum(run["bytes"] for run in runs if run["fill"] == 0),
        "largest_uniform_regions": largest,
        "known_region_checkpoints": regions,
        "save_library_markers": [{"offset": f"0x{m.start():08X}", "marker": m.group().decode()}
                                 for m in re.finditer(rb"(?:FLASH512|FLASH1M|FLASH|SRAM|EEPROM)_V[0-9]{3}", data)],
        "blocks_256k": blocks,
        "limitations": ["Uniform bytes do not prove unused storage.",
                        "Pointer-like words are candidates, not confirmed code references.",
                        "Computed/relative pointers and unvisited execution paths are not exhaustively resolved.",
                        "This is an initial layout audit, not a complete text or asset extraction."],
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "storage-audit.json").write_text(json.dumps(report, indent=2) + "\n")
    (output / "uniform-regions.json").write_text(json.dumps(runs, indent=2) + "\n")
    print(json.dumps({key: report[key] for key in ("rom_bytes", "potential_expansion_bytes",
                      "verified_reusable_bytes_inside_original", "uniform_ff_candidate_bytes",
                      "uniform_zero_bytes_not_counted_as_free", "trailing_ff_candidate")}, indent=2))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rom", nargs="?", type=Path, default=ORIGINAL_ROM)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    audit(args.rom, args.output)
