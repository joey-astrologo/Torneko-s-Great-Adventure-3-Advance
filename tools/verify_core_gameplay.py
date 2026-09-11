"""Native per-entry rendering, substitution guards, fixed tables and menu routes."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import struct

import mgba.log
from mgba._pylib import ffi,lib
from PIL import ImageChops
from tools import verify_dungeon_interface as ui
from tools.build_core_gameplay import CATALOG,OUTPUT,CHOICES,COMMAND_RECORDS,SHARED,encode
from tools.build_first_label import ORIGINAL_ROM,digest
from tools.game_text import GameTextCodec,PRINTF
from tools.translation_pipeline import FontZero,load_json
from tools.verify_expansion import Session
from tools.verify_items import write_json,distinct_glyph_observations
from tools.verify_first_label import require

STATE=Path('build/dungeon-interface/verification/save/world.state')
BASELINE=Path('build/dungeon-interface/torneko3-dungeon-interface-english.gba')
ITEM=0x0200A1BC; ACTOR=0x0200A34C; NUMBER=0x0200A1AC
DEST=0x0203F200; GUARD=b'GUARD123'; CAP=1000


def cstring(core,address,limit=1000):
    raw=bytes(core.memory[address:address+limit])
    end=raw.find(b'\0')
    require(end>=0,f'No terminator within {limit} bytes at {address:08x}')
    return raw[:end+1]


def write_bytes(core,address,raw):
    for i,b in enumerate(raw):core.memory.u8[address+i]=b


def slots(core,font,profile):
    widest=max((chr(x) for x in range(33,127)),key=lambda x:font.glyph(x)[1])
    width=font.glyph(widest)[1]
    values={'$t':'Torneko','$i0':'Oaken club','$i1':'Medicinal herb','$m0':'Slime','$m1':'Cannibox','$m2':'Mimic','$d0':'9999'}
    if profile=='stress':
        values.update({'$i0':widest*(144//width),'$i1':widest*(144//width),
                       '$m0':widest*(120//width),'$m1':widest*(120//width),'$m2':widest*(120//width),'$d0':'-2147483648'})
    core.memory.u16[0x020014CE]=0
    for i in range(2):write_bytes(core,ITEM+i*100,values[f'$i{i}'].encode().ljust(100,b'\0'))
    for i in range(3):write_bytes(core,ACTOR+i*30,values[f'$m{i}'].encode().ljust(30,b'\0'))
    core.memory.u32[NUMBER]=int(values['$d0'])&0xffffffff
    return values


def expanded(text,values):
    for key,value in values.items():text=text.replace(key,value)
    return text


def visible(raw,codec):
    return ''.join(t['text'] for t in codec.parse(raw,0)['tokens'] if t['kind']=='text')


def command_ink_check(glyphs,text,font):
    # The original second command row starts at y13 in a 24px window.
    # Font 0 stores 12 bitmap rows, but these labels use only 10/11 ink rows.
    # Check actual nontransparent pixels rather than requiring a blank row.
    glyphs,repeats=distinct_glyph_observations(glyphs)
    require([g['code'] for g in glyphs]==[font.glyph(c)[0] for c in text],'Command glyph sequence differs')
    bottom=0
    for g in glyphs:
        require(g['font']==0 and g['spacing']==0,'Command font/spacing changed')
        bitmap,_=font.descriptors[g['code']];at=bitmap-0x08000000
        raw=font.original[at:at+72]
        occupied=[(x,y) for y in range(12) for x in range(12) if (raw[y*6+x//2]>>(4*(x%2)))&15]
        for x,y in occupied:
            require(0<=g['x']+x<g['window_width'] and 0<=g['y']+y<g['window_height'],'Command ink clipped')
            bottom=max(bottom,g['y']+y+1)
        require(g['x']+g['advance']<=g['window_width'],'Command advances outside window')
    return {'glyphs':len(glyphs),'reobservations':repeats,'ink_bottom':bottom}


def source_for(core,entry,variant,build):
    if variant!='baseline':return build['gameplay']['relocated'][entry['id']]['offset']+0x08000000
    offset=int(entry['offset'],0)
    if offset in SHARED:return core.memory.u32[int(entry['pointer_owners'][0]['offset'],0)+0x08000000]
    return offset+0x08000000


def guarded_format(session,trace,source,mode=0,cap=CAP):
    core=session.core
    write_bytes(core,DEST-8,GUARD+b'\xA5'*cap+GUARD)
    ui.native_step(session,trace,0x0807D8CC,[source,DEST,DEST+cap-1,mode])
    raw=cstring(core,DEST,cap)
    require(bytes(core.memory[DEST-8:DEST])==GUARD and bytes(core.memory[DEST+cap:DEST+cap+8])==GUARD,'Formatter guard overwritten')
    require(raw[-1:]==b'\0','Unterminated formatter output')
    return raw


def message_case(session,state,entry,variant,build,folder,font,codec,profile):
    require(session.core.load_raw_state(state),'State restore failed')
    core=session.core;values=slots(core,font,profile);source=source_for(core,entry,variant,build)
    trace=ui.InterfaceTrace(core);trace.phase='message'
    try:
        raw=guarded_format(session,trace,source)
        english=variant=='english'
        if english:
            _,metric=encode(entry,ORIGINAL_ROM.read_bytes())
            expected=expanded(metric['display_template'],values)
            require(raw==expected.encode()+b'\0',f"Formatter lost/reordered substitutions: {entry['id']}")
        result=ui.native_step(session,trace,0x0807ADA4,[source,0,0,0,0,0,0],stop=0x0807B044,
                              overrides={0x0807AF76:{'r4':0}})
        # Only suppress per-glyph delay; native formatting, glyph selection,
        # positions, line stepping and page limit all execute original code.
        engine=[f for f in trace.formats if f['caller']=='0x0807AE04']
        require(len(engine)==1 and engine[0]['output_hex']==raw.hex(),'Message engine used another payload')
        checks=ui.check_glyphs(trace.positions,expected,font) if english else {}
        record={'id':entry['id'],'profile':profile,'source':hex(source),'formatted_hex':raw.hex(),
                'guarded_capacity':CAP,'checks':checks,'native':result,'formats':trace.formats,'glyphs':trace.positions}
    finally:trace.close()
    session.frames(2)
    label=f"{entry['id']}-{profile}"
    session.capture(label)
    write_json(folder/(label+'.json'),record)
    return record


def printf_raw(session,trace,source,source_raw,entry):
    fixture=encode(entry,ORIGINAL_ROM.read_bytes())[1]['row_layout']['numeric_fixture']
    numbers=iter(fixture or [])
    args=[]
    for fmt in PRINTF.findall(source_raw):
        args.append(7 if fmt==b'%c' else next(numbers))
    write_bytes(session.core,DEST-8,GUARD+b'\xA5'*256+GUARD)
    ui.native_step(session,trace,0x08096744,[DEST,source]+args)
    raw=cstring(session.core,DEST,256)
    require(bytes(session.core.memory[DEST-8:DEST])==GUARD and bytes(session.core.memory[DEST+256:DEST+264])==GUARD,'Printf guard overwritten')
    return raw


def row_case(session,state,entry,variant,build,folder,font,codec):
    require(session.core.load_raw_state(state),'State restore failed')
    core=session.core;slots(core,font,'normal');source=source_for(core,entry,variant,build)
    trace=ui.InterfaceTrace(core);trace.phase=entry['family']
    try:
        # Native stock window 1 supplies both the 80px command panel and
        # 208px statistics panel. Labels/choice fixtures use message window18.
        family=entry['family']
        ui.native_step(session,trace,0x0808B60C,[1 if family in ('stats','command') else 18,1,1])
        window=2 if family=='stats' else 0
        ui.native_step(session,trace,0x0808BBD8,[window])
        source_raw=cstring(core,source,256)
        raw=printf_raw(session,trace,source,source_raw,entry) if PRINTF.findall(source_raw) else guarded_format(session,trace,source)
        # Keep formatted bytes in fixture output while opening the draw window.
        write_bytes(core,DEST,raw)
        ui.native_step(session,trace,0x0808CB84,[0,0,DEST,window,13])
        ui.native_step(session,trace,0x0808BBF8,[window])
        english=variant=='english' or int(entry['offset'],0) in SHARED
        check=ui.check_glyphs(trace.positions,visible(raw,codec),font) if english else {}
        if english and family in ('command','choice','stats'):
            glyphs,_=distinct_glyph_observations(trace.positions)
            # Fixed columns must not overlap even when the whole row fits.
            boundaries={'command':[40],'choice':[52,100],'stats':[68,104,152]}[family]
            for boundary in boundaries:
                require(all(g['x']+g['advance']<=boundary for g in glyphs if g['x']<boundary),f'Column overlap: {entry["id"]}')
        record={'id':entry['id'],'source':hex(source),'raw_hex':raw.hex(),'checks':check,'glyphs':trace.positions}
    finally:trace.close()
    session.frames(2);session.capture(entry['id']);write_json(folder/(entry['id']+'.json'),record)
    return record


def setting_cases(session,state,variant,build,folder,font,codec,entries):
    core=session.core;require(core.load_raw_state(state),'State restore failed')
    for key in ('B','RIGHT','DOWN','A'):session.press(key,80)
    setting_state=bytes(ffi.buffer(core.save_raw_state()))
    results=[];covered=set()
    # 35 actual menu definitions, plus arena variants of Suspend/Give up.
    definitions=[(i,0) for i in range(35)]+[(0,26),(22,26)]
    for row,arena in definitions:
        core.load_raw_state(setting_state);core.memory.u8[0x02004FF0]=arena
        core.memory.u16[0x020091B0]=0
        trace=ui.InterfaceTrace(core);trace.phase='settings'
        try:
            ui.native_step(session,trace,0x0808BBD8,[0])
            ui.native_step(session,trace,0x0808C758,[0,0,0,152,24])
            result=ui.native_step(session,trace,0x080786AC,[0x08C3FBA0+row*20,row,0])
            ui.native_step(session,trace,0x0808BBF8,[0])
            formats=[f for f in trace.formats if f['caller']=='0x080786C4']
            require(len(formats)==1,'Settings callback did not reach formatter')
            source=int(formats[0]['source'],0)
            matched=[e for e in entries if e['family']=='setting' and source_for(core,e,variant,build)==source]
            require(len(matched)==1,f'Settings source did not match catalog: {row}/{source:08x}')
            e=matched[0];covered.add(e['id'])
            draws=trace.payloads;require(len(draws)==1,'Unexpected settings draw count')
            raw=bytes.fromhex(draws[0]['raw_hex'])
            raw=raw[:codec.parse(raw,0)['end']]
            english=variant=='english' or int(e['offset'],0) in SHARED
            checks=ui.check_glyphs(trace.positions,visible(raw,codec),font) if english else {}
            if english:
                glyphs,_=distinct_glyph_observations(trace.positions)
                for boundary in (64,96,112,128):
                    if b'\x03\x08'+bytes([boundary]) in raw:
                        require(all(g['x']+g['advance']<=boundary for g in glyphs if g['x']<boundary),f'Settings column overlap {e["id"]}')
            record={'id':e['id'],'row':row,'arena':arena,'checks':checks,'source':hex(source),'raw_hex':raw.hex(),
                    'native':result,'formats':trace.formats,'glyphs':trace.positions}
        finally:trace.close()
        session.frames(2);name=f'setting-{row:02d}-{arena}';session.capture(name);write_json(folder/(name+'.json'),record)
        results.append(record)
    require(covered=={e['id'] for e in entries if e['family']=='setting'},'Not all settings sources reached')
    return results


def fixed_command_cases(session,state,variant,build,folder,font,codec,entries):
    results=[]
    for row in range(4):
        core=session.core;core.load_raw_state(state)
        trace=ui.InterfaceTrace(core);trace.phase='fixed-command'
        try:
            ui.native_step(session,trace,0x0806C8C8,[1],overrides={0x0806CB98:{'r5':row}})
            e=next(e for e in entries if int(e['offset'],0)==COMMAND_RECORDS[row])
            # First command draw at local (0,0); native source selection still
            # performs the original multiply-by-30 and printf itself.
            draws=[d for d in trace.payloads if d['x']==0 and d['y']==0 and
                   any(g['draw_serial']==d['serial'] and g['window_origin']==[16,24] for g in trace.positions)]
            require(len(draws)==1,'Missing fixed command row')
            raw=bytes.fromhex(draws[0]['raw_hex']);text=visible(raw,codec)
            source=source_for(core,e,variant,build)
            expected_raw=cstring(core,source,30).replace(b'%c',b'\x07')
            # Enabled/disabled style is native state; visible text is invariant.
            require(text==visible(expected_raw,codec),'Computed command variant read the wrong record')
            glyphs=[g for g in trace.positions if g['draw_serial']==draws[0]['serial']]
            checks=ui.check_glyphs(glyphs,text,font) if variant=='english' else {}
            record={'row':row,'id':e['id'],'raw_hex':raw[:codec.parse(raw,0)['end']].hex(),'checks':checks}
        finally:trace.close()
        session.frames(2);session.capture(f'fixed-command-{row}');write_json(folder/f'fixed-command-{row}.json',record);results.append(record)
    return results


def natural_routes(session,state,folder,variant):
    session.core.load_raw_state(state);trace=ui.InterfaceTrace(session.core);results=[]
    try:
        keys=[('commands','B'),('right','RIGHT'),('down','DOWN'),('tactics','A'),('game-settings','A'),
              ('option-row','DOWN'),('option-right','RIGHT'),('option-left','LEFT')]
        option_colours={};option_values={}
        for label,key in keys:
            trace.phase=label;session.press(key,100,trace);session.capture('route-'+label)
            if label in ('option-row','option-right','option-left'):
                option_colours[label]=list(bytes(session.core.memory[0x020398DF:0x020398E2]))
                option_values[label]=session.core.memory.u16[0x020091A4]
        require(not trace.errors,'Natural menu trace errors')
        require(option_values['option-row']!=option_values['option-right'] and
                option_values['option-row']==option_values['option-left'],'Settings left/right did not update and restore selection')
        if variant=='english':
            codec=GameTextCodec(ORIGINAL_ROM.read_bytes());font=FontZero(ORIGINAL_ROM.read_bytes())
            for draw in trace.payloads:
                if draw['phase']=='commands' and draw['y']==2:continue # Village proper name is a separate family.
                check=command_ink_check if draw['phase']=='commands' else ui.check_glyphs
                check([g for g in trace.positions if g['draw_serial']==draw['serial']],
                      visible(bytes.fromhex(draw['raw_hex']),codec),font)
        write_json(folder/'natural-routes.json',{'inputs':session.frames_recorded,'option_colours':option_colours,'option_values':option_values,
                   'draws':trace.payloads,'glyphs':trace.positions,'trace':trace.report()})
    finally:trace.close()
    return len(keys)


def verify(variant,output=None,limit=None):
    mgba.log.silence();folder=Path(output or OUTPUT/'verification'/variant);folder.mkdir(parents=True,exist_ok=True)
    rom=BASELINE if variant=='baseline' else OUTPUT/f'torneko3-core-gameplay-{variant}.gba'
    build=load_json(OUTPUT/('english-build.json' if variant=='baseline' else f'{variant}-build.json'))
    original=ORIGINAL_ROM.read_bytes();codec=GameTextCodec(original);font=FontZero(original)
    entries=load_json(CATALOG)['entries'];state=STATE.read_bytes();records=[]
    with Session(rom.read_bytes(),folder) as session:
        messages=[e for e in entries if e['family']=='message']
        if limit is not None:messages=messages[:limit]
        for index,e in enumerate(messages):
            for profile in ('normal','stress') if variant=='english' else ('normal',):
                records.append(message_case(session,state,e,variant,build,folder,font,codec,profile))
            if index%25==0:print(variant,'message',index+1,'/',len(messages),flush=True)
        if limit is None:
            for e in entries:
                if e['family'] not in ('message','setting'):records.append(row_case(session,state,e,variant,build,folder,font,codec))
            settings=setting_cases(session,state,variant,build,folder,font,codec,entries)
            fixed=fixed_command_cases(session,state,variant,build,folder,font,codec,entries)
            routes=natural_routes(session,state,folder,variant)
        else:settings=[];fixed=[];routes=0
    report={'variant':variant,'rom_sha256':digest(rom.read_bytes()),'catalog_sha256':digest(CATALOG.read_bytes()),
            'state_sha256':digest(state),'entries':len(entries),'message_cases':len([r for r in records if 'profile' in r]),
            'row_cases':len([r for r in records if 'profile' not in r]),'settings_cases':len(settings),'fixed_command_cases':len(fixed),
            'natural_route_inputs':routes,'screens':len(list(folder.glob('*.png'))),'limited':limit is not None,
            'scope':'Controlled native message/row fixtures and natural menu navigation. Message fixtures suppress per-glyph delay and stop before the input wait; natural dungeon effects are separate playtesting.'}
    write_json(folder/'verification.json',report);print(variant,'complete',report,flush=True);return report


def compare():
    jp=OUTPUT/'verification/japanese';base=OUTPUT/'verification/baseline'
    names={p.name for p in jp.glob('*.png')};require(names=={p.name for p in base.glob('*.png')},'Control screenshot sets differ')
    from PIL import Image
    for name in sorted(names):require(ImageChops.difference(Image.open(jp/name),Image.open(base/name)).getbbox() is None,f'Japanese relocation changed pixels: {name}')
    write_json(OUTPUT/'verification/japanese-comparison.json',{'identical_screens':len(names),'japanese_sha256':digest((OUTPUT/'torneko3-core-gameplay-japanese.gba').read_bytes()),'baseline_sha256':digest(BASELINE.read_bytes())})
    print('Japanese relocation: identical screenshots',len(names),flush=True)


def verify_choice_readers():
    mgba.log.silence();folder=OUTPUT/'verification/fixed-choices';folder.mkdir(parents=True,exist_ok=True)
    results=[];hashes={}
    for variant in ('english','japanese','baseline'):
        rom=BASELINE if variant=='baseline' else OUTPUT/f'torneko3-core-gameplay-{variant}.gba'
        hashes[variant]=digest(rom.read_bytes())
        with Session(rom.read_bytes(),folder/variant) as session:
            for row in range(3):
                session.core.load_raw_state(STATE.read_bytes());trace=ui.InterfaceTrace(session.core)
                try:
                    call=ui.native_step(session,trace,0x080207DC,[],overrides={0x080207E2:{'r0':row}})
                    expected=session.core.memory.u32[0x080207EC]+row*32
                    require(call['return_r0']==expected,'Choice stride reader mismatch')
                    results.append({'variant':variant,'row':row,'source':hex(expected),'call':call})
                finally:trace.close()
    write_json(folder/'report.json',{'cases':results,'rom_sha256':hashes})
    return results


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('variant',choices=('english','japanese','baseline','compare'));p.add_argument('--limit',type=int)
    a=p.parse_args();compare() if a.variant=='compare' else verify(a.variant,limit=a.limit)
