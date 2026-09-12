"""Native system label readers, fixed fields, menus and composed log summaries."""
import argparse
import struct
from pathlib import Path
import mgba.log
from mgba._pylib import ffi,lib
from tools import build_system_labels as b, verify_core_gameplay as old
from tools import verify_dungeon_interface as ui, verify_ally_services as service
from tools import verify_keyboard_completion as keyboard
from tools.build_first_label import ORIGINAL_ROM, digest
from tools.build_name_entry import compact_name
from tools.game_text import GameTextCodec
from tools.translation_pipeline import check, load_json, FontZero
from tools.verify_expansion import Session
from tools.verify_items import write_json, distinct_glyph_observations, install_item

BASELINE=b.previous.OUTPUT/'torneko3-world-completion-english.gba'
STATE=service.STATE
RECORD=0x0203F000
LOCAL=0x03007800
SUITES={'menus':2,'summaries':65,'growth':12,'objects':6,'caps':75,'statistics':379,'details':2,'contexts':3,'messages':5}


def helper_hashes():
    return {Path(m.__file__).name:digest(Path(m.__file__).read_bytes()) for m in (ui,old,service,keyboard)}


def restore(s):check(s.core.load_raw_state(STATE.read_bytes()), 'System fixture state')


def source(e,variant,report):
    return 0x08000000+(int(e['offset'],0) if variant=='baseline' else report['system_labels']['relocated'][e['id']]['offset'])


def guard(c,at,cap):old.write_bytes(c,at-8,old.GUARD+b'\xa5'*cap+old.GUARD)


def guards(c,at,cap):check(bytes(c.memory[at-8:at])==old.GUARD and bytes(c.memory[at+cap:at+cap+8])==old.GUARD,'System buffer guards changed')


def draws(t,english):
    if not english:return []
    original=ORIGINAL_ROM.read_bytes();codec=GameTextCodec(original);font=FontZero(original);checks=[]
    for d in t.payloads:
        raw=bytes.fromhex(d['raw_hex']).split(b'\0',1)[0]+b'\0';text=old.visible(raw,codec)
        gs,_=distinct_glyph_observations([g for g in t.positions if g['draw_serial']==d['serial']])
        if not text:continue
        check([g['code'] for g in gs]==[font.glyph(ch)[0] for ch in text if ch!='\n'],'System glyph sequence differs '+repr(text))
        check(all(g['font']==0 and g['spacing']==0 for g in gs),'System font/spacing changed')
        try:ink=keyboard.ink_check(gs,original)
        except (ValueError,RuntimeError) as error:raise RuntimeError(str(error)+' '+repr(text)) from error
        check(ink['overlapping_ink_pixels']==0,'System label glyph ink overlaps '+repr(text));checks.append(ink)
    return checks


def record(s,t,name,variant,**data):
    r={'id':name,'checks':draws(t,variant=='english'),'guards_intact':True,**data}
    detail={**r,'payloads':t.payloads,'glyphs':t.positions,'formats':t.formats};t.close()
    s.frames(2);s.capture(name);r['screens']=[name+'.png'];write_json(s.output/(name+'.json'),dict(detail,screens=r['screens']));return r


def menus(s,variant):
    result=[];c=s.core
    for name,fn,args,stop,count in [('extra-menu',0x0800398C,[],0x08000000,6),('party-menu',0x08003A40,[6],0x08003ADC,4)]:
        restore(s);t=ui.InterfaceTrace(c)
        try:
            call=ui.native_step(s,t,fn,args,stop=stop);check(len(t.payloads)==count,'System menu draw count differs')
            words=range(0x0809B504,0x0809B51C,4) if name=='extra-menu' else range(0x08003C40,0x08003C50,4)
            check(all(bytes.fromhex(d['raw_hex']).startswith(old.cstring(c,c.memory.u32[w])) for d,w in zip(t.payloads,words,strict=True)),'System menu row identities differ')
            if name=='extra-menu':check(bytes(c.memory[0x02004FD8:0x02004FDE])==bytes(range(6)) and call['return_r0']==6,'Extra-mode menu identity changed')
            result.append(record(s,t,name,variant,call=call,rows=count))
        finally:t.close()
    return result


