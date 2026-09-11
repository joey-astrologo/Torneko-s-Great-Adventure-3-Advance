"""Enemy relocation, buffer/layout boundaries and integration ownership."""

from copy import deepcopy
import json
import struct
import tempfile
from pathlib import Path
import unittest

from tools.build_first_label import ORIGINAL_ROM, ROOT
from tools.build_enemies import CATALOG, add_enemies, extract_catalog, initialize_catalog, validate_catalog, encode_english
from tools.build_enemy_items import build_rom
from tools.rom_build import RomBuild
from tools.translation_pipeline import FontZero


class EnemyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not ORIGINAL_ROM.exists():
            raise unittest.SkipTest("Pinned local ROM required")
        cls.original = ORIGINAL_ROM.read_bytes()
        cls.catalog = json.loads(CATALOG.read_text())
        cls.font = FontZero(cls.original)

    def test_source_identity_pointers_and_coverage_fail_closed(self):
        for field in ("pointer_offset", "source_hex", "source_tokens", "row", "master_id"):
            edited = deepcopy(self.catalog)
            edited["entries"][0][field] = "invalid"
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_catalog(self.original, edited)
        for duplicate in (False, True):
            edited = deepcopy(self.catalog)
            edited["entries"].pop()
            if duplicate:
                edited["entries"].append(deepcopy(edited["entries"][0]))
            with self.assertRaises(ValueError):
                validate_catalog(self.original, edited)
        with self.assertRaisesRegex(ValueError, "pinned"):
            extract_catalog(b"X" + self.original[1:])

    def test_source_preserved_and_japanese_does_not_apply_english_layout(self):
        build = RomBuild(self.original)
        report = add_enemies(build, self.catalog, "japanese")
        data, ledger = build.finish()
        self.assertEqual(len(ledger["patches"]), 400)
        self.assertEqual(report["translated_entries"], 0)
        entries = {e["id"]: e for e in self.catalog["entries"]}
        for a in report["allocations"]:
            e = entries[a["id"]]
            raw = bytes.fromhex(e["source_hex"])
            self.assertEqual(data[a["offset"]:a["offset"]+a["bytes"]], raw)
            at = int(e["offset"], 0)
            self.assertEqual(data[at:at+len(raw)], raw)
            self.assertEqual(struct.unpack_from("<I", data, int(e["pointer_offset"],0))[0], a["offset"]+0x08000000)

    def test_cross_component_writes_to_enemy_ownership_are_rejected(self):
        build = RomBuild(self.original)
        add_enemies(build, self.catalog)
        for at in (0x192568, 0x1ACB74, 0x79A22):
            with self.assertRaisesRegex(ValueError, "collision"):
                build.patch("intruder", at, self.original[at:at+2], b"xx", "other")
        source = int(self.catalog["entries"][0]["offset"],0)
        with self.assertRaisesRegex(ValueError, "protected source"):
            build.patch("intruder", source, self.original[source:source+1], b"x", "other")

    def test_name_byte_limit_trait_layout_and_control_injection(self):
        name = deepcopy(self.catalog["entries"][0])
        name.update(english="i"*29, display=None)
        self.assertEqual(len(encode_english(name,self.font)[0]),30)
        for text in ("i"*30, "W"*19, "A\nB", "$m0", "%s", "A\0B"):
            name["english"] = text
            with self.subTest(text=text), self.assertRaises(ValueError):
                encode_english(name,self.font)
        trait = next(deepcopy(e) for e in self.catalog["entries"] if e["family"]=="trait")
        for text in ("One\nTwo\nThree\nFour", "W"*30, "A\n\nB"):
            trait["display"] = text
            with self.assertRaises(ValueError):
                encode_english(trait,self.font)

    def test_regeneration_preserves_full_draft_display_and_notes(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/"enemies.json"
            edited = deepcopy(self.catalog)
            edited["entries"][0].update(english="A full draft",display="A display",notes="Keep my note")
            raw = json.dumps(edited,ensure_ascii=False).encode()
            path.write_bytes(raw)
            self.assertEqual(initialize_catalog(self.original,path),edited)
            self.assertEqual(path.read_bytes(),raw)

    def test_complete_combined_build_is_deterministic_and_fully_accounted(self):
        data, report = build_rom(self.original)
        self.assertEqual([report[k]["translated_entries"] for k in ("enemies","items","contexts")],[400,719,344])
        self.assertTrue(report["ledger"]["complete_image_matches_ledger"])
        self.assertEqual(len(report["ledger"]["patches"]),1543)
        self.assertEqual(len(report["ledger"]["allocations"]),1507)
        self.assertEqual(data, (ROOT/"build/enemy-items/torneko3-enemies-items-english.gba").read_bytes())
        self.assertGreater(report["appended_remaining"], 15*1024*1024)


if __name__ == "__main__":
    unittest.main()
