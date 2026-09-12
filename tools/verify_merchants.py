"""World shop records through native printf, story continuations and menu drawing."""
import argparse
from pathlib import Path
import struct
import mgba.log
from tools import build_merchants as b
from tools import verify_core_gameplay as old
from tools import verify_dungeon_interface as ui
from tools import verify_ally_services as service
from tools import verify_arena_services as arena
from tools import verify_tutorial_gameplay as queue
from tools.verify_opening_story import STATE
from tools.build_first_label import ORIGINAL_ROM, digest
from tools.game_text import GameTextCodec, PRINTF
from tools.translation_pipeline import FontZero, load_json, check
from tools.verify_expansion import Session
from tools.verify_items import write_json

BASELINE=b.previous.OUTPUT/'torneko3-battle-completion-english.gba'
PRINTF_DEST=0x0203F800
NAMES=(0x0203F000,0x0203F080)


def restore(session,caches):
    queue.restore(session,STATE.read_bytes(),caches)


def source(e,variant,report):
    return 0x08000000+(int(e['offset'],0) if variant=='baseline' else report['merchants']['relocated'][e['id']]['offset'])


def format_case(s,t,e,variant,report,profile,font):
    c=s.core;values=old.slots(c,font,'stress' if profile in ('stress','bytes') else 'normal')
    if profile=='stress':c.memory.u16[0x020014CE]=1;values['$t']='Tipper'
    at=source(e,variant,report);source_raw=old.cstring(c,at,1024);fmts=PRINTF.findall(source_raw);printf_raw=None
    args=[];pyargs=[];number=0
    for f in fmts:
        if f==b'%s':
            name=(('i'*99) if profile=='bytes' else values[f'$i{number}']).encode();old.write_bytes(c,NAMES[number],name+b'\0');args.append(NAMES[number]);pyargs.append(name);number+=1
        else:args.append(int(values['$d0']));pyargs.append(int(values['$d0']))
    if fmts:
        old.write_bytes(c,PRINTF_DEST-8,old.GUARD+b'\xA5'*256+old.GUARD)
        ui.native_step(s,t,0x08096744,[PRINTF_DEST,at]+args);printf_raw=old.cstring(c,PRINTF_DEST,256)
        check(bytes(c.memory[PRINTF_DEST-8:PRINTF_DEST])==old.GUARD and bytes(c.memory[PRINTF_DEST+256:PRINTF_DEST+264])==old.GUARD,'Merchant printf guard overwrite')
        check(printf_raw==source_raw%tuple(pyargs),'Native merchant printf arguments differ');at=PRINTF_DEST
    raw=old.guarded_format(s,t,at,cap=1024)
    if variant=='english':
        expected=b.encode(e,ORIGINAL_ROM.read_bytes())[0]
        if fmts:expected=expected%tuple(pyargs)
        for k,v in values.items():expected=expected.replace(k.encode(),v.encode())
        check(raw==expected,'Merchant formatter changed payload '+e['id'])
    return at,raw,printf_raw


