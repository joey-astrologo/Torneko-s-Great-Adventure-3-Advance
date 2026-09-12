"""Arena service pages, real menus, roster/entry readers and bounded copies."""
import argparse
from pathlib import Path
import struct
import json
import mgba.log
from PIL import Image, ImageChops
from tools import build_arena_services as b
from tools import verify_core_gameplay as old
from tools import verify_dungeon_interface as ui
from tools import verify_ally_services as service
from tools.build_first_label import ORIGINAL_ROM,digest
from tools.game_text import GameTextCodec,PRINTF
from tools.translation_pipeline import FontZero,load_json,check
from tools.verify_expansion import Session
from tools.verify_items import write_json

STATE=service.STATE
BASELINE=b.previous.OUTPUT/'torneko3-story-completion-english.gba'
OUTPUT=b.OUTPUT
CATALOG=OUTPUT/'catalog.json'
NAME=0x0203F080


def source(e,variant,report):
    return 0x08000000+(int(e['offset'],0) if variant=='baseline' else report['arena']['relocated'][e['id']]['offset'])


def setup(core,font,profile):
    values=service.set_values(core,font,profile)
    core.memory.u8[0x02004F80]=int(profile=='stress');values['$j0']='２' if profile=='stress' else '１'
    return values


def formatted(session,trace,e,variant,report,profile,font):
    c=session.core;values=setup(c,font,profile);at=source(e,variant,report);encoded,metrics=b.encode(e,ORIGINAL_ROM.read_bytes())
    raw_source=old.cstring(c,at);cap=metrics['capacity'];english=variant=='english'
    cap=max(cap,3) if not english and e['family']=='unit' else cap
    expected=encoded
    for k,v in values.items():expected=expected.replace(k.encode(),v.encode('cp932'))
    fmts=PRINTF.findall(raw_source)
    if fmts:
        name=b"Justice's elder brother" if profile=='stress' else b'Slime'
        if e['family']=='rule':name=b'Ines' if profile=='stress' else b'Rosa'
        old.write_bytes(c,NAME,name+b'\0')
        pyargs=(10,name,99,999,46,9) if e['family']=='roster' else (name,99) if e['family']=='name_level' else tuple(name if f==b'%s' else 999 for f in fmts)
        args=[NAME if f==b'%s' else x for f,x in zip(fmts,pyargs,strict=True)]
        old.write_bytes(c,old.DEST-8,old.GUARD+b'\xA5'*cap+old.GUARD)
        ui.native_step(session,trace,0x08096744,[old.DEST,at]+args)
        raw=old.cstring(c,old.DEST,cap)
        check(bytes(c.memory[old.DEST-8:old.DEST])==old.GUARD and bytes(c.memory[old.DEST+cap:old.DEST+cap+8])==old.GUARD,'Arena printf guards')
        expected=expected%pyargs
    else:raw=old.guarded_format(session,trace,at,cap=cap)
    if english:check(raw==expected,f'Arena formatted payload differs {e["id"]}: {raw!r}/{expected!r}')
    return raw,cap


def entry_case(session,e,variant,report,profile,font,codec):
    c=session.core;check(c.load_raw_state(STATE.read_bytes()),'Arena state restore');trace=ui.InterfaceTrace(c)
    try:
        raw,cap=formatted(session,trace,e,variant,report,profile,font)
        if e['family']!='message':
            ui.native_step(session,trace,0x0808B60C,[18,1,1]);ui.native_step(session,trace,0x0808BBD8,[0])
            old.write_bytes(c,old.DEST,raw);ui.native_step(session,trace,0x0808CB84,[0,0,old.DEST,0,13]);ui.native_step(session,trace,0x0808BBF8,[0])
            checks=ui.check_glyphs(trace.positions,old.visible(raw,codec),font) if variant=='english' else {}
            record={'checks':checks,'glyphs':trace.positions}
    finally:trace.close()
    name=e['id']+'-'+profile
    if e['family']=='message':
        record=service.pages(session,source(e,variant,report),name,font,raw[:-1].decode('cp932') if variant=='english' else None)
        check(len(record['formats'])==1 and record['formats'][0]['output_hex']==raw.hex(),'Arena service engine changed payload')
    else:session.frames(2);session.capture(name);record['screens']=[name+'.png']
    record.update(id=e['id'],profile=profile,family=e['family'],formatted_hex=raw.hex(),guarded_capacity=cap)
    write_json(session.output/(name+'.json'),record)
    return {k:v for k,v in record.items() if k not in ('glyphs','formats','pages')}|{'pages':len(record.get('pages',[]))}


