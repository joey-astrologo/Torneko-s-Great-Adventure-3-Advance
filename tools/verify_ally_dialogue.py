"""Native ally selector/pages and complete prior-message history regression."""
import argparse
from collections import Counter
from pathlib import Path
import mgba.log
from mgba._pylib import ffi,lib
from PIL import Image,ImageChops
from tools import verify_tutorial_gameplay as queue
from tools import verify_core_gameplay as old,verify_dungeon_interface as ui
from tools.verify_ally_services import context
from tools.build_ally_dialogue import CATALOG,OUTPUT,TABLE,encode
from tools.build_first_label import ORIGINAL_ROM,digest
from tools.translation_pipeline import FontZero,load_json
from tools.verify_expansion import Session
from tools.verify_first_label import require
from tools.verify_items import write_json

BASELINE=Path('build/tutorial-gameplay/torneko3-tutorial-gameplay-english.gba')
STATE=Path('build/tutorial-gameplay/verification/save/world.state')


def set_values(core,font,profile,species=None):
    values=queue.set_values(core,font,profile)
    if profile=='normal' and species is not None:
        for i in (0,1):
            values[f'$m{i}']=species;old.write_bytes(core,old.ACTOR+30*i,species.encode().ljust(30,b'\0'))
    return values


def source_for(e,variant,report):
    return 0x08000000+(int(e['offset'],0) if variant=='baseline' else report['dialogue']['relocated'][e['id']]['offset'])


