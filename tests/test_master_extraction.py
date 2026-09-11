"""Guard font-index decoding, reference boundaries, and editable draft retention."""

import copy
import unittest

from tools.build_first_label import ORIGINAL_ROM, digest
from tools.extract_master_text import collapse_overlaps, merge_drafts, verify_roundtrip
from tools.game_text import DecodeError, GameTextCodec, rebuild, token_boundaries


class GameTextTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not ORIGINAL_ROM.is_file():
            raise unittest.SkipTest("The local Japanese ROM is required")
        cls.rom = ORIGINAL_ROM.read_bytes()
        cls.codec = GameTextCodec(cls.rom)

    def test_indexed_monster_name_and_description_decode_from_original_tables(self):
        self.assertEqual(self.codec.parse(self.rom, 0x191C14)["display"], "トルネコ")
        self.assertEqual(self.codec.parse(self.rom, 0x1AAFD1)["display"], "ちからをためて攻撃する")
        text = self.codec.parse(self.rom, 0x191C14)
        self.assertEqual(text["raw_hex"], "f961f984f966f94c00")
        self.assertEqual(rebuild(text["tokens"]), self.rom[text["offset"]:text["end"]])

    def test_single_byte_kana_use_the_game_mapping(self):
        self.assertEqual(self.codec.parse(b"\xc4\xdd\0", 0)["display"], "とん")
        self.assertEqual(self.codec.parse(b"ABC\0", 0)["display"], "ABC")

    def test_font_index_bounds_and_selected_font_are_explicit(self):
        last = self.codec.parse(bytes.fromhex("fe2000"), 0)
        self.assertEqual(last["display"], "壺")
        for raw in (bytes.fromhex("fe2100"), bytes.fromhex("f81f00"), b"\xf9\0"):
            with self.subTest(raw=raw), self.assertRaises(DecodeError):
                self.codec.parse(raw, 0)
        with self.assertRaises(DecodeError):
            GameTextCodec(self.rom, 1).parse(bytes.fromhex("fe2000"), 0)

    def test_dollar_arguments_are_fixed_width_not_greedy_numbers(self):
        raw = b"$i01$v051$/0842$j02\0"
        text = self.codec.parse(raw, 0)
        self.assertEqual([t["text"] for t in text["tokens"] if t["kind"] == "dollar_command"],
                         ["$i0", "$v05", "$/084", "$j0"])
        self.assertEqual(rebuild(text["tokens"]), raw)
        for raw in (b"$i\0", b"$v0\0", b"$/08\0"):
            with self.subTest(raw=raw), self.assertRaises(DecodeError):
                self.codec.parse(raw, 0)

    def test_unknown_command_is_preserved_without_guessing_arity(self):
        result = self.codec.parse(b"$q123\0", 0)
        self.assertEqual(result["tokens"][0]["grammar"], "unresolved")
        self.assertEqual(result["tokens"][0]["text"], "$q")
        self.assertEqual(rebuild(result["tokens"]), b"$q123\0")

    def test_binary_zero_argument_and_printf_argument_template_survive(self):
        raw = b"\x03\x08\0ABC\x03\x05%cHP %02d/%d\0"
        text = self.codec.parse(raw, 0)
        self.assertEqual(rebuild(text["tokens"]), raw)
        binary = [t for t in text["tokens"] if t["kind"] == "binary_control"]
        self.assertEqual(binary[0]["raw_hex"], "030800")
        self.assertEqual(binary[1]["argument_template_candidate"], "%c")
        self.assertEqual([t["text"] for t in text["tokens"] if t["kind"] == "printf"], ["%02d", "%d"])
        self.assertNotIn(2, token_boundaries(text["tokens"]))

    def test_glyph_trails_do_not_turn_into_commands(self):
        # F824 is the indexed '$' glyph, not a source dollar-command byte.
        result = self.codec.parse(bytes.fromhex("f824") + b"t\0", 0)
        self.assertTrue(all(t["kind"] != "dollar_command" for t in result["tokens"]))
        self.assertEqual(rebuild(result["tokens"]), bytes.fromhex("f824") + b"t\0")

    def test_repeated_control_prefix_is_opaque_and_lossless(self):
        result = self.codec.parse(self.rom, 0xC4E43C)
        self.assertTrue(result["display"].startswith("$tの最大ちから"))
        self.assertEqual([t["raw_hex"] for t in result["tokens"] if t["kind"] == "opaque_control"], ["03"])
        self.assertEqual(rebuild(result["tokens"]), self.rom[result["offset"]:result["end"]])

    def test_parser_limit_and_unknown_controls_fail_closed(self):
        for raw, maximum in ((b"abc\0", 3), (b"\x03\x07abc\0", 4096), (b"abc\x01\0", 4096)):
            with self.subTest(raw=raw), self.assertRaises(DecodeError):
                self.codec.parse(raw, 0, maximum)

    def test_suffix_references_keep_character_boundary_evidence(self):
        raw = "ソA".encode("cp932") + b"\0"
        texts = [self.codec.parse(raw, at) for at in (0, 1, 2)]
        roots, aliases = collapse_overlaps(texts, {1: [100], 2: [104]})
        self.assertEqual(len(roots), 1)
        self.assertEqual([a["boundary"] for a in aliases[0]],
                         ["inside_character_or_control", "token_or_character"])
        self.assertEqual(aliases[0][1]["pointer_candidates"], ["0x00000068"])

    def test_roundtrip_rejects_token_changes_and_overlaps(self):
        raw = b"ABC\0"
        parsed = self.codec.parse(raw, 0)
        entry = {"id": "sample", "offset": "0x0", "source_hex": raw.hex(), "source_tokens": parsed["tokens"]}
        self.assertEqual(verify_roundtrip(raw, [entry]), digest(raw))
        with self.assertRaisesRegex(ValueError, "overlapping"):
            verify_roundtrip(raw, [entry, entry])
        entry["source_tokens"][0]["raw_hex"] = b"ABD".hex()
        with self.assertRaisesRegex(ValueError, "Token reconstruction"):
            verify_roundtrip(raw, [entry])


class DraftRetentionTests(unittest.TestCase):
    def setUp(self):
        self.fresh = {"schema": 1, "base_sha256": "source", "entries": [
            {"id": "one", "source_hex": "61626300", "english": None, "notes": ""}]}

    def test_reextract_preserves_english_and_notes(self):
        previous = copy.deepcopy(self.fresh)
        previous["entries"][0].update(english="Independent draft", notes="Needs a menu screenshot")
        result = merge_drafts(self.fresh, previous)
        self.assertEqual(result["entries"][0]["english"], "Independent draft")
        self.assertEqual(result["entries"][0]["notes"], "Needs a menu screenshot")

    def test_changed_source_missing_ids_and_duplicates_are_not_silently_accepted(self):
        for change in ("source", "missing", "duplicate"):
            previous = copy.deepcopy(self.fresh)
            if change == "source":
                previous["entries"][0]["source_hex"] = "64656600"
            elif change == "missing":
                previous["entries"][0]["id"] = "removed"
            else:
                previous["entries"].append(previous["entries"][0])
            with self.subTest(change=change), self.assertRaises(ValueError):
                merge_drafts(self.fresh, previous)


if __name__ == "__main__":
    unittest.main()
