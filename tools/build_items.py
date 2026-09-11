"""Build the complete item-text family with menus and seven-letter naming."""

import argparse
import json
from pathlib import Path
import struct

from tools.build_first_label import ORIGINAL_ROM, ROOT, digest, load_manifest
from tools.build_name_entry import build_name_rom
from tools.game_text import GameTextCodec, rebuild
from tools.rom_build import RomBuild
from tools.translation_pipeline import FontZero, atomic_write, check, load_json

CATALOG = ROOT / "translations/items.json"
OUTPUT = ROOT / "build/items"
TABLES = {"name": (0x18F16C, 370), "description": (0x1B3498, 370)}
# Conservative draft limits reserve name space for decorations and description
# space for the information panel's extra line at y=100. Native checks still
# verify the formatted result, not merely these raw-text limits.
NAME_BYTES, NAME_WIDTH = 32, 100
DESCRIPTION_LINES, DESCRIPTION_WIDTH = 5, 192
# Keep starter terminology in sync with translations/glossary.json and items.json.
STARTER_DRAFTS = {
    1: ("Oaken club", "Raises attack power while equipped.\nThis weapon will not deteriorate."),
    3: ("Copper sword", "Raises attack power while equipped."),
    4: ("Iron axe", "Raises attack power while equipped."),
    5: ("Dragonsbane", "Raises attack power while equipped.\nDeals extra damage to fire-type\nmonsters."),
    58: ("Wooden shield", "Raises defence while equipped."),
    273: ("Medicinal herb", "Drink to restore a little HP.\nThrowing it heals most monsters,\nbut harms undead monsters."),
    304: ("Bread", "Eat to restore a little fullness."),
    305: ("Big bread", "Eat to restore fullness."),
}


def extract_catalog(original):
    check(digest(original) == load_manifest()["base_sha256"], "Item extraction requires the pinned Japanese original")
    codec, entries = GameTextCodec(original), []
    for family, (base, count) in TABLES.items():
        sources = {}
        for row in range(count):
            word = base + row * 4
            offset = struct.unpack_from("<I", original, word)[0] - 0x08000000
            parsed = codec.parse(original, offset)
            check(rebuild(parsed["tokens"]) == original[offset:parsed["end"]], "Item extraction is not lossless")
            if offset not in sources:
                sources[offset] = {"id": f"item.{family}.{row:03d}", "family": family,
                    "item_indices": [], "offset": f"0x{offset:08X}", "pointer_offsets": [],
                    "japanese": parsed["display"], "source_hex": parsed["raw_hex"],
                    "source_tokens": parsed["tokens"], "master_id": f"jp_{offset:08x}",
                    "english": None, "notes": ""}
            sources[offset]["item_indices"].append(row)
            sources[offset]["pointer_offsets"].append(f"0x{word:08X}")
        entries.extend(sources.values())
    return {"schema": 1, "base_sha256": digest(original), "font": 0, "entries": entries}


def initialize_catalog(original, path=CATALOG):
    path = Path(path)
    fresh = extract_catalog(original)
    if path.exists():
        existing = load_json(path)
        validate_catalog(original, existing)
        return existing
    for entry in fresh["entries"]:
        examples = [STARTER_DRAFTS[i][entry["family"] == "description"] for i in entry["item_indices"] if i in STARTER_DRAFTS]
        if examples:
            check(len(set(examples)) == 1, "Aliased item rows have different English drafts")
            entry["english"] = examples[0]
            entry["notes"] = "Independent draft from Japanese; insertion test, terminology remains editable."
    atomic_write(path, (json.dumps(fresh, ensure_ascii=False, indent=2) + "\n").encode())
    return fresh


def validate_catalog(original, catalog):
    fresh = extract_catalog(original)
    check(all(catalog[k] == fresh[k] for k in ("schema", "base_sha256", "font")), "Item catalog base/schema/font mismatch")
    entries = {e["id"]: e for e in catalog["entries"]}
    check(len(entries) == len(catalog["entries"]), "Duplicate item catalog ID")
    check(entries.keys() == {e["id"] for e in fresh["entries"]}, "Item catalog must cover both complete tables")
    for source in fresh["entries"]:
        entry = entries[source["id"]]
        for key in source.keys() - {"english", "notes"}:
            check(entry[key] == source[key], f"Item source metadata changed: {source['id']}/{key}")
        check(entry["english"] is None or isinstance(entry["english"], str), "Item English must be text or null")
        check(isinstance(entry.get("notes", ""), str), "Item notes must be text")
    return entries


