"""Prevent false source attribution and gaps when extending native coverage."""

import unittest

from tools.verify_translation import identify_wrapped_source, require_coverage


class NativeCoverageTests(unittest.TestCase):
    def test_duplicate_labels_follow_the_pointer_read_for_the_current_table(self):
        sources = {0x09000000: b"Yes\0", 0x09000010: b"Yes\0"}
        self.assertEqual(identify_wrapped_source(b"\x03\x05\x07Yes\0", sources,
                                                 {0x09000000: 2, 0x09000010: 1}), 0x09000000)
        self.assertEqual(identify_wrapped_source(b"\x03\x05\x07Yes\0", sources,
                                                 {0x09000000: 2, 0x09000010: 3}), 0x09000010)

    def test_wrapper_requires_a_complete_payload_and_observed_source(self):
        sources = {1: b"Yes\0"}
        self.assertIsNone(identify_wrapped_source(b"\x03\x05\x07Yes indeed\0", sources, {1: 1}))
        self.assertIsNone(identify_wrapped_source(b"Yes\0", sources, {1: 1}))
        with self.assertRaisesRegex(RuntimeError, "traced source read"):
            identify_wrapped_source(b"\x03\x05\x07Yes\0", sources, {})

    def test_settings_wrapper_can_append_its_style_reset(self):
        self.assertEqual(identify_wrapped_source(b"\x03\x05\x07Text speed\x03\x06\0",
                                                 {1: b"Text speed\0"}, {1: 1}), 1)

    def test_every_translated_entry_needs_a_native_check(self):
        with self.assertRaisesRegex(RuntimeError, "missing"):
            require_coverage({"present": {}, "missing": {}}, [{"id": "present"}])
        self.assertEqual(require_coverage({"present": {}}, [{"id": "present"}]), {"present"})

    def test_every_supported_slot_substitution_needs_a_native_check(self):
        expected = {"message": {"variants": [{"slot": "１"}, {"slot": "２"}]}}
        checks = [{"id": "message", "slot": "１"}]
        with self.assertRaisesRegex(RuntimeError, "Substitution variants"):
            require_coverage({"message": {}}, checks, expected)
        checks.append({"id": "message", "slot": "２"})
        self.assertEqual(require_coverage({"message": {}}, checks, expected), {"message"})


if __name__ == "__main__":
    unittest.main()
