"""Native house selection/name handoff and companion menu flag combinations."""
import argparse
import struct
from pathlib import Path
import mgba.log
from tools import build_encounter_ui as b,verify_system_labels as system
from tools import verify_dungeon_interface as ui,verify_core_gameplay as old
from tools import verify_tutorial_gameplay as queue
from tools.build_first_label import ORIGINAL_ROM,digest
from tools.game_text import GameTextCodec
from tools.translation_pipeline import check,load_json,FontZero
from tools.verify_expansion import Session
from tools.verify_items import write_json
BASELINE=b.previous.OUTPUT/'torneko3-system-labels-english.gba'
STATE=system.STATE


def source(e,variant,report):
    if e['family']=='announcement' and variant=='baseline':return int.from_bytes(BASELINE.read_bytes()[0x337C0:0x337C4],'little')
    return 0x08000000+(int(e['offset'],0) if variant=='baseline' else report['encounter_ui']['relocated'][e['id']]['offset'])


def house_cases(s,caches,variant,report,entries):
    result=[];c=s.core;font=FontZero(ORIGINAL_ROM.read_bytes());codec=GameTextCodec(ORIGINAL_ROM.read_bytes())
    for hero in (0,1):
        for row in range(-1,20):
            queue.restore(s,STATE.read_bytes(),caches);c.memory.u32[0x02004F8C]=hero;system.guard(c,old.DEST,30);t=ui.InterfaceTrace(c);e=next(e for e in entries if e['family']=='house' and e['pointer_owners'][0]['row']==row)
            try:
                if row<0:ui.native_step(s,t,0x08034A96,[],stop=0x08034AA2,overrides={0x08034A96:{'r5':old.DEST,'r4':0}})
                else:ui.native_step(s,t,0x08034B80,[],stop=0x08034B9E,overrides={0x08034B80:{'r3':row,'r4':0x02004F8C,'r5':old.DEST}})
                system.guards(c,old.DEST,30);raw=old.cstring(c,old.DEST,30);check(raw==old.cstring(c,source(e,variant,report)),'House selector/copy differs')
                base=c.memory.u32[0x0200000C];field=0x0203F042;system.guard(c,field,30);c.memory.u32[0x0200000C]=field-0x1977A
                before=bytes(c.memory[field-8:field])+bytes(c.memory[field+30:field+38]);old.write_bytes(c,field,bytes(c.memory[old.DEST:old.DEST+30]));actors=bytes(c.memory[old.ACTOR:old.ACTOR+90])
                ui.native_step(s,t,0x0803376E,[],stop=0x08033780,overrides={0x0803376E:{'r2':0x0200000C,'r5':0}})
                c.memory.u32[0x0200000C]=base;system.guards(c,field,30);check(old.cstring(c,old.ACTOR,30)==raw and bytes(c.memory[old.ACTOR+30:old.ACTOR+90])==actors[30:],'House field-to-actor handoff differs');check(bytes(c.memory[field-8:field])+bytes(c.memory[field+30:field+38])==before,'House adjacent fields changed')
                narrative=c.memory.u32[0x080337C0];expected_source=old.cstring(c,narrative);formatted=old.guarded_format(s,t,narrative,cap=1000);check(formatted==expected_source.replace(b'$m0',raw[:-1]),'House announcement substitution differs')
                queue.prepare_queue(s,t);queued=queue.enqueue(s,t,narrative,formatted);check(old.cstring(c,old.ACTOR,30)==raw,'House queue changed name slot')
            finally:t.close()
            name=f'house-{hero}-{row+1:02d}';rendered=queue.render_queue(s,name,font,queued['rows_hex'],False)
            if variant=='english':
                text=''.join(old.visible(bytes.fromhex(r),codec) for r in queued['rows_hex']);rendered['checks']=[ui.check_glyphs(rendered['glyphs'],text,font)]
            r={'id':name,'source_id':e['id'],'hero':hero,'row':row,'name_hex':raw.hex(),'formatted_hex':formatted.hex(),'queue':queued,'guards_intact':True,'adjacent_fields_unchanged':True,**rendered};write_json(s.output/(name+'.json'),r);result.append({k:v for k,v in r.items() if k not in ('glyphs','payloads')})
    return result


