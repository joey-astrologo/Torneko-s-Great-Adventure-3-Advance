"""Accept English inscription matching while preserving original kana behavior."""
from pathlib import Path
from PIL import Image,ImageChops
from tools import verify_inscriptions as v,verify_inscription_input as live
from tools.translation_pipeline import check,load_json
from tools.verify_items import write_json


def summarize():
    out=v.b.OUTPUT;original=v.ORIGINAL_ROM.read_bytes();baseline=v.BASELINE.read_bytes();catalog=load_json(out/'catalog.json');prior=load_json(v.BASELINE.parent/'english-build.json')['ledger'];end=max(a['offset']+a['bytes'] for a in prior['allocations']);reports={};proofs={}
    check(v.b.CATALOG.read_bytes()==(out/'catalog.json').read_bytes(),'Inscription catalog changed')
    for module in (v,live):check(Path(module.__file__).read_bytes()==(out/Path(module.__file__).name).read_bytes(),'Inscription frozen harness differs')
    for variant in ('english','japanese','baseline'):
        data=baseline if variant=='baseline' else (out/f'torneko3-inscriptions-{variant}.gba').read_bytes();path=out/'verification'/variant/'verification.json';r=load_json(path)
        check(r['rom_sha256']==v.digest(data) and r['source_sha256']==v.digest(original) and r['fixture_sha256']==v.digest(v.STATE.read_bytes()),'Inscription proof source differs')
        check(r['catalog_sha256']==v.digest(v.b.CATALOG.read_bytes()) and r['harness_sha256']==v.digest(Path(v.__file__).read_bytes()),'Inscription proof tooling differs')
        expected=v.test_cases(catalog['entries'],variant,original);check(not r['limited'] and len(r['cases'])==len(expected),'Inscription cases incomplete')
        for e,c in zip(expected,r['cases'],strict=True):
            check(all(c[k]==val for k,val in e.items()) and c['guards_intact'],'Inscription case/guard differs');check(len(bytes.fromhex(c['compact_hex']))<=8 and len(bytes.fromhex(c['decoded_hex']))<=64,'Inscription capacity exceeded')
        rows=[x for p in r['lists'] for x in p['rows']];check(len(rows)==49 and [x['row'] for x in rows]==list(range(49)) and all(len(bytes.fromhex(x['formatted_hex']))<=32 for x in rows),'Inscription native rows incomplete')
        ids=[e['item_id'] for e in catalog['entries'][::2]];selections=[('all',ids),('none',[])]+[(str(i),[i]) for i in ids]
        check(r['learned_selections']==[{'case':k,'selected_item_ids':x,'unused_slots_zero':True} for k,x in selections],'Learned-list native selector incomplete')
        check(len(r['screens'])==7 and all((path.parent/p).is_file() for p in r['screens']),'Inscription screenshot missing')
        if variant!='baseline':
            build=load_json(out/f'{variant}-build.json');check(build['catalog_sha256']==r['catalog_sha256'] and build['previous_rom_sha256']==v.digest(baseline),'Inscription build inputs differ');ledger=build['ledger'];rebuilt=bytearray(original+b'\xff'*(len(data)-len(original)))
            for a in ledger['allocations']:
                at=a['offset'];raw=data[at:at+a['bytes']];check(v.digest(raw)==a['sha256'],'Inscription allocation differs');rebuilt[at:at+len(raw)]=raw
            for p in ledger['patches']:
                at=p['offset'];before=bytes.fromhex(p['before']);after=bytes.fromhex(p['after']);check(rebuilt[at:at+len(before)]==before,'Inscription patch source differs');rebuilt[at:at+len(after)]=after
            check(bytes(rebuilt)==data and data[0x1000000:end]==baseline[0x1000000:end],'Unexplained inscription writes')
            for p in prior['patches']:
                at=p['offset'];raw=bytes.fromhex(p['after']);check(data[at:at+len(raw)]==raw,'Earlier inscription-base patch changed')
            for p in ledger['protected_sources']:check(data[p['start']:p['end_exclusive']]==original[p['start']:p['end_exclusive']],'Protected inscription source changed')
        reports[variant]=r;proofs[variant]={'rom_sha256':v.digest(data),'report_sha256':v.digest(path.read_bytes()),'matching_cases':len(r['cases']),'learned_selections':51,'screens':7}
    a,z=reports['japanese'],reports['baseline'];check(a['cases']==z['cases'] and a['lists']==z['lists'],'Inscription control behavior differs')
    for name in a['screens']:
        with Image.open(out/'verification/japanese'/name) as x,Image.open(out/'verification/baseline'/name) as y:check(ImageChops.difference(x.convert('RGB'),y.convert('RGB')).getbbox() is None,'Inscription control pixels differ '+name)
    english={c['id']:c for c in reports['english']['cases']};legacy={c['id']:c for c in z['cases']}
    for ident,c in legacy.items():check({k:value for k,value in english[ident].items() if k!='call'}=={k:value for k,value in c.items() if k!='call'},'Original inscription behavior regressed '+ident)
    for ident,c in english.items():
        if not ident.startswith('english-'):continue
        reference=legacy[f"legacy-{c['row']:02d}-hira" if c['learned'] else f"legacy-unlearned-{c['row']:02d}-hira"]
        x=bytes.fromhex(c['item_after_hex']);y=bytes.fromhex(reference['item_after_hex']);check(x[:4]+x[12:]==y[:4]+y[12:],'English inscription flags/accounting differ from Japanese result')
    path=out/'verification/input/verification.json';r=load_json(path);check(r['rom_sha256']==proofs['english']['rom_sha256'] and r['catalog_sha256']==v.digest(v.b.CATALOG.read_bytes()) and r['harness_sha256']==v.digest(Path(live.__file__).read_bytes()) and r['fixture_sha256']==v.digest(live.STATE.read_bytes()),'Live inscription inputs differ')
    check([c['item_id'] for c in r['cases']]==[192,193,213,240] and all(c['guards_intact'] and c['native_result']['item_id']==c['item_id'] for c in r['cases']),'Real inscription input cases incomplete')
    check(all((path.parent/p).is_file() for c in r['cases'] for p in c['screens']),'Inscription input screenshot missing')
    result={'status':'inscriptions_component_native_checks_passed','kana_sources':98,'item_identities':49,'english_matching_cases':549,'baseline_matching_cases':255,'legacy_regression_cases':255,'english_vs_japanese_outcome_comparisons':294,'native_learned_selections':51,'native_list_rows':49,'japanese_pixel_pairs':7,'real_joypad_inscriptions':4,'proofs':proofs,'complete_images_reconstructed_from_ledgers':True,'previous_patches_and_appended_bytes_preserved':True,'original_dictionary_and_kana_sources_preserved':True,'scope':reports['english']['scope']+' '+r['scope']};write_json(out/'component-checkpoint.json',result);print(result['status'],flush=True)

if __name__=='__main__':summarize()
