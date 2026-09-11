"""Original event operand, native story preparation and real frame-driven display."""
import argparse
from pathlib import Path
import mgba.log
from PIL import ImageChops
from tools import verify_dungeon_interface as ui
from tools.verify_expansion import Session
from tools.verify_tutorial_gameplay import cold_tables,restore
from tools.verify_core_gameplay import write_bytes,cstring,guarded_format
from tools.verify_items import write_json,distinct_glyph_observations
from tools.build_opening_story import OUTPUT,CATALOG,encode
from tools.build_first_label import ORIGINAL_ROM,ROOT,digest
from tools.translation_pipeline import FontZero,load_json,check

STATE=ROOT/'build/companion-dialogue/verification/save/world.state'
BASELINE=ROOT/'build/ally-nicknames/torneko3-ally-nicknames-english.gba'
STOPS={0x23:0x080663A2,0x25:0x0806553C,0x27:0x08065550,0x2C:0x080655C4}


def case(session,state,tables,e,event,variant,font):
    restore(session,state,tables);core=session.core
    command=0x08000000+int(event['command_offset'],0);source=core.memory.u32[command+4]
    controller=0x0203F000;write_bytes(core,controller,b'\0'*128);core.memory.u32[controller+0x24]=command
    trace=ui.InterfaceTrace(core);trace.phase=e['id']+'-'+event['pointer_offset']
    try:
        formatted=guarded_format(session,trace,source,cap=1024)
        call=ui.native_step(session,trace,0x08064E28,[controller],stop=STOPS[event['opcode']])
        root=core.memory.u32[0x03000010];native=cstring(core,root+0x5C,1024)
        check(native==formatted,'Event wrapper changed formatted payload')
        expected,metrics=encode(e,ORIGINAL_ROM.read_bytes());english=variant=='english' or e['reuse']
        check(native==(expected if english else bytes.fromhex(e['source_hex'])),'Native opening text differs')
        session.frames(480,trace)
        gs=[g for g in trace.positions if g['caller']=='0x08061B4E' and int(g['source'] or '0',0)==source]
        glyphs,repeats=distinct_glyph_observations(gs);checks={}
        if english:
            visible=metrics['visible'];checks=ui.check_glyphs(glyphs,visible,font)
            lines=visible.split('\n');at=0
            for row,line in enumerate(lines):
                group=glyphs[at:at+len(line)];at+=len(line)
                if not group:continue
                check(len({g['y'] for g in group})==1,'Opening line unexpectedly wrapped')
                width=sum(font.glyph(c)[1] for c in line)
                if e['layout']=='centered':check(abs(group[0]['x']-(208-width)//2)<=1,'Narration centering differs')
                check(all(g['y']==glyphs[0]['y']+12*(row-(1 if visible.startswith('\n') else 0)) for g in group),'Opening row spacing differs')
            check(at==len(glyphs),'Extra opening glyphs')
        check(glyphs and not trace.errors,'No native opening glyphs/errors')
        name=e['id']+'-'+event['pointer_offset'][2:];session.capture(name)
        report={'id':e['id'],'command_offset':event['command_offset'],'command_word':event['command_word'],'pointer_offset':event['pointer_offset'],'source':hex(source),'output_hex':native.hex(),'steps':call['steps'],'guards_intact':True,'checks':checks,'glyphs':glyphs,'formats':trace.formats,'screen':name+'.png'}
        write_json(session.output/(name+'.json'),report)
        return {k:v for k,v in report.items() if k not in ('glyphs','formats')}
    finally:trace.close()


def verify(variant='english',limit=None):
    mgba.log.silence();rom=BASELINE if variant=='baseline' else OUTPUT/f'torneko3-opening-story-{variant}.gba'
    folder=OUTPUT/'verification'/variant;catalog=load_json(CATALOG);font=FontZero(ORIGINAL_ROM.read_bytes());cases=[]
    with Session(rom.read_bytes(),folder) as session:
        tables=cold_tables(session);state=STATE.read_bytes()
        for i,e in enumerate(catalog['entries'][:limit] if limit else catalog['entries']):
            for event in e['events']:cases.append(case(session,state,tables,e,event,variant,font))
            if (i+1)%10==0:print(variant,i+1,'opening sources',flush=True)
    report={'variant':variant,'source_sha256':digest(ORIGINAL_ROM.read_bytes()),'rom_sha256':digest(rom.read_bytes()),'catalog_sha256':digest(CATALOG.read_bytes()),'harness_sha256':digest(Path(__file__).read_bytes()),'fixture_sha256':digest(STATE.read_bytes()),'limited':bool(limit),'cases':cases,'scope':'Controlled event-controller cursor points to each actual ROM command. Original fetch, wrapper, 1024-byte guarded formatter and frame-driven story rendering; all original choice parameters unchanged. Does not by itself execute branch selection or prove natural reachability.'}
    write_json(folder/'verification.json',report);return report


def compare():
    a=load_json(OUTPUT/'verification/japanese/verification.json');b=load_json(OUTPUT/'verification/baseline/verification.json')
    check(len(a['cases'])==len(b['cases'])==52,'Incomplete Japanese comparison')
    for x,y in zip(a['cases'],b['cases'],strict=True):
        check(x['id']==y['id'] and x['pointer_offset']==y['pointer_offset'] and x['output_hex']==y['output_hex'],'Japanese event payload differs')
        from PIL import Image
        with Image.open(OUTPUT/'verification/japanese'/x['screen']) as first, Image.open(OUTPUT/'verification/baseline'/y['screen']) as second:
            check(ImageChops.difference(first.convert('RGB'),second.convert('RGB')).getbbox() is None,'Japanese relocation changed pixels')
    return len(a['cases'])

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--variant',choices=['english','japanese','baseline'],default='english');p.add_argument('--limit',type=int)
    a=p.parse_args();verify(a.variant,a.limit)
