"""Check expansion boundaries and preservation independently of emulator routing."""

import struct
import unittest

from tools.audit_rom_storage import uniform_runs
from tools.build_expansion_probe import EXPANDED_SIZE, LABEL_OFFSET, LIMIT_PROBE_OFFSET, make_expanded_rom
from tools.build_first_label import ORIGINAL_ROM


class UniformRegionTests(unittest.TestCase):
    def test_finds_both_fill_types_and_keeps_end_exclusive(self):
        data = b"ABC" + bytes(256) + b"Z" + b"\xff" * 300
        self.assertEqual(uniform_runs(data), [
            {"start": 3, "end": 259, "bytes": 256, "fill": 0},
            {"start": 260, "end": 560, "bytes": 300, "fill": 255},
        ])

    def test_does_not_merge_separated_runs_or_count_short_ones(self):
        self.assertEqual(uniform_runs(bytes(255) + b"x" + bytes(255)), [])


class ExpansionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not ORIGINAL_ROM.is_file():
            raise unittest.SkipTest("The local Japanese ROM is required")
        cls.original = ORIGINAL_ROM.read_bytes()

    def test_preserves_original_except_pointer_and_uses_new_space(self):
        expanded = make_expanded_rom(self.original)
        self.assertEqual(len(expanded), EXPANDED_SIZE)
        self.assertEqual(expanded[:0xC78280], self.original[:0xC78280])
        self.assertEqual(expanded[0xC78284:0x1000000], self.original[0xC78284:])
        self.assertEqual(struct.unpack_from("<I", expanded, 0xC78280)[0], 0x09000000)
        self.assertEqual(expanded[LABEL_OFFSET:LABEL_OFFSET + 16], b"Start adventure\0")
        self.assertEqual(expanded[LABEL_OFFSET + 16:], b"\xff" * (0x1000000 - 16))

    def test_can_place_a_terminated_string_at_the_exact_end(self):
        expanded = make_expanded_rom(self.original, "ABC", EXPANDED_SIZE - 4)
        self.assertEqual(len(expanded), EXPANDED_SIZE)
        self.assertEqual(expanded[-4:], b"ABC\0")
        self.assertEqual(struct.unpack_from("<I", expanded, 0xC78280)[0], 0x09FFFFFC)

    def test_rejects_overflow_instead_of_growing_past_32_mib(self):
        with self.assertRaisesRegex(ValueError, "fit at a four-byte-aligned offset"):
            make_expanded_rom(self.original, "ABCD", EXPANDED_SIZE - 4)

    def test_rejects_existing_rom_space_and_unaligned_allocations(self):
        for offset in (0x00FD7B00, 0x01000001, -4):
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                make_expanded_rom(self.original, offset=offset)

    def test_rejects_wrong_base_and_embedded_terminators(self):
        with self.assertRaisesRegex(ValueError, "verified Japanese original"):
            make_expanded_rom(self.original[:-1])
        with self.assertRaisesRegex(ValueError, "contain no NUL"):
            make_expanded_rom(self.original, "A\0B")

    def test_limit_probe_pointer_uses_the_upper_half_address(self):
        expanded = make_expanded_rom(self.original, offset=LIMIT_PROBE_OFFSET)
        self.assertEqual(struct.unpack_from("<I", expanded, 0xC78280)[0], 0x09FFFFC0)


if __name__ == "__main__":
    unittest.main()
