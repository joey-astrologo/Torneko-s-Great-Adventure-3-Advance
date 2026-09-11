"""Build and verify unchanged Japanese relocation through three text systems."""

import argparse
import json
from pathlib import Path
import struct

import mgba.log
from PIL import Image

from tools.build_first_label import ORIGINAL_ROM, ROOT, digest, load_manifest
from tools.build_expansion_probe import EXPANDED_SIZE
from tools.inventory_text import parse_text
from tools.trace_text_systems import OUTPUT, capture_route
from tools.verify_first_label import require

MANIFEST = ROOT / "translations/proof/text_systems.json"


def build(data):
    require(digest(data) == load_manifest()["base_sha256"], "Expected verified Japanese original")
    expanded = bytearray(data)
    expanded.extend(b"\xFF" * (EXPANDED_SIZE - len(data)))
    cursor, allocations = len(data), []
    for entry in json.loads(MANIFEST.read_text())["entries"]:
        offset, pointer = int(entry["source_offset"], 16), int(entry["pointer_offset"], 16)
        raw = data[offset:offset + entry["source_bytes"]]
        require(digest(raw) == entry["source_sha256"], "Source text does not match manifest")
        parsed = parse_text(data, offset)
        require(parsed and bytes.fromhex(parsed["raw_hex"]) == raw, "Manifest does not cover exactly one supported string")
        require(struct.unpack_from("<I", data, pointer)[0] == 0x08000000 + offset, "Unexpected source pointer")
        cursor = (cursor + 3) & ~3
        require(cursor + len(raw) <= EXPANDED_SIZE, "Allocation exceeds GBA ROM limit")
        expanded[cursor:cursor + len(raw)] = raw
        struct.pack_into("<I", expanded, pointer, 0x08000000 + cursor)
        allocations.append({**entry, "destination_offset": f"0x{cursor:08X}",
                            "destination_address": f"0x{0x08000000 + cursor:08X}"})
        cursor += len(raw)
    # All original bytes except explicitly listed pointers must remain intact.
    restored = bytearray(expanded[:len(data)])
    for entry in allocations:
        pointer = int(entry["pointer_offset"], 16)
        restored[pointer:pointer + 4] = data[pointer:pointer + 4]
    require(restored == data, "Unexpected modification inside original ROM")
    return bytes(expanded), allocations


def verify(rom=ORIGINAL_ROM, output=OUTPUT / "relocation"):
    rom, output = Path(rom).resolve(), Path(output).resolve()
    data = rom.read_bytes()
    expanded, allocations = build(data)
    output.mkdir(parents=True, exist_ok=True)
    (output / "torneko3-text-systems-32m.gba").write_bytes(expanded)
    mgba.log.silence()
    routes = []
    saves = {}
    for allocation in allocations:
        route = allocation["route"]
        reports = []
        for variant, rom_data in (("original", data), ("expanded", expanded)):
            source = (0x08000000 + int(allocation["source_offset"], 16) if variant == "original"
                      else int(allocation["destination_address"], 16))
            pointer = 0x08000000 + int(allocation["pointer_offset"], 16)
            directory = output / variant / route
            report, save = capture_route(rom_data, directory, route,
                                         saves[variant] if route == "story" else None,
                                         (pointer, source))
            if route == "creation":
                saves[variant] = save
            require(any(int(r["address"], 16) == pointer for r in report["source_reads"]),
                    "Expected source pointer was not read")
            require(any(int(r["address"], 16) == source and r["instruction"] == "0x0807DBB2"
                        for r in report["source_reads"]), "Formatter did not read the expected source")
            formats = [f for f in report["formats"] if int(f["source"], 16) == source]
            require(formats, "Relocated source did not enter the formatter")
            reports.append((report, formats))
        images = sorted(p.name for p in (output / "original" / route).glob("*.png"))
        require(images, "No route screenshots")
        for name in images:
            with Image.open(output / "original" / route / name) as a, Image.open(output / "expanded" / route / name) as b:
                require(a.convert("RGB").tobytes() == b.convert("RGB").tobytes(), f"Pixels differ: {route}/{name}")
        for key in ("reads", "draws", "glyphs"):
            require(reports[0][0][key] == reports[1][0][key], f"Downstream {key} changed on {route}")
        require([r["output_hex"] for r in reports[0][1]] == [r["output_hex"] for r in reports[1][1]],
                "Formatted output changed after relocation")
        routes.append({"route": route, "screenshots_identical": images,
                       "decoder_and_glyph_traces_identical": True,
                       "formatter_output_identical": True,
                       "source_read_instructions": sorted({r["instruction"] for r in reports[1][0]["source_reads"]}),
                       "formatter_calls": reports[1][1]})
        print(f"Passed {route}: {len(images)} screenshots; formatter and rendering traces match", flush=True)
    require(saves["original"] == saves["expanded"], "Created cartridge saves differ")
    require(rom.read_bytes() == data, "Source ROM changed")
    report = {"passed": True, "source_sha256": digest(data), "expanded_sha256": digest(expanded),
              "allocations": allocations, "allocated_payload_bytes": sum(a["source_bytes"] for a in allocations),
              "routes": routes, "created_saves_identical": True, "save_sha256": digest(saves["original"]),
              "scope": "Unchanged Japanese relocation on recorded settings, new-log, and opening-story routes; not full-game coverage or longer-text capacity certification"}
    (output / "verification.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rom", nargs="?", type=Path, default=ORIGINAL_ROM)
    parser.add_argument("--output", type=Path, default=OUTPUT / "relocation")
    args = parser.parse_args()
    verify(args.rom, args.output)