def menu_cases(s,caches,variant):
    result=[];c=s.core;original=ORIGINAL_ROM.read_bytes()
    for base,count in b.MENUS:
        for enabled in range(8) if base==0xD9680 else (0,):
            queue.restore(s,STATE.read_bytes(),caches);flags=bytes((enabled>>i)&1 for i in range(3));old.write_bytes(c,0x02006B58,flags);t=ui.InterfaceTrace(c)
            try:
                for row in range(count):check(bytes(c.memory[base+0x08000004+row*12:base+0x0800000C+row*12])==original[base+4+row*12:base+12+row*12],'Companion menu flags/results changed')
                check(bytes(c.memory[base+0x08000000+count*12:base+0x08000000+(count+1)*12])==b'\0'*12,'Companion menu terminator changed')
                ui.native_step(s,t,0x0807B294,[base+0x08000000,0,0,0],stop=0x0807B3B6);check(len(t.payloads)==count,'Companion menu draw count differs')
                for d,row in zip(t.payloads,range(count),strict=True):
                    raw=old.cstring(c,c.memory.u32[base+0x08000000+row*12]);wanted=raw[1:] if raw.startswith(b'*') else raw;drawn=bytes.fromhex(d['raw_hex']).split(b'\0',1)[0]+b'\0';check(drawn[:2]==b'\x03\x05' and drawn[3:]==wanted,'Companion row identity/style differs')
                check(bytes(c.memory[0x02006B58:0x02006B5B])==flags,'Companion menu mutated availability');checks=system.draws(t,variant=='english');colours=[bytes.fromhex(d['raw_hex'])[2] for d in t.payloads];check(colours==([7 if enabled&(1<<i) else 2 for i in range(3)]+[7] if base==0xD9680 else [7]*count),'Companion availability colours differ');name=f'menu-{base:08x}-{enabled}';r={'id':name,'base':hex(base),'enabled':enabled,'rows':count,'flags_hex':flags.hex(),'guards_intact':True,'checks':checks,'colours':[bytes.fromhex(d['raw_hex'])[2] for d in t.payloads],'payloads':t.payloads,'glyphs':t.positions}
            finally:t.close()
            s.frames(2);s.capture(name);r['screens']=[name+'.png'];write_json(s.output/(name+'.json'),r);result.append({k:v for k,v in r.items() if k not in ('glyphs','payloads')})
    return result


def verify(variant):
    mgba.log.silence();rom=BASELINE if variant=='baseline' else b.OUTPUT/f'torneko3-encounter-ui-{variant}.gba';data=rom.read_bytes();report={} if variant=='baseline' else load_json(b.OUTPUT/f'{variant}-build.json');entries=load_json(b.OUTPUT/'catalog.json')['entries'];words=[]
    with Session(data,b.OUTPUT/'verification'/variant) as s:
        caches=queue.cold_tables(s)
        for e in entries:
            for p in e['pointer_owners']:
                at=int(p['offset'],0);wanted=source(e,variant,report);check(s.core.memory.u32[0x08000000+at]==wanted,'Encounter pointer differs');words.append({'word':hex(at),'source':hex(wanted)})
        houses=house_cases(s,caches,variant,report,entries);menus=menu_cases(s,caches,variant)
        r={'variant':variant,'rom_sha256':digest(data),'source_sha256':digest(ORIGINAL_ROM.read_bytes()),'catalog_sha256':digest((b.OUTPUT/'catalog.json').read_bytes()),'harness_sha256':digest(Path(__file__).read_bytes()),'helper_sha256':{**system.helper_hashes(),'verify_system_labels.py':digest(Path(system.__file__).read_bytes()),'verify_tutorial_gameplay.py':digest(Path(queue.__file__).read_bytes())},'fixture_sha256':digest(STATE.read_bytes()),'houses':houses,'menus':menus,'pointer_words':words,'screens':[p for c in houses+menus for p in c['screens']]};write_json(s.output/'verification.json',r);print(variant,len(houses),'house cases;',len(menus),'menu cases passed',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('variant',choices=('english','japanese','baseline'));a=p.parse_args();verify(a.variant)
