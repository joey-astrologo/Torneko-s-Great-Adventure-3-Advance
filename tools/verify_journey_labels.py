"""Native place readers/copies/draw loop and all four six-topic advice menus."""
import argparse
from pathlib import Path
import struct
import mgba.log
from PIL import Image,ImageChops
from tools.build_early_journey import OUTPUT,CATALOG,PLACE_BASE,encode
from tools.build_first_label import ROOT,ORIGINAL_ROM,digest
from tools.verify_early_journey import BASELINE,STATE
from tools.verify_expansion import Session
from tools.verify_tutorial_gameplay import cold_tables,restore
from tools.verify_core_gameplay import write_bytes,cstring,guarded_format
from tools.verify_items import write_json
from tools import verify_dungeon_interface as ui
from tools.translation_pipeline import load_json,check,FontZero


def draw_checks(trace,entries,variant,font):
    checks=[]
    for e in entries:
        raw=(encode(e,ORIGINAL_ROM.read_bytes())[0] if variant=='english' else bytes.fromhex(e['source_hex']))[:-1]
        prefix=b'\x03\x05\x07' if e['layout']=='choice' else b''
        matches=[d for d in trace.payloads if bytes.fromhex(d['raw_hex']).split(b'\0')[0]==prefix+raw]
        check(len(matches)==1,'Missing/duplicate native label: '+e['id'])
        glyphs=[g for g in trace.positions if g['draw_serial']==matches[0]['serial']]
        result=ui.check_glyphs(glyphs,encode(e,ORIGINAL_ROM.read_bytes())[1]['visible'],font) if variant=='english' else {'glyphs':len(glyphs)}
        check(glyphs,'Empty native label')
        checks.append({'id':e['id'],'raw_hex':raw.hex(),'draw_serial':matches[0]['serial'],**result})
    check(len(trace.payloads)==len(entries),'Unexpected menu rows')
    return checks


