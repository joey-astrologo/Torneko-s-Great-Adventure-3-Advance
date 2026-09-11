"""Protect fixed status/order buffers, substitutions and existing insertions."""
from copy import deepcopy
import unittest
from tools.build_gameplay_help import CATALOG, build_rom, encode, validate_catalog
from tools.build_first_label import ORIGINAL_ROM
from tools.translation_pipeline import load_json


class GameplayHelpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = ORIGINAL_ROM.read_bytes(); cls.catalog = load_json(CATALOG)
        cls.entries = {e['id']: e for e in cls.catalog['entries']}

    def test_source_and_ownership_cannot_be_reassigned(self):
        self.assertEqual(len(validate_catalog(self.original, self.catalog)), 191)
        for field in ('source_hex', 'source_tokens', 'pointer_owners', 'offset', 'row'):
            bad = deepcopy(self.catalog); bad['entries'][0][field] = 'changed'
            with self.subTest(field=field), self.assertRaises((ValueError, TypeError)):
                validate_catalog(self.original, bad)

    def test_duplicate_or_missing_entry_is_rejected(self):
        for duplicate in (False, True):
            bad = deepcopy(self.catalog)
            if duplicate: bad['entries'].append(bad['entries'][0])
            else: bad['entries'].pop()
            with self.assertRaises(ValueError): validate_catalog(self.original, bad)

    def test_fixed_status_buffer_includes_terminator(self):
        bad = deepcopy(self.entries['help.001b7dbc']); bad['english'] = 'i'*64
        with self.assertRaisesRegex(ValueError, 'buffer overflow'): encode(bad, self.original)

    def test_order_copy_buffer_includes_terminator(self):
        bad = deepcopy(self.entries['help.001b4ea6']); bad['english'] = 'i'*30
        with self.assertRaisesRegex(ValueError, 'buffer overflow'): encode(bad, self.original)

    def test_semantic_slots_cannot_be_lost_retyped_or_duplicated(self):
        for text in ('Can give orders.', '$t can order $m1.', '$t can order $m0 $m0.'):
            bad = deepcopy(self.entries['help.001b4f0c']); bad['english'] = text
            with self.subTest(text=text), self.assertRaises(ValueError): encode(bad, self.original)

    def test_screen_width_and_height_are_bounded(self):
        for text in ('W'*50, '\n'.join(['Line']*11)):
            bad = deepcopy(self.entries['help.000ea470']); bad['english'] = text
            with self.assertRaises(ValueError): encode(bad, self.original)

    def test_old_insertions_and_source_strings_survive_combined_build(self):
        from pathlib import Path
        prior = load_json('build/core-gameplay/english-build.json')
        old = Path('build/core-gameplay/torneko3-core-gameplay-english.gba').read_bytes()
        data, report = build_rom(self.original, 'english', self.catalog)
        for patch in prior['ledger']['patches']:
            at = patch['offset']; raw = bytes.fromhex(patch['after'])
            self.assertEqual(data[at:at+len(raw)], raw)
        for allocation in prior['ledger']['allocations']:
            at, n = allocation['offset'], allocation['bytes']
            self.assertEqual(data[at:at+n], old[at:at+n])
        for e in self.catalog['entries']:
            at = int(e['offset'], 0); raw = bytes.fromhex(e['source_hex'])
            self.assertEqual(data[at:at+len(raw)], raw)
        self.assertEqual(report['ledger']['memory_reservations'], prior['ledger']['memory_reservations'])


if __name__ == '__main__': unittest.main()
