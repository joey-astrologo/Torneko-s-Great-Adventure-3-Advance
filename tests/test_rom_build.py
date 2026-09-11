"""Cross-component ownership checks for complete translation builds."""

import unittest

from tools.build_first_label import ORIGINAL_ROM, digest
from tools.build_name_entry import build_name_rom
from tools.rom_build import RomBuild


class BuildLedgerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not ORIGINAL_ROM.is_file():
            raise unittest.SkipTest("The local Japanese ROM is required")
        cls.original = ORIGINAL_ROM.read_bytes()

    def setUp(self):
        self.build = RomBuild(self.original)

    def test_components_cannot_claim_overlapping_patches_even_if_bytes_match(self):
        self.build.patch("first", 100, self.original[100:104], self.original[100:104], "menus")
        with self.assertRaisesRegex(ValueError, "collision"):
            self.build.patch("second", 102, self.original[102:106], b"abcd", "items")
        self.build.patch("adjacent", 104, self.original[104:108], b"abcd", "items")
        _, ledger = self.build.finish()
        self.assertEqual(len(ledger["patches"]), 2)

    def test_allocation_ids_are_global_across_components(self):
        self.build.allocate("shared", b"first\0", "menus")
        with self.assertRaisesRegex(ValueError, "Duplicate allocation"):
            self.build.allocate("shared", b"second\0", "items")
        at = self.build.allocate("another", b"second\0", "items")
        self.assertEqual(at, 0x1000008)
        self.build.finish()

    def test_source_protection_applies_in_either_registration_order(self):
        self.build.protect_source("source", 100, 110, "items")
        with self.assertRaisesRegex(ValueError, "protected source"):
            self.build.patch("bad", 108, self.original[108:112], b"abcd", "names")
        self.build.patch("outside", 112, self.original[112:116], b"abcd", "names")
        with self.assertRaisesRegex(ValueError, "overlaps patch"):
            self.build.protect_source("later", 114, 118, "items")

    def test_finish_catches_writes_to_original_padding_and_unused_expansion(self):
        for offset in (10, 0x1000002, 0x1001000):
            with self.subTest(offset=offset):
                build = RomBuild(self.original)
                build.allocate("one", b"A\0", "menus")
                build.allocate("two", b"B\0", "items")
                build.data[offset] ^= 1
                with self.assertRaisesRegex(ValueError, "Unaccounted ROM changes"):
                    build.finish()

    def test_finish_catches_asset_changes_and_failed_patches_are_atomic(self):
        at = self.build.allocate("text", b"abc\0", "items")
        self.build.data[at] = ord("z")
        with self.assertRaisesRegex(ValueError, "outside ledger"):
            self.build.finish()
        original = bytes(self.build.data)
        with self.assertRaisesRegex(ValueError, "precondition"):
            self.build.patch("bad", 100, bytes(b ^ 1 for b in self.original[100:104]), b"abcd", "items")
        self.assertEqual(bytes(self.build.data), original)
        self.assertFalse(self.build.patches)

    def test_ram_reservations_reject_heap_collisions(self):
        self.build.reserve_memory("heap", 0x02010A90, 0x02034A90, "original")
        with self.assertRaisesRegex(ValueError, "overlaps"):
            self.build.reserve_memory("bad", 0x02034A8C, 0x02034A94, "names")
        self.build.reserve_memory("name", 0x0203BB38, 0x0203BB40, "names")
        self.assertEqual(len(self.build.finish()[1]["memory_reservations"]), 2)

    def test_combined_name_build_matches_the_pre_refactor_verified_image(self):
        rom, report = build_name_rom(self.original)
        self.assertEqual(digest(rom), "1708353fe119e7088ceb459f03ff7b2039852ae6611b1951d1d57cb60ef0b928")
        ledger = report["ledger"]
        self.assertEqual(len(ledger["allocations"]), 41)
        self.assertEqual(len(ledger["patches"]), 52)
        self.assertTrue(ledger["complete_image_matches_ledger"])


if __name__ == "__main__":
    unittest.main()