def summaries(s,variant,report,entries):
    c=s.core;result=[];by_at={int(e['offset'],0):e for e in entries}
    for row in [-1]+list(range(64)):
        restore(s);t=ui.InterfaceTrace(c);guard(c,old.DEST,64)
        try:
            if row<0:
                ui.native_step(s,t,0x08002928,[],stop=0x08002934,overrides={0x08002928:{'r6':old.DEST-0x27}})
                expected=bytes(c.memory[source(by_at[0x9B4DC],variant,report):source(by_at[0x9B4DC],variant,report)+23])
                check(bytes(c.memory[old.DEST:old.DEST+23])==expected and bytes(c.memory[old.DEST+23:old.DEST+64])==b'\xa5'*41,'Fixed 23-byte summary copy changed')
            else:
                name=ui.native_step(s,t,0x0805F33C,[row])['return_r0'];template=source(by_at[0x9B4F4],variant,report)
                ui.native_step(s,t,0x08002968,[],stop=0x08002972,overrides={0x08002968:{'r0':name,'r4':old.DEST,'r5':template}})
                check(old.cstring(c,old.DEST,64)==old.cstring(c,template)%old.cstring(c,name)[:-1],'Native entry-summary printf differs')
            guards(c,old.DEST,64);title=old.cstring(c,old.DEST,64);raw=bytearray(184)
            for slot in (0,1):
                at=slot*92;raw[at:at+8]=compact_name('WWWWWWW' if variant=='english' else 'Torneko');struct.pack_into('<hhh',raw,at+12,50,100,1);raw[at+20]=1;raw[at+23:at+23+len(title)]=title
            old.write_bytes(c,RECORD-8,old.GUARD+raw+old.GUARD);c.memory.u32[0x020105E0]=0;c.memory.u32[0x020105E4]=0
            fonts=bytes(c.memory[0x020398EC:0x020398F8]);ui.native_step(s,t,0x0806C7F8,[0,1,1]);ui.native_step(s,t,0x080853E0,[3,0,RECORD],stop=0x08085718,overrides={0x080853E0:{'sp':0x03007C00},0x080854F8:{'r8':row%2}})
            check(bytes(c.memory[RECORD:RECORD+184])==raw,'Summary fixture record changed');guards(c,RECORD,184);check(bytes(c.memory[0x020398EC:0x020398F8])==fonts,'Summary font table changed')
            check(any(title[:-1] in bytes.fromhex(d['raw_hex']).split(b'\0',1)[0] for d in t.payloads),'Summary title never drawn')
            result.append(record(s,t,f'summary-{row+1:02d}',variant,row=row,title_hex=title.hex(),record_and_guards_intact=True,font_tables_intact=True))
        finally:t.close()
    return result


def growth(s,variant):
    result=[];c=s.core
    for index in range(12):
        restore(s);t=ui.InterfaceTrace(c)
        try:
            ui.native_step(s,t,0x0806C7F8,[12,1,1]);ui.native_step(s,t,0x0808BBD8,[0]);guard(c,LOCAL+12,512);old.write_bytes(c,LOCAL+0x20C,b'\0'*512);c.memory.u32[LOCAL+0x458]=index
            ui.native_step(s,t,0x080732F8,[],stop=0x08073320,overrides={0x080732F8:{'sp':LOCAL,'r4':LOCAL+0x20C}})
            raw=old.cstring(c,LOCAL+12,512);check(raw==old.cstring(c,c.memory.u32[0x081B994C+index*4]),'Growth native selector differs');check(bytes(c.memory[LOCAL+0x20C:LOCAL+0x40C])==b'\0'*512,'Growth context changed')
            check(bytes(c.memory[LOCAL+4:LOCAL+12])==old.GUARD and c.memory.u32[LOCAL+0x458]==index,'Growth prefix/selector changed');ui.native_step(s,t,0x0808BBF8,[0]);result.append(record(s,t,f'growth-{index:02d}',variant,index=index,formatted_hex=raw.hex()))
        finally:t.close()
    return result


