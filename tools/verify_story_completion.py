"""Every journey event operand through its native wrapper and story display."""
import argparse
from pathlib import Path
import mgba.log
from PIL import Image, ImageChops
from tools import verify_dungeon_interface as ui
from tools.verify_expansion import Session
from tools.verify_tutorial_gameplay import cold_tables,restore
from tools.verify_core_gameplay import write_bytes,cstring,guarded_format
from tools.verify_items import write_json,distinct_glyph_observations
from tools.build_story_completion import OUTPUT,CATALOG,encode,choice_prefix
from tools.build_first_label import ORIGINAL_ROM,ROOT,digest
from tools.translation_pipeline import FontZero,load_json,check
from tools.verify_opening_story import STATE

BASELINE=ROOT/'build/early-journey/torneko3-early-journey-english.gba'
STOPS={0x23:0x080663A2,0x25:0x0806553C,0x26:0x08065546,0x2A:0x080655D4,0x2C:0x080655C4,0x96:0x08066396,0x97:0x08066396,0x24:0x08065532,0x27:0x08065550,0x28:0x08065566,0x2B:0x080655DC,0x2D:0x080655CC}


def check_choices(core,prompt,count):
    check(core.memory.u32[0x02000430]==count,'Native choice count changed')
    records=[]
    for i in range(count):
        record=[core.memory.u32[0x02008B80+i*12+j] for j in (0,4,8)]
        check(record==[core.memory.u32[prompt+12+i*8],0,i],'Native choice record changed')
        records.append(record)
    check([core.memory.u32[0x02008B80+count*12+j] for j in (0,4,8)]==[0,0,0xffffffff],'Native choice terminator changed')
    return records


