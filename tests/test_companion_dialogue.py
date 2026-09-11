"""Complete dialogue ownership, special responses and historical-build preservation."""
from copy import deepcopy
import struct
import unittest
from tools import build_ally_dialogue as prior
from tools.build_companion_dialogue import CATALOG, TABLE, ALTERNATES, build_rom, encode, validate_catalog
from tools.build_first_label import ORIGINAL_ROM, ROOT
from tools.translation_pipeline import load_json


class CompanionDialogueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original=ORIGINAL_ROM.read_bytes();cls.catalog=load_json(CATALOG)
        cls.entries=validate_catalog(cls.original,cls.catalog)

    def test_combined_inventory_owns_every_nonnull_table_word_once(self):
        old=load_json(prior.CATALOG)['entries']
        words=[int(e['pointer_offset'],0) for e in old+self.catalog['entries']]
        expected={p for p in range(TABLE,TABLE+200*80,4) if struct.unpack_from('<I',self.original,p)[0]}
        self.assertEqual(len(expected),1624)
        self.assertEqual(len(words),len(set(words)))
        self.assertEqual(set(words),expected|set(range(ALTERNATES,ALTERNATES+12,4)))

    def test_special_companions_keep_twenty_responses_and_three_alternatives(self):
        for row in (191,192):
            self.assertEqual({e['field'] for e in self.entries.values() if e['family']=='dialogue' and e['row']==row},set(range(20)))
        self.assertEqual({e['field'] for e in self.entries.values() if e['family']=='rosa_alt'},{0,1,2})

    def test_source_and_pointer_ownership_are_immutable(self):
        for key in ('source_hex','source_tokens','pointer_offset','row','field','family'):
            bad=deepcopy(self.catalog);bad['entries'][-1][key]='changed'
            with self.subTest(key=key),self.assertRaises((ValueError,TypeError)):validate_catalog(self.original,bad)

    def test_hero_and_secondary_actor_substitutions_cannot_be_dropped(self):
        for command in ('$t','$m1'):
            e=deepcopy(next(e for e in self.entries.values() if command in e['english']))
            e['english']=e['english'].replace(command,'Name')
            with self.subTest(command=command),self.assertRaisesRegex(ValueError,'substitutions'):encode(e,self.original)

    def test_speech_and_reserved_template_contracts_are_distinct(self):
        for speech in (True,False):
            e=deepcopy(next(e for e in self.entries.values() if e['japanese'].startswith('$m0「')==speech))
            e['english']=e['english'][6:-1] if speech else '$m0: "'+e['english']+'"'
            with self.subTest(speech=speech),self.assertRaisesRegex(ValueError,'quotation'):encode(e,self.original)

    def test_full_dialogue_survives_width_and_capacity_wrapping(self):
        for e in self.entries.values():
            raw,metrics=encode(e,self.original)
            self.assertEqual(raw[:-1].decode().split(),e['english'].split())
            self.assertLessEqual(metrics['formatted_byte_upper_bound'],1000)
            self.assertTrue(all(w<=208 for w in metrics['line_widths']))
            self.assertLessEqual(metrics['pages'],2)
        bad=deepcopy(self.catalog);bad['entries'][0]['display']='Short'
        with self.assertRaisesRegex(ValueError,'full dialogue wording'):validate_catalog(self.original,bad)

    def test_duplicate_boss_sources_and_test_name_keep_their_identity(self):
        for field in range(8):
            entries=[self.entries[f'companion.dialogue.{row:03d}.{field:02d}'] for row in (186,187,188)]
            self.assertEqual(len({e['offset'] for e in entries}),3)
            self.assertEqual(len({e['source_hex'] for e in entries}),1)
            self.assertEqual(len({e['english'] for e in entries}),1)
        for e in self.entries.values():
            if e['row']==198:
                self.assertIn('パウロ',e['japanese']);self.assertIn('Paulo',e['english'])
                self.assertNotIn('Tipper',e['english'])

    def test_previous_default_build_remains_byte_identical(self):
        data,_=prior.build_rom(self.original)
        self.assertEqual(data,(prior.OUTPUT/'torneko3-ally-dialogue-english.gba').read_bytes())

    def test_new_dialogue_preserves_prior_payloads_patches_and_unowned_words(self):
        old=(prior.OUTPUT/'torneko3-ally-dialogue-english.gba').read_bytes();old_report=load_json(prior.OUTPUT/'english-build.json')
        data,report=build_rom(self.original,catalog=self.catalog);ledger=report['ledger']
        allocations={a['id']:a for a in ledger['allocations']}
        for a in old_report['ledger']['allocations']:
            self.assertEqual(allocations[a['id']],a)
            at,n=a['offset'],a['bytes'];self.assertEqual(data[at:at+n],old[at:at+n])
        self.assertEqual(ledger['patches'][:len(old_report['ledger']['patches'])],old_report['ledger']['patches'])
        for p in old_report['ledger']['patches']:
            at=p['offset'];raw=bytes.fromhex(p['after']);self.assertEqual(data[at:at+len(raw)],raw)
        owned={int(e['pointer_offset'],0) for e in self.entries.values()}
        for at in range(TABLE,TABLE+200*80,4):
            if at not in owned:self.assertEqual(data[at:at+4],old[at:at+4])
        self.assertEqual(ledger['memory_reservations'],old_report['ledger']['memory_reservations'])


if __name__=='__main__':unittest.main()
