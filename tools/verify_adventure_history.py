"""Every history key, native formatter/row and composed Barinabo/floor suffix."""
import argparse
from pathlib import Path
import json
import struct
import mgba.log
from PIL import Image,ImageChops
from tools import build_adventure_history as b
from tools import verify_core_gameplay as old
from tools import verify_dungeon_interface as ui
from tools import verify_ally_services as service
from tools import verify_arena_services as arena
from tools.build_first_label import ORIGINAL_ROM,digest
from tools.game_text import GameTextCodec
from tools.translation_pipeline import FontZero,load_json,check
from tools.verify_expansion import Session
from tools.verify_items import write_json

STATE=service.STATE
BASELINE=b.previous.OUTPUT/'torneko3-arena-services-english.gba'
OUTPUT=b.OUTPUT
CATALOG=OUTPUT/'catalog.json'


def source(e,variant,report):
    return 0x08000000+(int(e['offset'],0) if variant=='baseline' else report['history']['relocated'][e['id']]['offset'])


def set_values(core,e,profile,hero):
    v=b.values(e,profile,hero);core.memory.u16[0x020014CE]=int(hero=='Tipper')
    core.memory.u32[old.NUMBER]=int(v['$d0']);core.memory.u32[old.NUMBER+4]=int(v['$d1'])
    # $v07 uses the same numeric slot as $d0. Entries use one form at a time.
    if '$v07' in e['english']:core.memory.u32[old.NUMBER]=int(v['$v07'])
    old.write_bytes(core,old.ITEM,v['$i0'].encode().ljust(100,b'\0'))
    return v


def contexts(session,variant,font):
    c=session.core;records=[];codec=GameTextCodec(ORIGINAL_ROM.read_bytes())
    for kind in ('barinabo','dungeon_clear'):
        for index in range(64 if kind=='barinabo' else 5):
            check(c.load_raw_state(STATE.read_bytes()),'History context state');root=c.memory.u32[0x02000004]
            if kind=='barinabo':
                c.memory.u8[0x02010619]=index;c.memory.u16[root+0x9E]=999;group,row=2,9
            else:
                at=root+20*index;c.memory.u16[at+0x34]=1;c.memory.u16[at+0x36]=99;c.memory.u32[at+0x38]=9999999
                c.memory.u16[at+0x42]=59;c.memory.u16[at+0x44]=59;c.memory.u16[at+0x46]=32767;group,row=3,2*index+1
            old.write_bytes(c,old.DEST-8,old.GUARD+b'\xA5'*512+old.GUARD);trace=ui.InterfaceTrace(c)
            try:
                ui.native_step(session,trace,0x08086C30,[group,row,old.DEST]);raw=old.cstring(c,old.DEST,512)
                check(bytes(c.memory[old.DEST-8:old.DEST])==old.GUARD and bytes(c.memory[old.DEST+512:old.DEST+520])==old.GUARD,'Composite history output overrun')
                if variant=='english':
                    if kind=='barinabo':
                        name=ui.native_step(session,trace,0x0805F33C,[index])['return_r0'];expected=b'Barinabo: '+old.cstring(c,name)[:-1]+b' 999F\0'
                    else:expected=b'\x03\x08\x40' + b'9999999 turns/32767:59:59\0'
                    check(raw==expected,f'History composite payload differs {kind}/{index}: {raw!r}/{expected!r}')
                ui.native_step(session,trace,0x0808B60C,[20,1,1]);ui.native_step(session,trace,0x0808BBD8,[0]);ui.native_step(session,trace,0x0808CB84,[4,3,old.DEST,0,0]);ui.native_step(session,trace,0x0808BBF8,[0])
                checks=arena.check_draws(trace,font) if variant=='english' else []
                record={'kind':kind,'index':index,'root':hex(root),'formatted_hex':raw.hex(),'checks':checks,'glyphs':trace.positions,'payloads':trace.payloads,'guards_intact':True}
            finally:trace.close()
            name=f'context-{kind}-{index:02d}';session.frames(2);session.capture(name);record['screens']=[name+'.png'];write_json(session.output/(name+'.json'),record);records.append({k:v for k,v in record.items() if k not in ('glyphs','payloads')})
    return records


