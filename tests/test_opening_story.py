"""Opening event ownership, layout contracts and preservation of earlier work."""
from copy import deepcopy
import struct
import unittest
from tools.build_opening_story import CATALOG,extract_catalog,validate_catalog,encode,build_rom
from tools.build_first_label import ORIGINAL_ROM,ROOT
from tools.translation_pipeline import load_json

class OpeningStoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original=ORIGINAL_ROM.read_bytes();cls.catalog=load_json(CATALOG);cls.entries=validate_catalog(cls.original,cls.catalog)

    def test_section_includes_refusal_rest_and_all_shared_sleep_owners(self):
        self.assertEqual(len(self.entries),46)
        self.assertEqual(sum(len(e['events']) for e in self.entries.values()),52)
        self.assertEqual(len(self.entries['opening.009c1eb0']['events']),9)
        self.assertEqual(self.entries['opening.00c2f4a8']['japanese'][:3],'ポポロ')
        self.assertEqual({e['id'] for e in self.entries.values() if any(x['opcode']==0x2c for x in e['events'])},{'opening.00c2f4e4','opening.009c2044'})

    def test_event_words_sources_and_context_cannot_change(self):
        for key in ('source_hex','source_tokens','events','reuse','layout','offset'):
            bad=deepcopy(self.catalog);bad['entries'][1][key]='changed'
            with self.subTest(key=key),self.assertRaises((ValueError,TypeError)):validate_catalog(self.original,bad)

    def test_event_choice_records_retain_yes_no_return_values(self):
        for ident,english,value in (('opening.0086f4c8','Yes',1),('opening.0086f4c0','No',0)):
            e=self.entries[ident];self.assertEqual(e['english'],english)
            self.assertEqual(e['choice_owners'][0]['return_value'],value)
            bad=deepcopy(self.catalog)
            next(x for x in bad['entries'] if x['id']==ident)['choice_owners'][0]['return_value']=1-value
            with self.assertRaisesRegex(ValueError,'source/owner'):validate_catalog(self.original,bad)

    def test_missing_or_duplicated_message_is_rejected(self):
        for duplicate in (False,True):
            bad=deepcopy(self.catalog)
            if duplicate:bad['entries'][-1]=bad['entries'][0]
            else:bad['entries'].pop()
            with self.assertRaises(ValueError):validate_catalog(self.original,bad)

    def test_prior_narration_cannot_be_rewritten_or_reallocated(self):
        e=deepcopy(self.entries['opening.0091bbb4']);e['english']='A changed opening.'
        with self.assertRaisesRegex(ValueError,'Earlier narration'):encode(e,self.original)

    def test_source_controls_and_presentation_are_reviewed(self):
        for text in ('$t says hello.','100%','{new}','Text\0tail','あ'):
            e=deepcopy(self.entries['opening.009c1eb0']);e['english']=text
            with self.subTest(text=text),self.assertRaises(ValueError):encode(e,self.original)
        e=deepcopy(self.entries['opening.0091b9c8']);e['english']=e['english'].lstrip()
        with self.assertRaisesRegex(ValueError,'blank line'):encode(e,self.original)
        e=deepcopy(self.entries['opening.009c1d2c']);e['english']=e['english'].replace('"','')
        with self.assertRaisesRegex(ValueError,'quotation'):encode(e,self.original)

    def test_messages_remain_within_measured_page_and_ram_capacity(self):
        for e in self.entries.values():
            raw,m=encode(e,self.original)
            self.assertLessEqual(m['lines'],3);self.assertLessEqual(len(raw),1024)
            self.assertTrue(all(w<=208 for w in m['line_widths']))
        e=deepcopy(self.entries['opening.009c1eb0']);e['english']='One\nTwo\nThree\nFour'
        with self.assertRaisesRegex(ValueError,'three-line'):encode(e,self.original)

    def test_complete_image_preserves_prior_work_and_event_choice_parameters(self):
        old=(ROOT/'build/ally-nicknames/torneko3-ally-nicknames-english.gba').read_bytes()
        prior=load_json(ROOT/'build/ally-nicknames/english-build.json')['ledger']
        data,report=build_rom(self.original);ledger=report['ledger'];alloc={a['id']:a for a in ledger['allocations']}
        for a in prior['allocations']:
            self.assertEqual(alloc[a['id']],a);at,n=a['offset'],a['bytes'];self.assertEqual(data[at:at+n],old[at:at+n])
        self.assertEqual(ledger['patches'][:len(prior['patches'])],prior['patches'])
        self.assertEqual(ledger['memory_reservations'],prior['memory_reservations'])
        self.assertEqual(len(ledger['patches'])-len(prior['patches']),53)
        for e in self.entries.values():
            at=int(e['offset'],0);raw=bytes.fromhex(e['source_hex']);self.assertEqual(data[at:at+len(raw)],raw)
            for event in e['events']:
                at=int(event['command_offset'],0);self.assertEqual(data[at:at+4],self.original[at:at+4])
            targets={struct.unpack_from('<I',data,int(ev['pointer_offset'],0))[0] for ev in e['events']+e.get('choice_owners',[])}
            self.assertEqual(len(targets),1)

if __name__=='__main__':unittest.main()
