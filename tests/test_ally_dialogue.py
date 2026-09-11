"""Dialogue ownership and the real history-capacity regression."""
from copy import deepcopy
from pathlib import Path
import unittest
from tools.build_ally_dialogue import CATALOG,TABLE,build_rom,encode,history_inventory,history_wrap,validate_catalog,CORE,HELP
from tools.build_first_label import ORIGINAL_ROM
from tools.translation_pipeline import FontZero,load_json


class AllyDialogueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original=ORIGINAL_ROM.read_bytes();cls.catalog=load_json(CATALOG);cls.font=FontZero(cls.original)

    def test_complete_eight_response_sets(self):
        entries=validate_catalog(self.original,self.catalog)
        self.assertEqual({(e['row'],e['field']) for e in entries.values()},{(r,f) for r in range(1,51) for f in range(8)})

    def test_source_and_pointer_fields_are_immutable(self):
        for key in ('source_hex','source_tokens','pointer_offset','row','field'):
            bad=deepcopy(self.catalog);bad['entries'][0][key]='changed'
            with self.subTest(key=key),self.assertRaises((ValueError,TypeError)):validate_catalog(self.original,bad)

    def test_preserve_both_troll_name_substitutions(self):
        e=deepcopy(next(e for e in self.catalog['entries'] if e['row']==35 and e['field']==0))
        e['english']=e['english'].replace('$m1','Troll')
        with self.assertRaisesRegex(ValueError,'substitutions'):encode(e,self.original)

    def test_no_silent_dialogue_abbreviations(self):
        bad=deepcopy(self.catalog);bad['entries'][0]['display']='Short version'
        with self.assertRaisesRegex(ValueError,'full wording'):validate_catalog(self.original,bad)

    def test_dialogue_wrap_keeps_all_words(self):
        for e in self.catalog['entries']:
            raw,metrics=encode(e,self.original)
            self.assertEqual(raw[:-1].decode().split(),e['english'].split())
            self.assertLessEqual(metrics['formatted_byte_upper_bound'],1000)
            self.assertTrue(all(w<=208 for w in metrics['line_widths']))

    def test_history_reflow_fixes_exactly_the_16_flagged_messages(self):
        report=history_inventory(self.original)
        self.assertEqual(len(report['messages']),311)
        expected={r['id'] for r in load_json('build/tutorial-gameplay/research/earlier-history-audit.json')['lines']}
        self.assertEqual(set(report['changed_ids']),expected)
        for e in report['messages']:
            self.assertEqual(e['old_display'].split(),e['display_template'].split())
            self.assertEqual(len(bytes.fromhex(e['old_raw_hex'])),len(bytes.fromhex(e['raw_hex'])))
            self.assertTrue(all(n<=59 for n in e['history_payload_upper_bounds']))
            self.assertLessEqual(len(e['display_template'].split('\n')),3)

    def test_old_hard_break_does_not_force_a_fourth_history_line(self):
        text='What a surprise! $i0\nwas really $i1!'
        wrapped=history_wrap(text,self.font)
        from tools.build_tutorial_gameplay import line_bytes
        self.assertEqual(wrapped.split(),text.split())
        self.assertEqual(len(wrapped.split('\n')),3)
        self.assertTrue(all(line_bytes(line)<=59 for line in wrapped.split('\n')))

    def test_history_rejects_an_overlong_narrow_word(self):
        with self.assertRaisesRegex(ValueError,'Unbreakable'):history_wrap('i'*60,self.font)

    def test_existing_build_defaults_remain_reproducible(self):
        from tools.build_tutorial_gameplay import build_rom as old_build
        data,_=old_build(self.original)
        self.assertEqual(data,Path('build/tutorial-gameplay/torneko3-tutorial-gameplay-english.gba').read_bytes())

    def test_owned_reflow_does_not_move_previous_allocations_or_patches(self):
        old=Path('build/tutorial-gameplay/torneko3-tutorial-gameplay-english.gba').read_bytes();prior=load_json('build/tutorial-gameplay/english-build.json')
        data,report=build_rom(self.original,catalog=self.catalog);changed=set(report['history']['changed_ids'])
        allocations={a['id']:a for a in report['ledger']['allocations']}
        for a in prior['ledger']['allocations']:
            new=allocations[a['id']];at,n=a['offset'],a['bytes']
            self.assertEqual((new['offset'],new['bytes'],new['owner']),(at,n,a['owner']))
            if a['id'] not in changed:self.assertEqual(data[at:at+n],old[at:at+n])
        for p in prior['ledger']['patches']:
            at=p['offset'];raw=bytes.fromhex(p['after']);self.assertEqual(data[at:at+len(raw)],raw)
        owned={int(e['pointer_offset'],0) for e in self.catalog['entries']}
        for p in range(TABLE,TABLE+200*80,4):
            if p not in owned:self.assertEqual(data[p:p+4],old[p:p+4])
        self.assertEqual(report['ledger']['memory_reservations'],prior['ledger']['memory_reservations'])


if __name__=='__main__':unittest.main()
