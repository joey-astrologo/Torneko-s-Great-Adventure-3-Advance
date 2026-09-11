"""Validate source checks and the proof patch's exported binary format."""

import copy
import unittest

from tools.build_first_label import ORIGINAL_ROM, load_manifest, patch_rom


class FirstLabelPatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not ORIGINAL_ROM.is_file():
            raise unittest.SkipTest("The local Japanese ROM is required")
        cls.original = ORIGINAL_ROM.read_bytes()

    def setUp(self):
        self.manifest = copy.deepcopy(load_manifest())

    def test_rejects_a_different_base(self):
        with self.assertRaisesRegex(ValueError, "ROM hash mismatch"):
            patch_rom(self.original[:-1], self.manifest)

    def test_rejects_text_that_leaves_no_terminator(self):
        self.manifest["english"] = "X" * self.manifest["field_bytes"]
        with self.assertRaisesRegex(ValueError, "fit with its terminator"):
            patch_rom(self.original, self.manifest)

    def test_rejects_an_embedded_terminator(self):
        self.manifest["english"] = "Be\0gin"
        with self.assertRaisesRegex(ValueError, "contain no NUL"):
            patch_rom(self.original, self.manifest)

    def test_rejects_an_incorrect_source_label(self):
        self.manifest["japanese"] = "ちがう"
        with self.assertRaisesRegex(ValueError, "Original label bytes"):
            patch_rom(self.original, self.manifest)

    def test_rejects_a_pointer_to_another_label(self):
        self.manifest["pointer_offset"] = "0x00C78290"
        with self.assertRaisesRegex(ValueError, "title menu pointer"):
            patch_rom(self.original, self.manifest)

    def test_exported_ips_reproduces_the_rom_and_preserves_other_data(self):
        patched, ips = patch_rom(self.original, self.manifest)
        self.assertEqual(ips[:5], b"PATCH")
        applied = bytearray(self.original)
        position = 5
        while ips[position:position + 3] != b"EOF":
            offset = int.from_bytes(ips[position:position + 3], "big")
            size = int.from_bytes(ips[position + 3:position + 5], "big")
            self.assertGreater(size, 0, "This proof should not need RLE")
            payload = ips[position + 5:position + 5 + size]
            self.assertEqual(len(payload), size)
            applied[offset:offset + size] = payload
            position += 5 + size
        self.assertEqual(position + 3, len(ips))
        self.assertEqual(bytes(applied), patched)
        self.assertEqual(len(patched), len(self.original))
        start = int(self.manifest["rom_offset"], 0)
        end = start + self.manifest["field_bytes"]
        self.assertEqual(patched[:start], self.original[:start])
        self.assertEqual(patched[end:], self.original[end:])
        self.assertEqual(patched[start:end], b"Begin\0\0\0\0\0\0\0")


if __name__ == "__main__":
    unittest.main()