def objects(s,variant):
    result=[];c=s.core
    for index in range(6):
        restore(s);t=ui.InterfaceTrace(c)
        try:
            raw=struct.pack('<III',4 if index<5 else 0,0,index if index<5 else 0);old.write_bytes(c,RECORD-8,old.GUARD+raw+old.GUARD);guard(c,old.DEST,30)
            ui.native_step(s,t,0x0801B454,[RECORD,old.DEST]);guards(c,old.DEST,30);guards(c,RECORD,12);check(bytes(c.memory[RECORD:RECORD+12])==raw,'Object input changed');text=old.cstring(c,old.DEST,30)
            pointer=c.memory.u32[c.memory.u32[0x0801B494]+index*4] if index<5 else c.memory.u32[0x0801B4A8];check(text==old.cstring(c,pointer),'Object native name selection differs')
            ui.native_step(s,t,0x0806C7F8,[12,1,1]);ui.native_step(s,t,0x0808BBD8,[0]);ui.native_step(s,t,0x0808CB84,[0,0,old.DEST,0,0]);ui.native_step(s,t,0x0808BBF8,[0]);result.append(record(s,t,f'object-{index}',variant,index=index,formatted_hex=text.hex(),reader='0x0801B454',display='isolated native text preview'))
        finally:t.close()
    return result


def caps(s,variant):
    original=ORIGINAL_ROM.read_bytes();rows=[i for i in range(370) if original[0xE07F4+i*28]<=2];check(len(rows)==75,'Equipment cap rows differ');c=s.core;result=[]
    for index in rows:
        restore(s);t=ui.InterfaceTrace(c)
        try:
            ui.native_step(s,t,0x0806C7F8,[12,1,1]);ui.native_step(s,t,0x0808BBD8,[0]);guard(c,LOCAL+0x68,64)
            ui.native_step(s,t,0x0806DE00,[],stop=0x0806DE28,overrides={0x0806DE00:{'sp':LOCAL,'r6':index}});guards(c,LOCAL+0x68,64);raw=old.cstring(c,LOCAL+0x68,64);value=struct.unpack_from('<h',original,0xE07F4+index*28+4)[0]
            check(raw==old.cstring(c,c.memory.u32[0x0806DE40])%value,'Equipment cap printf differs');ui.native_step(s,t,0x0808BBF8,[0]);result.append(record(s,t,f'cap-{index:03d}',variant,item=index,value=value,formatted_hex=raw.hex()))
        finally:t.close()
    return result


def statistics(s,variant):
    c=s.core;original=ORIGINAL_ROM.read_bytes();result=[];item=0x0200A480
    cases=[(i,0,0) for i in range(370)]+[(i,n,hidden) for i in (0,54,78) for n,hidden in ((8,0),(8,4),(8,8))]
    for index,n,hidden in cases:
        restore(s);install_item(c,item,index,99 if n else 0);c.memory.u8[item+0x12]=n
        for j in range(n):c.memory.u8[item+4+j]=0x80 if j<hidden else 1
        before=bytes(c.memory[item:item+24]);t=ui.InterfaceTrace(c);guard(c,old.DEST,1024)
        try:
            power=ui.native_step(s,t,0x0807EC14,[item])['return_r0'];power=power if power<0x80000000 else power-0x100000000
            ui.native_step(s,t,0x0806E1C0,[old.DEST,item]);guards(c,old.DEST,1024);check(bytes(c.memory[item:item+24])==before,'Equipment statistic reader changed item')
            raw=old.cstring(c,old.DEST,1024);kind=original[0xE07F4+index*28];marks=old.cstring(c,c.memory.u32[0x0806E2C0])[:-1]%(n-hidden) if kind in (0,2,7) else b'';p=old.cstring(c,c.memory.u32[0x0806E2C4])[:-1]%power if kind in (0,1,2) else b''
            check(raw==p+b' '+marks+b'\0','Equipment composition differs '+str(index));ui.native_step(s,t,0x0806C7F8,[12,1,1]);ui.native_step(s,t,0x0808BBD8,[0]);ui.native_step(s,t,0x0808CB84,[0,100,old.DEST,0,0]);ui.native_step(s,t,0x0808BBF8,[0]);result.append(record(s,t,f'stats-{index:03d}-{n}-{hidden}',variant,item=index,marks=n,hidden_marks=hidden,power=power,formatted_hex=raw.hex(),item_record_unchanged=True))
        finally:t.close()
    return result


