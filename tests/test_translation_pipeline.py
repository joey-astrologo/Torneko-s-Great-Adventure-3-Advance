"""Exercise source preservation, relocation ownership, and reader constraints."""

import copy
from pathlib import Path
import struct
import tempfile
import unittest

from tools.translation_pipeline import (
    ANCHORS, CATALOG, ORIGINAL_ROM, ROM_LIMIT, AppendAllocator, FontZero,
    build_rom, encode_english, extract, load_json, measure_variant, run,
    validate_translation,
)


class AllocatorTests(unittest.TestCase):
    def test_alignment_and_exact_end_without_overlap(self):
        allocator = AppendAllocator(0x1000000, 0x1000008)
        self.assertEqual(allocator.allocate("one", b"a\0"), 0x1000000)
        self.assertEqual(allocator.allocate("two", b"abc\0"), 0x1000004)
        self.assertEqual(allocator.cursor, allocator.limit)
        self.assertEqual(allocator.allocations[1]["padding_before"], 2)
        with self.assertRaisesRegex(ValueError, "capacity"):
            allocator.allocate("three", b"x")
        self.assertEqual(len(allocator.allocations), 2)

    def test_rejects_duplicate_ids_and_bad_alignment(self):
        allocator = AppendAllocator()
        allocator.allocate("one", b"x")
        for ident, alignment in (("one", 4), ("two", 3), ("two", 0)):
            with self.subTest(ident=ident, alignment=alignment), self.assertRaises(ValueError):
                allocator.allocate(ident, b"x", alignment)
        self.assertEqual(allocator.cursor, 0x1000001)

    def test_never_allocates_beyond_cartridge_limit(self):
        with self.assertRaises(ValueError):
            AppendAllocator(limit=ROM_LIMIT + 1)
        allocator = AppendAllocator(ROM_LIMIT - 4)
        self.assertEqual(allocator.allocate("last", b"abc\0"), ROM_LIMIT - 4)
        with self.assertRaises(ValueError):
            allocator.allocate("overflow", b"\0")


