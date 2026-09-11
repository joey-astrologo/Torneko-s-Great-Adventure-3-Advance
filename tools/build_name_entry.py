"""Build the bounded seven-letter Adventure Log proof from the Japanese ROM."""

import argparse
import json
from pathlib import Path
import string
import struct
import subprocess
import tempfile

from tools.build_first_label import ORIGINAL_ROM, ROOT, digest
from tools.rom_build import RomBuild
from tools.translation_pipeline import (ANCHORS, CATALOG, ROM_LIMIT,
                                        FontZero, atomic_write, build_rom, check, load_json)

OUTPUT = ROOT / "build/name-entry"
NAME_RAM = 0x0203BB38
LATIN_IDS = [i for i in range(0xBF, 0xFE) if i != 0xC9]
LATIN = dict(zip(string.ascii_uppercase + string.ascii_lowercase + string.digits, LATIN_IDS, strict=True))
NAME_LIMIT = 7
DEFAULT_NAME = "Torneko"


def compact_name(text):
    """Encode the alphanumeric names used by native verification."""
    check(1 <= len(text) <= NAME_LIMIT, "Name must contain one to seven letters")
    check(all(c in LATIN for c in text), "Verification names require ASCII letters/digits")
    return bytes(LATIN[c] for c in text) + b"\0"


