"""Complete context tables, retained controls, and shared insertion ownership."""

from copy import deepcopy
import json
from pathlib import Path
import struct
import tempfile
import unittest

from tools.build_first_label import ORIGINAL_ROM
from tools.build_item_contexts import (TABLES, add_contexts, build_context_rom, encode_english,
                                       extract_catalog, initialize_catalog, validate_catalog)
from tools.game_text import rebuild
from tools.rom_build import RomBuild
from tools.translation_pipeline import FontZero


class ItemContextTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not ORIGINAL_ROM.exists():
            raise unittest.SkipTest("The local Japanese ROM is required")
        cls.original = ORIGINAL_ROM.read_bytes()
        cls.catalog = extract_catalog(cls.original)
        cls.font = FontZero(cls.original)

    def test_whole_tables_relocate_exact_bytes_aliases_and_only_pointer_fields(self):
        rom, report = build_context_rom(self.original, self.catalog, "japanese")
        entries = {e["id"]: e for e in self.catalog["entries"]}
        self.assertEqual(len(entries), 344)
        words = set()
        for asset in report["contexts"]["allocations"]:
            entry = entries[asset["id"]]
            raw = rebuild(entry["source_tokens"])
            self.assertEqual(rom[asset["offset"]:asset["offset"] + asset["bytes"]], raw)
            source = int(entry["offset"], 0)
            self.assertEqual(rom[source:source + len(raw)], raw)
            for pointer in entry["pointer_offsets"]:
                offset = int(pointer, 0)
                self.assertNotIn(offset, words)
                words.add(offset)
                self.assertEqual(struct.unpack_from("<I", rom, offset)[0], 0x08000000 + asset["offset"])
            for category in entry["category_fields"]:
                self.assertEqual(struct.unpack_from("<I", rom, int(category["offset"], 0))[0], category["value"])
        self.assertEqual(words, {base + i * stride + field for base, count, stride, field in TABLES.values() for i in range(count)})
        alias = entries["context.synthesis.000"]
        self.assertEqual(alias["rows"], [0, 98, 99])
        self.assertEqual(len(report["ledger"]["allocations"]), 1104)
        self.assertEqual(len(report["ledger"]["patches"]), 1138)
        self.assertTrue(report["ledger"]["complete_image_matches_ledger"])

    def test_category_words_are_protected_across_components(self):
        build = RomBuild(self.original)
        add_contexts(build, self.catalog)
        at = 0x190808
        with self.assertRaisesRegex(ValueError, "protected source"):
            build.patch("bad.category", at, self.original[at:at + 4], b"abcd", "other")
        with self.assertRaisesRegex(ValueError, "collision"):
            build.patch("bad.pointer", at + 4, self.original[at + 4:at + 8], b"abcd", "other")

    def test_synthesis_preserves_six_pixel_gap_without_exposing_raw_controls(self):
        entry = {"layout": "synthesis_gap", "english": "Heading\nFirst effect line\nSecond effect line"}
        payload, metrics = encode_english(entry, self.font)
        self.assertEqual(payload, b"Heading\r\x1dFirst effect line\rSecond effect line\0")
        self.assertEqual(metrics["line_y"], [48, 67, 80])
        self.assertEqual(metrics["wrapped_bytes_including_nul"], len(payload) + 3)
        plain, metrics = encode_english({"layout": "synthesis_plain", "english": "None"}, self.font)
        self.assertEqual(plain, b"None\r\0")
        self.assertEqual(metrics["line_y"], [48])

    def test_synthesis_footer_heading_width_and_control_boundaries_fail_closed(self):
        for text in ("Heading only", "Heading\nOne\nTwo\nThree", "W" * 30 + "\nBody", "Heading\n\x1dBody", "Heading\n%s", "Heading\n\nBody"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                encode_english({"layout": "synthesis_gap", "english": text}, self.font)
        with self.assertRaises(ValueError):
            encode_english({"layout": "synthesis_plain", "english": "One\nTwo"}, self.font)

    def test_unidentified_names_keep_byte_and_pixel_reserves(self):
        for text in ("i" * 33, "W" * 20, "A\nB", "A\0B"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                encode_english({"layout": "name", "english": text}, self.font)
        self.assertEqual(encode_english({"layout": "name", "english": "Narrow pot"}, self.font)[0], b"Narrow pot\0")

    def test_regeneration_preserves_existing_drafts_and_notes_exactly(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "contexts.json"
            catalog = initialize_catalog(self.original, path)
            catalog["entries"][0].update(english="My staff", notes="Keep this note")
            raw = json.dumps(catalog, ensure_ascii=False).encode()
            path.write_bytes(raw)
            self.assertEqual(initialize_catalog(self.original, path), catalog)
            self.assertEqual(path.read_bytes(), raw)

    def test_missing_duplicate_and_modified_source_fields_are_rejected(self):
        for change in ("missing", "duplicate", "category", "pointer", "layout", "tokens"):
            catalog = deepcopy(self.catalog)
            entry = catalog["entries"][0]
            if change == "missing":
                catalog["entries"].pop()
            elif change == "duplicate":
                catalog["entries"].append(deepcopy(entry))
            elif change == "category":
                entry["category_fields"][0]["value"] = 7
            elif change == "pointer":
                entry["pointer_offsets"][0] = "0x00190808"
            elif change == "layout":
                entry["layout"] = "synthesis_plain"
            else:
                entry["source_tokens"][0]["raw_hex"] = "41"
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate_catalog(self.original, catalog)

    def test_nulls_remain_japanese_and_reordering_does_not_change_rom(self):
        catalog = deepcopy(self.catalog)
        catalog["entries"][0]["english"] = "Cedar staff"
        rom, report = build_context_rom(self.original, catalog)
        self.assertEqual(report["contexts"]["translated_entries"], 1)
        catalog["entries"].reverse()
        self.assertEqual(build_context_rom(self.original, catalog)[0], rom)
        entries = {e["id"]: e for e in catalog["entries"]}
        for asset in report["contexts"]["allocations"]:
            expected = b"Cedar staff\0" if asset["translated"] else rebuild(entries[asset["id"]]["source_tokens"])
            self.assertEqual(rom[asset["offset"]:asset["offset"] + asset["bytes"]], expected)


if __name__ == "__main__":
    unittest.main()