def details(s,variant,report,entries):
    c=s.core;result=[];by_at={int(e['offset'],0):e for e in entries}
    for name in ('visibility','synthesis'):
        restore(s);t=ui.InterfaceTrace(c)
        try:
            if name=='visibility':
                ui.native_step(s,t,0x0806C7F8,[12,1,1]);ui.native_step(s,t,0x0808BBD8,[0]);ui.native_step(s,t,0x0806E2CC,[source(by_at[0x1B447E],variant,report),0x0203F101],stop=0x0806E2E6)
                expected=old.cstring(c,source(by_at[0x1B447E],variant,report))
            else:
                ui.native_step(s,t,0x0806DD1A,[],stop=0x0806DD48)
                expected=old.cstring(c,source(by_at[0xC3DA2C],variant,report))
            check(len(t.payloads)==1 and bytes.fromhex(t.payloads[0]['raw_hex']).startswith(expected),'Equipment detail source differs');result.append(record(s,t,name,variant,formatted_hex=expected.hex()))
        finally:t.close()
    return result


def contexts(s,variant,report,entries):
    c=s.core;result=[]
    for e in [e for e in entries if int(e['offset'],0) in b.SMALL_CONTEXT]:
        restore(s);cfg=0x0203F080;old.write_bytes(c,cfg,b'\0'*36);c.memory.u32[cfg+32]=source(e,variant,report);guard(c,0x02008E38,5);guard(c,0x02008E50,16);t=ui.InterfaceTrace(c)
        try:
            ui.native_step(s,t,0x08070B8C,[],stop=0x08070BA8,overrides={0x08070B8C:{'r4':0x02008E50,'r1':c.memory.u32[0x08070BE8],'r5':0,'r8':cfg}});guards(c,0x02008E38,5);guards(c,0x02008E50,16);raw=old.cstring(c,0x02008E38,5)
            check(raw==old.cstring(c,source(e,variant,report)),'Adventure context truncated');ui.native_step(s,t,0x0806C7F8,[12,1,1]);ui.native_step(s,t,0x0808BBD8,[0]);formatted=[]
            for line,word in enumerate((0x08C3DB7C,0x08C3DB84)):
                text=old.guarded_format(s,t,c.memory.u32[word],cap=512);formatted.append(text.hex());ui.native_step(s,t,0x0808CB84,[0,line*14,old.DEST,0,0])
                if variant=='english':check(text==[b'Join Trip\0',b'Leave Trip\0'][line],'Adventure context command differs')
            ui.native_step(s,t,0x0808BBF8,[0]);result.append(record(s,t,e['id']+'-context',variant,context_hex=raw.hex(),formatted=formatted,display='native command composition preview'))
        finally:t.close()
    return result


def pages(s,at,name,wrapper):
    c=s.core;saved=service.context(c);records=[];formats=[];screens=[];old.write_bytes(c,0x0203F100,b'\x70\x47')
    regs={'r0':at,'r1':0x0203F101,'r2':0} if wrapper==0x0807AD68 else {'r0':at,'r1':1,'r2':0}
    ui.registers(c,{'cpsr':0xff,'sp':0x03007E00,**regs,'lr':0x08000001,'pc':wrapper})
    for page in range(40):
        t=ui.InterfaceTrace(c);t.phase=f'page-{page}';cpu=t.cpu
        try:
            info=ffi.new('struct mDebuggerEntryInfo*')
            for steps in range(3000000):
                pc=(int(cpu.gprs[15])&0xffffffff)-(2 if cpu.cpsr.packed&32 else 4)
                if pc==0x0807B044:break
                if pc==0x0807AF76:ui.registers(c,{'r4':0})
                # Confirmation wrappers choose their own native callback, whose
                # frame-yield entry is replaced only in this bounded fixture.
                if pc==0x0807ADA4:ui.registers(c,{'r1':0x0203F101})
                if pc in ui.BREAKS:info.address=pc;t.entered(t.debugger,lib.DEBUGGER_ENTER_BREAKPOINT,info)
                c.step()
            else:raise RuntimeError(f'System paged wrapper stalled {name}/{page}/{pc:08x}')
            check(not t.errors,str(t.errors));unread=int(cpu.gprs[5])&0xffffffff;final=c.memory.u8[unread]==0;formats.extend(f for f in t.formats if f['caller']=='0x0807AE04');records.append({'page':page,'final':final,'unread':hex(unread),'glyphs':t.positions});state=bytes(ffi.buffer(c.save_raw_state()))
        finally:t.close()
        ui.registers(c,saved);s.frames(2);label=f'{name}-p{page:02d}';s.capture(label);screens.append(label+'.png')
        if final:break
        check(c.load_raw_state(state),'System page continuation state');ui.registers(c,{'pc':0x0807B142})
    else:raise RuntimeError('Too many system pages')
    return {'pages':records,'formats':formats,'screens':screens}