class GrammarTests(unittest.TestCase):
    def test_encodes_commands_without_confusing_zero_with_a_terminator(self):
        self.assertEqual(encode_english("{center}Log {slot}\n{x:64}{choice:1}Slow"),
                         b"$cLog $j0\n\x03\x08\x40\x03\x14\x01Slow\0")

    def test_rejects_unmodelled_commands_and_unsupported_characters(self):
        for text in ("", "bad\0text", "a\r\nb", "café", "$j0", "`x", "{missing}", "{slot", "slot}", "{{slot}}"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                encode_english(text)

    def test_rejects_duplicate_json_keys(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            path.write_text('{"english": "a", "english": "b"}')
            with self.assertRaisesRegex(ValueError, "Duplicate JSON key"):
                load_json(path)


class CatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not ORIGINAL_ROM.is_file():
            raise unittest.SkipTest("The local Japanese ROM is required")
        cls.original = ORIGINAL_ROM.read_bytes()
        cls.font = FontZero(cls.original)

    def setUp(self):
        self.anchors = load_json(ANCHORS)
        self.catalog = load_json(CATALOG)

    def test_japanese_round_trip_is_identical_including_controls(self):
        catalog = extract(self.original, self.anchors)
        for entry in catalog["entries"]:
            rebuilt = b"".join(bytes.fromhex(t["raw_hex"]) for t in entry["source_tokens"]) + b"\0"
            self.assertEqual(rebuilt.hex(), entry["source_hex"])
        rebuilt, report = build_rom(self.original, catalog, self.anchors, "japanese")
        self.assertEqual(rebuilt, self.original)
        self.assertTrue(report["japanese_roundtrip_identical"])
        self.assertEqual(report["allocations"], [])

    def test_english_is_deterministic_and_changes_only_owned_pointers(self):
        rebuilt, report = build_rom(self.original, self.catalog, self.anchors)
        self.catalog["entries"].reverse()
        self.anchors["entries"].reverse()
        reordered, second = build_rom(self.original, self.catalog, self.anchors)
        self.assertEqual(rebuilt, reordered)
        self.assertEqual(report["allocations"], second["allocations"])
        self.assertEqual(len(rebuilt), ROM_LIMIT)
        restored = bytearray(rebuilt[:len(self.original)])
        entries = {e["id"]: e for e in self.catalog["entries"]}
        allocations = {a["id"]: a for a in report["allocations"]}
        for change in report["pointer_changes"]:
            offset = change["offset"]
            self.assertEqual(struct.unpack_from("<I", rebuilt, offset)[0],
                             0x08000000 + allocations[change["id"]]["offset"])
            restored[offset:offset + 4] = self.original[offset:offset + 4]
        self.assertEqual(restored, self.original)
        cursor = len(self.original)
        for allocation in report["allocations"]:
            at, size = allocation["offset"], allocation["bytes"]
            self.assertEqual(rebuilt[cursor:at], b"\xff" * (at - cursor))
            self.assertEqual(rebuilt[at:at + size], encode_english(entries[allocation["id"]]["english"]))
            cursor = at + size
        self.assertEqual(rebuilt[cursor:], b"\xff" * (ROM_LIMIT - cursor))

    def test_null_leaves_source_pointers_and_storage_unchanged(self):
        for entry in self.catalog["entries"]:
            entry["english"] = None
        rebuilt, report = build_rom(self.original, self.catalog, self.anchors)
        self.assertEqual(rebuilt, self.original)
        self.assertEqual(report["translated_entries"], 0)
        self.catalog["entries"][0]["english"] = "New game"
        rebuilt, report = build_rom(self.original, self.catalog, self.anchors)
        self.assertEqual(len(report["allocations"]), 1)
        for anchor in self.anchors["entries"][1:]:
            for pointer in anchor["pointers"]:
                at = int(pointer, 0)
                self.assertEqual(rebuilt[at:at + 4], self.original[at:at + 4])

    def test_rejects_wrong_rom_or_edited_source(self):
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            extract(self.original[:-1], self.anchors)
        for field, value in (("japanese", "changed"), ("source_hex", "00"), ("source_tokens", [])):
            catalog = copy.deepcopy(self.catalog)
            catalog["entries"][0][field] = value
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "Catalog source changed"):
                build_rom(self.original, catalog, self.anchors)

    def test_rejects_wrong_duplicate_or_unaligned_pointer_owners(self):
        for pointers, message in ((["0x00C78290"], "Pointer mismatch"),
                                  (["0x00C78280", "0x00C78280"], "Duplicate pointer"),
                                  (["0x00C78281"], "Invalid pointer")):
            anchors = copy.deepcopy(self.anchors)
            anchors["entries"][0]["pointers"] = pointers
            with self.subTest(pointers=pointers), self.assertRaisesRegex(ValueError, message):
                extract(self.original, anchors)

    def test_rejects_overlapping_sources_and_duplicate_catalog_ids(self):
        anchor = copy.deepcopy(self.anchors["entries"][0])
        anchor["id"] = "duplicate-source"
        self.anchors["entries"].append(anchor)
        with self.assertRaisesRegex(ValueError, "Overlapping catalog source"):
            extract(self.original, self.anchors)
        self.catalog["entries"].append(self.catalog["entries"][0])
        with self.assertRaisesRegex(ValueError, "Duplicate catalog"):
            build_rom(self.original, self.catalog, load_json(ANCHORS))

    def test_preserves_command_order_and_checks_fixed_columns(self):
        entry = next(e for e in self.catalog["entries"] if e["id"] == "settings.message_speed")
        profile = self.anchors["profiles"]["settings"]
        english = "Text speed{x:64}{choice:1}Slow{x:96}{choice:2}Norm{x:128}{choice:3}Fast"
        for text in (english.replace("{choice:1}", ""),
                     english.replace("{x:64}{choice:1}", "{choice:1}{x:64}")):
            with self.assertRaisesRegex(ValueError, "sequence differs"):
                validate_translation(text, entry["japanese"], profile, self.font)
        # Normal fits 32 pixels but leaves no cursor gap before the next option.
        validate_translation(english, entry["japanese"], profile, self.font)
        with self.assertRaisesRegex(ValueError, "next fixed column"):
            validate_translation(english.replace("Norm", "Normal"), entry["japanese"], profile, self.font)
        tight_profile = dict(profile, column_gap=0)
        validate_translation(english.replace("Norm", "Normal"), entry["japanese"], tight_profile, self.font)
        with self.assertRaisesRegex(ValueError, "next fixed column"):
            validate_translation(english.replace("Norm", "Normalx"), entry["japanese"], tight_profile, self.font)

    def test_checks_both_slot_numbers_and_formatted_ram_limit(self):
        text = "Log {slot}"
        profile = dict(self.anchors["profiles"]["message"])
        _, report = validate_translation(text, "{slot}", profile, self.font)
        variants = report["variants"]
        self.assertEqual([v["slot"] for v in variants], ["１", "２"])
        self.assertEqual([bytes.fromhex(v["payload_hex"]) for v in variants], [b"Log \x82\x50", b"Log \x82\x51"])
        self.assertGreater(variants[1]["lines"][0]["end_x"], variants[0]["lines"][0]["end_x"])
        profile["width"] = variants[0]["lines"][0]["end_x"]
        with self.assertRaisesRegex(ValueError, "window width"):
            validate_translation(text, "{slot}", profile, self.font)
        profile["width"], profile["payload_limit"] = 208, 6
        validate_translation(text, "{slot}", profile, self.font)  # NUL is beyond the payload, as in the reader.
        profile["payload_limit"] = 5
        with self.assertRaisesRegex(ValueError, "RAM payload"):
            validate_translation(text, "{slot}", profile, self.font)

    def test_rejects_line_overflow_and_bad_story_centering(self):
        with self.assertRaisesRegex(ValueError, "Too many lines"):
            validate_translation("a\nb", "title", self.anchors["profiles"]["title"], self.font)
        profile = self.anchors["profiles"]["story"]
        with self.assertRaisesRegex(ValueError, "begin with"):
            validate_translation("a{center}", "{center}a", profile, self.font)
        with self.assertRaisesRegex(ValueError, "window width"):
            validate_translation("W" * 40, "a", self.anchors["profiles"]["message"], self.font)

    def test_width_counts_ink_overhang_as_well_as_cursor_advance(self):
        class OverhangFont:
            def glyph(self, character):
                return ord(character), 3, 5
        profile = {"width": 4, "start_x": 0, "alignment": "left", "max_lines": 1, "payload_limit": None}
        with self.assertRaisesRegex(ValueError, "window width"):
            measure_variant("W", profile, OverhangFont(), "１")

    def test_default_choice_marker_is_preserved_but_has_no_glyph_width(self):
        raw, report = validate_translation("{default}Yes", "{default}はい",
                                           self.anchors["profiles"]["choice"], self.font)
        self.assertEqual(raw, b"*Yes\0")
        row = report["variants"][0]["lines"][0]
        self.assertEqual([g["code"] for g in row["glyphs"]], list(b"Yes"))
        self.assertEqual(row["glyphs"][0]["x"], 4)

    def test_default_choice_cannot_be_removed_moved_or_added_as_raw_text(self):
        profile = self.anchors["profiles"]["choice"]
        for english, source in (("Yes", "{default}はい"), ("Yes{default}", "{default}はい"), ("*No", "いいえ")):
            with self.subTest(english=english), self.assertRaises(ValueError):
                validate_translation(english, source, profile, self.font)

    def test_default_choice_is_not_an_invisible_command_in_other_readers(self):
        with self.assertRaisesRegex(ValueError, "prefix a menu label"):
            validate_translation("{default}Yes", "{default}はい", self.anchors["profiles"]["title"], self.font)

    def test_build_refuses_to_overwrite_source_path(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "torneko3-english.gba"
            source.write_bytes(self.original)
            with self.assertRaisesRegex(ValueError, "overwrite a source"):
                run("build", rom=source, output=directory)
            self.assertEqual(source.read_bytes(), self.original)


if __name__ == "__main__":
    unittest.main()
