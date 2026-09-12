"""Accept remaining world messages, initialized sources and native wrapper contracts."""
from pathlib import Path
from PIL import Image,ImageChops
from tools import verify_world_completion as v
from tools.translation_pipeline import check,load_json
from tools.verify_items import write_json


def summarize():
    out=v.b.OUTPUT;original=v.ORIGINAL_ROM.read_bytes();baseline=v.BASELINE.read_bytes();catalog=load_json(out/'catalog.json');prior=load_json(v.BASELINE.parent/'english-build.json')['ledger'];end=max(a['offset']+a['bytes'] for a in prior['allocations']);reports={};proofs={}
    check(v.b.CATALOG.read_bytes()==(out/'catalog.json').read_bytes(),'World completion catalog changed');harness=v.digest(Path(v.__file__).read_bytes());check(harness==v.digest((out/Path(v.__file__).name).read_bytes()),'World frozen harness differs')
    for variant in ('english','japanese','baseline'):
        data=baseline if variant=='baseline' else (out/f'torneko3-world-completion-{variant}.gba').read_bytes();path=out/'verification'/variant/'verification.json';r=load_json(path)
        check(r['rom_sha256']==v.digest(data) and r['source_sha256']==v.digest(original),'World proof image differs');check(r['catalog_sha256']==v.digest(v.b.CATALOG.read_bytes()) and r['harness_sha256']==harness,'World proof tooling differs');check(r['fixture_sha256']=={'paged':v.digest(v.service.STATE.read_bytes()),'world':v.digest(v.merchants.STATE.read_bytes())},'World proof fixture differs')
        expected={(e['id'],p) for e in catalog['entries'] for p in (('normal','stress','bytes') if variant=='english' and v.PRINTF.findall(bytes.fromhex(e['source_hex'])) else ('normal','stress') if variant=='english' else ('normal',))}
        check(not r['limited'] and len(r['cases'])==len(expected) and {(c['id'],c['profile']) for c in r['cases']}==expected,'World cases incomplete')
        check(all(c['guards_intact'] and len(bytes.fromhex(c['formatted_hex']))<=(1024 if c['family']=='observation' else 1000) for c in r['cases']),'World guard/capacity evidence differs')
        for c in r['cases']:
            if c['printf_hex']:check(len(bytes.fromhex(c['printf_hex']))<=256,'World printf exceeds capacity')
            if c['profile']=='bytes':check(c['pages']==0 and not c['screens'],'World capacity fixture not separate')
            else:check(c['pages']==len(c['screens']) and c['pages']>0,'World pages incomplete')
            if variant=='english':check(c['checks'] and all(c['checks']),'World glyph checks missing')
        words={int(p['offset'],0) for e in catalog['entries'] for p in e['pointer_owners']};check(len(r['pointer_words'])==21 and {int(p['word'],0) for p in r['pointer_words']}==words,'World pointer coverage incomplete')
        for p in r['pointer_words']:check(int(p['target'],0)==int.from_bytes(data[int(p['word'],0):int(p['word'],0)+4],'little'),'World pointer target differs')
        check(len(r['zoom_selectors'])==13 and [(x['mask'],x['phase'],x['explored']) for x in r['zoom_selectors']]==[(1,0,0),(0,0,1),(0,0,0)]+[(0,i,0) for i in range(1,11)],'Zoom native selections incomplete');check(sum(x['speech'] for x in r['zoom_selectors'])==1 and all(int(x['body'],0)==int(x['source'],0)+1 for x in r['zoom_selectors']),'Zoom prefix contract differs')
        check(len(r['warehouse_selectors'])==2 and {int(x['literal'],0) for x in r['warehouse_selectors']}=={0x7394C,0x73994},'Warehouse reader cases incomplete');check(r['screens']==[p for c in r['cases'] for p in c['screens']] and all((path.parent/p).is_file() for p in r['screens']),'World screenshot inventory differs')
        if variant!='baseline':
            build=load_json(out/f'{variant}-build.json');check(build['catalog_sha256']==r['catalog_sha256'] and build['previous_rom_sha256']==v.digest(baseline),'World build inputs differ');ledger=build['ledger'];rebuilt=bytearray(original+b'\xff'*(len(data)-len(original)))
            for a in ledger['allocations']:
                at=a['offset'];raw=data[at:at+a['bytes']];check(v.digest(raw)==a['sha256'],'World allocation differs');rebuilt[at:at+len(raw)]=raw
            for p in ledger['patches']:
                at=p['offset'];before=bytes.fromhex(p['before']);after=bytes.fromhex(p['after']);check(rebuilt[at:at+len(before)]==before,'World patch source differs');rebuilt[at:at+len(after)]=after
            check(bytes(rebuilt)==data and data[0x1000000:end]==baseline[0x1000000:end],'Unexplained world image writes')
            for p in prior['patches']:
                at=p['offset'];raw=bytes.fromhex(p['after']);check(data[at:at+len(raw)]==raw,'Earlier world-base patch changed')
            for p in ledger['protected_sources']:check(data[p['start']:p['end_exclusive']]==original[p['start']:p['end_exclusive']],'World protected source changed')
        reports[variant]=r;proofs[variant]={'rom_sha256':v.digest(data),'report_sha256':v.digest(path.read_bytes()),'cases':len(r['cases']),'screens':len(r['screens'])}
    a,z=reports['japanese'],reports['baseline'];check(a['screens']==z['screens'],'World control screenshot lists differ');check([(c['formatted_hex'],c['printf_hex'],c['speech'],c['protocol_prefix']) for c in a['cases']]==[(c['formatted_hex'],c['printf_hex'],c['speech'],c['protocol_prefix']) for c in z['cases']],'World control payload/flags differ')
    for name in a['screens']:
        with Image.open(out/'verification/japanese'/name) as x,Image.open(out/'verification/baseline'/name) as y:check(ImageChops.difference(x.convert('RGB'),y.convert('RGB')).getbbox() is None,'World Japanese pixels differ '+name)
    result={'status':'world_completion_native_checks_passed','sources':19,'pointer_words':21,'english_cases':40,'english_screens':len(reports['english']['screens']),'japanese_pixel_pairs':len(a['screens']),'zoom_selectors_and_marker_handoffs':13,'inline_warehouse_readers':2,'proofs':proofs,'complete_images_reconstructed_from_ledgers':True,'previous_patches_and_appended_bytes_preserved':True,'scope':reports['english']['scope']};write_json(out/'component-checkpoint.json',result);print(result['status'],len(a['screens']),'control pixel pairs',flush=True)

if __name__=='__main__':summarize()
