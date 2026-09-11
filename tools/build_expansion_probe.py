"""Build a 32 MiB ROM with the first menu label in newly appended storage."""

import argparse
import json
from pathlib import Path
import struct

from tools.build_first_label import ORIGINAL_ROM, ROOT, digest, load_manifest

OUTPUT = ROOT / "build/storage-audit"
EXPANDED_SIZE = 0x02000000
LABEL_OFFSET = 0x01000000
LIMIT_PROBE_OFFSET = 0x01FFFFC0
PROOF_TEXT = "Start adventure"


def make_expanded_rom(original, text=PROOF_TEXT, offset=LABEL_OFFSET):
    manifest = load_manifest()
    if digest(original) != manifest["base_sha256"]:
        raise ValueError("Expansion requires the verified Japanese original.")
    if len(original) != 0x01000000:
        raise ValueError("Expected a 16 MiB source ROM.")
    source_offset = int(manifest["rom_offset"], 0)
    pointer_offset = int(manifest["pointer_offset"], 0)
    source = manifest["japanese"].encode("cp932") + b"\0"
    if original[source_offset:source_offset + len(source)] != source:
        raise ValueError("Source menu label mismatch.")
    if struct.unpack_from("<I", original, pointer_offset)[0] != 0x08000000 + source_offset:
        raise ValueError("Source menu pointer mismatch.")
    if not text or "\0" in text:
        raise ValueError("Text must be nonempty and contain no NUL.")
    encoded = text.encode("cp932") + b"\0"
    if offset % 4 or not len(original) <= offset <= EXPANDED_SIZE - len(encoded):
        raise ValueError("Relocated text must fit at a four-byte-aligned offset in the appended region.")
    result = bytearray(original)
    result.extend(b"\xff" * (EXPANDED_SIZE - len(original)))
    result[offset:offset + len(encoded)] = encoded
    struct.pack_into("<I", result, pointer_offset, 0x08000000 + offset)
    return bytes(result)


def build(rom=ORIGINAL_ROM, output=OUTPUT):
    rom, output = Path(rom).resolve(), Path(output).resolve()
    target = output / "torneko3-expansion-32m.gba"
    if target.resolve() == rom:
        raise ValueError("Output must be separate from the source ROM.")
    original = rom.read_bytes()
    expanded = make_expanded_rom(original)
    output.mkdir(parents=True, exist_ok=True)
    target.write_bytes(expanded)
    report = {
        "source_sha256": digest(original), "expanded_sha256": digest(expanded),
        "source_bytes": len(original), "expanded_bytes": len(expanded),
        "appended_bytes": len(expanded) - len(original),
        "label": PROOF_TEXT, "label_bytes_including_nul": len(PROOF_TEXT.encode("ascii")) + 1,
        "label_file_offset": f"0x{LABEL_OFFSET:08X}",
        "label_gba_address": f"0x{0x08000000 + LABEL_OFFSET:08X}",
        "pointer_file_offset": "0x00C78280", "original_label_preserved": True,
        "changed_bytes_in_original_region": sum(a != b for a, b in zip(original, expanded)),
        "remaining_appended_bytes": len(expanded) - len(original) - len(PROOF_TEXT) - 1,
        "status": "Storage proof; not a final translation or full-game compatibility certification",
    }
    (output / "expansion-build.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rom", nargs="?", type=Path, default=ORIGINAL_ROM)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    print(json.dumps(build(args.rom, args.output), indent=2))
