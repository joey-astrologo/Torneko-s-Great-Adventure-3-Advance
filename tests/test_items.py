"""Whole-family item ownership, draft retention and insertion limits."""

from copy import deepcopy
import json
from pathlib import Path
import struct
import tempfile
import unittest

from tools.build_first_label import ORIGINAL_ROM
from tools.build_items import (TABLES, build_item_rom, encode_english,
                               extract_catalog, initialize_catalog, validate_catalog)
from tools.game_text import rebuild
from tools.translation_pipeline import FontZero


class ItemTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not ORIGINAL_ROM.exists():
            raise unittest.SkipTest("The local Japanese ROM is required")
        cls.original = ORIGINAL_ROM.read_bytes()
        cls.source = extract_catalog(cls.original)
        cls.font = FontZero(cls.original)

    def test_complete_tables_relocate_losslessly_and_keep_aliases(self):
        rom, report = build_item_rom(self.original, self.source, "japanese")
        entries = {e["id"]: e for e in self.source["entries"]}
        self.assertEqual(len(entries), 719)
        words = set()
        for asset in report["items"]["allocations"]:
            entry = entries[asset["id"]]
            start, size = asset["offset"], asset["bytes"]
            self.assertEqual(rom[start:start + size], rebuild(entry["source_tokens"]))
            source = int(entry["offset"], 0)
            self.assertEqual(rom[source:source + size], self.original[source:source + size])
            for word in entry["pointer_offsets"]:
                offset = int(word, 0)
                self.assertNotIn(offset, words)
                words.add(offset)
                self.assertEqual(struct.unpack_from("<I", rom, offset)[0], start + 0x08000000)
        self.assertEqual(words, {base + row * 4 for base, count in TABLES.values() for row in range(count)})
        self.assertEqual(len(report["ledger"]["allocations"]), 760)
        self.assertEqual(len(report["ledger"]["patches"]), 792)
        self.assertTrue(report["ledger"]["complete_image_matches_ledger"])

    def test_english_only_replaces_authored_entries_and_build_is_deterministic(self):
        catalog = deepcopy(self.source)
        catalog["entries"][0]["english"] = "None"
        rom, report = build_item_rom(self.original, catalog)
        second, repeated = build_item_rom(self.original, catalog)
        self.assertEqual(rom, second)
        self.assertEqual(report, repeated)
        self.assertEqual(report["items"]["translated_entries"], 1)
        entries = {e["id"]: e for e in catalog["entries"]}
        for asset in report["items"]["allocations"]:
            expected = b"None\0" if asset["translated"] else rebuild(entries[asset["id"]]["source_tokens"])
            self.assertEqual(rom[asset["offset"]:asset["offset"] + asset["bytes"]], expected)

    def test_existing_english_and_notes_are_preserved_without_rewriting_catalog(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "items.json"
            catalog = initialize_catalog(self.original, path)
            catalog["entries"][0].update(english="My draft", notes="Keep these notes")
            raw = json.dumps(catalog, ensure_ascii=False).encode()
            path.write_bytes(raw)
            self.assertEqual(initialize_catalog(self.original, path), catalog)
            self.assertEqual(path.read_bytes(), raw)

    def test_missing_duplicate_or_modified_source_ownership_is_rejected(self):
        for kind in ("missing", "duplicate", "pointer", "tokens", "alias", "source"):
            catalog = deepcopy(self.source)
            first = catalog["entries"][0]
            if kind == "missing":
                catalog["entries"].pop()
            elif kind == "duplicate":
                catalog["entries"].append(deepcopy(first))
            elif kind == "pointer":
                first["pointer_offsets"][0] = "0x0018F170"
            elif kind == "tokens":
                first["source_tokens"][0]["raw_hex"] = "41"
            elif kind == "alias":
                first["item_indices"].append(1)
            else:
                first["source_hex"] = "4100"
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                validate_catalog(self.original, catalog)

    def test_name_pixel_and_byte_reserves_are_separate(self):
        for text, message in (("W" * 20, "pixels"), ("i" * 33, "byte reserve"), ("A\nB", "lines")):
            with self.subTest(text=text), self.assertRaisesRegex(ValueError, message):
                encode_english({"family": "name", "english": text}, self.font)
        payload, _ = encode_english({"family": "name", "english": "Copper sword"}, self.font)
        self.assertEqual(payload, b"Copper sword\0")

    def test_description_has_native_carriage_returns_and_footer_reserve(self):
        payload, _ = encode_english({"family": "description", "english": "One\nTwo"}, self.font)
        self.assertEqual(payload, b"One\rTwo\r\0")
        for text in ("\n".join(["Line"] * 6), "W" * 30, "One\n\nTwo"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                encode_english({"family": "description", "english": text}, self.font)

    def test_commands_embedded_nuls_and_unapproved_encoding_fail_closed(self):
        for text in ("%s", "$i0", "A\0B", "{name}", "`", "Épée", "A\rB"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                encode_english({"family": "description", "english": text}, self.font)


if __name__ == "__main__":
    unittest.main()