def build_name_rom(original, catalog=None, anchors=None, build=None):
    catalog = load_json(CATALOG) if catalog is None else catalog
    anchors = load_json(ANCHORS) if anchors is None else anchors
    # This proof has the new limit. The ordinary curated build still uses four.
    catalog = json.loads(json.dumps(catalog))
    for entry in catalog["entries"]:
        if entry["id"] == "save.new_log_explanation":
            entry["english"] = "Start a new adventure.\nName Adventure Log {slot} using\nup to seven letters."
    build = RomBuild(original) if build is None else build
    _, base_report = build_rom(original, catalog, anchors, build=build)
    allocator = build.allocator
    allocation_start = len(allocator.allocations)
    changes = []

    def patch(offset, expected, replacement, reason):
        changes.append(build.patch(f"name.patch-{offset:08x}", offset, expected, replacement, "name-entry", reason))

    def word(offset, before, after, reason):
        patch(offset, struct.pack("<I", before), struct.pack("<I", after), reason)

    def asset(ident, payload):
        offset = build.allocate(ident, payload, "name-entry")
        return 0x08000000 + offset

    # Reserve eight bytes immediately after the original EWRAM BSS. Startup
    # now clears them too. The game's fixed heap ends at 02034A90, below BSS.
    build.reserve_memory("game.heap", 0x02010A90, 0x02034A90, "original", purpose="Existing occupied runtime arena")
    build.reserve_memory("name.current", NAME_RAM, NAME_RAM + 8, "name-entry", purpose="Extended zero-initialized current name")
    word(0x87A04, 0x0203BB38, 0x0203BB40, "Extend zero-initialized BSS by eight bytes")
    for offset in (0x1CC4, 0x26BC, 0x28B8, 0x7D634, 0x858FC):
        word(offset, 0x02004F82, NAME_RAM, "Relocate current Adventure Log name")
    for offset, before, after, reason in (
        (0x858E6, "0423", "0723", "Seven editor slots"),
        (0x85938, "0622", "0822", "Commit eight bytes"),
        (0x85940, "6871", "e871", "Terminate committed name at index seven"),
        (0x27CC, "052a", "072a", "Copy eight bytes into record +0x10"),
        (0x2306, "052d", "072d", "Load eight bytes from record +0x10"),
        (0x7BD74, "0120", "0020", "Font 0 for name keyboard redraw"),
        (0x7BDDA, "0120", "0020", "Font 0 for name keyboard and labels"),
    ):
        patch(offset, bytes.fromhex(before), bytes.fromhex(after), reason)

    mapping = bytearray(original[0xC4696C:0xC4696C + 0xBF * 2])
    mapping.extend(b"\0" * (512 - len(mapping)))
    for character, ident in LATIN.items():
        mapping[ident * 2:ident * 2 + 2] = ord(character).to_bytes(2, "big")
    mapping_address = asset("name.compact-map", bytes(mapping))
    word(0xC467E4, 0x08C4696C, mapping_address, "Extend type-zero compact character map")

    # Retain the second editor type's input map and grid. The two type-zero
    # pages use new Latin/digit IDs; punctuation retains its Japanese IDs.
    input_map = bytearray(original[0xC45B41:0xC45B41 + 0x154])
    page_addresses = []
    for page, letters in enumerate((string.ascii_uppercase, string.ascii_lowercase)):
        characters = list(letters + "0123456789-!? /+&()[]")
        characters += [None] * (80 - len(characters))
        ids = {str(i): 0x6F + i for i in range(10)}
        ids.update({"-": 0x79, "!": 0x7C, "?": 0x7E, " ": 0xBE,
                    "/": 0x7F, "+": 0x7A, "&": 0x7D, "(": 0xB5,
                    ")": 0xB6, "[": 0xB7, "]": 0xB8, **LATIN})
        raw = bytearray()
        for index, character in enumerate(characters):
            input_map[page * 85 + 5 + index] = ids[character] if character else 0
            column = index % 10
            raw.extend((3, 9, 8 + column * 20 + (8 if column >= 5 else 0)))
            if character is not None:
                raw.extend(character.encode("ascii"))
            if column == 9:
                raw.append(13)
        raw.append(0)
        page_addresses.append(asset(f"name.keyboard-page-{page}", bytes(raw)))
    word(0x7C48C, 0x08C45B41, asset("name.keyboard-input", bytes(input_map)), "Latin keyboard input IDs")
    # Point to ROM tables directly instead of the startup-copied pointer tables.
    pages = struct.pack("<IIII", *page_addresses, 0x08C45690, 0x08C454E8)
    word(0x7BEE8, 0x020007A8, asset("name.keyboard-pages", pages), "Latin keyboard display pointers")
    headers = []
    for page in range(2):
        raw = bytearray()
        for x, label in ((4, "abc" if page == 0 else "ABC"), (52, "Next"),
                         (136, "Back"), (176, "Done")):
            raw.extend((3, 9, x))
            raw.extend(label.encode("ascii"))
        headers.append(asset(f"name.keyboard-header-{page}", bytes(raw) + b"\0"))
    word(0x7BEE4, 0x02000798, asset("name.keyboard-headers", struct.pack("<IIII", *headers, *headers)), "English keyboard buttons")
    for offset, before, label in ((0x7BED0, 0x08C46738, "B: Cancel"),
                                  (0x7BED4, 0x08C46730, "B: Erase"),
                                  (0x7BEEC, 0x08C46740, "A: Enter  L: Case  R: Done")):
        word(offset, before, asset(f"name.hint-{offset:x}", label.encode() + b"\0"), "English button hint")
    word(0x85950, 0x08C784EC, asset("name.confirmation", b'Use "$i0"\nas the Adventure Log name?\0'), "Name substitution confirmation")

    code_address = 0x08000000 + ((allocator.cursor + 3) & ~3)
    with tempfile.TemporaryDirectory(prefix="torneko-name-asm-") as directory:
        run = subprocess.run([str(ROOT / ".tools/bin/armips"), str(ROOT / "tools/name_entry.asm"),
                              "-equ", "CODE_ADDRESS", hex(code_address), "-sym2", "symbols.txt"],
                             cwd=directory, text=True, capture_output=True)
        check(run.returncode == 0, "armips failed: " + run.stdout + run.stderr)
        code = (Path(directory) / "name-code.bin").read_bytes()
        symbols = {}
        for line in (Path(directory) / "symbols.txt").read_text().splitlines():
            fields = line.split()
            if len(fields) == 2 and fields[1] in ("ConvertName", "ConvertSlots"):
                symbols[fields[1]] = int(fields[0], 16)
    check(asset("name.code", code) == code_address, "Code allocation moved")
    for offset, symbol in ((0x7D228, "ConvertName"), (0x7D258, "ConvertSlots")):
        # Absolute Thumb tail jumps. ConvertSlots needs all four input
        # registers, so its 16-byte stub preserves r3 and jumps through r12.
        if symbol == "ConvertSlots":
            stub = bytes.fromhex("08b4024b9c4608bc6047c046") + struct.pack("<I", symbols[symbol] | 1)
        else:
            stub = bytes.fromhex("004b1847") + struct.pack("<I", symbols[symbol] | 1)
        patch(offset, original[offset:offset + len(stub)], stub, "Convert compact Japanese and Latin IDs")

    # Both new Adventure Logs use the same eight-byte compact default. Clear
    # the old slot * 6 offset before the existing default-string copy.
    word(0x85904, 0x08C4CE97, asset("name.default", compact_name(DEFAULT_NAME)), "Default new name to Torneko")
    patch(0x858CC, bytes.fromhex("4900"), bytes.fromhex("0021"), "Use the shared default in both slots")

    result, ledger = build.finish()
    font = FontZero(original)
    # Fixed-cell centering is based on a 12-pixel glyph box, while cells advance
    # 11 pixels. Bound the last position for every new glyph, including digits.
    right = max(1 + 6 * 11 + (12 - font.glyph(c)[1]) // 2 + font.glyph(c)[2] for c in LATIN)
    widest = max(font.glyph(c)[1] for c in LATIN) * NAME_LIMIT
    confirmation_width = max(sum(font.glyph(c)[1] for c in 'Use ""') + widest,
                             sum(font.glyph(c)[1] for c in 'as the Adventure Log name?'))
    check(right <= 80 and confirmation_width <= 208, "Name layout exceeds its window")
    report = {"source_sha256": digest(original), "rom_sha256": digest(result), "rom_bytes": len(result),
              "name_limit": NAME_LIMIT, "default_name": DEFAULT_NAME, "name_ram": f"0x{NAME_RAM:08X}", "save_bytes": 65536,
              "compact_latin_ids": LATIN, "symbols": symbols,
              "font_bounds": {"font": 0, "editor_max_ink_right": right, "editor_width": 80,
                              "confirmation_max_advance": confirmation_width, "confirmation_width": 208},
              "patches": changes, "text_build": base_report, "allocations": allocator.allocations[allocation_start:],
              "ledger": ledger,
              "appended_used_with_padding": allocator.cursor - len(original),
              "appended_remaining": allocator.limit - allocator.cursor}
    return bytes(result), report


def build(rom=ORIGINAL_ROM, output=OUTPUT):
    rom, output = Path(rom).resolve(), Path(output).resolve()
    target, report_path = output / "torneko3-name-entry.gba", output / "build.json"
    check(rom not in (target.resolve(), report_path.resolve()), "Output would overwrite input")
    data, report = build_name_rom(rom.read_bytes())
    atomic_write(target, data)
    atomic_write(report_path, json.dumps(report, indent=2).encode() + b"\n")
    return {"rom": str(target), **{k: report[k] for k in ("rom_sha256", "name_limit", "appended_used_with_padding")}}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rom", nargs="?", type=Path, default=ORIGINAL_ROM)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    print(json.dumps(build(args.rom, args.output), indent=2))
