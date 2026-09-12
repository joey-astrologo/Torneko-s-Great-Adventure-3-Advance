"""Accept system labels only after all native suites and baseline controls pass."""
from pathlib import Path
from PIL import Image,ImageChops
from tools import verify_system_labels as v
from tools.translation_pipeline import check,load_json
from tools.verify_items import write_json

SCOPE='42 original sources; native extra-mode and party menus, all 64 dungeon-entry summaries plus fixed 23-byte summary copy, 12 growth labels, five type-4 object indices plus fallback, 75 equipment-cap rows, 370 equipment-stat rows and nine mark fixtures, synthesis heading, visibility message, three bounded context copies/command compositions and five paged messages through their actual wrappers. Guarded fields and unchanged item/profile records. Controlled state/branch overrides and isolated instruction slices are explicit; natural progression, confirmation responses and end-to-end synthesis remain separate.'


def summarize():
    out=v.b.OUTPUT;original=v.ORIGINAL_ROM.read_bytes();baseline=v.BASELINE.read_bytes();catalog=load_json(out/'catalog.json');prior=load_json(v.BASELINE.parent/'english-build.json')['ledger'];end=max(a['offset']+a['bytes'] for a in prior['allocations']);reports={};proofs={};harness=v.digest(Path(v.__file__).read_bytes());words={int(p['offset'],0) for e in catalog['entries'] for p in e['pointer_owners']}
    check(v.b.CATALOG.read_bytes()==(out/'catalog.json').read_bytes(),'System catalog changed');check(harness==v.digest((out/Path(v.__file__).name).read_bytes()),'System frozen harness changed')
    for variant in ('english','japanese','baseline'):
        data=baseline if variant=='baseline' else (out/f'torneko3-system-labels-{variant}.gba').read_bytes();suites={};screens=[];hashes={}
        for suite,count in v.SUITES.items():
            path=out/'verification'/variant/(suite+'-verification.json');r=load_json(path);suites[suite]=r;hashes[suite]=v.digest(path.read_bytes())
            check(r['rom_sha256']==v.digest(data) and r['source_sha256']==v.digest(original),'System proof ROM changed');check(r['catalog_sha256']==v.digest(v.b.CATALOG.read_bytes()) and r['harness_sha256']==harness and r['helper_sha256']==v.helper_hashes() and r['fixture_sha256']==v.digest(v.STATE.read_bytes()),'System proof tooling/fixture changed')
            check(r['variant']==variant and r['suite']==suite and len(r['cases'])==count and len({c['id'] for c in r['cases']})==count,'System suite incomplete');check(all(c['guards_intact'] for c in r['cases']),'System guard proof missing')
            check({int(p['word'],0) for p in r['pointer_words']}==words and len(r['pointer_words'])==len(words),'System pointer coverage incomplete')
            for p in r['pointer_words']:check(int(p['source'],0)==int.from_bytes(data[int(p['word'],0):int(p['word'],0)+4],'little'),'System pointer evidence differs')
            check(r['screens']==[p for c in r['cases'] for p in c['screens']] and all((path.parent/p).is_file() for p in r['screens']),'System screenshots missing');screens+=r['screens']
            if variant=='english':
                for c in r['cases']:
                    if suite=='objects' and c['index']==0:check(c['formatted_hex']=='00','Empty object row changed')
                    else:check(c['checks'],'System glyph checks absent '+c['id'])
            if suite=='summaries':check([c['row'] for c in r['cases']]==list(range(-1,64)) and all(c['record_and_guards_intact'] and c['font_tables_intact'] and len(bytes.fromhex(c['title_hex']))<=64 for c in r['cases']),'System summary coverage/fields differ')
            if suite=='growth':check([c['index'] for c in r['cases']]==list(range(12)),'System growth indices differ')
            if suite=='objects':check([c['index'] for c in r['cases']]==list(range(6)),'System object indices differ')
            if suite=='statistics':check([c['item'] for c in r['cases'][:370]]==list(range(370)) and all(c['item_record_unchanged'] and len(bytes.fromhex(c['formatted_hex']))<=1024 for c in r['cases']),'System statistic field coverage differs')
            if suite=='contexts':check(all(c['context_hex']==b'Trip\0'.hex() for c in r['cases']) if variant=='english' else True,'System context abbreviation differs')
        if variant!='baseline':
            build=load_json(out/f'{variant}-build.json');check(build['rom_sha256']==v.digest(data) and build['catalog_sha256']==v.digest(v.b.CATALOG.read_bytes()) and build['previous_rom_sha256']==v.digest(baseline),'System build inputs differ');ledger=build['ledger'];rebuilt=bytearray(original+b'\xff'*(len(data)-len(original)))
            for a in ledger['allocations']:
                at=a['offset'];raw=data[at:at+a['bytes']];check(v.digest(raw)==a['sha256'],'System allocation hash differs');rebuilt[at:at+len(raw)]=raw
            for p in ledger['patches']:
                at=p['offset'];before=bytes.fromhex(p['before']);after=bytes.fromhex(p['after']);check(rebuilt[at:at+len(before)]==before,'System patch original differs');rebuilt[at:at+len(after)]=after
            check(bytes(rebuilt)==data and data[0x1000000:end]==baseline[0x1000000:end],'System unexplained ROM writes')
            for p in prior['patches']:
                at=p['offset'];raw=bytes.fromhex(p['after']);check(data[at:at+len(raw)]==raw,'Previous system-base patch changed')
            for p in ledger['protected_sources']:check(data[p['start']:p['end_exclusive']]==original[p['start']:p['end_exclusive']],'System protected source changed')
        reports[variant]=suites;proofs[variant]={'rom_sha256':v.digest(data),'suite_report_sha256':hashes,'cases':sum(v.SUITES.values()),'screens':len(screens)}
    pixel_pairs=0
    for suite in v.SUITES:
        a,z=reports['japanese'][suite],reports['baseline'][suite];check(a['screens']==z['screens'],'System control image lists differ')
        for x,y in zip(a['cases'],z['cases'],strict=True):
            for key in ('formatted_hex','title_hex','context_hex','formatted','power','value','marks','hidden_marks'):
                if key in x:check(x[key]==y[key],'System control native output differs '+key)
        for name in a['screens']:
            with Image.open(out/'verification/japanese'/name) as x,Image.open(out/'verification/baseline'/name) as y:check(ImageChops.difference(x.convert('RGB'),y.convert('RGB')).getbbox() is None,'System Japanese pixels differ '+name)
            pixel_pairs+=1
    result={'status':'system_labels_native_checks_passed','sources':42,'pointer_words':len(words),'english_cases':sum(v.SUITES.values()),'english_screens':proofs['english']['screens'],'japanese_pixel_pairs':pixel_pairs,'suites':v.SUITES,'proofs':proofs,'complete_images_reconstructed_from_ledgers':True,'previous_patches_and_appended_bytes_preserved':True,'scope':SCOPE};write_json(out/'component-checkpoint.json',result);print(result['status'],pixel_pairs,'control pixel pairs',flush=True)


if __name__=='__main__':summarize()
