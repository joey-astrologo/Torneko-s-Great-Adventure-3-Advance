"""Provenance checks must fail on broken byte, version and event chains."""
import copy
import unittest
from tools.build_first_label import ORIGINAL_ROM, ROOT
from tools.translation_pipeline import load_json
from tools.verify_story_provenance import check_natural, positioned_coordinates


class StoryProvenanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = ORIGINAL_ROM.read_bytes()
        cls.master = load_json(ROOT/'translations/master.json')['entries']
        cls.trace = load_json(ROOT/'build/story-provenance/natural/trace.json')

    def changed(self, mutate, message):
        trace = copy.deepcopy(self.trace); mutate(trace)
        with self.assertRaisesRegex(ValueError, message):
            check_natural(trace, self.original, self.master)

    def test_original_chain_covers_every_version(self):
        report = check_natural(self.trace, self.original, self.master)
        self.assertEqual(report['buffer_versions'], len(self.trace['versions']))
        self.assertEqual(report['unattributed_ram_reads'], 0)

    def test_source_from_a_different_event_is_rejected(self):
        self.changed(lambda t: t['versions'][0]['source'].update(address='0x0891BB3C'), 'Source changed')

    def test_original_operand_location_is_checked(self):
        def mutate(t):
            prep = t['preparations'][t['versions'][0]['preparation_serial']]
            event = t['commands'][t['wrappers'][prep['wrapper_serial']]['event_serial']]
            event['operand_word'] = event['cursor']
        self.changed(mutate, 'Wrong event operand word')

    def test_byte_mismatch_in_reused_ram_buffer_is_rejected(self):
        self.changed(lambda t: t['story_ram_reads'][0].update(raw_hex='ffffffff'), 'RAM read differs')

    def test_same_address_does_not_make_two_buffer_versions_interchangeable(self):
        def mutate(t):
            first = t['versions'][0]
            other = next(v for v in t['versions'][1:] if v['destination'] == first['destination'] and v['output_hex'] != first['output_hex'])
            raw = bytes.fromhex(first['output_hex'])
            alternate = bytes.fromhex(other['output_hex'])
            row = next(r for r in t['story_ram_reads'] if r['version_serial'] == 0
                and raw[r['byte_delta']:r['byte_delta']+len(bytes.fromhex(r['raw_hex']))]
                != alternate[r['byte_delta']:r['byte_delta']+len(bytes.fromhex(r['raw_hex']))])
            row['version_serial'] = other['serial']
        self.changed(mutate, 'RAM read differs')

    def test_unknown_ram_source_cannot_be_ignored(self):
        self.changed(lambda t: t['unattributed_story_reads'].append({'address':'0x02000000'}), 'Unattributed')

    def test_positions_keep_signed_x_and_relative_y(self):
        self.assertEqual(positioned_coordinates(0xFFF87029), (-8, -16))
        self.assertEqual(positioned_coordinates(0x0010FF29), (16, 127))


if __name__ == '__main__':
    unittest.main()