def verify(variant='english'):
    mgba.log.silence();rom=BASELINE if variant=='baseline' else OUTPUT/f'torneko3-early-journey-{variant}.gba'
    folder=OUTPUT/'verification'/('labels-'+variant);entries=load_json(CATALOG)['entries'];font=FontZero(ORIGINAL_ROM.read_bytes());cases=[]
    with Session(rom.read_bytes(),folder) as s:
        tables=cold_tables(s);state=STATE.read_bytes();core=s.core
        for e in [x for x in entries if x['layout']=='place']:
            restore(s,state,tables);trace=ui.InterfaceTrace(core);i=e['place_owners'][0]['index'];name=f'place-{i:02d}'
            try:
                getter=ui.native_step(s,trace,0x08066CC8,[i]);source=core.memory.u32[0x08000000+PLACE_BASE+i*12]
                check(getter['return_r0']==source,'Place getter selected wrong record')
                coordinates=ui.native_step(s,trace,0x08066CE0,[i,0x0203F000])
                actual=bytes(core.memory[0x0203F000:0x0203F008]);record=bytes.fromhex(e['place_owners'][0]['record_hex'])
                check(actual==record[4:] and coordinates['return_r0']==int(struct.unpack_from('<i',record,4)[0]>=0),'Place coordinates changed')
                dest=0x0200A34C;write_bytes(core,dest-8,b'\xA5'*46)
                copied=ui.native_step(s,trace,0x080767BC,[],stop=0x080767D2,overrides={0x080767BC:{'r6':i}})
                raw=cstring(core,source,1024)
                check(cstring(core,dest,30)==raw and core.memory.u8[dest+29]==0,'Place copy truncated')
                check(bytes(core.memory[dest-8:dest])==b'\xA5'*8 and bytes(core.memory[dest+30:dest+38])==b'\xA5'*8,'Place copy damaged adjacent slot')
                drawing=ui.native_step(s,trace,0x08076672,[0,0,0,0,0,i],stop=0x080766C8,overrides={0x08076672:{'r7':1,'r6':0}})
                heading=next(x for x in entries if x['layout']=='place_heading')
                checks=draw_checks(trace,[heading,e],variant,font)
                row={'kind':'place','id':e['id'],'index':i,'source':hex(source),'raw_hex':raw.hex(),'coordinates_hex':actual.hex(),
                     'guards_intact':True,'getter':getter,'copy':copied,'drawing':drawing,'checks':checks}
                s.frames(2);s.capture(name);row.update(screen=name+'.png',glyphs=trace.positions,payloads=trace.payloads)
                write_json(folder/(name+'.json'),row);cases.append({k:v for k,v in row.items() if k not in ('glyphs','payloads')})
            finally:trace.close()
            trace=ui.InterfaceTrace(core)
            try:
                prompt=next(x for x in entries if x['layout']=='place_prompt');source=core.memory.u32[0x0807682C]
                formatted=guarded_format(s,trace,source,cap=1000)
                template=encode(prompt,ORIGINAL_ROM.read_bytes())[0] if variant=='english' else bytes.fromhex(prompt['source_hex'])
                check(formatted==template.replace(b'$m0',raw[:-1]),'Zoom confirmation lost selected name')
                shown=ui.native_step(s,trace,0x0807ADA4,[source,0,0,0,0,0,0],stop=0x0807B044,overrides={0x0807AF76:{'r4':0}})
                formats=[f for f in trace.formats if f['caller']=='0x0807AE04']
                check(len(formats)==1 and formats[0]['output_hex']==formatted.hex(),'Native confirmation reader differs')
                checks=ui.check_glyphs(trace.positions,formatted[:-1].decode(),font) if variant=='english' else {'glyphs':len(trace.positions)}
                name=f'confirmation-{i:02d}';s.frames(2);s.capture(name)
                row={'kind':'confirmation','id':prompt['id'],'index':i,'source':hex(source),'formatted_hex':formatted.hex(),
                     'guards_intact':True,'drawing':shown,'checks':checks,'screen':name+'.png','glyphs':trace.positions,'formats':formats}
                write_json(folder/(name+'.json'),row);cases.append({k:v for k,v in row.items() if k not in ('glyphs','formats')})
            finally:trace.close()
        prompts=sorted({int(ev['prompt_command_offset'],0) for e in entries for ev in e['events'] if ev['opcode']==0x98})
        for prompt in prompts:
            restore(s,state,tables);trace=ui.InterfaceTrace(core);name=f'advice-{prompt:08x}'
            try:
                controller=0x0203F000;write_bytes(core,controller,b'\0'*128);core.memory.u32[controller+0x24]=0x08000000+prompt
                dispatch=ui.native_step(s,trace,0x08064E28,[controller],stop=0x08066396)
                choices=sorted([(ev['choice_index'],e) for e in entries for ev in e['events'] if ev.get('prompt_command_offset')==f'0x{prompt:08X}'])
                check(len(choices)==core.memory.u32[0x02000430]==6,'Incomplete advice list')
                records=[]
                for i,e in choices:
                    record=[core.memory.u32[0x02008B80+i*12+j] for j in (0,4,8)]
                    source=core.memory.u32[0x08000000+prompt+12+8*i]
                    check(record==[source,0,i],'Native choice order/value changed');records.append(record)
                check([core.memory.u32[0x02008BC8+j] for j in (0,4,8)]==[0,0,0xffffffff],'Choice terminator changed')
                draw=ui.native_step(s,trace,0x0807B294,[0x02008B80,0,0,0],stop=0x0807B3B6)
                checks=draw_checks(trace,[e for _,e in choices],variant,font)
                s.frames(2);s.capture(name)
                row={'kind':'advice','prompt_command_offset':hex(prompt),'dispatch':dispatch,'drawing':draw,'records':records,'checks':checks,
                     'screen':name+'.png','glyphs':trace.positions,'payloads':trace.payloads}
                write_json(folder/(name+'.json'),row);cases.append({k:v for k,v in row.items() if k not in ('glyphs','payloads')})
            finally:trace.close()
    result={'variant':variant,'rom_sha256':digest(rom.read_bytes()),'source_sha256':digest(ORIGINAL_ROM.read_bytes()),
            'catalog_sha256':digest(CATALOG.read_bytes()),'harness_sha256':digest(Path(__file__).read_bytes()),'fixture_sha256':digest(STATE.read_bytes()),
            'cases':cases,'scope':'Controlled native getter, coordinate getter, original 30-byte selected-name copy and original place menu row loop for every table record. All four actual advice event prefixes form six records then use the native generic menu drawer. Does not establish natural menu reachability, selected branch outcomes or map marker placement.'}
    write_json(folder/'verification.json',result);print(variant,len(cases),'label/menu cases',flush=True);return result


def compare():
    a=load_json(OUTPUT/'verification/labels-japanese/verification.json');b=load_json(OUTPUT/'verification/labels-baseline/verification.json')
    check(len(a['cases'])==len(b['cases'])==64,'Incomplete label controls')
    for x,y in zip(a['cases'],b['cases'],strict=True):
        check(x['kind']==y['kind'] and x['screen']==y['screen'],'Different label cases')
        if x['kind']=='place':check(x['raw_hex']==y['raw_hex'] and x['coordinates_hex']==y['coordinates_hex'],'Changed Japanese place copy')
        if x['kind']=='confirmation':check(x['formatted_hex']==y['formatted_hex'],'Changed Japanese confirmation')
        else:check([c['raw_hex'] for c in x['checks']]==[c['raw_hex'] for c in y['checks']],'Changed Japanese label payload')
        with Image.open(OUTPUT/'verification/labels-japanese'/x['screen']) as first,Image.open(OUTPUT/'verification/labels-baseline'/y['screen']) as second:
            check(ImageChops.difference(first.convert('RGB'),second.convert('RGB')).getbbox() is None,'Japanese label relocation changed pixels')
    return len(a['cases'])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--variant',choices=['english','japanese','baseline'],default='english');verify(p.parse_args().variant)