def check_draws(trace,font):
    codec=GameTextCodec(ORIGINAL_ROM.read_bytes());checks=[]
    for d in trace.payloads:
        text=old.visible(bytes.fromhex(d['raw_hex']),codec)
        if text:
            gs=[g for g in trace.positions if g['draw_serial']==d['serial']]
            checks.append(old.command_ink_check(gs,text,font))
    return checks


def menus(session,variant,font):
    c=session.core;records=[];original=ORIGINAL_ROM.read_bytes()
    for base,count in b.MENU_TABLES:
        check(c.load_raw_state(STATE.read_bytes()),'Arena menu state');trace=ui.InterfaceTrace(c)
        try:
            for i in range(count+1):
                check(bytes(c.memory[base+0x08000000+i*12+4:base+0x08000000+(i+1)*12])==original[base+i*12+4:base+(i+1)*12],'Arena choice return/flags changed')
            check(c.memory.u32[base+0x08000000+count*12]==0,'Arena menu terminator changed')
            ui.native_step(session,trace,0x0807B294,[base+0x08000000,0,0,0],stop=0x0807B3B6)
            check(len(trace.payloads)==count,'Arena menu missing rows')
            checks=check_draws(trace,font) if variant=='english' else []
            record={'kind':'menu','base':hex(base),'rows':count,'checks':checks,'glyphs':trace.positions,'payloads':trace.payloads}
        finally:trace.close()
        name=f'menu-{base:08x}';session.frames(2);session.capture(name);record['screens']=[name+'.png'];write_json(session.output/(name+'.json'),record);records.append({k:v for k,v in record.items() if k not in ('glyphs','payloads')})
    return records


def roster_cases(session,variant,font):
    c=session.core;records=[];names={e['row']:e['display'] or e['english'] for e in load_json(b.ROOT/'translations/enemies.json')['entries'] if e['family']=='name'}
    for hero in (0,1):
        for start in range(0,200,10):
            check(c.load_raw_state(STATE.read_bytes()),'Arena roster restore');c.memory.u16[0x020014CE]=hero
            for i,row in enumerate(range(start,start+10)):
                old.write_bytes(c,0x020091D0+i*8,struct.pack('<4H',row,0,99,0));c.memory.u32[0x02009228+4*i]=(10,11,123,9999)[i%4]
            before=bytes(c.memory[0x020091D0:0x02009258]);trace=ui.InterfaceTrace(c)
            try:
                ui.native_step(session,trace,0x08079868,[]);check(len(trace.payloads)==10,'Arena roster row count')
                check(bytes(c.memory[0x020091D0:0x02009258])==before,'Roster changed battle data')
                checks=check_draws(trace,font) if variant=='english' else []
                if variant=='english':
                    for i,d in enumerate(trace.payloads):
                        row=start+i;name='Tipper' if row==198 else names[row];odds=(10,11,123,9999)[i%4]
                        expected=(b'' if row==0 else (f'{i+1:2d}:{name} Lv99 '.encode()+b'\x03\x09\xa0'+f'{odds//10}.{odds%10}x'.encode()) if hero==0 else f'{name} Lv99'.encode())+b'\0'
                        observed=bytes.fromhex(d['raw_hex']).split(b'\0',1)[0]+b'\0'
                        check(observed==expected,f'Actual roster name/level/odds differs {hero}/{row}: {observed!r}/{expected!r}')
                        gs=[g for g in trace.positions if g['draw_serial']==d['serial']]
                        check(all(g['window_width']==208 and g['window_height']==128 for g in gs),'Arena private window geometry differs')
                        if hero==0 and row:
                            # Absolute window-local column; text starts at x=4.
                            count=len(f'{i+1:2d}:{name} Lv99 ')
                            unique,_=old.distinct_glyph_observations(gs)
                            check(all(g['x']+g['advance']<=160 for g in unique[:count]),'Arena names cross odds column')
                            check(unique[count]['x']==160,f'Arena odds column differs: {unique[count]["x"]}')
                record={'kind':'roster','hero':hero,'rows':list(range(start,start+10)),'checks':checks,'glyphs':trace.positions,'payloads':trace.payloads,'battle_data_preserved':True}
            finally:trace.close()
            name=f'roster-{hero}-{start:03d}';session.frames(2);session.capture(name);record['screens']=[name+'.png'];write_json(session.output/(name+'.json'),record);records.append({k:v for k,v in record.items() if k not in ('glyphs','payloads')})
    return records


