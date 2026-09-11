"""Extract a curated catalog and build checked, deterministic translation ROMs."""

import argparse
from functools import lru_cache
import json
from pathlib import Path
import re
import struct
import tempfile

from tools.build_first_label import ORIGINAL_ROM, ROOT, digest, load_manifest
from tools.font_metrics import FONT_LAYOUTS
from tools.inventory_text import parse_text
from tools.rom_build import AppendAllocator, RomBuild

ANCHORS = ROOT / "translations/anchors.json"
CATALOG = ROOT / "translations/catalog.json"
OUTPUT = ROOT / "build/translation"
ROM_LIMIT = 0x02000000
TOKENS = {"{slot}": b"$j0", "{center}": b"$c", "{default}": b"*",
          **{f"{{x:{n}}}": bytes((3, 8, n)) for n in (64, 96, 128)},
          **{f"{{choice:{n}}}": bytes((3, 20, n)) for n in (1, 2, 3)}}
SLOTS = ("１", "２")


def check(condition, message):
    if not condition:
        raise ValueError(message)


def load_json(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            check(key not in result, f"Duplicate JSON key: {key}")
            result[key] = value
        return result
    return json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=unique)


def token_parts(text):
    check(isinstance(text, str), "Text must be a string")
    parts = re.split(r"(\{[^{}]*\})", text)
    for part in parts:
        if part.startswith("{"):
            check(part in TOKENS, f"Unknown token: {part}")
        else:
            check("{" not in part and "}" not in part, "Unmatched token braces")
    return [p for p in parts if p]


def signature(text):
    return [p for p in token_parts(text) if p in TOKENS]


def source_display(parsed, reader=None):
    result = []
    reverse = {v: k for k, v in TOKENS.items()}
    for token in parsed["tokens"]:
        raw = bytes.fromhex(token["raw_hex"])
        if token["kind"] == "binary_control":
            check(raw in reverse, f"Unsupported source control: {raw.hex()}")
            result.append(reverse[raw])
        elif token["kind"] == "control":
            check(raw == b"\n", f"Unsupported source line control: {raw.hex()}")
            result.append("\n")
        else:
            text = token["text"]
            check(not any(c in text for c in "{}"), "Source requires a brace escape grammar")
            text = text.replace("$j0", "{slot}").replace("$c", "{center}")
            check("$" not in text and "`" not in text, "Unsupported source command")
            result.append(text)
    text = "".join(result)
    if reader == "menu" and text.startswith("*"):
        text = "{default}" + text[1:]
    return text


def extract(original, anchors):
    check(digest(original) == load_manifest()["base_sha256"] == anchors["base_sha256"], "Japanese base ROM hash mismatch")
    check(len(original) == 0x01000000, "Expected 16 MiB Japanese base")
    check(anchors["schema"] == 1 and anchors["font"] == 0, "Unsupported schema or font selection")
    entries, ids, owned, source_spans = [], set(), set(), []
    for anchor in anchors["entries"]:
        ident = anchor["id"]
        check(ident not in ids, f"Duplicate entry ID: {ident}")
        ids.add(ident)
        check(anchor["profile"] in anchors["profiles"], f"Unknown profile: {ident}")
        offset = int(anchor["offset"], 0)
        parsed = parse_text(original, offset)
        check(parsed is not None, f"Unsupported source text: {ident}")
        raw = b"".join(bytes.fromhex(t["raw_hex"]) for t in parsed["tokens"]) + b"\0"
        check(raw == original[offset:parsed["end"]], f"Lossless extraction failed: {ident}")
        for start, end in source_spans:
            check(parsed["end"] <= start or offset >= end, f"Overlapping catalog source strings: {ident}")
        source_spans.append((offset, parsed["end"]))
        check(anchor["pointers"], f"Missing pointer owners: {ident}")
        for pointer in anchor["pointers"]:
            address = int(pointer, 0)
            check(address % 4 == 0 and 0 <= address <= len(original) - 4, f"Invalid pointer location: {ident}")
            check(address not in owned, f"Duplicate pointer ownership: {pointer}")
            owned.add(address)
            check(struct.unpack_from("<I", original, address)[0] == 0x08000000 + offset, f"Pointer mismatch: {ident}")
        entries.append({"id": ident, "japanese": source_display(parsed, anchor.get("reader")), "english": None,
                        "context": anchor["context"], "source_hex": raw.hex(), "source_tokens": parsed["tokens"]})
    for address in owned:
        check(not any(start < address + 4 and address < end for start, end in source_spans), "A pointer overlaps catalog source text")
    return {"schema": 1, "base_sha256": digest(original), "font": 0, "entries": entries}


