"""Guard the byte boundaries needed for lossless text extraction."""

import unittest

from tools.inventory_text import parse_text


class TextParsingTests(unittest.TestCase):
    def test_zero_argument_does_not_terminate_direct_renderer_text(self):
        raw = b"\x03\x08\x00" + "名前".encode("cp932") + b"\0padding"
        result = parse_text(raw, 0)
        self.assertEqual(result["tokens"][0]["raw_hex"], "030800")
        self.assertEqual(result["display"], "<03 08 00>名前")
        self.assertEqual(result["end"], 8)

    def test_control_argument_is_not_a_shift_jis_lead(self):
        raw = b"\x03\x09\x88" + "ひ".encode("cp932") + b"\0"
        result = parse_text(raw, 0)
        self.assertEqual(result["display"], "<03 09 88>ひ")
        self.assertEqual(result["tokens"][1]["raw_hex"], "82d0")

    def test_multibyte_trail_and_halfwidth_text_survive_exactly(self):
        raw = "ソ\\ｿﾉ草\n$c名前".encode("cp932") + b"\0"
        result = parse_text(raw, 0)
        rebuilt = b"".join(bytes.fromhex(t["raw_hex"]) for t in result["tokens"]) + b"\0"
        self.assertEqual(rebuilt, raw)
        self.assertIn("ソ\\ｿﾉ草<LF>$c名前", result["display"])

    def test_unknown_controls_fail_closed(self):
        for raw in (b"\x03\x07abc\0", b"abc\x01\0", b"\x03"):
            with self.subTest(raw=raw):
                self.assertIsNone(parse_text(raw, 0))

    def test_invalid_or_custom_encoding_fails_closed(self):
        for raw in (b"\x81\0", b"\x80A\0", b"\xF0\x40\0", b"\xFF\0"):
            with self.subTest(raw=raw):
                self.assertIsNone(parse_text(raw, 0))

    def test_limit_must_include_the_terminator(self):
        self.assertIsNone(parse_text(b"abc\0", 0, maximum=3))
        self.assertEqual(parse_text(b"abc\0", 0, maximum=4)["raw_hex"], "61626300")
        self.assertIsNone(parse_text(b"abc", 0))

    def test_offsets_and_empty_strings(self):
        self.assertIsNone(parse_text(b"abc\0", -1))
        self.assertIsNone(parse_text(b"abc\0", 4))
        self.assertEqual(parse_text(b"prefix\0", 6)["bytes_including_nul"], 1)

    def test_cp932_aliases_retain_raw_bytes(self):
        # NEC/IBM duplicate encodings are why Unicode alone is not a lossless source.
        first = bytes.fromhex("ed40")
        second = bytes.fromhex("fa5c")
        self.assertEqual(first.decode("cp932"), second.decode("cp932"))
        for encoded in (first, second):
            result = parse_text(encoded + b"\0", 0)
            self.assertEqual(result["tokens"][0]["raw_hex"], encoded.hex())


if __name__ == "__main__":
    unittest.main()