def entry_conditions(session,variant,font):
    c=session.core;records=[]
    # Nine independently selected warning flags, plus all together and both companions.
    for flag in range(11):
        check(c.load_raw_state(STATE.read_bytes()),'Entry rules restore');args=[0]*11
        slots=(1,2,3,4,5,6,7,8,10)
        for slot in slots:
            if flag>=9 or slot==slots[flag]:args[slot]=1
        args[9]=int(flag==10);trace=ui.InterfaceTrace(c)
        try:
            ui.native_step(session,trace,0x0807A68C,args,stop=0x0807A8F4)
            checks=check_draws(trace,font) if variant=='english' else []
            check(len(trace.payloads)==(12 if flag>=9 else 4),'Entry warning row count')
            record={'kind':'entry_conditions','flags':flag,'checks':checks,'glyphs':trace.positions,'payloads':trace.payloads}
        finally:trace.close()
        name=f'entry-conditions-{flag:02d}';session.frames(2);session.capture(name);record['screens']=[name+'.png'];write_json(session.output/(name+'.json'),record);records.append({k:v for k,v in record.items() if k not in ('glyphs','payloads')})
    return records


def popups(session,font):
    """Regression for the separately owned, previously translated headers."""
    c=session.core;records=[]
    for hero in (0,1):
        for row in (1,107,137,162,188,198):
            check(c.load_raw_state(STATE.read_bytes()),'Arena popup restore');c.memory.u16[0x020014CE]=hero
            old.write_bytes(c,0x020091D0,struct.pack('<4H',row,0,99,0));c.memory.u32[0x02009228]=9999;c.memory.u32[0x02009254]=1
            trace=ui.InterfaceTrace(c)
            try:
                ui.native_step(session,trace,0x0807993C,[0,0],stop=0x08079A36)
                checks=check_draws(trace,font);check(len(trace.payloads)==2,'Arena popup header/trait missing')
                check(trace.payloads[0]['y']==2 and trace.payloads[1]['y']==39,'Earlier popup geometry changed')
                record={'kind':'popup_regression','hero':hero,'row':row,'checks':checks,'glyphs':trace.positions,'payloads':trace.payloads}
            finally:trace.close()
            name=f'popup-{hero}-{row:03d}';session.frames(2);session.capture(name);record['screens']=[name+'.png'];write_json(session.output/(name+'.json'),record);records.append({k:v for k,v in record.items() if k not in ('glyphs','payloads')})
    return records


def contexts(session,entries,variant,report,font):
    c=session.core;records=[];byoffset={int(e['offset'],0):e for e in entries}
    check(c.load_raw_state(STATE.read_bytes()),'Numeric restore');trace=ui.InterfaceTrace(c)
    try:
        ui.native_step(session,trace,0x0808B60C,[18,1,1]);at=source(byoffset[0xC41314],variant,report)
        ui.native_step(session,trace,0x0807B604,[0,at,0,0,10,3,10,100,1],stop=0x0807B82C,overrides={0x0807B648:{'pc':0x0807B64C}})
        check(trace.positions,'Betting numeric panel missing')
        if variant=='english':
            check(trace.positions[-1]['code']==font.glyph('T')[0],'Betting unit differs')
            check(all(g['x']+max(g['advance'],10)<=g['window_width'] and g['y']+12<=g['window_height'] for g in trace.positions),'Betting unit clipped')
        record={'kind':'numeric','glyphs':trace.positions,'payloads':trace.payloads}
    finally:trace.close()
    session.frames(2);session.capture('betting-numeric');record['screens']=['betting-numeric.png'];write_json(session.output/'betting-numeric.json',record);records.append({k:v for k,v in record.items() if k not in ('glyphs','payloads')})
    for profile in ('normal','stress'):
        check(c.load_raw_state(STATE.read_bytes()),'Balance restore');trace=ui.InterfaceTrace(c);saved=12345;n=9999999 if profile=='stress' else 100
        c.memory.u32[old.NUMBER]=saved;old.write_bytes(c,0x0200A3C4,b'\xA5'*100+old.GUARD)
        try:
            ui.native_step(session,trace,0x08079F88,[],overrides={0x08079F96:{'r0':n}})
            raw=old.cstring(c,0x0200A3C4,100);check(c.memory.u32[old.NUMBER]==saved,'Balance numeric slot not restored')
            check(bytes(c.memory[0x0200A428:0x0200A430])==old.GUARD,'Arena balance overrun')
            if variant=='english':check(raw==f'Tokens: {n}\0'.encode(),'Arena balance differs')
        finally:trace.close()
        records.append({'kind':'balance','profile':profile,'formatted_hex':raw.hex(),'numeric_slot_restored':True,'guards_intact':True,'screens':[]})
    # Real species copier plus real caller's 30-byte name/level destination.
    copies=[]
    for row in range(200):
        check(c.load_raw_state(STATE.read_bytes()),'Name level restore');trace=ui.InterfaceTrace(c)
        try:
            old.write_bytes(c,NAME-8,old.GUARD+b'\xA5'*64+old.GUARD)
            ui.native_step(session,trace,0x08032D6C,[row,NAME]);name=old.cstring(c,NAME,64)
            check(bytes(c.memory[NAME-8:NAME])==old.GUARD and bytes(c.memory[NAME+64:NAME+72])==old.GUARD,'Species copy overrun')
            old.write_bytes(c,old.ACTOR-8,old.GUARD+b'\xA5'*30+old.GUARD)
            ui.native_step(session,trace,0x08096744,[old.ACTOR,c.memory.u32[0x0807984C],NAME,99]);raw=old.cstring(c,old.ACTOR,30)
            check(bytes(c.memory[old.ACTOR-8:old.ACTOR])==old.GUARD and bytes(c.memory[old.ACTOR+30:old.ACTOR+38])==old.GUARD,'Arena actor slot overrun')
            if variant=='english':check(raw==name[:-1]+b' Lv99\0','Arena name/level slot differs')
            copies.append({'row':row,'name_hex':name.hex(),'formatted_hex':raw.hex(),'bytes':len(raw),'guards_intact':True})
        finally:trace.close()
    write_json(session.output/'name-level-copies.json',{'cases':copies,'scope':'Original species getter and caller printf with every species, level 99 and guards around the 30-byte actor slot.'})
    return records,copies


