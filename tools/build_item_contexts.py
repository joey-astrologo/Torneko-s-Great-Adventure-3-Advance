"""Combine complete unidentified-name and synthesis tables with the item build."""

import argparse
import json
from pathlib import Path
import struct

from tools.build_first_label import ORIGINAL_ROM, ROOT, digest, load_manifest
from tools.build_items import CATALOG as ITEMS, build_item_rom, encode_english as encode_item
from tools.game_text import GameTextCodec, rebuild
from tools.rom_build import RomBuild
from tools.translation_pipeline import FontZero, atomic_write, check, load_json

CATALOG = ROOT / "translations/item-contexts.json"
OUTPUT = ROOT / "build/item-contexts"
# Table offset, record count, stride and pointer field offset.
TABLES = {"unidentified": (0x190808, 246, 8, 4), "synthesis": (0x1B3A60, 100, 4, 0)}
# Cross-referenced item names follow translations/glossary.json and items.json.
DRAFTS = {
    "context.unidentified.000": "Cedar staff",
    "context.unidentified.052": "Pyrope ring",
    "context.unidentified.112": "Giraffe scroll",
    "context.unidentified.172": "Narrow pot",
    "context.unidentified.201": "Red herb",
    "context.unidentified.234": "Warm bread",
    "context.synthesis.001": "Plating scroll / Oaken club\nPrevents weapon deterioration.",
    "context.synthesis.002": "Dragonsbane synthesis\nDeals extra damage to fire-type\nmonsters.",
    "context.synthesis.033": "Blade shield synthesis\nReflects some damage received\nfrom monsters.",
    "context.synthesis.038": "Passage ring synthesis\nLets you walk on water.",
}


def extract_catalog(original):
    check(digest(original) == load_manifest()["base_sha256"], "Context extraction requires the pinned Japanese original")
    codec, entries = GameTextCodec(original), []
    for family, (base, count, stride, field) in TABLES.items():
        sources = {}
        for row in range(count):
            word = base + row * stride + field
            offset = struct.unpack_from("<I", original, word)[0] - 0x08000000
            parsed = codec.parse(original, offset)
            raw = rebuild(parsed["tokens"])
            check(raw == original[offset:parsed["end"]], "Context extraction is not lossless")
            if offset not in sources:
                gap = family == "synthesis" and b"\x1d" in raw
                check(not gap or raw.count(b"\x1d") == 1 and b"\r\x1d" in raw, "Unsupported synthesis source layout")
                sources[offset] = {"id": f"context.{family}.{row:03d}", "family": family,
                    "rows": [], "offset": f"0x{offset:08X}", "pointer_offsets": [], "category_fields": [],
                    "layout": "name" if family == "unidentified" else "synthesis_gap" if gap else "synthesis_plain",
                    "japanese": parsed["display"], "source_hex": raw.hex(), "source_tokens": parsed["tokens"],
                    "master_id": f"jp_{offset:08x}", "english": None, "notes": ""}
            entry = sources[offset]
            entry["rows"].append(row)
            entry["pointer_offsets"].append(f"0x{word:08X}")
            if field:
                category = struct.unpack_from("<I", original, word - 4)[0]
                check(category in (3, 7, 8, 9, 10, 11), "Unexpected unidentified-name category")
                entry["category_fields"].append({"offset": f"0x{word - 4:08X}", "value": category})
        entries.extend(sources.values())
    return {"schema": 1, "base_sha256": digest(original), "font": 0, "entries": entries}


def validate_catalog(original, catalog):
    fresh = extract_catalog(original)
    check(all(catalog[k] == fresh[k] for k in ("schema", "base_sha256", "font")), "Context catalog base/schema/font mismatch")
    entries = {e["id"]: e for e in catalog["entries"]}
    check(len(entries) == len(catalog["entries"]), "Duplicate context catalog ID")
    check(entries.keys() == {e["id"] for e in fresh["entries"]}, "Context catalog must cover both complete tables")
    for source in fresh["entries"]:
        entry = entries[source["id"]]
        for key in source.keys() - {"english", "notes"}:
            check(entry[key] == source[key], f"Context source metadata changed: {source['id']}/{key}")
        check(entry["english"] is None or isinstance(entry["english"], str), "Context English must be text or null")
        check(isinstance(entry.get("notes", ""), str), "Context notes must be text")
    return entries


def initialize_catalog(original, path=CATALOG):
    path = Path(path)
    if path.exists():
        catalog = load_json(path)
        validate_catalog(original, catalog)
        return catalog
    catalog = extract_catalog(original)
    for entry in catalog["entries"]:
        if entry["id"] in DRAFTS:
            entry.update(english=DRAFTS[entry["id"]], notes="Independent draft from Japanese; insertion example, terminology remains editable.")
    atomic_write(path, (json.dumps(catalog, ensure_ascii=False, indent=2) + "\n").encode())
    return catalog


