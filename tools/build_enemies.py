"""Checked relocation of both 200-row enemy tables and their English layouts."""

import json
from pathlib import Path
import struct

from tools.build_first_label import ORIGINAL_ROM, ROOT, digest, load_manifest
from tools.game_text import GameTextCodec, rebuild
from tools.translation_pipeline import FontZero, atomic_write, check

CATALOG = ROOT / "translations/enemies.json"
TABLES = {"name": (0x192568, 200), "trait": (0x1ACB74, 200)}
NAME_BYTES = 29  # Original name-copy buffers are 30 bytes including NUL.
TRAIT_WIDTH, TRAIT_LINES = 188, 3


def measure(text, font):
    x = right = 0
    for character in text:
        _, advance, ink = font.glyph(character)
        if ink:
            right = max(right, x + ink)
        x += advance
    return max(x, right)


def wrap(text, font, width=TRAIT_WIDTH):
    lines = []
    for word in text.split():
        check(measure(word, font) <= width, f"Word wider than display: {word}")
        if lines and measure(lines[-1] + " " + word, font) <= width:
            lines[-1] += " " + word
        else:
            lines.append(word)
    return "\n".join(lines)


def extract_catalog(original):
    check(digest(original) == load_manifest()["base_sha256"], "Enemy extraction requires the pinned Japanese original")
    codec, entries = GameTextCodec(original), []
    for family, (base, count) in TABLES.items():
        for row in range(count):
            word = base + row * 4
            offset = struct.unpack_from("<I", original, word)[0] - 0x08000000
            source = codec.parse(original, offset)
            entries.append({"id": f"enemy.{family}.{row:03d}", "family": family, "row": row,
                "offset": f"0x{offset:08X}", "pointer_offset": f"0x{word:08X}",
                "japanese": source["display"], "source_hex": source["raw_hex"],
                "source_tokens": source["tokens"], "master_id": f"jp_{offset:08x}",
                "english": None, "display": None, "notes": ""})
    return {"schema": 1, "base_sha256": digest(original), "font": 0, "entries": entries}


def validate_catalog(original, catalog):
    fresh = extract_catalog(original)
    check(all(catalog[k] == fresh[k] for k in ("schema", "base_sha256", "font")), "Enemy catalog base/schema/font mismatch")
    entries = {e["id"]: e for e in catalog["entries"]}
    check(len(entries) == len(catalog["entries"]) == 400, "Enemy catalog must have 400 unique entries")
    check(entries.keys() == {e["id"] for e in fresh["entries"]}, "Enemy table coverage differs")
    for source in fresh["entries"]:
        entry = entries[source["id"]]
        for key in source.keys() - {"english", "display", "notes"}:
            check(entry[key] == source[key], f"Enemy source metadata changed: {source['id']}/{key}")
        for key in ("english", "display"):
            check(entry[key] is None or isinstance(entry[key], str) and entry[key], f"Invalid enemy {key}")
        check(isinstance(entry["notes"], str), "Enemy notes must be text")
        check(entry["display"] is None or entry["english"] is not None, "Display without translation")
    return entries


def initialize_catalog(original, path=CATALOG):
    path = Path(path)
    if path.exists():
        existing = json.loads(path.read_text())
        validate_catalog(original, existing)
        return existing
    fresh = extract_catalog(original)
    master = {e["id"]: e for e in json.loads((ROOT / "translations/master.json").read_text())["entries"]}
    font = FontZero(original)
    for entry in fresh["entries"]:
        draft = master[entry["master_id"]]
        if draft["english"]:
            entry.update(english=draft["english"].replace("<CR>", "\n"), notes=draft["notes"])
            if entry["family"] == "trait":
                entry["display"] = wrap(entry["english"], font)
    atomic_write(path, (json.dumps(fresh, ensure_ascii=False, indent=2) + "\n").encode())
    return fresh


