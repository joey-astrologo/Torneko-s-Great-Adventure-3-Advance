"""Reject unsafe source changes, fixed-record overflow and shared ownership."""

from copy import deepcopy
import struct
import unittest

from tools.build_first_label import ORIGINAL_ROM
from tools.build_dungeon_interface import (CATALOG, ACTION_BASE, ACTION_COUNT, ACTION_STRIDE,
    HERO_BASE, HERO_POINTERS, add_interface, build_rom, encode_english, extract_catalog, validate_catalog)
from tools.rom_build import RomBuild
from tools.translation_pipeline import FontZero, load_json
from tools.build_enemy_items import build_rom as build_previous


class InterfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not ORIGINAL_ROM.exists():
            raise unittest.SkipTest("Local Japanese original required")
        cls.original = ORIGINAL_ROM.read_bytes()
        cls.catalog, cls.font = load_json(CATALOG), FontZero(cls.original)

    def test_complete_coverage_and_immutable_sources(self):
        self.assertEqual(len(validate_catalog(self.original, self.catalog)), 120)
        for field in ("source_hex", "source_tokens", "offset", "pointer_offsets", "rows", "master_id"):
            changed = deepcopy(self.catalog)
            changed["entries"][0][field] = "changed"
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_catalog(self.original, changed)
        for duplicate in (False, True):
            changed = deepcopy(self.catalog)
            changed["entries"].pop()
            if duplicate:
                changed["entries"].append(deepcopy(changed["entries"][0]))
            with self.assertRaises(ValueError):
                validate_catalog(self.original, changed)

    def test_fixed_records_keep_style_stride_and_padding(self):
        for language in ("japanese", "english"):
            build = RomBuild(self.original)
            report = add_interface(build, self.catalog, language)
            data, _ = build.finish()
            base = report["action_table_offset"]
            self.assertEqual(data[ACTION_BASE:ACTION_BASE + 41*12], self.original[ACTION_BASE:ACTION_BASE + 41*12])
            for e in self.catalog["entries"]:
                if e["family"] != "action":
                    continue
                raw = bytes.fromhex(e["source_hex"]) if language == "japanese" else encode_english(e, self.font)[0]
                at = base + e["rows"][0] * ACTION_STRIDE
                self.assertEqual(data[at:at+12], raw.ljust(12, b"\0"))
            target = struct.unpack_from("<I", data, HERO_POINTERS[0])[0] - 0x08000000
            self.assertEqual({struct.unpack_from("<I", data, p)[0] for p in HERO_POINTERS}, {target + 0x08000000})
            expected = self.original[HERO_BASE:HERO_BASE+20] if language == "japanese" else b"Torneko\0\0\0Tipper\0\0\0\0"
            self.assertEqual(data[target:target+20], expected)

    def test_byte_pixel_and_control_limits(self):
        action = next(deepcopy(e) for e in self.catalog["entries"] if e["family"] == "action")
        for text in ("i"*9, "W"*8, "A\nB", "$t", "%s", "A\0B"):
            action.update(english=text, display=None)
            with self.subTest(text=text), self.assertRaises(ValueError):
                encode_english(action, self.font)
        search = next(deepcopy(e) for e in self.catalog["entries"] if e["family"] == "search" and "$t" in e["japanese"])
        for text in ("No protagonist", "$t $t", "$t $i0", "$t " + "W"*40):
            search["english"] = text
            with self.subTest(text=text), self.assertRaises(ValueError):
                encode_english(search, self.font)

    def test_sources_windows_and_pointer_owners_cannot_collide(self):
        build = RomBuild(self.original)
        add_interface(build, self.catalog)
        for at in (0x1B3F60, 0x1B421C, 0x86F4D8, 0x6FBF4, 0x75750, 0x7DA7C):
            with self.subTest(at=at), self.assertRaisesRegex(ValueError, "collision"):
                build.patch("intruder", at, self.original[at:at+2], b"xx", "other")
        for at in (ACTION_BASE + 11, 0xC3DA74, HERO_BASE + 9):
            with self.subTest(at=at), self.assertRaisesRegex(ValueError, "protected source"):
                build.patch("intruder", at, self.original[at:at+1], b"x", "other")

    def test_complete_build_preserves_old_component_outputs_and_aliases(self):
        data, report = build_rom(self.original, "english", self.catalog)
        previous, previous_report = build_previous(self.original)
        for patch in previous_report["ledger"]["patches"]:
            at, raw = patch["offset"], bytes.fromhex(patch["after"])
            self.assertEqual(data[at:at + len(raw)], raw)
        for allocation in previous_report["ledger"]["allocations"]:
            at, size = allocation["offset"], allocation["bytes"]
            self.assertEqual(data[at:at + size], previous[at:at + size])
        base = report["interface"]["action_table_offset"]
        self.assertEqual(len(data), 0x2000000)
        self.assertEqual(struct.unpack_from("<I", data, 0x1B3F60)[0], struct.unpack_from("<I", data, 0x1B3FE0)[0])
        for e in self.catalog["entries"]:
            a = report["interface"]["relocated"][e["id"]]
            self.assertEqual(data[a["offset"]:a["offset"]+a["bytes"]], encode_english(e, self.font)[0])
        self.assertEqual(len({p["offset"] for p in report["ledger"]["patches"]}), len(report["ledger"]["patches"]))
        for window in report["interface"]["windows"]:
            at, source = window["relocated_offset"], window["source_start"]
            self.assertEqual(data[at:at+16], self.original[source:source+16])
            self.assertEqual(struct.unpack_from("<h", data, at+16)[0], 23)
            self.assertEqual(struct.unpack_from("<h", data, at+20)[0], 6)
            if window["pointer_offset"] == 0x75750:
                self.assertEqual(struct.unpack_from("<h", data, at+36)[0], 6)


if __name__ == "__main__":
    unittest.main()
