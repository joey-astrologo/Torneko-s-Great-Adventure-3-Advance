"""Native paged services, original menu readers and bounded formatting fixtures."""
import argparse
from collections import Counter
from pathlib import Path
import struct
import mgba.log
from mgba._pylib import ffi,lib
from PIL import Image,ImageChops
from tools import verify_core_gameplay as old
from tools import verify_dungeon_interface as ui
from tools.verify_gameplay_help import values_for
from tools.build_ally_services import CATALOG,OUTPUT,encode,MENU_TABLES,SMALL
from tools.build_first_label import ORIGINAL_ROM,digest
from tools.game_text import GameTextCodec,PRINTF
from tools.translation_pipeline import FontZero,load_json
from tools.verify_expansion import Session
from tools.verify_first_label import require
from tools.verify_items import write_json

STATE=Path('build/gameplay-help/verification/save/world.state')
BASELINE=Path('build/gameplay-help/torneko3-gameplay-help-english.gba')


def source_for(e,variant,report):
    return 0x08000000+(int(e['offset'],0) if variant=='baseline' else report['services']['relocated'][e['id']]['offset'])


def set_values(core,font,profile):
    values=values_for(core,font,profile)
    values['$j2']='Bout' if profile=='stress' else 'Trip'
    old.write_bytes(core,0x02008E38,values['$j2'].encode()+b'\0')
    return values


def expected_raw(entry,values):
    raw=encode(entry,ORIGINAL_ROM.read_bytes())[0]
    for k,v in values.items():raw=raw.replace(k.encode(),v.encode())
    return raw


def context(core):
    cpu=ffi.cast('struct ARMCore*',core._core.cpu);cpsr=int(cpu.cpsr.packed)
    return {'cpsr':cpsr,**{f'r{i}':int(cpu.gprs[i])&0xffffffff for i in range(15)},
            'pc':(int(cpu.gprs[15])&0xffffffff)-(2 if cpsr&32 else 4)}


