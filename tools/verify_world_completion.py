"""Actual paged wrappers, Zoom markers/cache and native world-item observations."""
import argparse
from pathlib import Path
import mgba.log
from mgba._pylib import ffi,lib
from tools import build_world_completion as b,verify_merchants as merchants
from tools import verify_ally_services as service,verify_tutorial_gameplay as queue
from tools import verify_core_gameplay as old,verify_dungeon_interface as ui
from tools.build_first_label import ORIGINAL_ROM,digest
from tools.game_text import GameTextCodec,PRINTF
from tools.translation_pipeline import check,load_json,FontZero
from tools.verify_items import write_json
from tools.verify_expansion import Session
BASELINE=b.previous.OUTPUT/'torneko3-inscriptions-english.gba'


def restore(s,caches,family):queue.restore(s,(merchants.STATE if family=='observation' else service.STATE).read_bytes(),caches)


def source(e,variant,report):
    if variant=='baseline':return b.WAREHOUSE[int(e['offset'],0)][1] if e['family']=='warehouse' else int(e['offset'],0)+0x08000000
    return report['world_completion']['relocated'][e['id']]['offset']+0x08000000


def pages(s,at,name,font,speech):
    # Same native page-loop boundaries as the accepted service harness, entered
    # through the actual wrapper so its [0,1,speech] stack arguments execute.
    c=s.core;saved=service.context(c);records=[];formats=[];screens=[];old.write_bytes(c,0x0203F100,b'\x70\x47')
    ui.registers(c,{'cpsr':0xff,'sp':0x03007E00,'r0':at,'r1':0x0203F101,'r2':int(speech),'lr':0x08000001,'pc':0x0807AD68})
    for page in range(40):
        t=ui.InterfaceTrace(c);t.phase=f'page-{page}';cpu=t.cpu
        try:
            info=ffi.new('struct mDebuggerEntryInfo*')
            for steps in range(3000000):
                pc=(int(cpu.gprs[15])&0xffffffff)-(2 if cpu.cpsr.packed&32 else 4)
                if pc==0x0807B044:break
                if pc==0x0807AF76:ui.registers(c,{'r4':0})
                if pc in ui.BREAKS:info.address=pc;t.entered(t.debugger,lib.DEBUGGER_ENTER_BREAKPOINT,info)
                c.step()
            else:raise RuntimeError(f'World paged wrapper stalled {name}/{page}/{pc:08x}')
            check(not t.errors,str(t.errors));unread=int(cpu.gprs[5])&0xffffffff;final=c.memory.u8[unread]==0;formats.extend(f for f in t.formats if f['caller']=='0x0807AE04');records.append({'page':page,'final':final,'unread':hex(unread),'glyphs':t.positions});state=bytes(ffi.buffer(c.save_raw_state()))
        finally:t.close()
        ui.registers(c,saved);s.frames(2);label=f'{name}-p{page:02d}';s.capture(label);screens.append(label+'.png')
        if final:break
        check(c.load_raw_state(state),'World page continuation state');ui.registers(c,{'pc':0x0807B142})
    else:raise RuntimeError('Too many world pages')
    return {'pages':records,'formats':formats,'screens':screens}


