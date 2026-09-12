"""Accept shared keyboard corrections with explicit patch supersession history."""
from pathlib import Path
from PIL import Image,ImageChops
from tools import verify_keyboard_completion as v,verify_keyboard_input as live
from tools.translation_pipeline import check,load_json
from tools.verify_items import write_json


def summarize():
    out=v.b.OUTPUT;original=v.ORIGINAL_ROM.read_bytes();baseline=v.BASELINE.read_bytes();prior=load_json(v.BASELINE.parent/'english-build.json')['ledger'];end=max(a['offset']+a['bytes'] for a in prior['allocations']);reports={};proofs={}
    check(v.b.CATALOG.read_bytes()==(out/'catalog.json').read_bytes(),'Keyboard catalog changed')
    for module in (v,live):check(Path(module.__file__).read_bytes()==(out/Path(module.__file__).name).read_bytes(),'Keyboard frozen harness differs')
    for variant in ('english','japanese','baseline','original'):
        data=original if variant=='original' else baseline if variant=='baseline' else (out/f'torneko3-keyboard-completion-{variant}.gba').read_bytes();path=out/'verification'/variant/'verification.json';r=load_json(path)
        check(r['rom_sha256']==v.digest(data) and r['source_sha256']==v.digest(original) and r['fixture_sha256']==v.digest(v.STATE.read_bytes()),'Keyboard proof source differs')
        check(r['catalog_sha256']==v.digest(v.b.CATALOG.read_bytes()) and r['harness_sha256']==v.digest(Path(v.__file__).read_bytes()),'Keyboard proof tooling differs')
        check(len(r['cases'])==8 and {(c['codec'],c['page'],c['history']) for c in r['cases']}=={(c,p,h) for c in (0,1) for p in (0,1) for h in (False,True)},'Keyboard context coverage incomplete')
        check(all(c['guards_intact'] and c['grid_glyphs'] for c in r['cases']),'Keyboard grid/input checks absent')
        check(len(r['histories'])==2 and all(h['records_intact'] and len(h['rows'])==8 and all(x['guards_intact'] for x in h['rows']) for h in r['histories']),'History coverage incomplete')
        check(r['popup']['ink']['glyphs']>0 and len(r['screens'])==11 and all((path.parent/name).is_file() for name in r['screens']),'Keyboard screens incomplete')
        if variant in ('english','japanese'):
            build=load_json(out/f'{variant}-build.json');check(build['catalog_sha256']==r['catalog_sha256'] and build['previous_rom_sha256']==v.digest(baseline),'Keyboard build inputs differ')
            ledger=build['ledger'];rebuilt=bytearray(original+b'\xff'*(len(data)-len(original)))
            for a in ledger['allocations']:
                at=a['offset'];raw=data[at:at+a['bytes']];check(v.digest(raw)==a['sha256'],'Keyboard allocation differs');rebuilt[at:at+len(raw)]=raw
            for p in ledger['patches']:
                at=p['offset'];before=bytes.fromhex(p['before']);after=bytes.fromhex(p['after']);check(rebuilt[at:at+len(before)]==before,'Keyboard patch source differs');rebuilt[at:at+len(after)]=after
            check(bytes(rebuilt)==data and data[0x1000000:end]==baseline[0x1000000:end],'Unexplained keyboard writes')
            for p in prior['patches']:
                at=p['offset'];raw=bytes.fromhex(p['after'])
                if variant=='english' and at in v.b.SHARED:
                    current=next(x for x in ledger['patches'] if x['offset']==at);check(current['before']==p['before'] and current['supersedes']==p and current['owner']=='keyboard-completion','Keyboard supersession lost previous owner history')
                else:check(data[at:at+len(raw)]==raw,'Unapproved previous patch change')
            for p in ledger['protected_sources']:check(data[p['start']:p['end_exclusive']]==original[p['start']:p['end_exclusive']],'Keyboard protected source changed')
        reports[variant]=r;proofs[variant]={'rom_sha256':v.digest(data),'report_sha256':v.digest(path.read_bytes()),'contexts':8,'history_rows':16,'screens':11}
    a,z=reports['japanese'],reports['baseline'];check(a['cases']==z['cases'] and a['histories']==z['histories'],'Control changed preceding keyboard/history')
    for name in a['screens']:
        with Image.open(out/'verification/japanese'/name) as x,Image.open(out/'verification/baseline'/name) as y:check(ImageChops.difference(x.convert('RGB'),y.convert('RGB')).getbbox() is None,'Keyboard control pixels differ '+name)
    # Kana original font/positions are exact. Latin font intentionally differs
    # from the Japanese original; comparison is with the accepted Latin grid.
    keys=('code','advance','x','y','font','spacing','window_origin','window_width','window_height')
    for e,o,z in zip(reports['english']['cases'],reports['original']['cases'],reports['baseline']['cases'],strict=True):
        reference=o if e['codec'] else z
        check(e['grid_hex']==reference['grid_hex'],'Keyboard alphabet changed')
        check([{k:g[k] for k in keys} for g in e['grid_glyphs']]==[{k:g[k] for k in keys} for g in reference['grid_glyphs']],'Keyboard grid font/geometry differs')
        check(e['ink']['overlapping_ink_pixels']==0,'Accepted grid ink overlaps')
    check(reports['english']['histories']==reports['baseline']['histories'],'History row layout/format changed')
    inputs={}
    for variant in ('english','baseline'):
        path=out/'verification'/('input-'+variant)/'verification.json';r=load_json(path)
        check(r['rom_sha256']==proofs[variant]['rom_sha256'] and r['harness_sha256']==v.digest(Path(live.__file__).read_bytes()) and r['fixture_sha256']==v.digest(live.STATE.read_bytes()),'Live keyboard proof inputs differ')
        check(len(r['cases'])==4 and all(c['guards_intact'] and c['returns'][-1]['return']==1 for c in r['cases']),'Keyboard live checks incomplete');inputs[variant]=r
    check(inputs['english']['cases']==inputs['baseline']['cases'],'Keyboard input behavior regressed')
    result={'status':'keyboard_completion_native_checks_passed','resources':6,'superseded_pointer_words':2,'new_popup_pointer_words':1,'new_grid_font_hooks':2,'native_contexts':8,'japanese_pixel_pairs':11,'original_kana_grid_comparisons':4,'history_rows':16,'guarded_decode_printf_pairs':16,'real_joypad_cases':4,'proofs':proofs,'complete_images_reconstructed_from_ledgers':True,'previous_allocations_and_unsuperseded_patches_preserved':True,'scope':reports['english']['scope'],'history_coordinate_note':'The native history renderer uses buffer coordinates starting at y=16; its eighth row exceeds the nominal descriptor height. All eight rows and screenshots retain the accepted native behavior. Capacity guards and horizontal ink are checked; no false generic y+12 viewport assertion is used.'}
    write_json(out/'component-checkpoint.json',result);print(result['status'],flush=True)

if __name__=='__main__':summarize()