def pages(session,source,name,font,expected=None):
    """Keep the native PC/stack/source cursor across actual three-line pages.

    Only glyph delay and the button wait are bypassed. A fixture BX LR
    callback replaces the frame-yield callback; the original 18-step page
    redraw loop executes, including its live RAM draw callback. Each
    continuation executes original page setup, line stepping and rendering.
    Frame presentation uses the saved idle CPU, then restores the native state.
    """
    core=session.core;saved=context(core);records=[];formats=[];screens=[]
    old.write_bytes(core,0x0203F100,b'\x70\x47')
    ui.registers(core,{'cpsr':0xff,'sp':0x03007E00,'r0':source,'r1':0x0203F101,'r2':0,'r3':0,'lr':0x08000001,'pc':0x0807ADA4})
    for i in range(3):core.memory.u32[0x03007E00+4*i]=0
    for page in range(40):
        trace=ui.InterfaceTrace(core);trace.phase=f'page-{page}';cpu=trace.cpu
        try:
            info=ffi.new('struct mDebuggerEntryInfo*')
            for steps in range(3000000):
                pc=(int(cpu.gprs[15])&0xffffffff)-(2 if cpu.cpsr.packed&32 else 4)
                if pc==0x0807B044:break
                if pc==0x0807AF76:ui.registers(core,{'r4':0})
                if pc in ui.BREAKS:
                    info.address=pc;trace.entered(trace.debugger,lib.DEBUGGER_ENTER_BREAKPOINT,info)
                core.step()
            else:raise RuntimeError(f'Page stalled {name}/{page}/{pc:08x}')
            require(not trace.errors,str(trace.errors))
            unread=int(cpu.gprs[5])&0xffffffff;final=core.memory.u8[unread]==0
            check={}
            if expected is not None:
                lines=expected.split('\n')[page*3:page*3+3];text='\n'.join(lines)
                check=ui.check_glyphs(trace.positions,text,font) if text.replace('\n','') else {'blank':True}
            formats.extend(f for f in trace.formats if f['caller']=='0x0807AE04')
            records.append({'page':page,'final':final,'unread':hex(unread),'steps':steps,'checks':check,'glyphs':trace.positions})
            state=bytes(ffi.buffer(core.save_raw_state()))
        finally:trace.close()
        ui.registers(core,saved);session.frames(2);label=f'{name}-p{page:02d}';session.capture(label);screens.append(label+'.png')
        if final:break
        require(core.load_raw_state(state),'Page state restore failed');ui.registers(core,{'pc':0x0807B142})
    else:raise RuntimeError('Too many pages')
    if expected is not None:require(len(records)==(len(expected.split('\n'))+2)//3,'Incorrect native page count')
    return {'pages':records,'formats':formats,'screens':screens}


def entry_case(session,state,e,variant,report,font,codec,profile):
    core=session.core;require(core.load_raw_state(state),'Restore failed');values=set_values(core,font,profile)
    source=source_for(e,variant,report);family=e['family'];english=variant=='english';trace=ui.InterfaceTrace(core)
    try:
        raw_source=old.cstring(core,source);cap=encode(e,ORIGINAL_ROM.read_bytes())[1]['capacity']
        if PRINTF.findall(raw_source):
            numbers=[(-2147483648 if f==b'%7d' else 999) if profile=='stress' else 7 for f in PRINTF.findall(raw_source)]
            old.write_bytes(core,old.DEST-8,old.GUARD+b'\xA5'*cap+old.GUARD)
            ui.native_step(session,trace,0x08096744,[old.DEST,source]+numbers)
            raw=old.cstring(core,old.DEST,cap)
            require(bytes(core.memory[old.DEST-8:old.DEST])==old.GUARD and bytes(core.memory[old.DEST+cap:old.DEST+cap+8])==old.GUARD,'Printf guards overwritten')
            expected=expected_raw(e,values)%tuple(numbers) if english else None
        else:
            raw=old.guarded_format(session,trace,source,cap=cap)
            expected=expected_raw(e,values) if english else None
        if english:require(raw==expected,f'Formatted payload differs: {e["id"]}: {raw!r}/{expected!r}')
        visible=old.visible(raw,codec)
        if family!='message':
            ui.native_step(session,trace,0x0808B60C,[18,1,1]);ui.native_step(session,trace,0x0808BBD8,[0])
            old.write_bytes(core,old.DEST,raw)
            ui.native_step(session,trace,0x0808CB84,[0,0,old.DEST,0,13]);ui.native_step(session,trace,0x0808BBF8,[0])
            check=ui.check_glyphs(trace.positions,visible,font) if english else {}
            if english and family=='stats':
                require(check['max_right']<=188,'Ally stats exceed actual detail width')
                for boundary in (46,104):require(all(g['x']+g['advance']<=boundary for g in trace.positions if g['x']<boundary),'Stats overlap')
            record={'checks':check,'glyphs':trace.positions}
    finally:trace.close()
    name=f'{e["id"]}-{profile}'
    if family=='message':
        record=pages(session,source,name,font,raw[:-1].decode('ascii') if english else None)
        require(len(record['formats'])==1 and record['formats'][0]['output_hex']==raw.hex(),'Service reader changed text')
    else:
        session.frames(2);session.capture(name);record['screens']=[name+'.png']
    record.update({'id':e['id'],'family':family,'profile':profile,'source':hex(source),'formatted_hex':raw.hex(),'guarded_capacity':cap})
    write_json(session.output/(name+'.json'),record)
    return {k:v for k,v in record.items() if k not in ('glyphs','formats','pages') } | {'pages':len(record.get('pages',[]))}


def menus(session,state,entries,variant,report,font):
    core=session.core;records=[];english=variant=='english'
    for group in range(12):
        for mode in (0,1):
            require(core.load_raw_state(state),'Restore failed');set_values(core,font,'normal' if mode==0 else 'stress')
            trace=ui.InterfaceTrace(core)
            try:
                base=0x08C3DB78+group*56
                ui.native_step(session,trace,0x08096654,[0x020090C0,base,56])
                result=ui.native_step(session,trace,0x0807191C,[mode])
                sources=[core.memory.u32[base+8*i+4] for i in range(7) if core.memory.u32[base+8*i]]
                formats=[f for f in trace.formats if f['caller']=='0x080719C8']
                require([int(f['source'],0) for f in formats]==sources,'Ally table stride/reader changed')
                checks=[]
                if english:
                    for draw,f in zip(trace.payloads,formats,strict=True):
                        raw=bytes.fromhex(f['output_hex']);checks.append(old.command_ink_check([g for g in trace.positions if g['draw_serial']==draw['serial']],old.visible(raw,GameTextCodec(ORIGINAL_ROM.read_bytes())),font))
                record={'kind':'ally','group':group,'mode':mode,'sources':list(map(hex,sources)),'checks':checks,'native':result,'formats':formats,'glyphs':trace.positions}
            finally:trace.close()
            name=f'ally-menu-{group:02d}-{mode}';session.frames(2);session.capture(name);record['screens']=[name+'.png'];write_json(session.output/(name+'.json'),record);records.append(record)
    for base,count in MENU_TABLES:
        require(core.load_raw_state(state),'Restore failed');trace=ui.InterfaceTrace(core)
        try:
            ui.native_step(session,trace,0x0807B294,[0x08000000+base,0,0,0],stop=0x0807B3B6)
            require(len(trace.payloads)==count,'Service menu row count changed')
            checks=[]
            if english:
                for draw in trace.payloads:
                    checks.append(old.command_ink_check([g for g in trace.positions if g['draw_serial']==draw['serial']],old.visible(bytes.fromhex(draw['raw_hex']),GameTextCodec(ORIGINAL_ROM.read_bytes())),font))
            record={'kind':'service','base':hex(base),'rows':count,'checks':checks,'glyphs':trace.positions,'payloads':trace.payloads}
        finally:trace.close()
        name=f'menu-{base:08x}';session.frames(2);session.capture(name);record['screens']=[name+'.png'];write_json(session.output/(name+'.json'),record);records.append(record)
    # Execute the actual manager's bounded title/context copies before its
    # ally-record traversal. Supply only its 36-byte configuration in scratch.
    copies=[]
    for o in (0xC3DF8C,0xC411B0,0xC41ACC):
        require(core.load_raw_state(state),'Restore failed');e=next(e for e in entries if int(e['offset'],0)==o)
        cfg=0x0203F080;old.write_bytes(core,cfg,b'\0'*36);core.memory.u32[cfg+32]=source_for(e,variant,report)
        old.write_bytes(core,0x02008E30,old.GUARD+b'\xA5'*5+old.GUARD)
        old.write_bytes(core,0x02008E48,old.GUARD+b'\xA5'*16+old.GUARD)
        trace=ui.InterfaceTrace(core)
        try:ui.native_step(session,trace,0x08070B8C,[],stop=0x08070BA8,overrides={0x08070B8C:{'r4':0x02008E50,'r1':core.memory.u32[0x08070BE8],'r5':0,'r8':cfg}})
        finally:trace.close()
        raw=old.cstring(core,0x02008E38,5);title=old.cstring(core,0x02008E50,16)
        require(bytes(core.memory[0x02008E30:0x02008E38])==old.GUARD and bytes(core.memory[0x02008E3D:0x02008E45])==old.GUARD,'Context copy guards')
        require(bytes(core.memory[0x02008E48:0x02008E50])==old.GUARD and bytes(core.memory[0x02008E60:0x02008E68])==old.GUARD,'Title copy guards')
        if english:require(raw==(e['display']+'\0').encode() and title==b'Ally list\0','Context/title copy truncated')
        copies.append({'source':hex(source_for(e,variant,report)),'raw_hex':raw.hex(),'title_hex':title.hex(),'guards_intact':True})
    return records,copies


def verify(variant='english',limit=None):
    mgba.log.silence();rom=BASELINE if variant=='baseline' else OUTPUT/f'torneko3-ally-services-{variant}.gba';folder=OUTPUT/'verification'/variant
    report={} if variant=='baseline' else load_json(OUTPUT/f'{variant}-build.json');catalog=load_json(CATALOG);original=ORIGINAL_ROM.read_bytes();font=FontZero(original);codec=GameTextCodec(original)
    with Session(rom.read_bytes(),folder) as session:
        cases=[];counts=Counter()
        for e in catalog['entries']:
            if limit and counts[e['family']]>=limit:continue
            for profile in ('normal','stress') if variant=='english' else ('normal',):
                cases.append(entry_case(session,STATE.read_bytes(),e,variant,report,font,codec,profile))
            counts[e['family']]+=1
            if len(cases)%20<2:print(variant,dict(counts),flush=True)
        menu,copies=menus(session,STATE.read_bytes(),catalog['entries'],variant,report,font)
        screens=[s for c in cases+menu for s in c['screens']]
        result={'rom_sha256':digest(rom.read_bytes()),'catalog_sha256':digest(CATALOG.read_bytes()),'harness_sha256':digest(Path(__file__).read_bytes()),'limited':bool(limit),'counts':dict(counts),'cases':cases,'menus':[{k:v for k,v in m.items() if k not in ('glyphs','payloads','formats')} for m in menu],'copies':copies,'screens':screens,
                'scope':'Native service formatter and every message page; 12 original ally tables in both native layouts; warehouse/bank menu readers; actual five/16-byte manager copies. Generic isolated rows are checked separately from natural transactions. Input wait/glyph delay and frame-yield timing bypassed only in disposable message fixtures; original page redraw callbacks execute.'}
        write_json(folder/'verification.json',result);print(variant,'passed',len(screens),flush=True);return result


def compare():
    a=load_json(OUTPUT/'verification/japanese/verification.json');b=load_json(OUTPUT/'verification/baseline/verification.json')
    require(not a['limited'] and not b['limited'] and a['screens']==b['screens'],'Incomplete controls')
    for name in a['screens']:
        with Image.open(OUTPUT/'verification/japanese'/name) as x,Image.open(OUTPUT/'verification/baseline'/name) as y:
            require(ImageChops.difference(x.convert('RGB'),y.convert('RGB')).getbbox() is None,f'Japanese relocation changed pixels: {name}')
    result={'pixel_pairs':len(a['screens']),'japanese_sha256':a['rom_sha256'],'baseline_sha256':b['rom_sha256']};write_json(OUTPUT/'verification/japanese-control.json',result);return result


def service_contexts(variant='english'):
    """Original numeric-input panel and bank/token summary readers."""
    mgba.log.silence();rom=BASELINE if variant=='baseline' else OUTPUT/f'torneko3-ally-services-{variant}.gba';folder=OUTPUT/'verification'/variant
    entries=load_json(CATALOG)['entries'];report={} if variant=='baseline' else load_json(OUTPUT/f'{variant}-build.json');english=variant=='english';font=FontZero(ORIGINAL_ROM.read_bytes());codec=GameTextCodec(ORIGINAL_ROM.read_bytes());records=[]
    with Session(rom.read_bytes(),folder) as session:
        core=session.core
        for o in (0xC3F334,0xC3F808):
            require(core.load_raw_state(STATE.read_bytes()),'Restore failed');e=next(e for e in entries if int(e['offset'],0)==o);trace=ui.InterfaceTrace(core)
            try:
                ui.native_step(session,trace,0x0808B60C,[18,1,1])
                ui.native_step(session,trace,0x0807B604,[0,source_for(e,variant,report),0,0,9999999,7,0,9999999,0],stop=0x0807B82C,overrides={0x0807B648:{'pc':0x0807B64C}})
                glyphs=trace.positions
                require(glyphs,'Numeric panel was not drawn')
                if english:
                    unit=e['display'] or e['english'];actual=[g['code'] for g in glyphs]
                    require(actual[-len(unit):]==[font.glyph(c)[0] for c in unit],'Numeric unit missing')
                    require(all(g['x']+max(g['advance'],10)<=g['window_width'] and g['y']+12<=g['window_height'] for g in glyphs),'Numeric input unit clipped')
                record={'kind':'numeric_input','source':hex(source_for(e,variant,report)),'glyphs':glyphs}
            finally:trace.close()
            name=f'numeric-{o:08x}';session.frames(2);session.capture(name);record['screens']=[name+'.png'];write_json(folder/(name+'.json'),record);records.append(record)
        from tools.verify_items import install_item
        for o in (0xC3E548,0xC3E550):
            require(core.load_raw_state(STATE.read_bytes()),'Restore failed')
            e=next(e for e in entries if int(e['offset'],0)==o);source=source_for(e,variant,report)
            install_item(core,0x0200A480,1);core.memory.u32[0x02009110]=source
            trace=ui.InterfaceTrace(core)
            try:
                ui.native_step(session,trace,0x080755C0,[0,1,0x0200A480,0,16])
                draws=[d for d in trace.payloads if int(d['address'],0)==source]
                require(len(draws)==1,'Transfer caller label was not drawn')
                glyphs=[g for g in trace.positions if g['draw_serial']==draws[0]['serial']]
                checks=ui.check_glyphs(glyphs,e['display'] or e['english'],font) if english else {}
                if english:require(checks['window_width']==48 and checks['max_right']<=48,'Wrong transfer popup geometry')
                record={'kind':'warehouse_transfer','source':hex(source),'checks':checks,'glyphs':glyphs}
            finally:trace.close()
            name=f'transfer-{o:08x}';session.frames(2);session.capture(name);record['screens']=[name+'.png'];write_json(folder/(name+'.json'),record);records.append(record)
        for kind in ('bank','tokens0','tokens1','tokens2','tokens3'):
            for profile in ('normal','stress') if english else ('normal',):
                require(core.load_raw_state(STATE.read_bytes()),'Restore failed');trace=ui.InterfaceTrace(core);n=1234567 if profile=='normal' else -2147483648
                try:
                    old.write_bytes(core,0x0200A3C4,b'\xA5'*100+old.GUARD)
                    if kind=='bank':
                        ui.native_step(session,trace,0x0807789C,[],overrides={0x080778A8:{'r0':n},0x080778AE:{'r0':n}})
                        source=core.memory.u32[0x080778C4]
                    else:
                        row=int(kind[-1]);core.memory.u8[0x0200915C]=row
                        ui.native_step(session,trace,0x08077B7C,[],overrides={0x08077B86:{'r0':n},0x08077B8E:{'r0':n}})
                        source=core.memory.u32[0x08C3FB5C+4*row]
                    raw=old.cstring(core,0x0200A3C4,100)
                    require(bytes(core.memory[0x0200A428:0x0200A430])==old.GUARD,'Header buffer guard')
                    if english:
                        e=next(e for e in entries if source_for(e,variant,report)==source)
                        expected=expected_raw(e,{'$d0':str(n),'$d1':str(n)})
                        if kind=='bank':expected=expected%(n,n)
                        require(raw==expected,'Native header reader changed argument order')
                    # Original bank header descriptor supplies a 200px panel.
                    # The token counter uses the same shared destination; its
                    # text is also tested in this conservative 200px envelope.
                    ui.native_step(session,trace,0x0807B294,[0x08C3F158,0,0,0x08C3F1A8],stop=0x0807B3D8)
                    draws=[d for d in trace.payloads if int(d['address'],0)==0x0200A3C4]
                    require(len(draws)==1,'Header descriptor not drawn')
                    glyphs=[g for g in trace.positions if g['draw_serial']==draws[0]['serial']]
                    checks=ui.check_glyphs(glyphs,old.visible(raw,codec),font) if english else {}
                    record={'kind':kind,'profile':profile,'source':hex(source),'formatted_hex':raw.hex(),'checks':checks,'glyphs':glyphs}
                finally:trace.close()
                name=f'header-{kind}-{profile}';session.frames(2);session.capture(name);record['screens']=[name+'.png'];write_json(folder/(name+'.json'),record);records.append(record)
    result={'rom_sha256':digest(rom.read_bytes()),'catalog_sha256':digest(CATALOG.read_bytes()),'harness_sha256':digest(Path(__file__).read_bytes()),'cases':records,'screens':[s for r in records for s in r['screens']]};write_json(folder/'service-contexts.json',result);return result


class ServiceTrace(ui.InterfaceTrace):
    def __init__(self,core,entry):
        self.entry=entry;super().__init__(core)
        point=ffi.new('struct mBreakpoint*');point.address=0x0806DCDC;point.segment=-1;point.type=lib.BREAKPOINT_HARDWARE
        require(self.debugger.platform.setBreakpoint(self.debugger.platform,point)>=0,'No service redirect')
    def entered(self,debugger,reason,info):
        super().entered(debugger,reason,info)
        if info!=ffi.NULL and reason==lib.DEBUGGER_ENTER_BREAKPOINT and info.address==0x0806DCDC and not self.redirects:
            self.redirects+=1
            ui.registers(self.core,{'r0':int(self.cpu.gprs[1])&0xffffffff,'pc':self.entry})
        debugger.state=lib.DEBUGGER_RUNNING


def service_routes(variant='english'):
    """Enter two real service handlers, then use ordinary button navigation."""
    from tools.verify_items import install_item
    mgba.log.silence();rom=BASELINE if variant=='baseline' else OUTPUT/f'torneko3-ally-services-{variant}.gba';folder=OUTPUT/'verification/routes'/variant
    report={} if variant=='baseline' else load_json(OUTPUT/f'{variant}-build.json');catalog=load_json(CATALOG)
    entries={int(e['offset'],0):e for e in catalog['entries']};records=[]
    with Session(rom.read_bytes(),folder) as session:
        for kind,entry in [('warehouse',0x080738CC),('bank',0x08077628)]:
            require(session.core.load_raw_state(STATE.read_bytes()),'Route restore failed');install_item(session.core,0x0200A480,1);trace=ServiceTrace(session.core,entry);screens=[];keys=[]
            def press(key):
                trace.phase=str(len(keys));session.press(key,180,trace);name=f'{kind}-{len(keys):02d}';session.capture(name);screens.append(name+'.png');keys.append(key)
            try:
                for key in ('B','A','A','A'):press(key)
                require(trace.redirects==1,'Service entry not reached once')
                if kind=='warehouse':
                    for key in ('DOWN','DOWN','A'):press(key)
                    help_source=source_for(entries[0xC3EAB0],variant,report)
                    help_formats=[f for f in trace.formats if int(f['source'],0)==help_source]
                    require(help_formats,'Warehouse Instructions command did not select help')
                    if variant=='english':require(bytes.fromhex(help_formats[-1]['output_hex'])==encode(entries[0xC3EAB0],ORIGINAL_ROM.read_bytes())[0],'Handler help text changed')
                    followup=source_for(entries[0xC3E528],variant,report)
                    for _ in range(14):
                        press('A')
                        if any(int(f['source'],0)==followup for f in trace.formats):break
                    else:raise RuntimeError('Warehouse help did not return to menu')
                    press('A')
                    require(any(int(f['source'],0)==source_for(entries[0xC3E5C8],variant,report) for f in trace.formats),'Empty withdrawal branch missing')
                    for key in ('A','B','A'):press(key)
                else:
                    press('A')
                    require(any(int(f['source'],0)==source_for(entries[0xC3F234],variant,report) for f in trace.formats),'Empty-bank menu missing')
                    press('B')
                    require(any(int(f['source'],0)==source_for(entries[0xC3F650],variant,report) for f in trace.formats),'Bank Cancel did not choose farewell')
                    press('A')
                require(not trace.errors,str(trace.errors))
                record={'kind':kind,'handler':hex(entry),'inputs':keys,'screens':screens,'formats':trace.formats,'scope':'One fixture redirect from item-information entry into the original service handler using the live callback. All subsequent keys, waits, paging, menu selection and empty/cancel branches run normally; no transaction balances or storage records changed by fixtures.'}
            finally:trace.close()
            write_json(folder/(kind+'.json'),record);records.append(record)
    result={'rom_sha256':digest(rom.read_bytes()),'catalog_sha256':digest(CATALOG.read_bytes()),'harness_sha256':digest(Path(__file__).read_bytes()),'cases':records,'screens':[s for r in records for s in r['screens']]};write_json(folder/'verification.json',result);print(variant,'service routes',len(result['screens']),flush=True);return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('variant',choices=('english','japanese','baseline','compare'),nargs='?',default='english');p.add_argument('--limit',type=int);a=p.parse_args()
    compare() if a.variant=='compare' else verify(a.variant,a.limit)
