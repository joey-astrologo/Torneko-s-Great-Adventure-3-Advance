"""Accept complete encounter UI with one explicit prior narration correction."""
from pathlib import Path
from PIL import Image,ImageChops
from tools import verify_encounter_ui as v
from tools.translation_pipeline import check,load_json
from tools.verify_items import write_json

SCOPE='36 newly translated original resources and one corrected existing house announcement: both protagonist tables and all 20 themed houses plus fallback, original 30-byte copy and field-to-actor handoff, queue/history and visible announcements, five companion menus and all eight spell-availability combinations. Original records, menu returns, flags, protected source bytes and prior allocations retained. One exact tutorial pointer patch is explicitly superseded to add the article; Japanese controls retain the prior tutorial narration. Controlled fixtures and instruction slices do not establish natural house generation, companion effects or spell execution.'


def summarize():
    out=v.b.OUTPUT;original=v.ORIGINAL_ROM.read_bytes();baseline=v.BASELINE.read_bytes();catalog=load_json(out/'catalog.json');prior=load_json(v.BASELINE.parent/'english-build.json')['ledger'];end=max(a['offset']+a['bytes'] for a in prior['allocations']);harness=v.digest(Path(v.__file__).read_bytes());words={int(p['offset'],0) for e in catalog['entries'] for p in e['pointer_owners']};reports={};proofs={}
    check(v.b.CATALOG.read_bytes()==(out/'catalog.json').read_bytes() and harness==v.digest((out/Path(v.__file__).name).read_bytes()),'Encounter frozen inputs changed')
    helpers={**v.system.helper_hashes(),'verify_system_labels.py':v.digest(Path(v.system.__file__).read_bytes()),'verify_tutorial_gameplay.py':v.digest(Path(v.queue.__file__).read_bytes())}
    for variant in ('english','japanese','baseline'):
        data=baseline if variant=='baseline' else (out/f'torneko3-encounter-ui-{variant}.gba').read_bytes();path=out/'verification'/variant/'verification.json';r=load_json(path)
        check(r['rom_sha256']==v.digest(data) and r['source_sha256']==v.digest(original),'Encounter ROM proof changed');check(r['catalog_sha256']==v.digest(v.b.CATALOG.read_bytes()) and r['harness_sha256']==harness and r['helper_sha256']==helpers and r['fixture_sha256']==v.digest(v.STATE.read_bytes()),'Encounter proof tooling/fixture changed')
        check(len(r['houses'])==42 and [(c['hero'],c['row']) for c in r['houses']]==[(hero,row) for hero in (0,1) for row in range(-1,20)],'Encounter house selections incomplete')
        check(len(r['menus'])==12 and [(int(c['base'],0),c['enabled']) for c in r['menus']]==[(base,flags) for base,count in v.b.MENUS for flags in (range(8) if base==0xD9680 else (0,))],'Encounter menu flag coverage incomplete')
        check(all(c['guards_intact'] and c['adjacent_fields_unchanged'] and len(bytes.fromhex(c['name_hex']))<=30 and c['queue']['guards_intact'] for c in r['houses']),'Encounter house guard/copy evidence missing')
        check(all(c['guards_intact'] for c in r['menus']),'Encounter menu guard evidence missing')
        if variant=='english':check(all(c['checks'] for c in r['houses']+r['menus']),'Encounter English glyph checks absent')
        check(len(r['pointer_words'])==58 and {int(p['word'],0) for p in r['pointer_words']}==words,'Encounter pointer coverage incomplete')
        for p in r['pointer_words']:check(int(p['source'],0)==int.from_bytes(data[int(p['word'],0):int(p['word'],0)+4],'little'),'Encounter pointer report differs')
        check(r['screens']==[p for c in r['houses']+r['menus'] for p in c['screens']] and len(r['screens'])==54 and all((path.parent/p).is_file() for p in r['screens']),'Encounter screenshots missing')
        if variant!='baseline':
            build=load_json(out/f'{variant}-build.json');check(build['rom_sha256']==v.digest(data) and build['previous_rom_sha256']==v.digest(baseline) and build['catalog_sha256']==v.digest(v.b.CATALOG.read_bytes()),'Encounter build inputs differ');ledger=build['ledger'];rebuilt=bytearray(original+b'\xff'*(len(data)-len(original)));supersessions=build['encounter_ui']['supersessions']
            check(len(supersessions)==int(variant=='english'),'Encounter unexpected supersession count')
            if supersessions:
                old=next(p for p in prior['patches'] if p['offset']==0x337C0);check(supersessions[0]['offset']==0x337C0 and supersessions[0]['supersedes']==old,'Encounter supersession lost previous ownership')
            for a in ledger['allocations']:
                at=a['offset'];raw=data[at:at+a['bytes']];check(v.digest(raw)==a['sha256'],'Encounter allocation hash differs');rebuilt[at:at+len(raw)]=raw
            for p in ledger['patches']:
                at=p['offset'];before=bytes.fromhex(p['before']);after=bytes.fromhex(p['after']);check(rebuilt[at:at+len(before)]==before,'Encounter patch original differs');rebuilt[at:at+len(after)]=after
            check(bytes(rebuilt)==data and data[0x1000000:end]==baseline[0x1000000:end],'Encounter unexplained ROM writes')
            for p in prior['patches']:
                if variant=='english' and p['offset']==0x337C0:continue
                at=p['offset'];raw=bytes.fromhex(p['after']);check(data[at:at+len(raw)]==raw,'Earlier encounter-base patch changed')
            for p in ledger['protected_sources']:check(data[p['start']:p['end_exclusive']]==original[p['start']:p['end_exclusive']],'Encounter protected source changed')
        reports[variant]=r;proofs[variant]={'rom_sha256':v.digest(data),'report_sha256':v.digest(path.read_bytes()),'house_cases':42,'menu_cases':12,'screens':54}
    a,z=reports['japanese'],reports['baseline'];check(a['screens']==z['screens'],'Encounter control screenshots differ')
    check([(c['name_hex'],c['formatted_hex'],c['queue']['rows_hex']) for c in a['houses']]==[(c['name_hex'],c['formatted_hex'],c['queue']['rows_hex']) for c in z['houses']],'Encounter Japanese name/handoff/history differs');check([c['colours'] for c in a['menus']]==[c['colours'] for c in z['menus']],'Encounter Japanese availability colours differ')
    for name in a['screens']:
        with Image.open(out/'verification/japanese'/name) as x,Image.open(out/'verification/baseline'/name) as y:check(ImageChops.difference(x.convert('RGB'),y.convert('RGB')).getbbox() is None,'Encounter Japanese pixels differ '+name)
    result={'status':'encounter_ui_native_checks_passed','sources':37,'new_inventory_sources':36,'corrected_existing_sources':1,'pointer_words':58,'english_cases':54,'english_screens':54,'japanese_pixel_pairs':54,'proofs':proofs,'complete_images_reconstructed_from_ledgers':True,'previous_patches_preserved_except_explicit_narration_supersession':True,'previous_appended_bytes_preserved':True,'scope':SCOPE};write_json(out/'component-checkpoint.json',result);print(result['status'],flush=True)


if __name__=='__main__':summarize()
