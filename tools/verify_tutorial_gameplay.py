"""Native queue/history, scroll controls, initialized pointers and label copies."""
import argparse
from collections import Counter
from pathlib import Path
import mgba.log
from mgba._pylib import ffi,lib
from PIL import Image,ImageChops
from tools import verify_core_gameplay as old, verify_dungeon_interface as ui
from tools.verify_ally_services import context
from tools.build_tutorial_gameplay import CATALOG,OUTPUT,INIT_SOURCE,INIT_TABLES,encode
from tools.build_first_label import ORIGINAL_ROM,digest
from tools.translation_pipeline import FontZero,load_json
from tools.game_text import GameTextCodec
from tools.verify_expansion import Session
from tools.verify_first_label import require
from tools.verify_items import write_json

STATE=Path('build/ally-services/verification/save/world.state')
BASELINE=Path('build/ally-services/torneko3-ally-services-english.gba')
HISTORY=0x0203E000


def source_for(e,variant,report):
    return 0x08000000+(int(e['offset'],0) if variant=='baseline' else report['tutorials']['relocated'][e['id']]['offset'])


def set_values(core,font,profile):
    values=old.slots(core,font,'stress' if profile=='stress' else 'normal')
    values.update({'$i1':'Wearproof','$i2':'Bang scroll','$i3':'Magic ward'})
    if profile in ('stress','narrow'):
        ch=max((chr(i) for i in range(33,127)),key=lambda c:font.glyph(c)[1]) if profile=='stress' else 'i'
        for i in range(4):values[f'$i{i}']=ch*min(99,144//font.glyph(ch)[1])
        for i in range(3):values[f'$m{i}']=ch*min(29,120//font.glyph(ch)[1])
        values['$d0']='-2147483648'
    for i in range(4):old.write_bytes(core,old.ITEM+i*100,values[f'$i{i}'].encode().ljust(100,b'\0'))
    for i in range(3):old.write_bytes(core,old.ACTOR+i*30,values[f'$m{i}'].encode().ljust(30,b'\0'))
    core.memory.u32[old.NUMBER]=int(values['$d0'])&0xffffffff
    return values


def cold_tables(session):
    session.frames(5);tables=[]
    for a,b in INIT_TABLES:
        ram=0x02000000+a-INIT_SOURCE;raw=bytes(session.core.memory[ram:ram+b-a])
        require(raw==session.rom_data[a:b],f'Cold initialized pointer table differs: {a:08x}')
        tables.append({'rom_start':a,'rom_end':b,'ram_start':ram,'raw_hex':raw.hex()})
    return tables


def restore(session,state,tables):
    require(session.core.load_raw_state(state),'State restore failed')
    for t in tables:old.write_bytes(session.core,t['ram_start'],bytes.fromhex(t['raw_hex']))


def prepare_queue(session,trace,start=0,history_start=0):
    core=session.core;ui.native_step(session,trace,0x0805D0B4,[0])
    old.write_bytes(core,0x02007440,b'\xA5'*1280)
    old.write_bytes(core,HISTORY-8,old.GUARD+b'\xA5'*1280+old.GUARD)
    core.memory.u32[0x0200000C]=HISTORY-0x1979C
    for a in (0x02007430,0x02007432,0x02007434):core.memory.u16[a]=start
    core.memory.u32[0x02007948]=history_start
    core.memory.u8[0x02007940]=0;core.memory.u8[0x02007941]=0;core.memory.u8[0x02007942]=1


def enqueue(session,trace,source,expected=None):
    core=session.core;start=core.memory.u16[0x02007434];history=core.memory.u32[0x02007948]
    call=ui.native_step(session,trace,0x0805D3D4,[source],stop=0x0805D488)
    count=(core.memory.u16[0x02007434]-start)%16
    rows=[old.cstring(core,0x02007440+80*((start+i)%16),80) for i in range(count)]
    records=[bytes(core.memory[HISTORY+64*((history+i)%20):HISTORY+64*((history+i)%20)+64]) for i in range(count)]
    require(count>0 and core.memory.u32[0x02007948]==(history+count)%20,'Queue/history index drift')
    require(bytes(core.memory[HISTORY-8:HISTORY])==old.GUARD and bytes(core.memory[HISTORY+1280:HISTORY+1288])==old.GUARD,'History guards overwritten')
    for row,record in zip(rows,records,strict=True):
        require(record[0]==1 and record[-1]==0xA5,'History record header/guard changed')
        if expected is not None:require(record[3:3+len(row)]==row,'History truncated a displayed line')
    if expected is not None:
        wanted=expected[:-1].lstrip(b'!').replace(b'\r',b'\n').split(b'\n')
        if wanted[-1]==b'':wanted.pop()
        require(rows==[r+b'\0' for r in wanted],f'Queue lost/reflowed text: {rows!r}/{wanted!r}')
        require(all(len(r)<=60 for r in rows),'History payload overflow')
    return {'rows_hex':[r.hex() for r in rows],'history_hex':[r.hex() for r in records],
            'queue_start':start,'history_start':history,'steps':call['steps'],'guards_intact':True}


def render_queue(session,name,font,rows,english):
    """Original renderer/scroll loop; only frame yields and button waits bypassed.

    A fourth row is staged below the three visible rows before the original
    scroll callback runs. Validate its full glyphs and horizontal bounds, then
    capture the native pause and final viewport. Do not impose a false static
    y-bound on that staging row.
    """
    core=session.core;saved=context(core);main=core.memory.u32[0x0200000C]
    trace=ui.InterfaceTrace(core);screens=[];pauses=[];yields=0;chunks=[]
    def collect(t):
        require(not t.errors,str(t.errors))
        chunks.append({'glyphs':t.positions,'payloads':t.payloads})
    try:
        ui.native_step(session,trace,0x0808B60C,[18,1,1])
        core.memory.u32[0x02034DD8]=18;core.memory.u8[0x020398E8]=0;core.memory.u8[0x02002FCE]=2
        ui.registers(core,{'cpsr':255,'sp':0x03007E00,'pc':0x0805D4C8,'lr':0x08000001})
        cpu=trace.cpu;info=ffi.new('struct mDebuggerEntryInfo*')
        for steps in range(2000000):
            pc=(int(cpu.gprs[15])&0xffffffff)-(2 if cpu.cpsr.packed&32 else 4)
            if pc==0x08000000:break
            if pc in (0x08005408,0x0805D708):
                if pc==0x0805D708:
                    require(core.memory.u8[0x020398E8]==1,'Pause path lost renderer control')
                    pauses.append({'pc':hex(pc),'after_draws':sum(len(c['payloads']) for c in chunks)+len(trace.payloads)})
                    state=bytes(ffi.buffer(core.save_raw_state()));collect(trace);trace.close();trace=None
                    core.memory.u32[0x0200000C]=0;ui.registers(core,saved);session.frames(2)
                    label=f'{name}-pause{len(pauses)}';session.capture(label);screens.append(label+'.png')
                    require(core.load_raw_state(state),'Pause restore failed')
                    # A new C debugger continues the recorded trace after the
                    # paused native CPU/RAM state has been restored.
                    trace=ui.InterfaceTrace(core);cpu=trace.cpu
                else:yields+=1
                ui.registers(core,{'pc':int(cpu.gprs[14])&~1});continue
            if pc in ui.BREAKS:info.address=pc;trace.entered(trace.debugger,lib.DEBUGGER_ENTER_BREAKPOINT,info)
            core.step()
        else:raise RuntimeError(f'Queue renderer stalled: {name}/{pc:08x}')
        collect(trace)
    finally:
        if trace is not None:trace.close()
    draws=[];glyphs=[];checks=[]
    for chunk in chunks:
        for d in chunk['payloads']:
            raw=bytes.fromhex(d['raw_hex']).split(b'\0')[0]+b'\0';draws.append(raw.hex())
            gs=[g for g in chunk['glyphs'] if g['draw_serial']==d['serial']]
            if english:
                text=raw[:-1].replace(b'\x03\x1f',b'').decode('ascii')
                require([g['code'] for g in gs]==[font.glyph(c)[0] for c in text],'Queue renderer lost glyphs')
                for g,c in zip(gs,text,strict=True):
                    require(g['font']==0 and g['spacing']==0,'Queue font/spacing changed')
                    require(g['window_width']==208 and g['window_height']==40,'Queue viewport changed')
                    require(0<=g['x'] and g['x']+max(g['advance'],font.glyph(c)[2])<=208,'Queue line clipped horizontally')
                    require(g['y'] in (2,14,26,38),'Queue row/scroll position changed')
                checks.append({'glyphs':len(gs),'max_right':max((g['x']+g['advance'] for g in gs),default=0),'y':gs[0]['y'] if gs else None})
        glyphs.extend(chunk['glyphs'])
    require(draws==rows,'Original queue renderer skipped/reordered rows')
    core.memory.u32[0x0200000C]=0;ui.registers(core,saved);session.frames(2)
    label=name+'-final';session.capture(label);screens.append(label+'.png');core.memory.u32[0x0200000C]=main
    return {'screens':screens,'pauses':pauses,'frame_yields_bypassed':yields,'steps':steps,'glyphs':glyphs,'checks':checks}


def entry_case(session,state,tables,e,variant,report,font,codec,profile):
    restore(session,state,tables);core=session.core;values=set_values(core,font,profile);source=source_for(e,variant,report)
    english=variant=='english';slots_before=bytes(core.memory[old.ITEM:old.ACTOR+90]);trace=ui.InterfaceTrace(core)
    try:
        raw=old.guarded_format(session,trace,source)
        if english:
            template=encode(e,ORIGINAL_ROM.read_bytes())[0].replace(b'$w',b'\x03\x1f')
            for k,v in values.items():template=template.replace(k.encode(),v.encode())
            require(raw==template,f'Full formatter differs: {e["id"]}')
        prepare_queue(session,trace);queued=enqueue(session,trace,source,raw if english else None)
        require(bytes(core.memory[old.ITEM:old.ACTOR+90])==slots_before,'Formatting changed item/actor slots')
        formatted=[f for f in trace.formats if f['caller']=='0x0805D45C']
        require(len(formatted)==len(queued['rows_hex']),'Wrong native queue formatter count')
    finally:trace.close()
    name=f'{e["id"]}-{profile}';record={'id':e['id'],'family':e['family'],'profile':profile,'source':hex(source),'formatted_hex':raw.hex(),'queue':queued,'screens':[]}
    if profile!='narrow':
        record.update(render_queue(session,name,font,queued['rows_hex'],english))
    write_json(session.output/(name+'.json'),record)
    return {k:v for k,v in record.items() if k not in ('glyphs','payloads')}


def select_slice(core,entry,stop,values,result_reg):
    saved=context(core);cpu=ffi.cast('struct ARMCore*',core._core.cpu)
    try:
        ui.registers(core,{'cpsr':255,'sp':0x03007E00,'pc':entry,**values})
        for steps in range(100):
            pc=(int(cpu.gprs[15])&0xffffffff)-(2 if cpu.cpsr.packed&32 else 4)
            if pc==stop:return {'steps':steps,'source':hex(int(cpu.gprs[result_reg])&0xffffffff)}
            core.step()
        raise RuntimeError(f'Selection slice stalled: {entry:08x}/{pc:08x}')
    finally:ui.registers(core,saved)


def native_selection(session,state,tables,variant,report,font):
    core=session.core;records=[]
    # Execute original indexed pointer selection and bounded copy instructions.
    for family,count,entry,stop,dest in [('effect',100,0x080397D8,0x080397F6,old.ITEM+100),('object',8,0x0800AC28,0x0800AC48,None)]:
        for index in range(count):
            restore(session,state,tables);set_values(core,font,'normal')
            if family=='effect':
                core.memory.u16[0x0200D610]=index;override={'r4':old.ITEM,'r8':0};source=core.memory.u32[0x081B7590+4*index];at=dest
            else:
                selector=core.memory.u32[0x0800AC6C];core.memory.u16[selector]=index
                at=core.memory.u32[0x0800AC70];override={};source=core.memory.u32[0x02000060+4*index]
            old.write_bytes(core,at-8,old.GUARD+b'\xA5'*100+old.GUARD);trace=ui.InterfaceTrace(core)
            try:ui.native_step(session,trace,entry,[],stop=stop,overrides={entry:override})
            finally:trace.close()
            raw=old.cstring(core,at,100);require(raw==old.cstring(core,source,100),'Native indexed copy truncated')
            require(bytes(core.memory[at-8:at])==old.GUARD and bytes(core.memory[at+100:at+108])==old.GUARD,'Native label copy guards')
            record={'kind':family,'index':index,'source':hex(source),'raw_hex':raw.hex(),'guards_intact':True}
            if family=='effect':
                trace=ui.InterfaceTrace(core)
                try:
                    feedback=core.memory.u32[0x08039824];formatted=old.guarded_format(session,trace,feedback)
                    if variant=='english':
                        e=next(e for e in load_json(CATALOG)['entries'] if e['offset']=='0x001B7720')
                        expected=encode(e,ORIGINAL_ROM.read_bytes())[0].replace(b'$i0',b'Oaken club').replace(b'$i1',raw[:-1])
                        require(formatted==expected,'Native copied effect label missing from removal feedback')
                    prepare_queue(session,trace);record['removal_feedback']=enqueue(session,trace,feedback,formatted if variant=='english' else None)
                finally:trace.close()
            records.append(record)
    selections=[]
    for family,count,pc,stop,result_reg in [('tutorial',9,0x08020D26,0x08020D2E,0),('strength',3,0x08036B30,0x08036B3A,1),('cancel',25,0x0803B3DE,0x0803B3E8,1),('trap',40,0x08046228,0x08046238,0)]:
        for index in range(count):
            restore(session,state,tables)
            if family=='tutorial':override={'r3':index};expected=core.memory.u32[0x081B4AF8+4*index]
            elif family=='strength':override={'r5':index,'r6':0};expected=core.memory.u32[0x020000F8+4*index]
            elif family=='cancel':override={'r4':index};expected=core.memory.u32[0x02000104+4*index]
            else:
                override={};core.memory.u32[0x03007E1C]=index//2;core.memory.u32[0x03007E20]=index%2;expected=core.memory.u32[0x0200016C+4*index]
            result=select_slice(core,pc,stop,override,result_reg)
            require(int(result['source'],0)==expected,f'Original {family} selector chose wrong source: {index}')
            selections.append({'kind':family,'index':index,**result})
    return {'copies':records,'selections':selections}


def joined_and_wrap(session,state,tables,variant,report,font):
    entries={int(e['offset'],0):e for e in load_json(CATALOG)['entries']};records=[]
    for index,(prefix,suffix) in enumerate(((0x1B5032,0x1B507E),(0x1B5021,0x1B507E),(0x1B5032,0x1B5038),(0x1B5032,0x1B505B))):
        restore(session,state,tables);core=session.core;set_values(core,font,'normal');trace=ui.InterfaceTrace(core)
        try:
            # The last case also crosses both native ring boundaries.
            prepare_queue(session,trace,14 if index==3 else 0,19 if index==3 else 0)
            pieces=[]
            for o in (prefix,suffix):
                source=source_for(entries[o],variant,report);raw=old.guarded_format(session,trace,source)
                # Exercise the leading ! branch with a pending message-start
                # flag. It must clear that flag without printing the marker.
                core.memory.u8[0x02007942]=1
                q=enqueue(session,trace,source,raw if variant=='english' else None)
                require(bytes.fromhex(q['history_hex'][0])[2]==(1 if o==prefix else 0),'Damage continuation flag changed')
                pieces.append(q)
        finally:trace.close()
        rows=[row for q in pieces for row in q['rows_hex']]
        rendering=render_queue(session,f'joined-{index}',font,rows,variant=='english')
        record={'kind':'joined_damage','pair':[hex(prefix),hex(suffix)],'pieces':pieces,**rendering}
        write_json(session.output/f'joined-{index}.json',record);records.append({k:v for k,v in record.items() if k!='glyphs'})
    return records


def verify(variant='english',limit=None):
    mgba.log.silence();rom=BASELINE if variant=='baseline' else OUTPUT/f'torneko3-tutorial-gameplay-{variant}.gba'
    report={} if variant=='baseline' else load_json(OUTPUT/f'{variant}-build.json');font=FontZero(ORIGINAL_ROM.read_bytes());codec=GameTextCodec(ORIGINAL_ROM.read_bytes())
    cases=[];counts=Counter();out=OUTPUT/'verification'/variant
    with Session(rom.read_bytes(),out) as session:
        tables=cold_tables(session)
        for e in load_json(CATALOG)['entries']:
            if limit and counts[e['family']]>=limit:continue
            profiles=('normal','stress','narrow') if variant=='english' else ('normal',)
            for profile in profiles:cases.append(entry_case(session,STATE.read_bytes(),tables,e,variant,report,font,codec,profile))
            counts[e['family']]+=1
            if sum(counts.values())%25==0:print(variant,dict(counts),flush=True)
        selections=native_selection(session,STATE.read_bytes(),tables,variant,report,font)
        joined=joined_and_wrap(session,STATE.read_bytes(),tables,variant,report,font)
    result={'rom_sha256':digest(rom.read_bytes()),'catalog_sha256':digest(CATALOG.read_bytes()),'harness_sha256':digest(Path(__file__).read_bytes()),'fixture_state_sha256':digest(STATE.read_bytes()),
            'limited':bool(limit),'counts':dict(counts),'cold_initialized_tables':tables,'cases':cases,**selections,'joined_damage':joined,'screens':[n for c in cases+joined for n in c['screens']],
            'scope':'Original native formatter, queue/history writer, message renderer/scroll loop and indexed selection/copy slices. Disposable history backing and static-table refresh from independently verified cold boot. Scheduler, frame yields and input waits bypassed in rendering fixtures; no claim of natural item/trap/combat scenario coverage.'}
    write_json(out/'verification.json',result);print(variant,'passed',len(result['screens']),flush=True);return result


def compare():
    a=load_json(OUTPUT/'verification/japanese/verification.json');b=load_json(OUTPUT/'verification/baseline/verification.json')
    require(not a['limited'] and not b['limited'] and a['screens']==b['screens'],'Incomplete Japanese controls')
    for name in a['screens']:
        with Image.open(OUTPUT/'verification/japanese'/name) as x,Image.open(OUTPUT/'verification/baseline'/name) as y:
            require(ImageChops.difference(x.convert('RGB'),y.convert('RGB')).getbbox() is None,f'Japanese relocation changed pixels: {name}')
    return {'pixel_pairs':len(a['screens']),'japanese_sha256':a['rom_sha256'],'baseline_sha256':b['rom_sha256']}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--variant',choices=['english','japanese','baseline'],default='english');p.add_argument('--limit',type=int)
    args=p.parse_args();verify(args.variant,args.limit)