def verify(variant,limit=None):
    mgba.log.silence();rom=BASELINE if variant=='baseline' else OUTPUT/f'torneko3-arena-services-{variant}.gba'
    catalog=load_json(CATALOG);report={} if variant=='baseline' else load_json(OUTPUT/f'{variant}-build.json');font=FontZero(ORIGINAL_ROM.read_bytes());codec=GameTextCodec(ORIGINAL_ROM.read_bytes())
    with Session(rom.read_bytes(),OUTPUT/'verification'/variant) as session:
        cases=[]
        for i,e in enumerate(catalog['entries'][:limit]):
            for profile in ('normal','stress') if variant=='english' else ('normal',):cases.append(entry_case(session,e,variant,report,profile,font,codec))
            if i%10==0:print(variant,i+1,'sources',flush=True)
        menu=menus(session,variant,font);rosters=roster_cases(session,variant,font);rules=entry_conditions(session,variant,font);popup=popups(session,font)
        ctx,copies=contexts(session,catalog['entries'],variant,report,font)
        screens=[s for c in cases+menu+rosters+rules+popup+ctx for s in c['screens']]
        result={'rom_sha256':digest(rom.read_bytes()),'source_sha256':digest(ORIGINAL_ROM.read_bytes()),'catalog_sha256':digest(CATALOG.read_bytes()),
            'harness_sha256':digest(Path(__file__).read_bytes()),'fixture_sha256':digest(STATE.read_bytes()),'limited':bool(limit),'cases':cases,
            'menus':menu,'rosters':rosters,'entry_conditions':rules,'popups':popup,'contexts':ctx,'name_level_copies':len(copies),'screens':screens,
            'scope':'All service pages and guarded substitutions; eight typed native menus; all 200 species in both native roster paths and all ten positions; eleven native entry-warning combinations; betting numeric unit and balance getter; 200 bounded name/level copies. Controlled states and message wait bypasses do not establish natural arena access, battle outcomes, entry consequences or password registration.'}
        write_json(session.output/'verification.json',result);print(variant,'passed',len(cases),'cases;',len(screens),'screens',flush=True)


