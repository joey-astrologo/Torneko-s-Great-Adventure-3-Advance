"""Inventory pointer-backed Japanese text candidates without assuming completeness."""

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re
import struct

from tools.build_first_label import ORIGINAL_ROM, ROOT, digest, load_manifest

OUTPUT = ROOT / "build/text-inventory"
# Argument lengths established from DrawEncodedText's Thumb dispatch branches.
CONTROL_ARGUMENTS = {0x05: 1, 0x06: 0, 0x08: 1, 0x09: 1, 0x0F: 1,
                     0x11: 0, 0x12: 0, 0x14: 1, 0x15: 1, 0x16: 0, 0x1F: 0}


def parse_text(data, start, maximum=4096):
    """Return lossless tokens for a supported NUL-terminated byte sequence.

    This is a candidate parser, not a full script decoder. Unknown controls,
    invalid CP932, missing terminators, and truncated characters fail closed.
    Control arguments are opaque bytes, including zero and Shift-JIS lead bytes.
    """
    if not 0 <= start < len(data):
        return None
    pos, end, tokens = start, min(len(data), start + maximum), []
    japanese = 0
    while pos < end:
        first = data[pos]
        if first == 0:
            return {"offset": start, "end": pos + 1, "bytes_including_nul": pos + 1 - start,
                    "raw_hex": data[start:pos + 1].hex(), "tokens": tokens,
                    "japanese_characters": japanese,
                    "display": "".join(t["text"] for t in tokens)}
        width = 1
        kind = "text"
        if first == 3:
            if pos + 1 >= end or data[pos + 1] not in CONTROL_ARGUMENTS:
                return None
            width = 2 + CONTROL_ARGUMENTS[data[pos + 1]]
            if pos + width > end:
                return None
            kind = "binary_control"
            rendered = "<" + data[pos:pos + width].hex(" ").upper() + ">"
        elif first in (9, 10, 13, 0x1B, 0x1D):
            kind = "control"
            rendered = {9: "<TAB>", 10: "<LF>", 13: "<CR>",
                        0x1B: "<1B>", 0x1D: "<1D>"}[first]
        elif first < 0x20 or first == 0x7F or first >= 0xFD:
            return None
        else:
            width = 2 if 0x80 <= first <= 0x9F or 0xE0 <= first <= 0xFC else 1
            if pos + width > end:
                return None
            try:
                rendered = data[pos:pos + width].decode("cp932")
            except UnicodeDecodeError:
                return None
            if len(rendered) != 1 or any(0xE000 <= ord(c) <= 0xF8FF or ord(c) < 0x20 for c in rendered):
                return None
            japanese += sum(0x3040 <= ord(c) <= 0x30FF or 0x3400 <= ord(c) <= 0x9FFF
                            or 0xFF66 <= ord(c) <= 0xFF9F for c in rendered)
        raw = data[pos:pos + width].hex()
        if kind == "text" and tokens and tokens[-1]["kind"] == "text":
            tokens[-1]["raw_hex"] += raw
            tokens[-1]["text"] += rendered
        else:
            tokens.append({"kind": kind, "raw_hex": raw, "text": rendered})
        pos += width
    return None


def find_thumb_calls(data, targets, end=None):
    """Find candidate ARMv4T Thumb BL encodings, not verified instructions."""
    found = defaultdict(list)
    for source in range(0, min(len(data), end or len(data)) - 3, 2):
        high, low = struct.unpack_from("<HH", data, source)
        if high & 0xF800 != 0xF000 or low & 0xF800 != 0xF800:
            continue
        delta = ((high & 0x7FF) << 12) | ((low & 0x7FF) << 1)
        if delta & 0x400000:
            delta -= 0x800000
        target = 0x08000000 + source + 4 + delta
        if target in targets:
            found[target].append(source + 0x08000000)
    return {f"0x{target:08X}": [f"0x{p:08X}" for p in found[target]] for target in targets}