def verify(variant,limit=None):
    mgba.log.silence();rom=BASELINE if variant=='baseline' else OUTPUT/f'torneko3-adventure-history-{variant}.gba'
    catalog=load_json(CATALOG);report={} if variant=='baseline' else load_json(OUTPUT/f'{variant}-build.json');original=ORIGINAL_ROM.read_bytes();font=FontZero(original);codec=GameTextCodec(original);byoffset={int(e['offset'],0):e for e in catalog['entries']}
    with Session(rom.read_bytes(),OUTPUT/'verification'/variant) as session:
        c=session.core;lookups=[];cases=[]
        check(c.load_raw_state(STATE.read_bytes()),'History lookup state')
        for at in range(b.TABLE,b.END-8,8):
            key,target=struct.unpack_from('<II',original,at);trace=ui.InterfaceTrace(c)
            try:
                r=ui.native_step(session,trace,0x08087788,[key]);e=byoffset.get(target-0x08000000)
                expected=source(e,variant,report) if e else target
                check(r['return_r0']==expected and c.memory.u32[at+0x08000000]==key,'History key/value lookup differs')
                lookups.append({'pointer_word':hex(at+4),'key':codec.parse(original,key-0x08000000)['display'],'returned':hex(r['return_r0'])})
            finally:trace.close()
        for index,e in enumerate(catalog['entries'][:limit]):
            for hero in ('Torneko','Tipper'):
                for profile in ('normal','stress') if variant=='english' else ('normal',):
                    check(c.load_raw_state(STATE.read_bytes()),'History display state');values=set_values(c,e,profile,hero);trace=ui.InterfaceTrace(c)
                    try:
                        key=int(e['pointer_owners'][0]['key_offset'],0)+0x08000000
                        found=ui.native_step(session,trace,0x08087788,[key])['return_r0'];check(found==source(e,variant,report),'History row lookup lost translation')
                        raw=old.guarded_format(session,trace,found,mode=1,cap=512)
                        if variant=='english':
                            expected=b.payload(e)
                            for k,v in values.items():expected=expected.replace(k.encode(),v.encode())
                            check(raw==expected,f'History formatter differs {e["id"]}: {raw!r}/{expected!r}')
                        ui.native_step(session,trace,0x0808B60C,[20,1,1]);ui.native_step(session,trace,0x0808BBD8,[0])
                        y=3+13*(index%10);ui.native_step(session,trace,0x0808CB84,[4,y,old.DEST,0,0]);ui.native_step(session,trace,0x0808BBF8,[0])
                        checks=arena.check_draws(trace,font) if variant=='english' else []
                        record={'id':e['id'],'hero':hero,'profile':profile,'y':y,'formatted_hex':raw.hex(),'checks':checks,'glyphs':trace.positions,'payloads':trace.payloads,'guards_intact':True}
                    finally:trace.close()
                    name=f'{e["id"]}-{hero}-{profile}';session.frames(2);session.capture(name);record['screens']=[name+'.png'];write_json(session.output/(name+'.json'),record);cases.append({k:v for k,v in record.items() if k not in ('glyphs','payloads')})
            if index%10==0:print(variant,index+1,'history sources',flush=True)
        composed=contexts(session,variant,font)
        result={'rom_sha256':digest(rom.read_bytes()),'source_sha256':digest(original),'catalog_sha256':digest(CATALOG.read_bytes()),'fixture_sha256':digest(STATE.read_bytes()),
            'harness_sha256':digest(Path(__file__).read_bytes()),'limited':bool(limit),'key_lookups':lookups,'cases':cases,'contexts':composed,'screens':[s for c in cases+composed for s in c['screens']],
            'scope':'Every native table lookup including blank/error rows; every translated source through the mode-1 formatter and original history row renderer, both protagonists and stated numeric fixtures. Original context reader composes all 64 dungeon-name/Barinabo floor variants and five cleared-dungeon time/turn rows. Achievement triggers and history counter maximums remain separate.'}
        write_json(session.output/'verification.json',result);print(variant,'passed',len(cases),'cases',flush=True)


