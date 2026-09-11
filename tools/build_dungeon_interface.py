"""Translate complete dungeon, trap, search-message and fixed action families."""

import argparse
import json
from pathlib import Path
import struct

from tools.build_first_label import ORIGINAL_ROM, ROOT, digest, load_manifest
from tools.build_name_entry import build_name_rom
from tools import build_items, build_item_contexts, build_enemies
from tools.game_text import GameTextCodec, rebuild
from tools.rom_build import RomBuild
from tools.translation_pipeline import FontZero, atomic_write, check, load_json

CATALOG = ROOT / "translations/dungeon-interface.json"
OUTPUT = ROOT / "build/dungeon-interface"
TABLES = {"dungeon": (0x1B3F60, 64), "trap": (0x1B421C, 23), "search": (0x86F4D8, 21)}
ACTION_BASE, ACTION_COUNT, ACTION_STRIDE = 0x1B4281, 41, 12
ACTION_POINTERS = (0x6FBF4, 0x7003C, 0x75760)
WINDOW_POINTERS = (0x6FAA0, 0x6FFB4, 0x75750)
HERO_BASE, HERO_STRIDE = 0x1B453E, 10
HERO_POINTERS = (0x32A18, 0x32B78, 0x32CD8, 0x32D9C, 0x32DE8, 0x78940, 0x7DA7C)
GROUND_SEARCH = ((0x917884, 0x91784C), (0x917860, 0x917854))
EXTRAS = {0x1B4278: (0x20760, 0x702A8), 0xC3DA60: (0x6F5EC,),
          0xC3EE5C: (0x75768,), 0xC3EE84: (0x761B4,)}


def extract_catalog(original):
    check(digest(original) == load_manifest()["base_sha256"], "Interface extraction requires pinned Japanese ROM")
    codec, entries = GameTextCodec(original), []

    def entry(family, row, offset):
        source = codec.parse(original, offset)
        check(rebuild(source["tokens"]) == original[offset:source["end"]], "Interface source is not lossless")
        return {"id": f"interface.{family}.{row:03d}", "family": family, "rows": [],
                "offset": f"0x{offset:08X}", "pointer_offsets": [], "japanese": source["display"],
                "source_hex": source["raw_hex"], "source_tokens": source["tokens"],
                "master_id": f"jp_{offset:08x}", "english": None, "display": None, "notes": ""}

    for family, (base, count) in TABLES.items():
        sources = {}
        for row in range(count):
            word = base + row * 4
            offset = struct.unpack_from("<I", original, word)[0] - 0x08000000
            if offset not in sources:
                sources[offset] = entry(family, row, offset)
            sources[offset]["rows"].append(row)
            sources[offset]["pointer_offsets"].append(f"0x{word:08X}")
        entries.extend(sources.values())
    for row, (offset, pointer) in enumerate(GROUND_SEARCH, 21):
        e = entry("search", row, offset)
        e["rows"], e["pointer_offsets"] = [row], [f"0x{pointer:08X}"]
        check(struct.unpack_from("<I", original, pointer)[0] == offset + 0x08000000, "Ground-search pointer changed")
        entries.append(e)
    for row in range(2):
        e = entry("hero", row, HERO_BASE + row * HERO_STRIDE)
        e["rows"] = [row]
        raw = bytes.fromhex(e["source_hex"])
        check(original[HERO_BASE + row * 10:HERO_BASE + (row + 1) * 10] == raw.ljust(10, b"\0"), "Hero stride/padding changed")
        entries.append(e)
    for row in range(ACTION_COUNT):
        offset = ACTION_BASE + row * ACTION_STRIDE
        e = entry("action", row, offset)
        e["rows"] = [row]
        raw = bytes.fromhex(e["source_hex"])
        check(raw.startswith(b"\x03\x05\x07") and len(raw) <= ACTION_STRIDE and
              original[offset:offset + ACTION_STRIDE] == raw.ljust(ACTION_STRIDE, b"\0"),
              "Fixed action record has unexpected style, length or padding")
        entries.append(e)
    for row, (offset, pointers) in enumerate(EXTRAS.items()):
        e = entry("override", row, offset)
        e["rows"], e["pointer_offsets"] = [row], [f"0x{p:08X}" for p in pointers]
        for pointer in pointers:
            check(struct.unpack_from("<I", original, pointer)[0] == offset + 0x08000000, "Override source pointer changed")
        entries.append(e)
    return {"schema": 1, "base_sha256": digest(original), "font": 0, "entries": entries}


