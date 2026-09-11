"""Nickname source ownership, compact limits and collision-safe combined builds."""
from copy import deepcopy
import struct
import unittest
from tools.build_ally_nicknames import CATALOG,TABLE,ROWS,build_rom,validate_catalog,encode,expected_compact
from tools.build_first_label import ORIGINAL_ROM,ROOT
from tools.translation_pipeline import load_json
from tools.build_name_entry import LATIN

class AllyNicknameTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original=ORIGINAL_ROM.read_bytes();cls.catalog=load_json(CATALOG)
        cls.entries=validate_catalog(cls.original,cls.catalog)

    def test_complete_table_and_shared_boss_sources(self):
        self.assertEqual({int(e['pointer_offset'],0) for e in self.entries.values()},set(range(TABLE,TABLE+ROWS*4,4)))
        self.assertEqual(len({e['offset'] for e in self.entries.values()}),198)
        bosses=[self.entries[f'ally.nickname.{r:03d}'] for r in (186,187,189)]
        self.assertEqual(len({e['offset'] for e in bosses}),1)
        self.assertEqual({e['english'] for e in bosses},{'Big Boss'})

    def test_source_identity_and_owner_cannot_change(self):
        for key in ('offset','pointer_offset','source_hex','source_tokens','species_japanese','row','master_id'):
            bad=deepcopy(self.catalog);bad['entries'][-1][key]='changed'
            with self.subTest(key=key),self.assertRaises((TypeError,ValueError)):validate_catalog(self.original,bad)

    def test_omitted_or_duplicate_rows_are_rejected(self):
        for action in ('omit','duplicate'):
            bad=deepcopy(self.catalog)
            if action=='omit':bad['entries'].pop()
            else:bad['entries'][-1]=bad['entries'][0]
            with self.subTest(action=action),self.assertRaises(ValueError):validate_catalog(self.original,bad)

    def test_shared_source_cannot_receive_conflicting_translations(self):
        bad=deepcopy(self.catalog);bad['entries'][187]['display']='Other'
        with self.assertRaisesRegex(ValueError,'Shared nickname'):validate_catalog(self.original,bad)

    def test_unsupported_or_oversized_compact_names_are_rejected(self):
        for text in ('TooLong','A B','A\0B','ABC!','あいう'):
            e=deepcopy(self.catalog['entries'][0]);e['display']=text
            with self.subTest(text=text),self.assertRaises(ValueError):encode(e,self.original)

    def test_full_reference_name_is_preserved_apart_from_short_display(self):
        e=self.entries['ally.nickname.021'];raw,metrics=encode(e,self.original)
        self.assertEqual((e['english'],e['display']),('Gootrude','Gooty'))
        self.assertEqual(raw,b'Gooty\0');self.assertEqual(metrics['full_english'],'Gootrude')
        self.assertEqual(self.entries['ally.nickname.198']['english'],'Paulo')
        self.assertEqual(self.entries['ally.nickname.198']['species_english'],'Tipper')

    def test_both_initial_and_duplicate_suffixes_fit_in_six_bytes(self):
        for base,suffix,text in (('Robby',0,'Robb0'),('Robby',9,'Robb9'),('Merc',1,'Merc1'),('Doc',1,'Doc1')):
            compact,value=expected_compact(base,suffix)
            self.assertEqual(value,text);self.assertEqual(compact,bytes(LATIN[c] for c in text)+b'\0')
            self.assertLessEqual(len(compact),6)
        with self.assertRaises(ValueError):expected_compact('Merc',10)

    def test_combined_build_preserves_previous_allocations_and_save_layout(self):
        old_rom=(ROOT/'build/companion-dialogue/torneko3-companion-dialogue-english.gba').read_bytes()
        old=load_json(ROOT/'build/companion-dialogue/english-build.json')['ledger']
        data,report=build_rom(self.original);ledger=report['ledger'];allocations={a['id']:a for a in ledger['allocations']}
        for a in old['allocations']:
            self.assertEqual(allocations[a['id']],a);at,n=a['offset'],a['bytes']
            self.assertEqual(data[at:at+n],old_rom[at:at+n])
        self.assertEqual(ledger['patches'][:len(old['patches'])],old['patches'])
        self.assertEqual(ledger['memory_reservations'],old['memory_reservations'])
        self.assertEqual(len(ledger['patches'])-len(old['patches']),201)
        for e in self.entries.values():
            at=int(e['offset'],0);raw=bytes.fromhex(e['source_hex'])
            self.assertEqual(data[at:at+len(raw)],raw)
        boss_words=[struct.unpack_from('<I',data,TABLE+4*r)[0] for r in (186,187,189)]
        self.assertEqual(len(set(boss_words)),1)

if __name__=='__main__':unittest.main()
