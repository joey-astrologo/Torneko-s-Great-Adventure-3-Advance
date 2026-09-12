"""Accept complete merchant source, record, world-page and capacity checks."""
from pathlib import Path
from PIL import Image,ImageChops
from tools import verify_merchants as v
from tools.build_first_label import ORIGINAL_ROM,digest
from tools.game_text import PRINTF
from tools.translation_pipeline import load_json,check
from tools.verify_items import write_json


def summarize():
    out=v.b.OUTPUT;original=ORIGINAL_ROM.read_bytes();baseline=v.BASELINE.read_bytes();catalog=load_json(out/'catalog.json');reports={};proofs={}
    check((out/'catalog.json').read_bytes()==v.b.CATALOG.read_bytes(),'Merchant catalog changed')
    harness=digest((out/'verify_merchants.py').read_bytes());check(harness==digest(Path(v.__file__).read_bytes()),'Merchant harness changed')
    prior=load_json(v.BASELINE.parent/'english-build.json')['ledger'];end=max(a['offset']+a['bytes'] for a in prior['allocations'])
    for variant in ('english','japanese','baseline'):
        path=out/'verification'/variant/'verification.json';r=load_json(path);data=baseline if variant=='baseline' else (out/f'torneko3-merchants-{variant}.gba').read_bytes()
        check(r['rom_sha256']==digest(data) and r['source_sha256']==digest(original),'Merchant proof ROM differs')
        check(r['catalog_sha256']==digest((out/'catalog.json').read_bytes()) and r['harness_sha256']==harness and r['fixture_sha256']==digest(v.STATE.read_bytes()),'Merchant proof inputs differ')
        expected={(e['id'],p) for e in catalog['entries'] for p in (('normal','stress','bytes') if variant=='english' and PRINTF.findall(bytes.fromhex(e['source_hex'])) else ('normal','stress') if variant=='english' else ('normal',))}
        check(not r['limited'] and len(r['cases'])==len(expected) and {(e['id'],e['profile']) for e in r['cases']}==expected,'Incomplete merchant cases')
        check(all(c['guards_intact'] and c['slots_intact'] for c in r['cases']),'Merchant guard proof incomplete')
        for c in r['cases']:
            if c['printf_hex']:check(len(bytes.fromhex(c['printf_hex']))<=256,'Merchant printf overflow')
            check(len(bytes.fromhex(c['formatted_hex']))<=1024,'Merchant world overflow')
            if c['profile']=='bytes':check(not c['screens'] and c['checks'],'Merchant capacity fixture differs')
            elif c['family'] in ('speech','observation'):check(c['pages']==len(c['screens']) and c['pages']>0,'Merchant incomplete pages')
        words={int(p['offset'],0) for e in catalog['entries'] for p in e['pointer_owners']}
        check(len(r['pointer_words'])==453 and {int(p['word'],0) for p in r['pointer_words']}==words,'Merchant pointer coverage incomplete')
        for p in r['pointer_words']:check(int(p['source'],0)==int.from_bytes(data[int(p['word'],0):int(p['word'],0)+4],'little'),'Merchant pointer result differs')
        check(r['table_checks']==[{'base':hex(base),'records':count,'stride':stride,'nontext_words_unchanged':True} for base,count,stride in ((v.b.SHOP_BASE,19,0xA4),(v.b.PLAYER_BASE,2,0x40),(v.b.MENU_BASE,4,12))],'Merchant table metadata proof incomplete')
        check(r['selections']==[{'kind':'shop','index':i,'selected':hex(0x08000000+v.b.SHOP_BASE+i*0xA4)} for i in range(19)]+[{'kind':'player_shop','flag':f,'selected':hex(0x08000000+v.b.PLAYER_BASE+(0x40 if f==2 else 0))} for f in range(4)],'Merchant native selection proof differs')
        check(len(r['menus'])==1 and r['menus'][0]['rows']==3,'Merchant menu missing')
        check(r['screens']==[s for c in r['cases']+r['menus'] for s in c['screens']] and len(r['screens'])==len(set(r['screens'])),'Merchant screenshot inventory differs')
        check(all((path.parent/s).is_file() for s in r['screens']),'Merchant screenshot missing')
        if variant=='english':check(all(c['checks'] and all(c['checks']) for c in r['cases']+r['menus']),'Merchant English glyph proof missing')
        if variant!='baseline':
            build=load_json(out/f'{variant}-build.json');check(build['previous_rom_sha256']==digest(baseline) and build['catalog_sha256']==r['catalog_sha256'],'Merchant build input differs')
            ledger=build['ledger'];rebuilt=bytearray(original+b'\xff'*(len(data)-len(original)))
            for a in ledger['allocations']:
                at=a['offset'];raw=data[at:at+a['bytes']];check(digest(raw)==a['sha256'],'Merchant allocation differs');rebuilt[at:at+len(raw)]=raw
            for p in ledger['patches']:
                at=p['offset'];before=bytes.fromhex(p['before']);after=bytes.fromhex(p['after']);check(rebuilt[at:at+len(before)]==before,'Merchant patch source differs');rebuilt[at:at+len(after)]=after
            check(bytes(rebuilt)==data and data[0x1000000:end]==baseline[0x1000000:end],'Unexplained merchant image writes')
            for p in prior['patches']:
                at=p['offset'];raw=bytes.fromhex(p['after']);check(data[at:at+len(raw)]==raw,'Earlier merchant-base patch changed')
            for s in ledger['protected_sources']:check(data[s['start']:s['end_exclusive']]==original[s['start']:s['end_exclusive']],'Merchant protected source changed')
        proofs[variant]={'rom_sha256':digest(data),'report_sha256':digest(path.read_bytes()),'cases':len(r['cases']),'screens':len(r['screens'])};reports[variant]=r
    a,z=reports['japanese'],reports['baseline'];check(a['screens']==z['screens'],'Merchant Japanese screenshots differ')
    check([(c['formatted_hex'],c['printf_hex'],c['pages']) for c in a['cases']]==[(c['formatted_hex'],c['printf_hex'],c['pages']) for c in z['cases']],'Merchant Japanese payloads/pages differ')
    for name in a['screens']:
        with Image.open(out/'verification/japanese'/name) as x,Image.open(out/'verification/baseline'/name) as y:check(ImageChops.difference(x.convert('RGB'),y.convert('RGB')).getbbox() is None,'Merchant Japanese pixels differ '+name)
    result={'status':'merchants_component_native_checks_passed','sources':132,'pointer_words':453,'english_cases':282,'english_screens':len(reports['english']['screens']),'native_record_selections':23,'japanese_pixel_pairs':len(a['screens']),
        'proofs':proofs,'complete_images_reconstructed_from_ledgers':True,'previous_patches_and_appended_bytes_preserved':True,'scope':a['scope']}
    write_json(out/'component-checkpoint.json',result);print(result['status'],len(a['screens']),'Japanese pixel pairs',flush=True)

if __name__=='__main__':summarize()