def validate_catalog(original, catalog):
    fresh = extract_catalog(original)
    check(all(catalog[k] == fresh[k] for k in ("schema", "base_sha256", "font")), "Interface header changed")
    entries = {e["id"]: e for e in catalog["entries"]}
    check(len(entries) == len(catalog["entries"]) and entries.keys() == {e["id"] for e in fresh["entries"]},
          "Interface catalog must cover all complete families without duplicate IDs")
    for source in fresh["entries"]:
        e = entries[source["id"]]
        for key in source.keys() - {"english", "display", "notes"}:
            check(e[key] == source[key], f"Interface source metadata changed: {e['id']}/{key}")
        check(isinstance(e["english"], str) and e["english"], f"Missing interface English: {e['id']}")
        check(e["display"] is None or isinstance(e["display"], str) and e["display"], "Invalid display override")
        check(isinstance(e["notes"], str), "Interface notes must be text")
    return entries


def measure(text, font):
    x = right = 0
    for c in text:
        _, advance, ink = font.glyph(c)
        right = max(right, x + ink)
        x += advance
    return max(x, right)


def encode_english(entry, font):
    text = entry["display"] or entry["english"]
    check(text and all(32 <= ord(c) < 127 or c == "\n" for c in text), "Interface text must be printable ASCII/LF")
    family = entry["family"]
    check(not any(c in text for c in "%`{}"), "Interface text contains an unsupported format/control")
    if family == "search":
        check(text.count("$t") == entry["japanese"].count("$t") and "$" not in text.replace("$t", ""),
              "Search messages must preserve the exact player-name substitution")
        # Conservative seven-letter allowance. Native $t selects the fixed
        # protagonist table (Torneko/Tipper), not the Adventure Log name.
        widest = max("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz", key=lambda c: measure(c, font))
        visible = text.replace("$t", widest * 7)
        check(len(text.split("\n")) <= 3, "Search message exceeds three lines")
        limit = 208
        raw = text.encode() + b"\0"
        check(len(visible.encode()) + 1 <= 1000, "Search formatter buffer exceeded")
    else:
        check("$" not in text and "\n" not in text, "Interface labels must be single-line literals")
        visible = text
        raw = text.encode() + b"\0"
        if family == "hero":
            check(len(raw) <= HERO_STRIDE, "Hero label exceeds fixed ten-byte record")
            limit = 120
        elif family == "action":
            check(len(raw) <= 9, "Action text exceeds eight-byte fixed record payload")
            raw = b"\x03\x05\x07" + raw
            limit = 44  # Warehouse draws at x4 inside its 48px action window.
        elif family == "override":
            if bytes.fromhex(entry["source_hex"]).startswith(b"\x03\x05\x07"):
                raw = b"\x03\x05\x07" + raw
            limit = 44
        else:
            check(len(raw) <= 30, "Dungeon/trap name exceeds conservative 29-byte payload")
            limit = 98 if family == "dungeon" else 144
    widths = [measure(line, font) for line in visible.split("\n")]
    check(max(widths) <= limit, f"Interface label exceeds {limit}px: {entry['id']} / {max(widths)}")
    return raw, {"widths": widths, "pixel_limit": limit, "bytes_including_nul": len(raw)}


