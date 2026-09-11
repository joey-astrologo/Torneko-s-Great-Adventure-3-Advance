"""Reject ROM corruption and renderer-contract mistakes in gameplay insertion."""
from copy import deepcopy
import struct
import unittest
from tools.build_first_label import ORIGINAL_ROM
from tools.build_core_gameplay import CATALOG,CHOICES,COMMAND_RECORDS,SHARED,build_rom,encode,validate_catalog
from tools.translation_pipeline import load_json


class CoreGameplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original=ORIGINAL_ROM.read_bytes();cls.catalog=load_json(CATALOG)
        cls.entries={e['id']:e for e in cls.catalog['entries']}
        cls.data,cls.report=build_rom(cls.original,'english',cls.catalog)

    def test_complete_scope_and_source_contract(self):
        self.assertEqual(len(validate_catalog(self.original,self.catalog)),262)
        for field in ('source_hex','source_tokens','pointer_owners','offset','master_id'):
            bad=deepcopy(self.catalog);bad['entries'][0][field]='changed'
            with self.subTest(field=field),self.assertRaises((ValueError,TypeError)):
                validate_catalog(self.original,bad)
        bad=deepcopy(self.catalog);bad['entries'].pop()
        with self.assertRaises(ValueError):validate_catalog(self.original,bad)

    def test_substitutions_cannot_be_lost_duplicated_or_retyped(self):
        for text in ('Hit $m1.','Hit $m1 for $d0 $d0.','Hit $m0 for $d0.','$m1 took %s damage.','$m1 took $d0 damage.\0'):
            bad=deepcopy(self.entries['gameplay.001b4dac']);bad['english']=text
            with self.subTest(text=text),self.assertRaises(ValueError):encode(bad,self.original)

    def test_printf_and_option_contracts_are_immutable(self):
        for ident,old,new in [('gameplay.001b3c16','%d','%s'),('gameplay.00c40208','031402','031403'),
                              ('gameplay.00c400d0','{arrow}',''),('gameplay.00c40028','*','')]:
            bad=deepcopy(self.entries[ident]);bad['english']=bad['english'].replace(old,new)
            with self.subTest(ident=ident),self.assertRaises(ValueError):encode(bad,self.original)

    def test_fixed_column_overflow_is_rejected_before_build(self):
        bad=deepcopy(self.entries['gameplay.001b3cab'])
        bad['english']=bad['english'].replace('Items','WWWWWW')
        with self.assertRaisesRegex(ValueError,'columns overlap'):encode(bad,self.original)

    def test_wrapping_reserves_dynamic_name_width_and_three_line_limit(self):
        bad=deepcopy(self.entries['gameplay.001b4dac'])
        for text in ('$m1 $d0 '+'W'*40,'$m1\n$d0\none\ntoo many'):
            bad['english']=text
            with self.subTest(text=text),self.assertRaises(ValueError):encode(bad,self.original)
        for e in self.catalog['entries']:
            if e['family']=='message':
                _,m=encode(e,self.original)
                self.assertLessEqual(max(m['worst_line_widths']),208)
                self.assertLessEqual(len(m['worst_line_widths']),3)
                self.assertLessEqual(m['formatted_byte_upper_bound'],1000)

    def test_both_computed_tables_retain_every_stride_and_padding(self):
        for pointer,offsets,stride in ((0x207EC,CHOICES,32),(0x6CC04,COMMAND_RECORDS,30)):
            base=struct.unpack_from('<I',self.data,pointer)[0]-0x08000000
            self.assertEqual(self.data[offsets[0]:offsets[-1]+stride],self.original[offsets[0]:offsets[-1]+stride])
            for i,o in enumerate(offsets):
                e=self.entries[f'gameplay.{o:08x}'];raw=encode(e,self.original)[0]
                self.assertEqual(self.data[base+i*stride:base+(i+1)*stride],raw.ljust(stride,b'\0'))
                self.assertEqual(self.report['gameplay']['relocated'][e['id']]['offset'],base+i*stride)

    def test_existing_components_and_shared_owners_remain_identical(self):
        previous=load_json('build/dungeon-interface/english-build.json')
        from pathlib import Path
        data=Path('build/dungeon-interface/torneko3-dungeon-interface-english.gba').read_bytes()
        for p in previous['ledger']['patches']:
            after=bytes.fromhex(p['after']);self.assertEqual(self.data[p['offset']:p['offset']+len(after)],after)
        for a in previous['ledger']['allocations']:
            at,n=a['offset'],a['bytes'];self.assertEqual(self.data[at:at+n],data[at:at+n])
        for offset,owner in SHARED.items():
            row=self.report['gameplay']['relocated'][f'gameplay.{offset:08x}']
            self.assertEqual(row['shared_owner'],owner)
            self.assertEqual(sum(p['id']==owner for p in self.report['ledger']['patches']),1)
        self.assertEqual(len(self.data),0x02000000)

    def test_japanese_relocation_preserves_sources_and_curated_english(self):
        data,report=build_rom(self.original,'japanese',self.catalog)
        for e in self.catalog['entries']:
            at=report['gameplay']['relocated'][e['id']]['offset']
            expected=encode(e,self.original)[0] if int(e['offset'],0) in SHARED else bytes.fromhex(e['source_hex'])
            self.assertEqual(data[at:at+len(expected)],expected)
        for word in (0xCA28B8,0xCA2978):self.assertEqual(data[word:word+2],b'\x09\x00')


if __name__=='__main__':unittest.main()
