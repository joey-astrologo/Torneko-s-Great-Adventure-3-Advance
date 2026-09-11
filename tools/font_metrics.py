"""Extract original Latin glyphs and measure literal ASCII without host-font substitution."""

import struct

FONT_LAYOUTS = (
    {"id": 0, "name": "Small / 12 rows", "table": 0x08C93B4C, "count": 1345, "rows": 12},
    {"id": 1, "name": "Small / 10 rows", "table": 0x08C9E5CC, "count": 382, "rows": 10},
    {"id": 2, "name": "Decorative / 12 rows", "table": 0x08CA1300, "count": 97, "rows": 12},
)


def extract_fonts(data):
    fonts = []
    for layout in FONT_LAYOUTS:
        descriptors = {}
        for index in range(layout["count"]):
            offset = layout["table"] - 0x08000000 + index * 12
            bitmap, code, advance, unknown, colored, reserved = struct.unpack_from("<IHhHBB", data, offset)
            descriptors[code] = (offset, bitmap, advance, unknown, colored, reserved)
        glyphs = {}
        for code in range(32, 127):
            mapped = struct.unpack_from("<H", data, 0xCA2674 + code * 2)[0]
            if mapped not in descriptors:
                raise ValueError(f"Font {layout['id']} lacks ASCII {code:02X}")
            offset, bitmap, advance, unknown, colored, reserved = descriptors[mapped]
            raw = data[bitmap - 0x08000000:bitmap - 0x08000000 + 72]
            if len(raw) != 72:
                raise ValueError("Incomplete glyph bitmap")
            # Each bitmap row is six bytes: twelve pixels, low nibble first.
            rows = [[(raw[y * 6 + x // 2] >> (4 * (x % 2))) & 15 for x in range(12)] for y in range(12)]
            occupied = [(x, y) for y in range(layout["rows"]) for x in range(12) if rows[y][x]]
            bbox = ([min(x for x, y in occupied), min(y for x, y in occupied),
                     max(x for x, y in occupied) + 1, max(y for x, y in occupied) + 1] if occupied else None)
            glyphs[chr(code)] = {"code": code, "mapped_code": mapped, "advance": advance,
                                 "descriptor": f"0x{offset + 0x08000000:08X}", "bitmap": f"0x{bitmap:08X}",
                                 "colored": colored, "unknown_u16": unknown, "reserved_u8": reserved,
                                 "ink_bounds": bbox, "pixels": rows[:layout["rows"]],
                                 "stored_bitmap_hex": raw.hex()}
        fonts.append({**layout, "glyphs": glyphs})
    return fonts


def measure_line(font, text, spacing=0):
    """Measure literal ASCII; control syntax must be interpreted by the caller.

    Return both cursor advance and visible right edge, since they need not agree.
    Dollar/backtick handling differs by reader and is deliberately rejected here.
    """
    cursor, right = 0, 0
    for character in text:
        if character in "$`" or character not in font["glyphs"]:
            raise ValueError(f"Not plain renderable ASCII: {character!r}")
        glyph = font["glyphs"][character]
        if glyph["ink_bounds"]:
            right = max(right, cursor + glyph["ink_bounds"][2])
        cursor += glyph["advance"] + spacing
    return {"advance": cursor, "ink_right": right}