def add_interface(build, catalog, language="english"):
    check(language in ("english", "japanese"), "Unsupported interface language")
    entries = validate_catalog(build.original, catalog)
    font, prepared, metrics = FontZero(build.original), {}, {}
    for ident, e in entries.items():
        raw, offset = bytes.fromhex(e["source_hex"]), int(e["offset"], 0)
        build.protect_source(ident, offset, offset + len(raw), "dungeon-interface")
        english, metrics[ident] = encode_english(e, font)
        prepared[ident] = english if language == "english" else raw
    hero_block = b"".join(prepared[f"interface.hero.{row:03d}"].ljust(HERO_STRIDE, b"\0") for row in range(2))
    build.protect_source("interface.hero-table", HERO_BASE, HERO_BASE + len(hero_block), "dungeon-interface")
    hero_at = build.allocate("interface.hero-table", hero_block, "dungeon-interface")
    for pointer in HERO_POINTERS:
        build.patch(f"interface.hero-base.{pointer:08x}", pointer, struct.pack("<I", HERO_BASE + 0x08000000),
                    struct.pack("<I", hero_at + 0x08000000), "dungeon-interface", "Relocate built-in Torneko/Tipper pair; preserve ten-byte stride")
    block = bytearray()
    for row in range(ACTION_COUNT):
        raw = prepared[f"interface.action.{row:03d}"]
        block.extend(raw.ljust(ACTION_STRIDE, b"\0"))
    build.protect_source("interface.action-table", ACTION_BASE, ACTION_BASE + len(block), "dungeon-interface")
    base = build.allocate("interface.action-table", block, "dungeon-interface")
    for pointer in ACTION_POINTERS:
        build.patch(f"interface.action-base.{pointer:08x}", pointer, struct.pack("<I", ACTION_BASE + 0x08000000),
                    struct.pack("<I", base + 0x08000000), "dungeon-interface", "Complete fixed action table; preserve 12-byte stride")
    windows = []
    if language == "english":
        source_format = b"\x03\x12%s " + "問題".encode("cp932") + b"%d\0"
        check(build.original[0xC3D910:0xC3D910 + len(source_format)] == source_format, "Puzzle header format changed")
        build.protect_source("interface.puzzle-format", 0xC3D910, 0xC3D910 + len(source_format), "dungeon-interface")
        at = build.allocate("interface.puzzle-format", b"\x03\x12%s #%d\0", "dungeon-interface")
        build.patch("interface.puzzle-format", 0x6CD18, struct.pack("<I", 0x08C3D910),
                    struct.pack("<I", at + 0x08000000), "dungeon-interface", "Compact puzzle-number header; preserve both arguments")
        for pointer in WINDOW_POINTERS:
            offset = struct.unpack_from("<I", build.original, pointer)[0] - 0x08000000
            raw = bytearray(build.original[offset:offset + 64])
            check(struct.unpack_from("<h", raw, 16)[0] in (23, 24) and
                  struct.unpack_from("<h", raw, 20)[0] in (4, 5), "Action window profile changed")
            ident = f"interface.window.{pointer:08x}"
            build.protect_source(ident, offset, offset + 64, "dungeon-interface")
            struct.pack_into("<h", raw, 16, 23)
            struct.pack_into("<h", raw, 20, 6)
            if pointer == 0x75750:
                # Warehouse actions occupy window 2; window 1 is the lower
                # side panel. Both retain their aligned right-hand column.
                check(struct.unpack_from("<2h", raw, 32)[0] == 23 and
                      struct.unpack_from("<h", raw, 36)[0] == 5, "Warehouse action geometry changed")
                struct.pack_into("<h", raw, 36, 6)
            at = build.allocate(ident, raw, "dungeon-interface")
            build.patch(ident, pointer, struct.pack("<I", offset + 0x08000000), struct.pack("<I", at + 0x08000000),
                        "dungeon-interface", "Widen action window to 48px at x184; preserve inventory gap")
            windows.append({"pointer_offset": pointer, "source_start": offset, "source_end_exclusive": offset + 64,
                            "relocated_offset": at, "x": 184, "width": 48})
    relocated = {}
    for ident, e in entries.items():
        if e["family"] == "hero":
            at = hero_at + e["rows"][0] * HERO_STRIDE
        elif e["family"] == "action":
            at = base + e["rows"][0] * ACTION_STRIDE
        else:
            at = build.allocate(ident, prepared[ident], "dungeon-interface")
            for word in e["pointer_offsets"]:
                build.patch(f"{ident}.{word}", int(word, 0), struct.pack("<I", int(e["offset"], 0) + 0x08000000),
                            struct.pack("<I", at + 0x08000000), "dungeon-interface", "Relocate verified interface reader source")
        relocated[ident] = {"offset": at, "bytes": len(prepared[ident]), "metrics": metrics[ident]}
    return {"language": language, "entries": len(entries), "catalog_sha256": digest(json.dumps(catalog, sort_keys=True, ensure_ascii=False).encode()),
            "relocated": relocated, "action_table_offset": base, "windows": windows}


def build_rom(original, language="english", catalog=None):
    build = RomBuild(original)
    build_name_rom(original, build=build)
    # Previous milestone remains English in both variants: the control isolates
    # ONLY the newly relocated interface component.
    for module, add in ((build_items, build_items.add_items), (build_item_contexts, build_item_contexts.add_contexts),
                        (build_enemies, build_enemies.add_enemies)):
        add(build, load_json(module.CATALOG), "english")
    report = add_interface(build, load_json(CATALOG) if catalog is None else catalog, language)
    data, ledger = build.finish()
    return data, {"source_sha256": digest(original), "rom_sha256": digest(data), "interface": report, "ledger": ledger}


def build(output=OUTPUT):
    output = Path(output)
    prepared = {language: build_rom(ORIGINAL_ROM.read_bytes(), language) for language in ("japanese", "english")}
    for language, (_, report) in prepared.items():
        atomic_write(output / f"{language}-build.json", (json.dumps(report, indent=2) + "\n").encode())
    for language, (data, report) in prepared.items():
        atomic_write(output / f"torneko3-dungeon-interface-{language}.gba", data)
        print(language, report["rom_sha256"], report["ledger"]["appended_used_with_padding"])
    return prepared


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    build(parser.parse_args().output)