def encode_english(entry, font):
    text = entry["display"] if entry["display"] is not None else entry["english"]
    check(isinstance(text, str) and text, "Enemy English must be nonempty")
    check(all(c == "\n" or 32 <= ord(c) <= 126 for c in text), "Enemy text requires printable ASCII and LF")
    check(not any(c in text for c in "$%`{}"), "Enemy text cannot contain formatter commands")
    lines = text.split("\n")
    check(all(lines), "Empty enemy display line")
    widths = [measure(line, font) for line in lines]
    if entry["family"] == "name":
        check(len(lines) == 1 and len(text) <= NAME_BYTES, "Enemy name exceeds original copy buffer")
        check(max(widths) <= 120, "Enemy name exceeds checked details layout")
    else:
        check(len(lines) <= TRAIT_LINES and max(widths) <= TRAIT_WIDTH, f"Enemy trait exceeds {TRAIT_LINES} lines / {TRAIT_WIDTH}px: {entry['id']}")
    payload = text.replace("\n", "\r").encode("ascii") + b"\0"
    check(len(payload) + 6 <= 512, "Enemy trait wrapper exceeds original stack buffer")
    return payload, {"line_widths": widths, "bytes_including_nul": len(payload),
                     "full_english": entry["english"], "display": text}


def add_layout(build):
    # Each pointer is an established caller-owned format literal. Original
    # source strings stay immutable; no global renderer or shared y table edit.
    formats = {
        "ally_species": (0x732C8, 0xC3E3E4, b"Max HP $d0\x03\x08\x40[$m0]\0"),
        "encounter_header": (0x79B84, 0xC41484, b"%2d:%s\rLv%d  %d%c%dx\0"),
        "encounter_alternate_header": (0x799A8, 0xC413D4, b"%s Lv%d\0"),
    }
    codec = GameTextCodec(build.original)
    for ident, (word, source, payload) in formats.items():
        parsed = codec.parse(build.original, source)
        build.protect_source("enemy.layout.source." + ident, source, parsed["end"], "enemies")
        at = build.allocate("enemy.layout." + ident, payload, "enemies")
        build.patch("enemy.layout." + ident, word, struct.pack("<I", 0x08000000 + source),
                    struct.pack("<I", 0x08000000 + at), "enemies", "Fit full enemy name and retain level/multiplier")
    build.patch("enemy.layout.header_rule", 0x79A16, bytes.fromhex("1222"), bytes.fromhex("1f22"),
                "enemies", "Move encounter separator below two-line header: y18 to y31")
    build.patch("enemy.layout.trait_y", 0x79A22, bytes.fromhex("815e"), bytes.fromhex("2721"),
                "enemies", "Use local y39 for traits after two-line header; shared row table unchanged")


def add_enemies(build, catalog, language="english"):
    check(language in ("japanese", "english"), "Unsupported enemy language")
    entries = validate_catalog(build.original, catalog)
    font = FontZero(build.original)
    allocations, checks = [], {}
    for ident, entry in sorted(entries.items()):
        source, word = int(entry["offset"], 0), int(entry["pointer_offset"], 0)
        raw = rebuild(entry["source_tokens"])
        check(raw.hex() == entry["source_hex"], "Enemy source reconstruction differs")
        build.protect_source(ident, source, source + len(raw), "enemies")
        if language == "english" and entry["english"] is not None:
            raw, checks[ident] = encode_english(entry, font)
        at = build.allocate(ident, raw, "enemies")
        build.patch(ident, word, struct.pack("<I", 0x08000000 + source), struct.pack("<I", 0x08000000 + at),
                    "enemies", "Relocate complete monster name/trait table entry")
        allocations.append({"id": ident, "family": entry["family"], "row": entry["row"],
            "offset": at, "bytes": len(raw), "source_offset": source, "translated": ident in checks})
    if language == "english":
        add_layout(build)
    return {"language": language, "entries": len(entries), "pointer_words": len(entries),
            "translated_entries": len(checks), "allocations": allocations, "checks": checks,
            "catalog_sha256": digest(json.dumps(catalog, sort_keys=True, ensure_ascii=False).encode())}