def inventory(rom=ORIGINAL_ROM, output=OUTPUT):
    rom, output = Path(rom).resolve(), Path(output).resolve()
    data = rom.read_bytes()
    if digest(data) != load_manifest()["base_sha256"]:
        raise ValueError("Text inventory requires the verified Japanese original")
    references = defaultdict(list)
    for source in range(0, len(data) - 3, 4):
        value = struct.unpack_from("<I", data, source)[0]
        if 0x08000000 <= value < 0x08000000 + len(data):
            references[value - 0x08000000].append(source)
    entries = []
    for offset, refs in sorted(references.items()):
        parsed = parse_text(data, offset)
        if parsed is None or parsed["japanese_characters"] < 2:
            continue
        reconstructed = b"".join(bytes.fromhex(t["raw_hex"]) for t in parsed["tokens"]) + b"\0"
        if reconstructed != data[offset:parsed["end"]]:
            raise RuntimeError("Candidate tokens do not reconstruct the original bytes")
        # The raw bytes are authoritative; Unicode labels are only a viewing aid.
        parsed.update({"id": f"jp_{offset:08x}", "address": f"0x{0x08000000 + offset:08X}",
                       "pointer_candidates": [f"0x{x:08X}" for x in refs],
                       "evidence": "static candidate; requires reader/table validation",
                       "dollar_tokens": re.findall(r"\$[A-Za-z](?:[0-9]+)?", parsed["display"]),
                       "printf_tokens": re.findall(r"%(?:[-+ #0]*\d*(?:\.\d+)?[a-zA-Z%])", parsed["display"])})
        entries.append(parsed)
    # Count the union rather than double-counting suffix and overlapping candidates.
    union_bytes, previous_end = 0, 0
    for entry in entries:
        union_bytes += max(0, entry["end"] - max(previous_end, entry["offset"]))
        previous_end = max(previous_end, entry["end"])
    regions = Counter((entry["offset"] // 0x10000) * 0x10000 for entry in entries)
    controls = Counter(token["raw_hex"][:4] for entry in entries for token in entry["tokens"]
                       if token["kind"] == "binary_control")
    report = {"source_sha256": digest(data), "candidate_count": len(entries),
              "candidate_byte_union_including_nuls": union_bytes,
              "binary_controls": dict(controls),
              "dollar_tokens": dict(Counter(t for e in entries for t in e["dollar_tokens"])),
              "regions_64k": [{"offset": f"0x{start:08X}", "candidates": count}
                              for start, count in sorted(regions.items())],
              "thumb_bl_candidates": find_thumb_calls(data, (0x0808C72C, 0x0808CBA0, 0x0808BC4C)),
              "limitations": ["Counts are candidates, not a complete or verified game script.",
                              "Pointer-shaped data can be false positives; suffixes can be separate entries.",
                              "Only aligned pointers into the primary ROM view are scanned.",
                              "Short/ASCII-only strings, relative offsets, compressed text, custom glyph codes, and unknown controls can be missed.",
                              "Token raw_hex plus a NUL reconstructs exact bytes; Unicode re-encoding is not guaranteed to do so.",
                              "Dollar/printf matches are lexical observations; command arguments and semantics need reader analysis."]}
    output.mkdir(parents=True, exist_ok=True)
    (output / "candidates.json").write_text(json.dumps(entries, ensure_ascii=False, indent=2) + "\n")
    (output / "inventory.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    with (output / "candidates.tsv").open("w") as stream:
        stream.write("id\taddress\tbytes\tpointer_candidates\tpreview\n")
        for entry in entries:
            preview = entry["display"].replace("\t", "\\t").replace("\n", "\\n").replace("\r", "\\r")
            stream.write(f'{entry["id"]}\t{entry["address"]}\t{entry["bytes_including_nul"]}\t'
                         f'{",".join(entry["pointer_candidates"])}\t{preview}\n')
    print(json.dumps({key: report[key] for key in ("candidate_count", "candidate_byte_union_including_nuls", "binary_controls", "dollar_tokens")}, ensure_ascii=False, indent=2))
    return entries, report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rom", nargs="?", type=Path, default=ORIGINAL_ROM)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    inventory(args.rom, args.output)