def world_pages(s,e,at,raw,name,font,english,t):
    c=s.core;root=c.memory.u32[0x03000010];structure=root+0x50;c.memory.u32[structure+8]=0
    speech=e['family']=='speech';function=0x080622D4 if speech else 0x08062294;stop=0x0806230C if speech else 0x080622C8
    call=ui.native_step(s,t,function,[at],stop=stop)
    check(c.memory.u32[structure+4]==(0x142 if speech else 0x42),'Merchant world wrapper mode differs')
    check(old.cstring(c,structure+12,1024)==raw,'Merchant native world payload differs')
    initial=len(t.positions);pages=[];screens=[];page_start=initial;last_state=None;seen_wait=False;transitions=[]
    for step in range(4096):
        state=c.memory.u32[structure+8]
        if state!=last_state:transitions.append(state);last_state=state
        if state in (6,9) and not seen_wait:
            gs=t.positions[page_start:]
            checks={}
            if english:
                page_lines=raw[:-1].decode().split('\n')[len(pages)*3:len(pages)*3+3];text='\n'.join(page_lines)
                checks=ui.check_glyphs(gs,text,font) if text.replace('\n','') else {'blank':True}
                chars=text.replace('\n','');check([g['code'] for g in gs]==[font.glyph(ch)[0] for ch in chars],'Merchant repeated/missing glyphs')
                for g,ch in zip(gs,chars,strict=True):check(g['x']+max(g['advance'],font.glyph(ch)[2])<=208,'Merchant ink outside world window')
                index=0
                for row,line in enumerate(page_lines):
                    group=gs[index:index+len(line)];index+=len(line)
                    check(all(g['y']==gs[0]['y']+row*12 for g in group),'Merchant world row drift')
            cursor=c.memory.u32[structure+0x40C];snapshot=c.save_raw_state();c.memory.u32[structure+8]=6
            count=len(t.positions);s.frames(2,t);label=f'{name}-p{len(pages):02d}';s.capture(label)
            check(c.memory.u32[structure+0x40C]==cursor and old.cstring(c,structure+12,1024)==raw,'Presentation changed merchant source/cursor')
            check(len(t.positions)==count,'Presentation rendered extra merchant glyphs');check(c.load_raw_state(snapshot),'Restore merchant presentation snapshot')
            pages.append({'page':len(pages),'state':state,'cursor':hex(cursor),'final':state==9,'glyphs':gs,'checks':checks});screens.append(label+'.png');page_start=len(t.positions);seen_wait=True
            if state==9:break
        if state not in (6,9):seen_wait=False
        ui.native_step(s,t,0x08061760,[structure],overrides={0x08061D3C:{'r0':1}} if state==6 else None)
    else:raise RuntimeError('World merchant pages did not finish '+name)
    check(pages and pages[-1]['final'],'Merchant missing final page')
    if english:check(len(pages)==(len(raw[:-1].split(b'\n'))+2)//3,'Merchant page count differs')
    check(old.cstring(c,structure+12,1024)==raw,'Native merchant scroll altered text')
    return {'wrapper':call,'mode':hex(0x142 if speech else 0x42),'pages':pages,'checks':[p['checks'] for p in pages],'screens':screens,'states':transitions}


def entry_case(s,e,variant,report,profile,caches,font):
    restore(s,caches);c=s.core;t=ui.InterfaceTrace(c);name=e['id']+'-'+profile
    try:
        at,raw,printf_raw=format_case(s,t,e,variant,report,profile,font)
        before=bytes(c.memory[old.ITEM:old.ACTOR+90])
        if profile=='bytes':result={'checks':[{'printf_capacity':256,'printf_bytes_including_nul':len(printf_raw),'world_bytes_including_nul':len(raw)}],'pages':[],'screens':[]}
        elif e['family'] in ('speech','observation'):result=world_pages(s,e,at,raw,name,font,variant=='english',t)
        else:
            t.positions.clear();ui.native_step(s,t,0x0808B60C,[18,1,1]);ui.native_step(s,t,0x0808BBD8,[0]);old.write_bytes(c,old.DEST,raw)
            ui.native_step(s,t,0x0808CB84,[0,0,old.DEST,0,0]);ui.native_step(s,t,0x0808BBF8,[0]);checks=ui.check_glyphs(t.positions,old.visible(raw,GameTextCodec(ORIGINAL_ROM.read_bytes())),font) if variant=='english' else {}
            s.frames(2);s.capture(name);result={'checks':[checks],'pages':[],'screens':[name+'.png'],'glyphs':t.positions}
        check(bytes(c.memory[old.ITEM:old.ACTOR+90])==before,'Merchant reader altered substitution slots');check(not t.errors,'Merchant trace errors')
        result.update(id=e['id'],family=e['family'],profile=profile,formatted_hex=raw.hex(),printf_hex=printf_raw.hex() if printf_raw else None,guards_intact=True,slots_intact=True)
        write_json(s.output/(name+'.json'),result)
        return {k:v for k,v in result.items() if k not in ('glyphs','pages')}|{'pages':len(result['pages'])}
    finally:t.close()


def selections(s,caches,original):
    c=s.core;results=[]
    for index in range(19):
        restore(s,caches);result=queue.select_slice(c,0x080630AA,0x080630B2,{'r0':index},7);base=b.SHOP_BASE+index*0xA4
        check(int(result['source'],0)==base+0x08000000,'Native merchant stride differs');results.append({'kind':'shop','index':index,'selected':result['source']})
    for flag in (0,1,2,3):
        restore(s,caches);result=queue.select_slice(c,0x08063B4A,0x08063B52,{'r4':flag},7);base=b.PLAYER_BASE+(0x40 if flag==2 else 0)
        check(int(result['source'],0)==base+0x08000000,'Native player-shop selection differs');results.append({'kind':'player_shop','flag':flag,'selected':result['source']})
    return results


def menu(s,caches,font,variant):
    restore(s,caches);c=s.core;t=ui.InterfaceTrace(c)
    try:
        ui.native_step(s,t,0x0807B294,[b.MENU_BASE+0x08000000,0,0,0],stop=0x0807B3B6);check(len(t.payloads)==3,'Merchant menu missing entries')
        checks=arena.check_draws(t,font) if variant=='english' else [];s.frames(2);s.capture('merchant-menu')
        result={'checks':checks,'screens':['merchant-menu.png'],'rows':3};write_json(s.output/'merchant-menu.json',dict(result,payloads=t.payloads,glyphs=t.positions));return result
    finally:t.close()


def verify(variant,limit=None):
    mgba.log.silence();original=ORIGINAL_ROM.read_bytes();catalog=load_json(b.OUTPUT/'catalog.json');font=FontZero(original)
    rom=BASELINE if variant=='baseline' else b.OUTPUT/f'torneko3-merchants-{variant}.gba';data=rom.read_bytes();report=None if variant=='baseline' else load_json(b.OUTPUT/f'{variant}-build.json');cases=[];words=[];table_checks=[]
    with Session(data,b.OUTPUT/'verification'/variant) as s:
        caches=queue.cold_tables(s)
        for e in catalog['entries']:
            target=source(e,variant,report)
            for p in e['pointer_owners']:
                word=int(p['offset'],0);check(s.core.memory.u32[0x08000000+word]==target,'Merchant pointer differs');words.append({'word':p['offset'],'source':hex(target)})
        for base,size,count,offsets in ((b.SHOP_BASE,0xA4,19,set(range(4,0x54,4))),(b.PLAYER_BASE,0x40,2,set(range(8,0x40,4))),(b.MENU_BASE,12,4,{0})):
            for index in range(count):
                at=base+size*index
                for off in range(0,size,4):
                    if off not in offsets or base==b.MENU_BASE and index==3:check(data[at+off:at+off+4]==original[at+off:at+off+4],'Merchant nontext record word changed')
            table_checks.append({'base':hex(base),'records':count,'stride':size,'nontext_words_unchanged':True})
        for index,e in enumerate(catalog['entries'][:limit] if limit else catalog['entries']):
            profiles=('normal','stress') if variant=='english' else ('normal',)
            if variant=='english' and PRINTF.findall(bytes.fromhex(e['source_hex'])):profiles+=('bytes',)
            for profile in profiles:cases.append(entry_case(s,e,variant,report,profile,caches,font))
            if (index+1)%15==0:print(variant,index+1,'merchant sources',flush=True)
        selected=selections(s,caches,original) if not limit else [];menus=[menu(s,caches,font,variant)] if not limit else []
        result={'variant':variant,'rom_sha256':digest(data),'source_sha256':digest(original),'catalog_sha256':digest((b.OUTPUT/'catalog.json').read_bytes()),'harness_sha256':digest(Path(__file__).read_bytes()),'fixture_sha256':digest(STATE.read_bytes()),
            'limited':bool(limit),'cases':cases,'pointer_words':words,'table_checks':table_checks,'selections':selected,'menus':menus,'screens':[p for r in cases+menus for p in r['screens']],
            'scope':'132 sources / 453 pointers. Native world wrappers, complete story scrolling, guarded 256-byte printf plus 1024-byte formatter, normal/wide English substitutions and separate 99-byte item-name capacity fixtures. All 19 merchant indices and four player-shop flag choices, original three-row menu and protected cash/stock/record metadata. Explicit continuation input and snapshot presentation are controlled; natural shop access, purchases, synthesis, forging, medals and proceeds/save consequences remain separate.'}
        write_json(s.output/'verification.json',result);print(variant,'passed',len(cases),'cases;',len(result['screens']),'screens',flush=True)
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('variant',choices=('english','japanese','baseline'));p.add_argument('--limit',type=int);a=p.parse_args();verify(a.variant,a.limit)