def summarize():
    original=ORIGINAL_ROM.read_bytes();catalog=load_json(CATALOG);baseline=BASELINE.read_bytes();proofs={}
    prior=load_json(BASELINE.parent/'english-build.json')['ledger'];end=max(a['offset']+a['bytes'] for a in prior['allocations'])
    for variant in ('english','japanese','baseline'):
        path=OUTPUT/'verification'/variant/'verification.json';r=load_json(path);data=baseline if variant=='baseline' else (OUTPUT/f'torneko3-arena-services-{variant}.gba').read_bytes()
        check(r['rom_sha256']==digest(data) and r['source_sha256']==digest(original),'Arena proof ROM mismatch')
        check(r['catalog_sha256']==digest(CATALOG.read_bytes()) and r['harness_sha256']==digest((OUTPUT/'verify_arena_services.py').read_bytes()) and r['fixture_sha256']==digest(STATE.read_bytes()),'Arena proof input mismatch')
        expected={(e['id'],p) for e in catalog['entries'] for p in (('normal','stress') if variant=='english' else ('normal',))}
        check(not r['limited'] and len(r['cases'])==len(expected) and {(e['id'],e['profile']) for e in r['cases']}==expected,'Incomplete arena cases')
        check({int(x['base'],0) for x in r['menus']}=={a for a,_ in b.MENU_TABLES} and len(r['menus'])==8,'Missing arena menus')
        check(len(r['rosters'])==40 and {(x['hero'],tuple(x['rows'])) for x in r['rosters']}=={(h,tuple(range(s,s+10))) for h in (0,1) for s in range(0,200,10)},'Missing arena rosters')
        check(len(r['entry_conditions'])==11 and {x['flags'] for x in r['entry_conditions']}==set(range(11)) and r['name_level_copies']==200,'Incomplete arena specialized readers')
        check(len(r['popups'])==12 and {(x['hero'],x['row']) for x in r['popups']}=={(h,n) for h in (0,1) for n in (1,107,137,162,188,198)},'Incomplete popup regression')
        check({(x['kind'],x.get('profile')) for x in r['contexts']}=={('numeric',None),('balance','normal'),('balance','stress')},'Incomplete arena input/header readers')
        if variant!='baseline':
            report=load_json(OUTPUT/f'{variant}-build.json');check(report['previous_rom_sha256']==digest(baseline),'Arena baseline differs');ledger=report['ledger'];rebuilt=bytearray(original+b'\xff'*(len(data)-len(original)))
            for a in ledger['allocations']:
                at=a['offset'];raw=data[at:at+a['bytes']];check(digest(raw)==a['sha256'],'Arena allocation hash mismatch');rebuilt[at:at+len(raw)]=raw
            for p in ledger['patches']:
                at=p['offset'];before=bytes.fromhex(p['before']);after=bytes.fromhex(p['after']);check(rebuilt[at:at+len(before)]==before,'Arena patch source differs');rebuilt[at:at+len(after)]=after
            check(bytes(rebuilt)==data and data[0x1000000:end]==baseline[0x1000000:end],'Unexplained arena ROM changes')
            for src in ledger['protected_sources']:check(data[src['start']:src['end_exclusive']]==original[src['start']:src['end_exclusive']],'Protected arena source changed')
            for p in prior['patches']:check(data[p['offset']:p['offset']+len(bytes.fromhex(p['after']))]==bytes.fromhex(p['after']),'Earlier pointer/code patch changed')
        proofs[variant]={'rom_sha256':digest(data),'report_sha256':digest(path.read_bytes()),'cases':len(r['cases']),'screens':len(r['screens'])}
    ja=load_json(OUTPUT/'verification/japanese/verification.json');base=load_json(OUTPUT/'verification/baseline/verification.json');check(ja['screens']==base['screens'],'Arena Japanese screen sets differ')
    for name in ja['screens']:
        with Image.open(OUTPUT/'verification/japanese'/name) as x,Image.open(OUTPUT/'verification/baseline'/name) as y:check(ImageChops.difference(x.convert('RGB'),y.convert('RGB')).getbbox() is None,'Arena Japanese pixel mismatch '+name)
    result={'status':'arena_component_native_checks_passed','sources':len(catalog['entries']),'pointer_words':sum(len(e['pointer_owners']) for e in catalog['entries']),
        'english_cases':len(catalog['entries'])*2,'japanese_pixel_pairs':len(ja['screens']),'native_menus':8,'native_rosters':40,'native_entry_warning_combinations':11,
        'native_name_level_copies':200,'native_popup_regressions':12,'proofs':proofs,'complete_images_reconstructed_from_ledgers':True,'previous_patches_and_appended_bytes_preserved':True,
        'scope':'Arena component controlled reader/layout acceptance, not natural battle, registration or dungeon-entry outcomes.'}
    write_json(OUTPUT/'component-checkpoint.json',result);print(result['status'],flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('variant',choices=('english','japanese','baseline','summarize'));p.add_argument('--limit',type=int);a=p.parse_args()
    summarize() if a.variant=='summarize' else verify(a.variant,a.limit)