def summarize():
    original=ORIGINAL_ROM.read_bytes();catalog=load_json(CATALOG);baseline=BASELINE.read_bytes();proofs={};prior=load_json(BASELINE.parent/'english-build.json')['ledger'];end=max(a['offset']+a['bytes'] for a in prior['allocations'])
    for variant in ('english','japanese','baseline'):
        path=OUTPUT/'verification'/variant/'verification.json';r=load_json(path);data=baseline if variant=='baseline' else (OUTPUT/f'torneko3-adventure-history-{variant}.gba').read_bytes()
        check(r['rom_sha256']==digest(data) and r['source_sha256']==digest(original),'History proof ROM mismatch')
        check(r['catalog_sha256']==digest(CATALOG.read_bytes()) and r['harness_sha256']==digest((OUTPUT/'verify_adventure_history.py').read_bytes()) and r['fixture_sha256']==digest(STATE.read_bytes()),'History proof input mismatch')
        expected={(e['id'],h,p) for e in catalog['entries'] for h in ('Torneko','Tipper') for p in (('normal','stress') if variant=='english' else ('normal',))}
        check(not r['limited'] and len(r['cases'])==len(expected) and {(e['id'],e['hero'],e['profile']) for e in r['cases']}==expected,'Incomplete history cases')
        check(len(r['key_lookups'])==108 and {int(x['pointer_word'],0) for x in r['key_lookups']}==set(range(b.TABLE+4,b.END-8,8)),'Missing history lookup')
        check(len(r['contexts'])==69 and {(x['kind'],x['index']) for x in r['contexts']}=={('barinabo',i) for i in range(64)}|{('dungeon_clear',i) for i in range(5)},'Missing composed history contexts')
        if variant!='baseline':
            report=load_json(OUTPUT/f'{variant}-build.json');check(report['previous_rom_sha256']==digest(baseline),'History baseline differs');ledger=report['ledger'];rebuilt=bytearray(original+b'\xff'*(len(data)-len(original)))
            for a in ledger['allocations']:
                at=a['offset'];raw=data[at:at+a['bytes']];check(digest(raw)==a['sha256'],'History allocation hash mismatch');rebuilt[at:at+len(raw)]=raw
            for p in ledger['patches']:
                at=p['offset'];before=bytes.fromhex(p['before']);after=bytes.fromhex(p['after']);check(rebuilt[at:at+len(before)]==before,'History patch source differs');rebuilt[at:at+len(after)]=after
            check(bytes(rebuilt)==data and data[0x1000000:end]==baseline[0x1000000:end],'Unexplained history changes')
            for src in ledger['protected_sources']:check(data[src['start']:src['end_exclusive']]==original[src['start']:src['end_exclusive']],'History protected source changed')
            for p in prior['patches']:check(data[p['offset']:p['offset']+len(bytes.fromhex(p['after']))]==bytes.fromhex(p['after']),'Earlier history-base patch changed')
        proofs[variant]={'rom_sha256':digest(data),'report_sha256':digest(path.read_bytes()),'cases':len(r['cases'])}
    a=load_json(OUTPUT/'verification/japanese/verification.json');z=load_json(OUTPUT/'verification/baseline/verification.json');check(a['screens']==z['screens'],'History Japanese screen sets differ')
    for name in a['screens']:
        with Image.open(OUTPUT/'verification/japanese'/name) as x,Image.open(OUTPUT/'verification/baseline'/name) as y:check(ImageChops.difference(x.convert('RGB'),y.convert('RGB')).getbbox() is None,'History Japanese pixels differ '+name)
    result={'status':'history_component_native_checks_passed','sources':100,'pointer_words':104,'native_key_lookups':108,'english_cases':400,'native_composite_contexts':69,'japanese_pixel_pairs':len(a['screens']),
        'proofs':proofs,'complete_images_reconstructed_from_ledgers':True,'previous_patches_and_appended_bytes_preserved':True,'scope':'History table/mode-1 formatter/row and original special context reader proof. Natural achievements and maximum stored counters require their separately stated evidence.'}
    write_json(OUTPUT/'table-checkpoint.json',result);print(result['status'],flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('variant',choices=('english','japanese','baseline','summarize'));p.add_argument('--limit',type=int);a=p.parse_args();summarize() if a.variant=='summarize' else verify(a.variant,a.limit)