def case(session,state,tables,e,event,variant,font,hero):
    restore(session,state,tables);core=session.core
    if '$t' in e['japanese']:core.memory.u16[0x020014CE]=int(hero=='Tipper')
    command=0x08000000+int(event['command_offset'],0);source=core.memory.u32[command+4]
    controller=0x0203F000;write_bytes(core,controller,b'\0'*128);core.memory.u32[controller+0x24]=command
    trace=ui.InterfaceTrace(core);trace.phase=e['id']+'-'+event['pointer_offset']+'-'+hero
    try:
        formatted=guarded_format(session,trace,source,cap=1024)
        call=ui.native_step(session,trace,0x08064E28,[controller],stop=STOPS[event['opcode']])
        root=core.memory.u32[0x03000010];native=cstring(core,root+0x5C,1024)
        check(native==formatted,'Journey wrapper changed formatted payload')
        if event['opcode'] in (0x96,0x97):check_choices(core,command,event['choice_count'])
        expected,metrics=encode(e,ORIGINAL_ROM.read_bytes(),hero)
        expected=(expected if variant=='english' else bytes.fromhex(e['source_hex'])).replace(b'$t',hero.encode())
        check(native==expected,'Native journey output differs')
        session.frames(480,trace)
        gs=[g for g in trace.positions if g['caller']=='0x08061B4E' and int(g['source'] or '0',0)==source]
        glyphs,repeats=distinct_glyph_observations(gs);checks={}
        if variant=='english':
            visible=metrics['visible'];checks=ui.check_glyphs(glyphs,visible,font);at=0
            for row,line in enumerate(visible.split('\n')):
                group=glyphs[at:at+len(line)];at+=len(line)
                if group:
                    check(all(g['y']==glyphs[0]['y']+12*(row-int(visible.startswith('\n'))) for g in group),'Story line wrapped or moved')
                    if e['layout']=='centered':check(abs(group[0]['x']-(208-metrics['line_widths'][row])//2)<=1,'Story centering changed')
            check(at==len(glyphs),'Extra journey glyphs')
        check(glyphs and not trace.errors,'No native journey glyphs/errors: '+str(trace.errors))
        name=e['id']+'-'+event['pointer_offset'][2:]+'-'+hero;session.capture(name)
        report={'id':e['id'],'hero':hero,'command_offset':event['command_offset'],'command_word':event['command_word'],
            'pointer_offset':event['pointer_offset'],'source':hex(source),'output_hex':native.hex(),'steps':call['steps'],
            'guards_intact':True,'checks':checks,'glyphs':glyphs,'formats':trace.formats,'screen':name+'.png'}
        write_json(session.output/(name+'.json'),report)
        return {k:v for k,v in report.items() if k not in ('glyphs','formats')}
    finally:trace.close()


def verify(variant='english',limit=None,checkpoint=None,range_start=None,range_end=None):
    global OUTPUT,CATALOG
    if checkpoint:
        OUTPUT=ROOT/'build/completion/checkpoints'/checkpoint;CATALOG=OUTPUT/'catalog.json'
    mgba.log.silence();rom=BASELINE if variant=='baseline' else OUTPUT/f'torneko3-story-completion-{variant}.gba'
    folder=OUTPUT/'verification'/variant;catalog=load_json(CATALOG);font=FontZero(ORIGINAL_ROM.read_bytes());cases=[];menus=[]
    chunked=range_start is not None or range_end is not None
    if chunked:
        check(limit is None and range_start is not None and range_end is not None,'Incomplete/conflicting chunk arguments')
        check(0<=range_start<range_end<=len(catalog['entries']),'Invalid story chunk')
        folder=folder/'chunks'/f'{range_start:04d}-{range_end:04d}'
    selected=catalog['entries'][range_start:range_end] if chunked else catalog['entries'][:limit] if limit else catalog['entries']
    with Session(rom.read_bytes(),folder) as session:
        tables=cold_tables(session);state=STATE.read_bytes()
        for i,e in enumerate(selected):
            for event in e['events']:
                if event['opcode']==0x98:continue
                for hero in (('Torneko','Tipper') if '$t' in e['japanese'] else ('Torneko',)):
                    cases.append(case(session,state,tables,e,event,variant,font,hero))
            if (i+1)%25==0:print(variant,i+1,'journey sources',flush=True)
        if not limit and (not chunked or range_end==len(catalog['entries'])):menus=verify_menus(session,state,tables,catalog,variant,font)
    report={'variant':variant,'source_sha256':digest(ORIGINAL_ROM.read_bytes()),'rom_sha256':digest(rom.read_bytes()),
        'catalog_sha256':digest(CATALOG.read_bytes()),'harness_sha256':digest(Path(__file__).read_bytes()),'fixture_sha256':digest(STATE.read_bytes()),
        'limited':bool(limit) or chunked,'range':[range_start,range_end] if chunked else None,'cases':cases,'menus':menus,'scope':'Controlled cursor selects each actual ROM event command. Native fetch/wrapper, guarded 1024-byte formatter and normal-frame rendering; original command/choice parameters unchanged. Both protagonists for every $t source; centered narration retains native alignment. Choice prefixes produce the original count, ordered records and terminator, then use the native generic menu drawer. These fixtures do not establish natural scenario reachability or choice outcomes.'}
    write_json(folder/'verification.json',report);return report


def verify_menus(session,state,tables,catalog,variant,font):
    from tools.verify_journey_labels import draw_checks
    groups={};original=ORIGINAL_ROM.read_bytes();core=session.core;results=[]
    for e in catalog['entries']:
        for ev in e['events']:
            if ev['opcode']==0x98:groups.setdefault(int(ev['prompt_command_offset'],0),{})[ev['choice_index']]=e
    for prompt,choices in sorted(groups.items()):
        words=choice_prefix(original,prompt);count=len(words)
        check(set(choices)==set(range(count)),'Incomplete reviewed choice menu')
        restore(session,state,tables);trace=ui.InterfaceTrace(core);name=f'choices-{prompt:08x}'
        try:
            controller=0x0203F000;write_bytes(core,controller,b'\0'*128);core.memory.u32[controller+0x24]=prompt+0x08000000
            dispatch=ui.native_step(session,trace,0x08064E28,[controller],stop=0x08066396)
            records=check_choices(core,prompt+0x08000000,count)
            drawing=ui.native_step(session,trace,0x0807B294,[0x02008B80,0,0,0],stop=0x0807B3B6)
            checks=draw_checks(trace,[choices[i] for i in range(count)],variant,font)
            check(not trace.errors,'Choice trace errors')
            session.frames(2);session.capture(name)
            row={'prompt_command_offset':hex(prompt),'dispatch':dispatch,'drawing':drawing,'records':records,'checks':checks,'screen':name+'.png'}
            write_json(session.output/(name+'.json'),dict(row,glyphs=trace.positions,payloads=trace.payloads));results.append(row)
        finally:trace.close()
    return results


def expected_cases():
    return {(e['id'],ev['pointer_offset'],h) for e in load_json(CATALOG)['entries'] for ev in e['events'] if ev['opcode']!=0x98 for h in (('Torneko','Tipper') if '$t' in e['japanese'] else ('Torneko',))}


def compare():
    a=load_json(OUTPUT/'verification/japanese/verification.json');b=load_json(OUTPUT/'verification/baseline/verification.json')
    check(len(a['cases'])==len(b['cases'])==len(expected_cases()),'Incomplete Japanese journey comparison')
    for x,y in zip(a['cases'],b['cases'],strict=True):
        check(all(x[k]==y[k] for k in ('id','hero','pointer_offset','output_hex')),'Japanese journey output differs')
        with Image.open(OUTPUT/'verification/japanese'/x['screen']) as first,Image.open(OUTPUT/'verification/baseline'/y['screen']) as second:
            check(ImageChops.difference(first.convert('RGB'),second.convert('RGB')).getbbox() is None,'Japanese relocation changed pixels')
    for x,y in zip(a.get('menus',[]),b.get('menus',[]),strict=True):
        check(x['prompt_command_offset']==y['prompt_command_offset'],'Different choice menu')
        check([r['raw_hex'] for r in x['checks']]==[r['raw_hex'] for r in y['checks']],'Japanese choice bytes differ')
        with Image.open(OUTPUT/'verification/japanese'/x['screen']) as first,Image.open(OUTPUT/'verification/baseline'/y['screen']) as second:
            check(ImageChops.difference(first.convert('RGB'),second.convert('RGB')).getbbox() is None,'Japanese choice relocation changed pixels')
    return len(a['cases'])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--variant',choices=['english','japanese','baseline'],default='english');p.add_argument('--limit',type=int);p.add_argument('--checkpoint')
    p.add_argument('--range-start',type=int);p.add_argument('--range-end',type=int)
    a=p.parse_args();verify(a.variant,a.limit,a.checkpoint,a.range_start,a.range_end)