def dialogue_pages(session,source,name,font,expected=None):
    """Use the exact (0,1,1) stack flags passed by the ally dialogue wrapper.

    Only the frame-yield callback, glyph delay and input wait are bypassed.
    Original page setup, formatter, draw and continuation instructions run.
    """
    core=session.core;saved=context(core);pages=[];screens=[];formats=[]
    old.write_bytes(core,0x0203F100,b'\x70\x47')
    ui.registers(core,{'cpsr':255,'sp':0x03007E00,'r0':source,'r1':0x0203F101,'r2':0,'r3':0,'lr':0x08000001,'pc':0x0807ADA4})
    for i,x in enumerate((0,1,1)):core.memory.u32[0x03007E00+4*i]=x
    for page in range(8):
        trace=ui.InterfaceTrace(core);cpu=trace.cpu
        try:
            info=ffi.new('struct mDebuggerEntryInfo*')
            for steps in range(3000000):
                pc=(int(cpu.gprs[15])&0xffffffff)-(2 if cpu.cpsr.packed&32 else 4)
                if pc==0x0807B044:break
                if pc==0x0807AF76:ui.registers(core,{'r4':0})
                if pc in ui.BREAKS:info.address=pc;trace.entered(trace.debugger,lib.DEBUGGER_ENTER_BREAKPOINT,info)
                core.step()
            else:raise RuntimeError(f'Dialogue page stalled: {name}/{pc:08x}')
            require(not trace.errors,str(trace.errors));unread=int(cpu.gprs[5])&0xffffffff;final=core.memory.u8[unread]==0
            checks=ui.check_glyphs(trace.positions,'\n'.join(expected.split('\n')[3*page:3*page+3]),font) if expected is not None else {}
            formats.extend(f for f in trace.formats if f['caller']=='0x0807AE04')
            pages.append({'page':page,'final':final,'steps':steps,'checks':checks,'glyphs':trace.positions})
            state=bytes(ffi.buffer(core.save_raw_state()))
        finally:trace.close()
        ui.registers(core,saved);session.frames(2);label=f'{name}-p{page:02d}';session.capture(label);screens.append(label+'.png')
        if final:break
        require(core.load_raw_state(state),'Page state restore failed');ui.registers(core,{'pc':0x0807B142})
    else:raise RuntimeError('Too many dialogue pages')
    if expected is not None:require(len(pages)==(len(expected.split('\n'))+2)//3,'Native page count differs')
    return {'pages':pages,'screens':screens,'formats':formats,'native_stack_flags':[0,1,1]}


def dialogue_case(session,state,tables,e,variant,report,font,profile,species):
    queue.restore(session,state,tables);core=session.core;values=set_values(core,font,profile,species);source=source_for(e,variant,report)
    rec=0x0203F000;old.write_bytes(core,rec,b'\0'*0x150);core.memory.u16[rec+8]=e['row']
    selected=queue.select_slice(core,0x0803C3C8,0x0803C3E2,{'r0':rec,'r1':e['field']},6)
    require(int(selected['source'],0)==source,'Original ally table selector chose wrong pointer')
    before=bytes(core.memory[old.ACTOR:old.ACTOR+60]);trace=ui.InterfaceTrace(core)
    try:raw=old.guarded_format(session,trace,source)
    finally:trace.close()
    if variant=='english':
        expected=encode(e,ORIGINAL_ROM.read_bytes())[0]
        for k,v in values.items():expected=expected.replace(k.encode(),v.encode())
        require(raw==expected,'Ally dialogue formatter lost text or actor slots')
    require(bytes(core.memory[old.ACTOR:old.ACTOR+60])==before,'Formatter changed adjacent actor slots')
    name=f'{e["id"]}-{profile}';result={'id':e['id'],'row':e['row'],'field':e['field'],'profile':profile,'source':hex(source),'selector':selected,'formatted_hex':raw.hex(),'guards_intact':True,'screens':[]}
    if profile!='narrow':
        result.update(dialogue_pages(session,source,name,font,raw[:-1].decode('ascii') if variant=='english' else None))
        require(len(result['formats'])==1 and result['formats'][0]['output_hex']==raw.hex(),'Ally paged reader output differs')
    write_json(session.output/(name+'.json'),result)
    return {k:v for k,v in result.items() if k not in ('pages','formats')}|{'pages':len(result.get('pages',[]))}


def history_cases(session,state,tables,report,font):
    cases=[]
    for e in report['history']['messages']:
        for profile in ('normal','stress','narrow'):
            queue.restore(session,state,tables);core=session.core;values=set_values(core,font,profile)
            source=0x08000000+e['relocated'];trace=ui.InterfaceTrace(core)
            try:
                raw=old.guarded_format(session,trace,source);expected=bytes.fromhex(e['raw_hex'])
                for k,v in values.items():expected=expected.replace(k.encode(),v.encode())
                require(raw==expected,f'History formatter differs: {e["id"]}/{profile}')
                queue.prepare_queue(session,trace);queued=queue.enqueue(session,trace,source,raw)
            finally:trace.close()
            name=f'history-{e["id"]}-{profile}';case={'id':e['id'],'profile':profile,'changed':e['changed'],'queue':queued,'screens':[]}
            if e['changed'] and profile!='narrow':case.update(queue.render_queue(session,name,font,queued['rows_hex'],True))
            write_json(session.output/(name+'.json'),case);cases.append({k:v for k,v in case.items() if k!='glyphs'})
    return cases


def old_history_reproduction(report,font):
    """Demonstrate the old limit failure with valid synthetic narrow slots.

    This establishes native truncation under that bounded stress input, not
    natural reachability of a particular generated/custom item name.
    """
    out=OUTPUT/'verification/history-before';records=[]
    with Session(BASELINE.read_bytes(),out) as session:
        tables=queue.cold_tables(session)
        for e in report['history']['messages']:
            if not e['changed']:continue
            queue.restore(session,STATE.read_bytes(),tables);set_values(session.core,font,'narrow');trace=ui.InterfaceTrace(session.core)
            try:
                source=0x08000000+e['relocated'];require(old.cstring(session.core,source)==bytes.fromhex(e['old_raw_hex']),'Baseline allocation moved unexpectedly')
                queue.prepare_queue(session,trace);queued=queue.enqueue(session,trace,source)
            finally:trace.close()
            lost=[i for i,(row,hist) in enumerate(zip(queued['rows_hex'],queued['history_hex'],strict=True)) if bytes.fromhex(row)!=bytes.fromhex(hist)[3:].split(b'\0')[0]+b'\0']
            require(lost,f'Expected old history truncation not reproduced: {e["id"]}')
            records.append({'id':e['id'],'truncated_rows':lost,'queue':queued})
    result={'rom_sha256':digest(BASELINE.read_bytes()),'fixed_rom_sha256':report['rom_sha256'],'fixture_state_sha256':digest(STATE.read_bytes()),'cases':records,'scope':'Native before/fixed comparison with maximum narrow item names; no assertion of natural name reachability.'}
    write_json(out/'verification.json',result);return result


def health_selectors(session,state,tables):
    results=[];core=session.core;cpu=ffi.cast('struct ARMCore*',core._core.cpu)
    for row in range(1,51):
        for hp in (39,40,79,80):
            for random_result in (0,99):
                queue.restore(session,state,tables);saved=context(core);rec=0x0203F000
                old.write_bytes(core,rec,b'\0'*0x150);core.memory.u16[rec+8]=row
                core.memory.u32[rec+0x54]=hp;core.memory.u32[rec+0x58]=100
                ui.registers(core,{'cpsr':255,'sp':0x03007E00,'pc':0x0803C2BC,'r0':rec,'lr':0x08000001});random_calls=0
                try:
                    for steps in range(10000):
                        pc=(int(cpu.gprs[15])&0xffffffff)-(2 if cpu.cpsr.packed&32 else 4)
                        if pc==0x0803C34A:break
                        if pc==0x0808DEC0:
                            ui.registers(core,{'r0':random_result,'pc':int(cpu.gprs[14])&~1});random_calls+=1;continue
                        core.step()
                    else:raise RuntimeError(f'Health selector stalled: {row}/{pc:08x}')
                    selected=int(cpu.gprs[6])&0xffffffff
                    expected=(4 if hp<40 else 2 if hp<80 else 0)+(1 if random_result<50 else 0)
                    require(random_calls==1 and selected==expected,'Original HP dialogue band/choice differs')
                    results.append({'row':row,'hp':hp,'max_hp':100,'controlled_random_result':random_result,'response':selected,'steps':steps})
                finally:ui.registers(core,saved)
    return results


def verify(variant='english',limit=None):
    mgba.log.silence();rom=BASELINE if variant=='baseline' else OUTPUT/f'torneko3-ally-dialogue-{variant}.gba';folder=OUTPUT/'verification'/variant
    report={} if variant=='baseline' else load_json(OUTPUT/f'{variant}-build.json');font=FontZero(ORIGINAL_ROM.read_bytes());catalog=load_json(CATALOG)
    names={e['row']:e['english'] for e in load_json('translations/enemies.json')['entries'] if e['family']=='name'};cases=[]
    with Session(rom.read_bytes(),folder) as session:
        tables=queue.cold_tables(session)
        for index,e in enumerate(catalog['entries']):
            if limit and index>=limit:break
            for profile in ('normal','stress','narrow') if variant=='english' else ('normal',):
                cases.append(dialogue_case(session,STATE.read_bytes(),tables,e,variant,report,font,profile,names[e['row']]))
            if (index+1)%40==0:print(variant,index+1,'dialogue entries',flush=True)
        history=history_cases(session,STATE.read_bytes(),tables,report,font) if variant=='english' and not limit else []
        health=health_selectors(session,STATE.read_bytes(),tables) if not limit else []
    result={'rom_sha256':digest(rom.read_bytes()),'catalog_sha256':digest(CATALOG.read_bytes()),'harness_sha256':digest(Path(__file__).read_bytes()),
            'page_helper_sha256':digest((Path(__file__).parent/'verify_tutorial_gameplay.py').read_bytes()),'fixture_state_sha256':digest(STATE.read_bytes()),
            'limited':bool(limit),'cases':cases,'cold_initialized_tables':tables,'history_cases':history,'health_selectors':health,
            'screens':[name for c in cases+history for name in c['screens']],
            'scope':'Native 80-byte ally record selector, guarded formatter and paged engine with original ally stack flags. Supplied species/speaker slots, glyph delays/input waits/frame yield bypassed. Full earlier core/help history stress coverage is separate from natural conversations and name reachability.'}
    write_json(folder/'verification.json',result)
    if variant=='english' and not limit:old_history_reproduction(report,font)
    print(variant,'passed',len(cases),len(history),'cases',flush=True);return result


def compare():
    ja=load_json(OUTPUT/'verification/japanese/verification.json');base=load_json(OUTPUT/'verification/baseline/verification.json')
    require(not ja['limited'] and not base['limited'] and ja['screens']==base['screens'],'Incomplete Japanese controls')
    for name in ja['screens']:
        with Image.open(OUTPUT/'verification/japanese'/name) as x,Image.open(OUTPUT/'verification/baseline'/name) as y:
            require(ImageChops.difference(x.convert('RGB'),y.convert('RGB')).getbbox() is None,f'Ally Japanese relocation changed pixels: {name}')
    return len(ja['screens'])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--variant',choices=['english','japanese','baseline'],default='english');p.add_argument('--limit',type=int)
    args=p.parse_args();verify(args.variant,args.limit)
