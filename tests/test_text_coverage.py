"""Coverage must distinguish physical sources, suffixes and pointer-shaped data."""
import struct
import unittest
from tools.audit_text_coverage import SourceIndex,all_pointer_words,cartridge_offset


class TextCoverageTests(unittest.TestCase):
    def test_cartridge_windows_normalize_without_wrapping_past_file_end(self):
        for base in (0x08000000,0x0A000000,0x0C000000):
            self.assertEqual(cartridge_offset(base+123,0x1000000),123)
            self.assertIsNone(cartridge_offset(base+0x1000000,0x1000000))
        for at in (0x02000000,0x07000000,0x0E000000):self.assertIsNone(cartridge_offset(at,0x2000000))

    def test_unaligned_pointer_words_keep_original_locations_and_views(self):
        data=bytearray(40)
        for at,base in ((0,0x08000000),(9,0x08000000),(18,0x0A000000),(27,0x0C000000)):
            struct.pack_into('<I',data,at,base+7)
        refs,counts=all_pointer_words(data)
        self.assertEqual({int(w['word'],0) for w in refs[7]},{0,9,18,27})
        self.assertEqual({w['mode'] for w in refs[7]},{'aligned_primary','unaligned_primary','unaligned_mirror'})
        self.assertEqual(counts['unaligned_mirror'],2)

    def test_last_unaligned_word_is_not_dropped(self):
        data=bytearray(17);struct.pack_into('<I',data,13,0x08000007)
        refs,_=all_pointer_words(data)
        self.assertEqual(refs[7][0]['word'],'0x0000000D')

    def test_odd_pointer_target_is_not_silently_treated_as_thumb_address(self):
        data=bytearray(16);struct.pack_into('<I',data,0,0x08000009)
        refs,_=all_pointer_words(data)
        self.assertIn(9,refs);self.assertNotIn(8,refs)

    def test_suffix_character_and_control_arguments_have_distinct_coverage(self):
        tokens=[{'kind':'text','raw_hex':'82a0','text':'あ'},
            {'kind':'dollar_command','raw_hex':'246d30','text':'$m0'},
            {'kind':'binary_control','raw_hex':'030507','text':'<03 05 07>'},
            {'kind':'terminator','raw_hex':'00','text':''}]
        entry={'id':'example','offset':'0x4','source_hex':''.join(t['raw_hex'] for t in tokens),'source_tokens':tokens}
        index=SourceIndex([entry]);self.assertEqual(index.locate(4)['kind'],'source_start')
        for at in (6,9,12):self.assertEqual(index.locate(at)['kind'],'character_or_token_boundary')
        for at in (5,7,8,10,11):self.assertEqual(index.locate(at)['kind'],'inside_character_or_control')
        for at in (3,13):self.assertEqual(index.locate(at)['kind'],'uncovered')

    def test_overlapping_sources_cannot_produce_false_coverage(self):
        entries=[{'id':str(i),'offset':hex(i),'source_hex':'414200','source_tokens':[]} for i in (4,6)]
        with self.assertRaisesRegex(ValueError,'Overlapping'):SourceIndex(entries)


if __name__=='__main__':unittest.main()