def encode_english(entry, font):
    if entry["layout"] == "name":
        return encode_item({"family": "name", "english": entry["english"]}, font)
    # Reuse printable-text and font-0 ink/advance checks, then apply the actual
    # synthesis reader's vertical profile rather than ordinary item description rules.
    _, metrics = encode_item({"family": "description", "english": entry["english"]}, font)
    lines = entry["english"].split("\n")
    if entry["layout"] == "synthesis_gap":
        check(2 <= len(lines) <= 3, "Synthesis requires one heading and one or two effect lines")
        payload = lines[0].encode() + b"\r\x1d" + b"\r".join(line.encode() for line in lines[1:]) + b"\0"
        ys = [48] + [67 + i * 13 for i in range(len(lines) - 1)]
    else:
        check(entry["layout"] == "synthesis_plain" and len(lines) == 1, "Plain synthesis placeholder must be one line")
        payload, ys = lines[0].encode() + b"\r\0", [48]
    check(all(y + 12 <= 100 for y in ys), "Synthesis text collides with statistics footer")
    # sprintf's fixed style wrapper adds three bytes; the native destination is 1024 bytes.
    check(len(payload) + 3 <= 1024, "Synthesis wrapper exceeds its native stack buffer")
    return payload, {**metrics, "line_y": ys, "encoded_bytes_including_nul": len(payload),
                     "wrapped_bytes_including_nul": len(payload) + 3, "wrapper_buffer_bytes": 1024}


def add_contexts(build, catalog, language="english"):
    check(language in ("english", "japanese"), "Unsupported context language")
    entries = validate_catalog(build.original, catalog)
    font, prepared, checks = FontZero(build.original), {}, {}
    for ident, entry in entries.items():
        raw = rebuild(entry["source_tokens"])
        offset = int(entry["offset"], 0)
        build.protect_source(ident, offset, offset + len(raw), "item-contexts")
        for field in entry["category_fields"]:
            at = int(field["offset"], 0)
            build.protect_source(f"{ident}.category-{at:08x}", at, at + 4, "item-contexts")
        if language == "english" and entry["english"] is not None:
            raw, checks[ident] = encode_english(entry, font)
        prepared[ident] = raw
    allocations = []
    for ident in sorted(entries):
        entry = entries[ident]
        at = build.allocate(ident, prepared[ident], "item-contexts")
        for word in entry["pointer_offsets"]:
            build.patch(ident, int(word, 0), struct.pack("<I", int(entry["offset"], 0) + 0x08000000),
                        struct.pack("<I", at + 0x08000000), "item-contexts", f"Relocate complete {entry['family']} table entry")
        allocations.append({"id": ident, "offset": at, "bytes": len(prepared[ident]), "translated": ident in checks})
    return {"language": language, "entries": len(entries), "pointer_words": sum(len(e["pointer_offsets"]) for e in entries.values()),
            "translated_entries": len(checks), "allocations": allocations, "checks": checks,
            "catalog_sha256": digest(json.dumps(catalog, sort_keys=True, ensure_ascii=False).encode())}


def build_context_rom(original, catalog, language="english", item_catalog=None):
    build = RomBuild(original)
    _, previous = build_item_rom(original, load_json(ITEMS) if item_catalog is None else item_catalog, build=build)
    contexts = add_contexts(build, catalog, language)
    data, ledger = build.finish()
    return data, {"source_sha256": digest(original), "rom_sha256": digest(data), "contexts": contexts,
                  "item_build_sha256_before_contexts": previous["rom_sha256"], "ledger": ledger,
                  "appended_used_with_padding": ledger["appended_used_with_padding"], "appended_remaining": ledger["appended_remaining"]}


def build(rom=ORIGINAL_ROM, catalog_path=CATALOG, output=OUTPUT, language="english"):
    rom, catalog_path, output = Path(rom).resolve(), Path(catalog_path).resolve(), Path(output).resolve()
    target, report_path = output / f"torneko3-item-contexts-{language}.gba", output / f"{language}-build.json"
    check(catalog_path.suffix == ".json" and len({rom, catalog_path, target.resolve(), report_path.resolve(), ITEMS.resolve()}) == 5,
          "Build output overlaps an input or catalog has invalid extension")
    original = rom.read_bytes()
    catalog = initialize_catalog(original, catalog_path)
    data, report = build_context_rom(original, catalog, language)
    atomic_write(target, data)
    atomic_write(report_path, (json.dumps(report, indent=2) + "\n").encode())
    print(json.dumps({"rom": str(target), "rom_sha256": report["rom_sha256"],
                      "new_strings": report["contexts"]["entries"], "new_pointer_words": report["contexts"]["pointer_words"],
                      "new_english_entries": report["contexts"]["translated_entries"],
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
