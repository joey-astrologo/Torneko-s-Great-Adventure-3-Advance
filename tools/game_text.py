"""Lossless source decoding through the Japanese ROM's font-zero tables.

The Unicode view is for reading. Only token raw_hex is used for reconstruction.
Indexed glyphs depend on the active font; font zero is the explicit extraction
view, not a claim that every source's runtime font has been verified.
"""

import re
import struct

from tools.font_metrics import FONT_LAYOUTS
from tools.inventory_text import CONTROL_ARGUMENTS

# Source consumption in FormatGameText (0807D8CC); $c is the separately
# established story alignment command. These are byte counts, not digit runs.
DOLLAR_ARGUMENTS = {"x": 0, "+": 0, "w": 0, "i": 1, "m": 1, "d": 1,
                    "v": 2, "t": 0, "C": 1, "/": 3, "j": 1, "p": 1, "c": 0}
PRINTF = re.compile(rb"%(?:%|[-+ #0]*(?:\d+|\*)?(?:\.(?:\d+|\*))?(?:hh|ll|[hlLzjt])?[diuoxXfFeEgGaAcspn])")
LINE_CONTROLS = {9: "<TAB>", 10: "\n", 13: "<CR>", 0x1B: "<1B>", 0x1D: "<1D>"}


class DecodeError(ValueError):
    def __init__(self, offset, reason):
        self.offset, self.reason = offset, reason
        super().__init__(f"0x{offset:08X}: {reason}")


def character_width(first):
    return 2 if 0x80 <= first <= 0x9F or 0xE0 <= first <= 0xFE else 1


def unicode_code(code):
    return code.to_bytes(2 if code > 255 else 1, "big").decode("cp932")


def rebuild(tokens):
    return b"".join(bytes.fromhex(t["raw_hex"]) for t in tokens)


def token_boundaries(tokens):
    """Character/control boundaries; command arguments are never suffix starts."""
    boundaries, pos = set(), 0
    for token in tokens:
        raw = bytes.fromhex(token["raw_hex"])
        if token["kind"] == "text":
            i = 0
            while i < len(raw):
                boundaries.add(pos + i)
                i += character_width(raw[i])
        else:
            boundaries.add(pos)
        pos += len(raw)
    return boundaries