def entry_case(s,caches,e,variant,report,profile,font,original):
    restore(s,caches,e['family']);c=s.core;t=ui.InterfaceTrace(c);at=source(e,variant,report);source_raw=old.cstring(c,at,1024);speech=e['family']=='warehouse' or e['family']=='zoom' and source_raw[:1]==b'*';prefix=source_raw[:1] if e['family']=='zoom' else b''
    if prefix:at+=1
    before=source_raw;printf_raw=None;values=old.slots(c,font,'stress' if profile!='normal' else 'normal');name=e['id']+'-'+profile
    try:
        raw_source=old.cstring(c,at,1024);fmts=PRINTF.findall(raw_source)
        if fmts:
            text=('i'*99 if profile=='bytes' else values['$i0']).encode();old.write_bytes(c,merchants.NAMES[0],text+b'\0');old.write_bytes(c,merchants.PRINTF_DEST-8,old.GUARD+b'\xa5'*256+old.GUARD)
            ui.native_step(s,t,0x08096744,[merchants.PRINTF_DEST,at,merchants.NAMES[0]]);printf_raw=old.cstring(c,merchants.PRINTF_DEST,256);check(printf_raw==raw_source%(text,),'World item printf changed');at=merchants.PRINTF_DEST
            check(bytes(c.memory[at-8:at])==old.GUARD and bytes(c.memory[at+256:at+264])==old.GUARD,'World item printf guard changed')
        cap=1024 if e['family']=='observation' else 1000;raw=old.guarded_format(s,t,at,cap=cap)
        if variant=='english':
            expected=b.encode(e,original)[0][len(prefix):]
            if fmts:expected=expected%(text,)
            for k,val in values.items():expected=expected.replace(k.encode(),val.encode())
            check(raw==expected,'World completion formatter changed '+e['id'])
        if profile=='bytes':result={'screens':[],'pages':[],'checks':[{'printf_bytes_including_nul':len(printf_raw),'formatted_bytes_including_nul':len(raw),'capacity':cap}]}
        elif e['family']=='observation':result=merchants.world_pages(s,e,at,raw,name,font,variant=='english',t)
        else:
            t.close();t=None;result=pages(s,at,name,font,speech);check(len(result['formats'])==1 and result['formats'][0]['output_hex']==raw.hex(),'World paged payload changed');lines=raw[:-1].split(b'\n')
            if variant=='english':
                check(len(result['pages'])==(len(lines)+2)//3,'World paged line count changed')
                for page in result['pages']:
                    text=old.visible(b'\n'.join(lines[page['page']*3:page['page']*3+3])+b'\0',GameTextCodec(original));page['checks']=ui.check_glyphs(page['glyphs'],text,font) if text else {'blank':True}
            result['checks']=[p.get('checks',{}) for p in result['pages']]
        check(old.cstring(c,source(e,variant,report),1024)==before,'Original world source changed')
        result.update(id=e['id'],family=e['family'],profile=profile,formatted_hex=raw.hex(),printf_hex=printf_raw.hex() if printf_raw else None,guards_intact=True,speech=speech,protocol_prefix=prefix.decode());write_json(s.output/(name+'.json'),result)
        return {k:val for k,val in result.items() if k not in ('pages','formats')}|{'pages':len(result['pages'])}
    finally:
        if t is not None:t.close()


def selectors(s,caches,variant,report,entries):
    results=[];by_at={int(e['offset'],0):e for e in entries};c=s.core
    targets=[(1,0,0,0x86F3BC),(0,0,1,0x86F3D0),(0,0,0,0x86F374)]+[(0,i,0,int.from_bytes(ORIGINAL_ROM.read_bytes()[b.ZOOM_CACHE[0]+i*4:b.ZOOM_CACHE[0]+i*4+4],'little')-0x08000000) for i in range(1,11)]
    for mask,phase,explored,at in targets:
        restore(s,caches,'zoom');t=ui.InterfaceTrace(c)
        try:r=ui.native_step(s,t,0x080604A8,[],overrides={0x080604B0:{'r0':mask},0x080604BA:{'r0':phase},0x080604D6:{'r0':explored}})
        finally:t.close()
        wanted=source(by_at[at],variant,report);check(r['return_r0']==wanted,'Zoom selector source differs');raw=old.cstring(c,wanted,1024);check(raw[:1] in (b'-',b'*'),'Zoom selector prefix differs')
        body=queue_slice(c,0x08076648,0x08076658,{'r0':wanted,'r9':0x0203F101},0);speech=queue_slice(c,0x08076648,0x08076658,{'r0':wanted,'r9':0x0203F101},2);check(body==wanted+1 and speech==int(raw[:1]==b'*'),'Native Zoom marker/speech handoff changed');results.append({'mask':mask,'phase':phase,'explored':explored,'source':hex(wanted),'body':hex(body),'speech':speech})
    warehouses=[]
    for at,(word,ram) in b.WAREHOUSE.items():
        restore(s,caches,'warehouse');start,stop=(0x08073940,0x08073946) if word==0x7394C else (0x0807397A,0x08073980);got=queue_slice(c,start,stop,{'r5':0x0203F101},0);check(got==source(by_at[at],variant,report),'Warehouse inline pointer reader differs');warehouses.append({'source_offset':hex(at),'literal':hex(word),'selected':hex(got)})
    return results,warehouses


def queue_slice(c,start,stop,values,reg):
    from tools.verify_tutorial_gameplay import select_slice
    return int(select_slice(c,start,stop,values,reg)['source'],0)


def verify(variant,limit=None):
    mgba.log.silence();original=ORIGINAL_ROM.read_bytes();rom=BASELINE if variant=='baseline' else b.OUTPUT/f'torneko3-world-completion-{variant}.gba';data=rom.read_bytes();report=None if variant=='baseline' else load_json(b.OUTPUT/f'{variant}-build.json');entries=load_json(b.OUTPUT/'catalog.json')['entries'];font=FontZero(original);cases=[];words=[]
    with Session(data,b.OUTPUT/'verification'/variant) as s:
        caches=queue.cold_tables(s);a,z=b.ZOOM_CACHE;raw=bytes(s.core.memory[0x02000400:0x02000400+z-a]);check(raw==data[a:z],'Cold Zoom cache differs');caches.append({'rom_start':a,'rom_end':z,'ram_start':0x02000400,'raw_hex':raw.hex()})
        for at,(_,ram) in b.WAREHOUSE.items():
            e=next(e for e in entries if int(e['offset'],0)==at);raw=bytes.fromhex(e['source_hex']);check(bytes(s.core.memory[ram:ram+len(raw)])==raw,'Cold inline warehouse text differs');caches.append({'rom_start':at,'rom_end':at+len(raw),'ram_start':ram,'raw_hex':raw.hex()})
        for e in entries:
            for p in e['pointer_owners']:
                word=int(p['offset'],0);wanted=int(p['expected_address'],0) if variant=='baseline' else source(e,variant,report);check(s.core.memory.u32[word+0x08000000]==wanted,'World completion pointer differs');words.append({'word':p['offset'],'target':hex(wanted)})
        for e in entries[:limit] if limit else entries:
            profiles=('normal','stress') if variant=='english' else ('normal',)
            if variant=='english' and PRINTF.findall(bytes.fromhex(e['source_hex'])):profiles+=('bytes',)
            for profile in profiles:cases.append(entry_case(s,caches,e,variant,report,profile,font,original))
            print(variant,e['id'],'passed',flush=True)
        selected,warehouses=([],[]) if limit else selectors(s,caches,variant,report,entries)
        result={'variant':variant,'rom_sha256':digest(data),'source_sha256':digest(original),'catalog_sha256':digest((b.OUTPUT/'catalog.json').read_bytes()),'harness_sha256':digest(Path(__file__).read_bytes()),'fixture_sha256':{'paged':digest(service.STATE.read_bytes()),'world':digest(merchants.STATE.read_bytes())},'limited':bool(limit),'cases':cases,'pointer_words':words,'zoom_selectors':selected,'warehouse_selectors':warehouses,'screens':[p for e in cases for p in e['screens']],'scope':'19 remaining world sources / 21 pointers. Actual 0807AD68 paged-wrapper flags, Zoom marker removal and 13 selectors, cold initialized Zoom cache and inline warehouse strings, two warehouse literal readers, native observation scrolling and guarded 256-byte item printf / 1024-byte world buffers. State/selector overrides and callbacks are controlled fixtures; natural travel, item grants, warehouse operations and persistence are separate.'};write_json(s.output/'verification.json',result);print(variant,len(cases),'world completion cases passed',flush=True)
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('variant',choices=('english','japanese','baseline'));p.add_argument('--limit',type=int);a=p.parse_args();verify(a.variant,a.limit)