def encode_english(entry, font):
    english = entry["english"]
    check(isinstance(english, str) and english, "Item English must be nonempty")
    check(all(c == "\n" or 32 <= ord(c) <= 126 for c in english), "Item English requires printable ASCII and LF")
    check(not any(c in english for c in "$%`{}"), "Item text does not accept formatter/control commands")
    lines = english.split("\n")
    check(all(lines), "Empty item text lines are unsupported")
    width = NAME_WIDTH if entry["family"] == "name" else DESCRIPTION_WIDTH
    max_lines = 1 if entry["family"] == "name" else DESCRIPTION_LINES
    check(len(lines) <= max_lines, f"Item text exceeds {max_lines} lines")
    measurements = []
    for line in lines:
        x = right = 0
        for character in line:
            _, advance, ink = font.glyph(character)
            if ink:
                right = max(right, x + ink)
            x += advance
        check(max(x, right) <= width, f"Item line exceeds {width} pixels")
        measurements.append({"advance": x, "ink_right": right})
    payload = english.replace("\n", "\r").encode("ascii")
    if entry["family"] == "name":
        check(len(payload) <= NAME_BYTES, "Item name leaves insufficient formatter byte reserve")
    else:
        payload += b"\r"
    return payload + b"\0", {"lines": measurements, "raw_width_limit": width,
                               "encoded_bytes_including_nul": len(payload) + 1}


def add_items(build, catalog, language="english"):
    check(language in ("japanese", "english"), "Unsupported item language")
    entries = validate_catalog(build.original, catalog)
    font = FontZero(build.original)
    prepared, measurements = {}, {}
    for ident, entry in entries.items():
        raw = rebuild(entry["source_tokens"])
        check(raw.hex() == entry["source_hex"], "Item source token reconstruction failed")
        offset = int(entry["offset"], 0)
        build.protect_source(ident, offset, offset + len(raw), "items")
        if language == "english" and entry["english"] is not None:
            raw, measurements[ident] = encode_english(entry, font)
        prepared[ident] = raw
    allocations = []
    for ident in sorted(entries):
        entry = entries[ident]
        at = build.allocate(ident, prepared[ident], "items")
        for word in entry["pointer_offsets"]:
            offset = int(word, 0)
            build.patch(ident, offset, struct.pack("<I", 0x08000000 + int(entry["offset"], 0)),
                        struct.pack("<I", 0x08000000 + at), "items", f"Relocate complete item {entry['family']} table entry")
        allocations.append({"id": ident, "family": entry["family"], "item_indices": entry["item_indices"],
                            "offset": at, "source_offset": int(entry["offset"], 0),
                            "bytes": len(prepared[ident]), "translated": ident in measurements})
    return {"language": language, "entries": len(entries), "table_pointer_words": sum(len(e["pointer_offsets"]) for e in entries.values()),
            "translated_entries": len(measurements), "allocations": allocations, "checks": measurements,
            "catalog_sha256": digest(json.dumps(catalog, sort_keys=True, ensure_ascii=False).encode())}


def build_item_rom(original, catalog, language="english", build=None):
    build = RomBuild(original) if build is None else build
    _, name_report = build_name_rom(original, build=build)
    items = add_items(build, catalog, language)
    data, ledger = build.finish()
    return data, {"source_sha256": digest(original), "rom_sha256": digest(data),
                  "items": items, "ledger": ledger, "name_build_sha256_before_items": name_report["rom_sha256"],
                  "appended_used_with_padding": ledger["appended_used_with_padding"],
                  "appended_remaining": ledger["appended_remaining"]}


def build(rom=ORIGINAL_ROM, catalog_path=CATALOG, output=OUTPUT, language="english"):
    rom, catalog_path, output = Path(rom).resolve(), Path(catalog_path).resolve(), Path(output).resolve()
    check(catalog_path.suffix == ".json" and catalog_path != rom, "Invalid item catalog output path")
    target = output / f"torneko3-items-{language}.gba"
    report_path = output / f"{language}-build.json"
    check(len({rom, catalog_path, target.resolve(), report_path.resolve()}) == 4, "Build output overlaps an input")
    original = rom.read_bytes()
    catalog = initialize_catalog(original, catalog_path)
    data, report = build_item_rom(original, catalog, language)
    atomic_write(target, data)
    atomic_write(report_path, (json.dumps(report, indent=2) + "\n").encode())
    print(json.dumps({"rom": str(target), "rom_sha256": report["rom_sha256"],
                     "item_entries": report["items"]["entries"], "table_pointer_words": report["items"]["table_pointer_words"],
                     "translated_entries": report["items"]["translated_entries"],
                     "appended_used_with_padding": report["appended_used_with_padding"]}, indent=2))
    return data, report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rom", nargs="?", type=Path, default=ORIGINAL_ROM)
    parser.add_argument("--catalog", type=Path, default=CATALOG)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--language", choices=("japanese", "english"), default="english")
    args = parser.parse_args()
    build(args.rom, args.catalog, args.output, args.language)
