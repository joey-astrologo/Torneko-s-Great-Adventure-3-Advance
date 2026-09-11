"""Regress real queue/history, copied-label and initializer constraints."""
from copy import deepcopy
from pathlib import Path
import unittest
from tools.build_tutorial_gameplay import CATALOG,INIT_TABLES,build_rom,encode,validate_catalog,line_bytes
from tools.build_first_label import ORIGINAL_ROM
from tools.translation_pipeline import FontZero,load_json


class TutorialGameplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original=ORIGINAL_ROM.read_bytes();cls.catalog=load_json(CATALOG);cls.entries={e['id']:e for e in cls.catalog['entries']}

    def test_history_is_tighter_than_live_queue_and_width(self):
        e=deepcopy(self.entries['tutorial.001b67ff']);e['english']='i'*59
        self.assertEqual(encode(e,self.original)[0],b'i'*59+b'\0')
        e['english']='i'*60
        with self.assertRaisesRegex(ValueError,'Unbreakable'):encode(e,self.original)

    def test_item_slot_width_does_not_hide_narrow_byte_overflow(self):
        e=deepcopy(self.entries['tutorial.001b5ebf']);e['english']='$i2 iiiiiiiiiiii'
        raw,metrics=encode(e,self.original)
        self.assertIn(b'\n',raw)
        self.assertEqual(line_bytes('$i2'),48)
        self.assertTrue(all(n<=59 for n in metrics['history_payload_upper_bounds']))
        font=FontZero(self.original)
        self.assertEqual(min(font.glyph(chr(c))[1] for c in range(32,127)),3)

    def test_tutorial_must_keep_one_pause_and_two_nonempty_segments(self):
        for text in ('Equip this.','Equip this.$wPress B.$wChoose Items.','$wPress B.','Equip this.$w'):
            e=deepcopy(self.entries['tutorial.001b47ea']);e['english']=text
            with self.subTest(text=text),self.assertRaises(ValueError):encode(e,self.original)

    def test_joined_damage_marker_and_slots_are_semantic(self):
        for ident,text in [('tutorial.001b507e','$m1 takes $d0 damage.'),('tutorial.001b5032','!$m0:'),('tutorial.001b5ebf','$i3 failed to work.')]:
            e=deepcopy(self.entries[ident]);e['english']=text
            with self.subTest(ident=ident),self.assertRaises(ValueError):encode(e,self.original)

    def test_effect_labels_fit_the_same_item_slot_and_width_contract(self):
        e=deepcopy(self.entries['tutorial.001b70d3']);e['english']='W'*40
        with self.assertRaisesRegex(ValueError,'144 pixels'):encode(e,self.original)
        e['english']='First\nsecond'
        with self.assertRaises(ValueError):encode(e,self.original)

    def test_reject_source_or_initializer_owner_edits(self):
        self.assertEqual(len(validate_catalog(self.original,self.catalog)),285)
        for field in ('source_hex','source_tokens','offset','pointer_owners','excluded_owners'):
            bad=deepcopy(self.catalog);bad['entries'][0][field]='changed'
            with self.subTest(field=field),self.assertRaises((ValueError,TypeError)):validate_catalog(self.original,bad)

    def test_prior_allocations_and_unowned_initializer_bytes_remain_exact(self):
        prior=load_json('build/ally-services/english-build.json');old=Path('build/ally-services/torneko3-ally-services-english.gba').read_bytes()
        data,report=build_rom(self.original,'english',self.catalog)
        for p in prior['ledger']['patches']:
            at=p['offset'];raw=bytes.fromhex(p['after']);self.assertEqual(data[at:at+len(raw)],raw)
        for a in prior['ledger']['allocations']:
            at,n=a['offset'],a['bytes'];self.assertEqual(data[at:at+n],old[at:at+n])
        owned={i for e in self.catalog['entries'] for p in e['pointer_owners'] for i in range(int(p['offset'],0),int(p['offset'],0)+4)}
        for a,b in INIT_TABLES:
            for i in range(a,b):
                if i not in owned:self.assertEqual(data[i],old[i])
        for e in self.catalog['entries']:
            at=int(e['offset'],0);raw=bytes.fromhex(e['source_hex']);self.assertEqual(data[at:at+len(raw)],raw)
        self.assertEqual(report['ledger']['memory_reservations'],prior['ledger']['memory_reservations'])


if __name__=='__main__':unittest.main()