class GameTextCodec:
    def __init__(self, rom, font_id=0):
        layout = FONT_LAYOUTS[font_id]
        self.font_id = font_id
        self.codes = [struct.unpack_from("<H", rom, layout["table"] - 0x08000000 + i * 12 + 4)[0]
                      for i in range(layout["count"])]
        self.code_set = set(self.codes)
        self.single = struct.unpack_from("<256H", rom, 0xCA2674)
        self.characters = {}

    def glyph(self, raw, offset):
        if raw in self.characters:
            return self.characters[raw]
        code = int.from_bytes(raw, "big")
        encoding = "cp932"
        if len(raw) == 1:
            code = self.single[code]
            encoding = "single_byte_map"
        elif raw[0] >= 0xF8:
            # 0808C686..0808C6A4: (lead - F8) * E0 + trail - 20.
            index = (raw[0] - 0xF8) * 224 + raw[1] - 32
            if raw[1] < 32 or not 0 <= index < len(self.codes):
                raise DecodeError(offset, "font index outside selected descriptor table")
            code = self.codes[index]
            encoding = "font_index"
        if code not in self.code_set:
            raise DecodeError(offset, f"glyph {code:04X} absent from font {self.font_id}")
        try:
            text = unicode_code(code)
        except UnicodeError as exc:
            raise DecodeError(offset, f"glyph {code:04X} has no CP932 viewing label") from exc
        if any(ord(c) < 32 or 0xE000 <= ord(c) <= 0xF8FF for c in text):
            raise DecodeError(offset, "glyph has no ordinary Unicode viewing label")
        self.characters[raw] = text, encoding
        return text, encoding

    def parse(self, data, start, maximum=4096):
        if not 0 <= start < len(data):
            raise DecodeError(start, "source outside ROM")
        pos, limit, tokens = start, min(len(data), start + maximum), []
        japanese, indexed = 0, 0
        while pos < limit:
            first = data[pos]
            kind, encoding, width = "text", None, 1
            extra = {}
            if first == 0:
                tokens.append({"kind": "terminator", "raw_hex": "00", "text": ""})
                return {"offset": start, "end": pos + 1, "raw_hex": data[start:pos + 1].hex(),
                        "tokens": tokens, "display": "".join(t["text"] for t in tokens),
                        "japanese_characters": japanese, "indexed_characters": indexed}
            if first == 3:
                if pos + 1 < limit and data[pos + 1] == 3:
                    # Several statistics labels contain 03 03 08 xx. The
                    # formatter default branch copies the first 03 alone,
                    # then processes the next 03. Preserve this opaque prefix;
                    # do not assign it a drawing meaning.
                    tokens.append({"kind": "opaque_control", "raw_hex": "03", "text": "<03>",
                                   "grammar": "formatter_literal_prefix"})
                    pos += 1
                    continue
                if pos + 1 >= limit or data[pos + 1] not in CONTROL_ARGUMENTS:
                    raise DecodeError(pos, "unknown or truncated binary control")
                width = 2 + CONTROL_ARGUMENTS[data[pos + 1]]
                if pos + width > limit:
                    raise DecodeError(pos, "truncated binary control arguments")
                # Some printf source templates supply a renderer argument with
                # %c. Keep that candidate template together, without pretending
                # the literal '%' is the final attribute byte seen by drawing.
                if CONTROL_ARGUMENTS[data[pos + 1]] == 1 and (argument := PRINTF.match(data, pos + 2, limit)):
                    width = 2 + len(argument[0])
                    extra["argument_template_candidate"] = argument[0].decode("ascii")
                kind = "binary_control"
                text = "<" + data[pos:pos + width].hex(" ").upper() + ">"
            elif first in LINE_CONTROLS:
                kind, text = "control", LINE_CONTROLS[first]
            elif first < 32 or first in (0x7F, 0xFF):
                raise DecodeError(pos, f"unsupported byte {first:02X}")
            elif first == ord("$"):
                kind = "dollar_command"
                command = chr(data[pos + 1]) if pos + 1 < limit else ""
                if command in DOLLAR_ARGUMENTS:
                    width = 2 + DOLLAR_ARGUMENTS[command]
                    if pos + width > limit or any(b < 32 or b > 126 for b in data[pos + 1:pos + width]):
                        raise DecodeError(pos, "truncated/non-ASCII dollar command arguments")
                    extra["grammar"] = "story" if command == "c" else "shared_formatter"
                else:
                    width = 2 if command and 32 <= ord(command) <= 126 else 1
                    extra["grammar"] = "unresolved"
                text = data[pos:pos + width].decode("ascii")
            elif first == ord("%") and (match := PRINTF.match(data, pos, limit)):
                kind, width = "printf", len(match[0])
                text, extra["grammar"] = match[0].decode("ascii"), "lexical_only"
            else:
                width = character_width(first)
                if pos + width > limit:
                    raise DecodeError(pos, "truncated character")
                text, encoding = self.glyph(data[pos:pos + width], pos)
                japanese += sum(0x3040 <= ord(c) <= 0x30FF or 0x3400 <= ord(c) <= 0x9FFF
                                or 0xFF66 <= ord(c) <= 0xFF9F for c in text)
                indexed += encoding == "font_index"
            raw = data[pos:pos + width].hex()
            if kind == "text" and tokens and tokens[-1]["kind"] == kind and tokens[-1].get("encoding") == encoding:
                tokens[-1]["raw_hex"] += raw
                tokens[-1]["text"] += text
            else:
                token = {"kind": kind, "raw_hex": raw, "text": text, **extra}
                if encoding:
                    token["encoding"] = encoding
                tokens.append(token)
            pos += width
        raise DecodeError(pos, "missing terminator within parser limit")
