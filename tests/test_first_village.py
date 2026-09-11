"""Village ownership, source contracts, complete scope and build preservation."""
from copy import deepcopy
import struct
import unittest
from tools.build_first_village import CATALOG,OWNERS,extract_catalog,validate_catalog,encode,build_rom
from tools.build_first_label import ORIGINAL_ROM,ROOT
from tools.translation_pipeline import load_json


class FirstVillageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original=ORIGINAL_ROM.read_bytes();cls.catalog=load_json(CATALOG)
        cls.entries=validate_catalog(cls.original,cls.catalog)

    def test_complete_section_and_all_shared_owners(self):
        self.assertEqual(len(self.entries),281)
        self.assertEqual(sum(len(e['events']) for e in self.entries.values()),367)
        self.assertEqual({ev['opcode'] for e in self.entries.values() for ev in e['events']},{0x23,0x25,0x26,0x2a,0x2c})
        self.assertTrue(all(len(e['events']) for e in self.entries.values()))
        self.assertIn('village.00b6e608',self.entries) # Ines choice
        self.assertIn('village.00b6e7d4',self.entries) # Rosa confirmation

    def test_missing_duplicate_or_changed_owner_rejected(self):
        for change in ('missing','duplicate','events','source_hex','layout','group','end_exclusive'):
            c=deepcopy(self.catalog)
            if change=='missing':c['entries'].pop()
            elif change=='duplicate':c['entries'][-1]=c['entries'][0]
            else:c['entries'][0][change]='changed'
            with self.subTest(change=change),self.assertRaises((ValueError,TypeError)):validate_catalog(self.original,c)

    def test_earlier_opening_sources_have_no_new_ownership(self):
        old={e['master_id'] for e in load_json(ROOT/'translations/opening-story.json')['entries']}
        self.assertFalse(old & {e['master_id'] for e in self.entries.values()})
        self.assertEqual(load_json(OWNERS),extract_catalog(self.original))

    def test_protagonist_substitution_is_retained_and_measured(self):
        e=self.entries['village.00b7a9e0'];a,ma=encode(e,self.original,'Torneko');b,mb=encode(e,self.original,'Tipper')
        self.assertEqual(a,b);self.assertEqual(a.count(b'$t'),1)
        self.assertIn('Torneko',ma['visible']);self.assertIn('Tipper',mb['visible'])
        changed=deepcopy(e);changed['english']=e['english'].replace('$t','Torneko')
        with self.assertRaisesRegex(ValueError,'formatter contract'):encode(changed,self.original)

    def test_unreviewed_controls_and_multipage_overflow_rejected(self):
        e=deepcopy(self.entries['village.009c3560'])
        for text in ('Text\0tail','$v07','100%','{text}','Text\n'*4):
            e['english']=text
            with self.subTest(text=text),self.assertRaises(ValueError):encode(e,self.original)

    def test_speaker_quotes_and_three_line_page_preserved(self):
        e=deepcopy(self.entries['village.009c2264']);e['english']=e['english'].replace('"','')
        with self.assertRaisesRegex(ValueError,'Speech presentation'):encode(e,self.original)
        for entry in self.entries.values():
            raw,m=encode(entry,self.original)
            self.assertLessEqual(m['lines'],3);self.assertLessEqual(len(raw),1024)
            self.assertTrue(all(w<=208 for w in m['line_widths']))

    def test_combined_build_preserves_all_prior_data_and_command_words(self):
        baseline=(ROOT/'build/opening-story/torneko3-opening-story-english.gba').read_bytes()
        old=load_json(ROOT/'build/opening-story/english-build.json')['ledger']
        data,report=build_rom(self.original);ledger=report['ledger'];alloc={a['id']:a for a in ledger['allocations']}
        for a in old['allocations']:
            self.assertEqual(alloc[a['id']],a);at,n=a['offset'],a['bytes']
            self.assertEqual(data[at:at+n],baseline[at:at+n])
        self.assertEqual(ledger['patches'][:len(old['patches'])],old['patches'])
        self.assertEqual(ledger['memory_reservations'],old['memory_reservations'])
        self.assertEqual(len(ledger['patches'])-len(old['patches']),367)
        for e in self.entries.values():
            at=int(e['offset'],0);end=int(e['end_exclusive'],0)
            self.assertEqual(data[at:end],self.original[at:end])
            pointers=set()
            for event in e['events']:
                at=int(event['command_offset'],0)
                self.assertEqual(data[at:at+4],self.original[at:at+4])
                pointers.add(struct.unpack_from('<I',data,at+4)[0])
            self.assertEqual(len(pointers),1)


if __name__=='__main__':unittest.main()