def encode_english(text):
    check(text != "", "English text must be nonempty, or null to leave untranslated")
    raw = bytearray()
    for part in token_parts(text):
        if part in TOKENS:
            raw.extend(TOKENS[part])
        else:
            check(all(c == "\n" or 32 <= ord(c) <= 126 for c in part), "English requires printable ASCII and LF")
            check("$" not in part and "`" not in part, "Use supported tokens instead of raw dollar/backtick commands")
            raw.extend(part.encode("ascii"))
    return bytes(raw) + b"\0"


class FontZero:
    def __init__(self, original):
        self.original = original
        layout = FONT_LAYOUTS[0]
        self.descriptors = {}
        for index in range(layout["count"]):
            at = layout["table"] - 0x08000000 + index * 12
            bitmap, code, advance = struct.unpack_from("<IHh", original, at)
            self.descriptors[code] = (bitmap, advance)

    @lru_cache(maxsize=None)
    def glyph(self, character):
        encoded = character.encode("cp932")
        code = int.from_bytes(encoded, "big")
        if len(encoded) == 1:
            code = struct.unpack_from("<H", self.original, 0xCA2674 + code * 2)[0]
        check(code in self.descriptors, f"Font 0 has no glyph for {character!r}")
        bitmap, advance = self.descriptors[code]
        raw = self.original[bitmap - 0x08000000:bitmap - 0x08000000 + 72]
        xs = [x for y in range(12) for x in range(12) if (raw[y * 6 + x // 2] >> (4 * (x % 2))) & 15]
        return code, advance, max(xs) + 1 if xs else 0


def format_payload(text, slot):
    """Model only the commands supported by this curated batch, excluding NUL."""
    return encode_english(text)[:-1].replace(b"$j0", slot.encode("cp932"))


def measure_variant(text, profile, font, slot):
    lines = text.split("\n")
    check(1 <= len(lines) <= profile["max_lines"], "Too many lines for the reader")
    output = []
    for line in lines:
        centered = profile["alignment"] == "center"
        parts = token_parts(line)
        if centered:
            check(parts and parts[0] == "{center}" and parts.count("{center}") == 1,
                  "Each story line must begin with {center}")
        else:
            check("{center}" not in parts, "Center command is unsupported by this profile")
        x = 0 if centered else profile["start_x"]
        ink_right = x
        glyphs = []
        for part in parts:
            if part in ("{center}", "{default}") or part.startswith("{choice:"):
                continue
            if part.startswith("{x:"):
                next_x = int(part[3:-1])
                check(max(x, ink_right) + profile.get("column_gap", 0) <= next_x,
                      "Text leaves insufficient space before the next fixed column")
                x = next_x
                check(x < profile["width"], "Column starts outside the window")
                continue
            visible = slot if part == "{slot}" else part
            for character in visible:
                code, advance, ink = font.glyph(character)
                glyphs.append({"code": code, "x": x, "advance": advance})
                if ink:
                    ink_right = max(ink_right, x + ink)
                x += advance
        check(max(x, ink_right) <= profile["width"], "Text exceeds the window width")
        if centered:
            shift = (profile["width"] - x) // 2
            for glyph in glyphs:
                glyph["x"] += shift
            ink_right += shift
            x += shift
        output.append({"text": line, "end_x": x, "ink_right": ink_right,
                       "width": profile["width"], "glyphs": glyphs})
    payload = format_payload(text, slot)
    limit = profile["payload_limit"]
    check(limit is None or len(payload) <= limit, "Formatted text exceeds the RAM payload limit")
    return {"slot": slot if "{slot}" in text else None, "payload_bytes": len(payload),
            "payload_hex": payload.hex(), "lines": output}


def validate_translation(text, japanese, profile, font):
    encoded = encode_english(text)
    check(signature(text) == signature(japanese), "Control/placeholder sequence differs from Japanese source")
    if "{default}" in text:
        check(profile.get("strip_default_marker") and text.startswith("{default}")
              and text.count("{default}") == 1, "Default-selection marker must prefix a menu label")
    if profile.get("strip_default_marker"):
        check(not text.startswith("*"), "Use {default} for the menu's default-selection marker")
    variants = [measure_variant(text, profile, font, slot) for slot in (SLOTS if "{slot}" in text else SLOTS[:1])]
    return encoded, {"encoded_bytes_including_nul": len(encoded),
                     "maximum_formatted_payload": max(v["payload_bytes"] for v in variants),
                     "variants": variants}


def build_rom(original, catalog, anchors, language="english", build=None):
    check(language in ("english", "japanese"), "Unknown output language")
    extracted = extract(original, anchors)
    check(catalog["schema"] == 1 and catalog["font"] == 0 and catalog["base_sha256"] == extracted["base_sha256"],
          "Catalog schema, font, or base hash mismatch")
    by_id = {}
    for entry in catalog["entries"]:
        check(entry["id"] not in by_id, "Duplicate catalog entry ID")
        by_id[entry["id"]] = entry
    sources = {e["id"]: e for e in extracted["entries"]}
    check(by_id.keys() == sources.keys(), "Catalog IDs must exactly match the curated anchors")
    prepared, checks = {}, {}
    font = FontZero(original)
    for anchor in anchors["entries"]:
        ident = anchor["id"]
        entry, source = by_id[ident], sources[ident]
        for field in ("japanese", "source_hex", "source_tokens"):
            check(entry[field] == source[field], f"Catalog source changed: {ident}/{field}")
        if language == "english" and entry["english"] is not None:
            try:
                prepared[ident], checks[ident] = validate_translation(entry["english"], source["japanese"],
                                                                    anchors["profiles"][anchor["profile"]], font)
            except ValueError as error:
                raise ValueError(f"{ident}: {error}") from error
    build = RomBuild(original) if build is None else build
    check(build.original == original, "Shared build uses another original ROM")
    allocator = build.allocator
    allocation_start = len(allocator.allocations)
    for anchor in anchors["entries"]:
        offset = int(anchor["offset"], 0)
        build.protect_source(anchor["id"], offset, offset + len(bytes.fromhex(sources[anchor["id"]]["source_hex"])), "curated")
    pointer_changes = []
    for anchor in sorted(anchors["entries"], key=lambda e: e["id"]):
        ident = anchor["id"]
        if language == "japanese":
            # Reconstruct from the catalog's byte tokens, not by Unicode re-encoding.
            raw = b"".join(bytes.fromhex(t["raw_hex"]) for t in by_id[ident]["source_tokens"]) + b"\0"
            at = int(anchor["offset"], 0)
            check(raw == original[at:at + len(raw)], "Japanese reconstruction differs from source")
        elif ident in prepared:
            raw = prepared[ident]
            at = build.allocate(ident, raw, "curated")
            for pointer in anchor["pointers"]:
                offset = int(pointer, 0)
                pointer_changes.append(build.patch(ident, offset, original[offset:offset + 4],
                                                    struct.pack("<I", 0x08000000 + at), "curated", "Relocate curated text"))
    result, ledger = build.finish()
    report = {"language": language, "font": 0, "source_sha256": digest(original), "rom_sha256": digest(result),
              "catalog_sha256": digest(json.dumps(catalog, sort_keys=True, ensure_ascii=False).encode()),
              "anchors_sha256": digest(json.dumps(anchors, sort_keys=True, ensure_ascii=False).encode()),
              "rom_bytes": len(result), "catalog_entries": len(sources), "translated_entries": len(prepared),
              "japanese_roundtrip_identical": bytes(result) == original if language == "japanese" else None,
              "allocations": allocator.allocations[allocation_start:], "appended_used_with_padding": allocator.cursor - allocator.start,
              "appended_remaining": allocator.limit - allocator.cursor, "pointer_changes": pointer_changes,
              "checks": checks, "original_fonts_and_text_preserved": True, "ledger": ledger}
    return bytes(result), report


def atomic_write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".translation-", delete=False) as stream:
        temporary = Path(stream.name)
        try:
            stream.write(data)
            stream.close()
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)


def run(action, rom=ORIGINAL_ROM, catalog_path=CATALOG, anchors_path=ANCHORS, output=OUTPUT, language="english"):
    rom, output = Path(rom).resolve(), Path(output).resolve()
    original, anchors = rom.read_bytes(), load_json(anchors_path)
    if action == "extract":
        target = output / "extracted-ja.json"
        content = json.dumps(extract(original, anchors), ensure_ascii=False, indent=2).encode() + b"\n"
        report = {"extracted": len(anchors["entries"]), "path": str(target)}
    else:
        data, report = build_rom(original, load_json(catalog_path), anchors, language)
        target = output / ("torneko3-english.gba" if language == "english" else "torneko3-japanese-roundtrip.gba")
        content = data
    protected = {rom, Path(catalog_path).resolve(), Path(anchors_path).resolve()}
    check(target.resolve() not in protected, "Output would overwrite a source input")
    if action == "build":
        report_path = output / f"{language}-build.json"
        check(report_path.resolve() not in protected, "Report would overwrite a source input")
    atomic_write(target, content)
    if action == "build":
        atomic_write(report_path, json.dumps(report, ensure_ascii=False, indent=2).encode() + b"\n")
    print(json.dumps({k: v for k, v in report.items() if k not in ("allocations", "checks", "pointer_changes")}, indent=2))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("extract", "build"))
    parser.add_argument("rom", nargs="?", type=Path, default=ORIGINAL_ROM)
    parser.add_argument("--catalog", type=Path, default=CATALOG)
    parser.add_argument("--anchors", type=Path, default=ANCHORS)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--language", choices=("japanese", "english"), default="english")
    args = parser.parse_args()
    run(args.action, args.rom, args.catalog, args.anchors, args.output, args.language)