def messages(s,variant,report,entries):
    result=[];c=s.core;font=FontZero(ORIGINAL_ROM.read_bytes());codec=GameTextCodec(ORIGINAL_ROM.read_bytes())
    for e in [e for e in entries if e['family']=='message']:
        restore(s);at=int(e['offset'],0);src=source(e,variant,report);wrapper=0x0807B208 if at==0xA6948 else 0x0807B1CC if at in (0x9B6AC,0x9B6C4) else 0x0807AD68
        t=ui.InterfaceTrace(c)
        try:
            if at in (0x9B6AC,0x9B6C4):
                selected=ui.native_step(s,t,0x080050B0,[],overrides={0x080050B6:{'r0':int(at==0x9B6AC)}})['return_r0'];check(selected==src,'Retry native selector differs')
            raw=old.guarded_format(s,t,src,cap=1000)
        finally:t.close()
        r=pages(s,src,e['id'],wrapper);check(len(r['formats'])==1 and r['formats'][0]['output_hex']==raw.hex(),'System paged payload changed');checks=[]
        if variant=='english':
            lines=raw[:-1].split(b'\n');check(len(r['pages'])==(len(lines)+2)//3,'System paged line count differs')
            for page in r['pages']:
                text=old.visible(b'\n'.join(lines[page['page']*3:page['page']*3+3])+b'\0',codec);checks.append(ui.check_glyphs(page['glyphs'],text,font))
        r.update(id=e['id'],checks=checks,wrapper=hex(wrapper),formatted_hex=raw.hex(),guards_intact=True);write_json(s.output/(e['id']+'.json'),r);result.append({k:v for k,v in r.items() if k not in ('pages','formats')})
    return result


def verify(variant,suite):
    mgba.log.silence();rom=BASELINE if variant=='baseline' else b.OUTPUT/f'torneko3-system-labels-{variant}.gba';report={} if variant=='baseline' else load_json(b.OUTPUT/f'{variant}-build.json');entries=load_json(b.OUTPUT/'catalog.json')['entries'];data=rom.read_bytes()
    with Session(data,b.OUTPUT/'verification'/variant) as s:
        words=[]
        for e in entries:
            for p in e['pointer_owners']:
                at=int(p['offset'],0);expected=source(e,variant,report);check(s.core.memory.u32[0x08000000+at]==expected,'System pointer owner differs');words.append({'word':hex(at),'source':hex(expected)})
        cases={'menus':lambda:menus(s,variant),'summaries':lambda:summaries(s,variant,report,entries),'growth':lambda:growth(s,variant),'objects':lambda:objects(s,variant),'caps':lambda:caps(s,variant),'statistics':lambda:statistics(s,variant),'details':lambda:details(s,variant,report,entries),'contexts':lambda:contexts(s,variant,report,entries),'messages':lambda:messages(s,variant,report,entries)}[suite]()
        check(len(cases)==SUITES[suite] and all(c['guards_intact'] for c in cases),'System suite incomplete')
        result={'variant':variant,'suite':suite,'rom_sha256':digest(data),'source_sha256':digest(ORIGINAL_ROM.read_bytes()),'catalog_sha256':digest((b.OUTPUT/'catalog.json').read_bytes()),'harness_sha256':digest(Path(__file__).read_bytes()),'helper_sha256':helper_hashes(),'fixture_sha256':digest(STATE.read_bytes()),'pointer_words':words,'cases':cases,'screens':[p for c in cases for p in c['screens']]};write_json(s.output/(suite+'-verification.json'),result);print(variant,suite,len(cases),'passed',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('variant',choices=('english','japanese','baseline'));p.add_argument('suite',choices=('menus','summaries','growth','objects','caps','statistics','details','contexts','messages'));a=p.parse_args();verify(a.variant,a.suite)
