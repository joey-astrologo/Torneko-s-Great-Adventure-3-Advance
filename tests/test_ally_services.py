"""Guard actual fixed fields, column contracts and prior ROM ownership."""
from copy import deepcopy
from pathlib import Path
import unittest
from tools.build_ally_services import CATALOG,build_rom,encode,validate_catalog
from tools.build_first_label import ORIGINAL_ROM
from tools.translation_pipeline import load_json

class AllyServicesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original=ORIGINAL_ROM.read_bytes();cls.catalog=load_json(CATALOG);cls.entries={e['id']:e for e in cls.catalog['entries']}
    def test_fixed_context_and_title_termination(self):
        for ident,n in [('service.00c3df8c',5),('service.00c411b0',5),('service.00c41acc',5),('service.00c3df94',16)]:
            bad=deepcopy(self.entries[ident]);bad['display']='i'*n
            with self.subTest(ident=ident),self.assertRaisesRegex(ValueError,'Buffer overflow'):encode(bad,self.original)
    def test_numeric_picker_has_one_unit_cell(self):
        bad=deepcopy(self.entries['service.00c3f808']);bad['display']='tokens'
        with self.assertRaisesRegex(ValueError,'unit cell'):encode(bad,self.original)
    def test_warehouse_transfer_labels_fit_actual_popup(self):
        bad=deepcopy(self.entries['service.00c3e550']);bad['english']='To storage'
        with self.assertRaisesRegex(ValueError,'transfer popup'):encode(bad,self.original)
    def test_slots_and_printf_types_cannot_change(self):
        for ident,text in [('service.00c3de64','Leave'),('service.00c3de64','Leave $m2'),('service.00c3f830','$d1 tokens for $d1 gold?'),('service.00c3f6b4','Bank %dG Cash %7dG')]:
            bad=deepcopy(self.entries[ident]);bad['english']=text
            with self.subTest(ident=ident),self.assertRaises(ValueError):encode(bad,self.original)
    def test_original_default_selection_marker_is_required(self):
        bad=deepcopy(self.entries['service.00c3e4f8']);bad['english']='Withdraw'
        with self.assertRaisesRegex(ValueError,'Default marker'):encode(bad,self.original)
    def test_stats_columns_preserve_separation(self):
        bad=deepcopy(self.entries['service.00c3e400']);bad['english']='Attack{hex:03082e}$d0{hex:030844}XP $d1'
        with self.assertRaisesRegex(ValueError,'stats columns'):encode(bad,self.original)
    def test_message_pages_keep_full_help_and_bounded_output(self):
        raw,metric=encode(self.entries['service.00c3eab0'],self.original)
        self.assertGreater(metric['display_template'].count('\n'),3)
        self.assertIn(b'200',raw);self.assertIn(b'Warehouse pot',raw)
        bad=deepcopy(self.entries['service.00c3eab0']);bad['english']='Store items. '*100
        with self.assertRaisesRegex(ValueError,'Buffer overflow'):encode(bad,self.original)
    def test_cannot_reassign_sources_or_pointer_owners(self):
        self.assertEqual(len(validate_catalog(self.original,self.catalog)),138)
        for field in ('source_hex','source_tokens','offset','pointer_owners','excluded_owners'):
            bad=deepcopy(self.catalog);bad['entries'][0][field]='changed'
            with self.subTest(field=field),self.assertRaises((ValueError,TypeError)):validate_catalog(self.original,bad)
    def test_combined_build_preserves_prior_assets_patches_and_ram(self):
        old=Path('build/gameplay-help/torneko3-gameplay-help-english.gba').read_bytes();prior=load_json('build/gameplay-help/english-build.json')
        data,report=build_rom(self.original,'english',self.catalog)
        for p in prior['ledger']['patches']:
            at=p['offset'];raw=bytes.fromhex(p['after']);self.assertEqual(data[at:at+len(raw)],raw)
        for a in prior['ledger']['allocations']:
            at,n=a['offset'],a['bytes'];self.assertEqual(data[at:at+n],old[at:at+n])
        for e in self.catalog['entries']:
            at=int(e['offset'],0);raw=bytes.fromhex(e['source_hex']);self.assertEqual(data[at:at+len(raw)],raw)
            for p in e['excluded_owners']:
                at=int(p['offset'],0);self.assertEqual(data[at:at+4],old[at:at+4])
        self.assertEqual(report['ledger']['memory_reservations'],prior['ledger']['memory_reservations'])

if __name__=='__main__':unittest.main()
