"""Check width accounting independently of any particular ROM glyph design."""

import unittest

from tools.font_metrics import measure_line


class FontWidthTests(unittest.TestCase):
    def setUp(self):
        self.font = {"glyphs": {
            "i": {"advance": 3, "ink_bounds": [1, 1, 2, 10]},
            "W": {"advance": 7, "ink_bounds": [0, 1, 8, 10]},
            " ": {"advance": 5, "ink_bounds": None},
            "$": {"advance": 7, "ink_bounds": [0, 0, 7, 12]},
            "`": {"advance": 5, "ink_bounds": [0, 0, 5, 12]},
        }}

    def test_space_has_advance_without_ink(self):
        self.assertEqual(measure_line(self.font, "i "), {"advance": 8, "ink_right": 2})

    def test_visible_overhang_is_not_hidden_by_advance(self):
        self.assertEqual(measure_line(self.font, "iW"), {"advance": 10, "ink_right": 11})

    def test_extra_spacing_matches_per_glyph_cursor_updates(self):
        self.assertEqual(measure_line(self.font, "ii", spacing=1), {"advance": 8, "ink_right": 6})

    def test_empty_line_has_zero_width(self):
        self.assertEqual(measure_line(self.font, ""), {"advance": 0, "ink_right": 0})

    def test_controls_and_unmapped_characters_require_an_explicit_reader(self):
        for text in ("$", "`", "\n", "\t", "é"):
            with self.subTest(text=text):
                with self.assertRaises(ValueError):
                    measure_line(self.font, text)


if __name__ == "__main__":
    unittest.main()
