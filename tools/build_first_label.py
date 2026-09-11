"""Build the first text-only proof patch from the verified Japanese ROM."""

import argparse
import hashlib
import json
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL_ROM = ROOT / "Dragon Quest Characters - Torneko no Daibouken 3 Advance - Fushigi no Dungeon (Japan).gba"
MANIFEST = ROOT / "translations/proof/title_begin.json"
OUTPUT = ROOT / "build/first-label"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def load_manifest():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def patch_rom(original, manifest):
    """Require the Japanese base and preserve the label's fixed allocation."""
    if digest(original) != manifest["base_sha256"]:
        raise ValueError("ROM hash mismatch: this proof requires the verified Japanese original.")
    offset = int(manifest["rom_offset"], 0)
    pointer = int(manifest["pointer_offset"], 0)
    size = manifest["field_bytes"]
    source = manifest["japanese"].encode(manifest["encoding"])
    translated = manifest["english"].encode(manifest["encoding"])
    if not translated or b"\0" in translated or len(translated) >= size:
        raise ValueError("The label must be nonempty, contain no NUL, and fit with its terminator.")
    if len(source) >= size or original[offset:offset + size] != source.ljust(size, b"\0"):
        raise ValueError("Original label bytes or padding do not match the manifest.")
    if struct.unpack_from("<I", original, pointer)[0] != 0x08000000 + offset:
        raise ValueError("The title menu pointer does not reference the expected label.")
    replacement = translated.ljust(size, b"\0")
    patched = original[:offset] + replacement + original[offset + size:]
    # This proof uses one ordinary IPS record; no RLE or ROM expansion is needed.
    ips = b"PATCH" + offset.to_bytes(3, "big") + size.to_bytes(2, "big") + replacement + b"EOF"
    return patched, ips


def build(rom=ORIGINAL_ROM, output=OUTPUT):
    rom, output = Path(rom).resolve(), Path(output).resolve()
    target = output / "torneko3-title-begin.gba"
    if target.resolve() == rom:
        raise ValueError("Output must be separate from the source ROM.")
    original = rom.read_bytes()
    manifest = load_manifest()
    patched, ips = patch_rom(original, manifest)
    output.mkdir(parents=True, exist_ok=True)
    target.write_bytes(patched)
    (output / "torneko3-title-begin.ips").write_bytes(ips)
    report = {
        "label": manifest,
        "source_rom": rom.name,
        "source_sha256": digest(original),
        "patched_sha256": digest(patched),
        "rom_bytes": len(patched),
        "changed_bytes": sum(a != b for a, b in zip(original, patched)),
        "ips_sha256": digest(ips),
    }
    (output / "build-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rom", nargs="?", type=Path, default=ORIGINAL_ROM)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    print(json.dumps(build(args.rom, args.output), ensure_ascii=False, indent=2))
