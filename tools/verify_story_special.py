"""Native pet substitutions, bounded story pages and Japanese relocation controls."""
import argparse
from pathlib import Path
from collections import Counter
import mgba.log
from PIL import Image,ImageChops
from tools import build_story_special as b
from tools import verify_dungeon_interface as ui
from tools.verify_expansion import Session
from tools.verify_tutorial_gameplay import cold_tables,restore
from tools.verify_opening_story import STATE
from tools.verify_core_gameplay import write_bytes,cstring,guarded_format
from tools.verify_items import distinct_glyph_observations,write_json
from tools.verify_story_completion import STOPS
from tools.build_name_entry import LATIN
from tools.translation_pipeline import FontZero,load_json,check
from tools.build_first_label import ORIGINAL_ROM,ROOT,digest

OUTPUT=b.OUTPUT
BASELINE=ROOT/'build/completion/checkpoints/story-pages/torneko3-story-completion-english.gba'
PROFILES={'latin':{'$p1':'Biscuit','$p2':'Mittens'},'wide_latin':{'$p1':'WWWWWWW','$p2':'WWWWWWW'},'legacy_japanese':{'$p1':'あああああああ','$p2':'あああああああ'}}


def compact(text,original):
    result=[];mapping=original[0xC4696C:0xC4696C+0xBF*2]
    for c in text:
        if c in LATIN:result.append(LATIN[c]);continue
        raw=c.encode('cp932');ids=[i for i in range(0xBF) if mapping[i*2:i*2+2]==raw]
        check(len(ids)==1,'No unambiguous legacy compact glyph');result.append(ids[0])
    check(len(result)<=7,'Pet fixture exceeds native slots')
    return result


def seed(core,values,original):
    for key,index in (('$p1',0x57),('$p2',0x5F)):
        ids=compact(values[key],original)
        for i in range(7):core.memory.u16[0x020010C0+2*(index+i)]=ids[i] if i<len(ids) else 0


def expected_cases(catalog):
    return {(e['id'],ev['pointer_offset'],hero,profile) for e in catalog['entries'] if e['layout']!='keyword'
        for ev in e['events'] for hero in (('Torneko','Tipper') if '$t' in e['japanese'] else ('Torneko',))
        for profile in (PROFILES if '$p' in e['japanese'] else ('latin',))}


def verify(variant):
    mgba.log.silence();original=ORIGINAL_ROM.read_bytes();catalog=load_json(OUTPUT/'catalog.json');font=FontZero(original)
    rom=BASELINE if variant=='baseline' else OUTPUT/f'torneko3-story-special-{variant}.gba';data=rom.read_bytes();results=[]
    with Session(data,OUTPUT/'verification'/variant) as s:
        tables=cold_tables(s);state=STATE.read_bytes()
        for e in catalog['entries']:
            if e['layout']=='keyword':continue
            for ev in e['events']:
                for hero in (('Torneko','Tipper') if '$t' in e['japanese'] else ('Torneko',)):
                    for profile in (PROFILES if '$p' in e['japanese'] else ('latin',)):
                        restore(s,state,tables);core=s.core;values={**PROFILES[profile],'$t':hero};seed(core,values,original)
                        core.memory.u16[0x020014CE]=int(hero=='Tipper')
                        neighbors=[core.memory.u16[a] for a in (0x0200116C,0x0200117C,0x0200118C)]
                        controller=0x0203F000;command=int(ev['command_offset'],0)+0x08000000;source=core.memory.u32[command+4]
                        write_bytes(core,controller,b'\0'*128);core.memory.u32[controller+0x24]=command
                        trace=ui.InterfaceTrace(core);name=e['id']+'-'+ev['pointer_offset'][2:]+'-'+hero+'-'+profile;trace.phase=name
                        try:
                            formatted=guarded_format(s,trace,source,cap=1024)
                            call=ui.native_step(s,trace,0x08064E28,[controller],stop=STOPS[ev['opcode']])
                            root=core.memory.u32[0x03000010];native=cstring(core,root+0x5C,1024)
                            raw,metrics=b.encode(e,original,values);expected=raw if variant=='english' else bytes.fromhex(e['source_hex'])
                            for key,value in values.items():expected=expected.replace(key.encode(),value.encode('cp932'))
                            check(native==formatted==expected,'Special native output differs')
                            s.frames(480,trace)
                            glyphs,_=distinct_glyph_observations([g for g in trace.positions if g['caller']=='0x08061B4E' and int(g['source'] or '0',0)==source])
                            checks={}
                            if variant=='english':
                                checks=ui.check_glyphs(glyphs,metrics['visible'],font);n=0
                                for row,line in enumerate(metrics['visible'].split('\n')):
                                    group=glyphs[n:n+len(line)];n+=len(line)
                                    check(all(g['y']==glyphs[0]['y']+12*row for g in group),'Special line wrapped unexpectedly')
                                check(n==len(glyphs),'Extra special glyphs')
                            check(glyphs and not trace.errors,'Missing special glyphs/trace errors')
                            check(neighbors==[core.memory.u16[a] for a in (0x0200116C,0x0200117C,0x0200118C)],'Pet formatter changed adjacent variables')
                            s.capture(name);result={'id':e['id'],'pointer_offset':ev['pointer_offset'],'hero':hero,'profile':profile,'source':hex(source),'output_hex':native.hex(),'call':call,'checks':checks,'guards_intact':True,'screen':name+'.png'}
                            write_json(s.output/(name+'.json'),dict(result,glyphs=glyphs));results.append(result)
                        finally:trace.close()
            print(variant,e['id'],len(results),flush=True)
    check({(x['id'],x['pointer_offset'],x['hero'],x['profile']) for x in results}==expected_cases(catalog),'Incomplete special cases')
    report={'variant':variant,'rom_sha256':digest(data),'source_sha256':digest(original),'catalog_sha256':digest((OUTPUT/'catalog.json').read_bytes()),'harness_sha256':digest(Path(__file__).read_bytes()),'fixture_sha256':digest(STATE.read_bytes()),'cases':results,'scope':'Controlled actual event dispatch and normal-frame rendering. Both heroes where substituted; seven-letter Latin, wide Latin and seven fullwidth Japanese pet names; guarded native formatter and neighboring variables. Keyword comparison and save persistence are separate checks.'}
    write_json(OUTPUT/'verification'/variant/'verification.json',report)
    return report


def compare():
    a=load_json(OUTPUT/'verification/japanese/verification.json');z=load_json(OUTPUT/'verification/baseline/verification.json')
    expected=expected_cases(load_json(OUTPUT/'catalog.json'));check(len(a['cases'])==len(z['cases'])==len(expected),'Incomplete Japanese special comparison')
    for x,y in zip(a['cases'],z['cases'],strict=True):
        check(all(x[k]==y[k] for k in ('id','pointer_offset','hero','profile','output_hex')),'Different Japanese special cases')
        with Image.open(OUTPUT/'verification/japanese'/x['screen']) as p,Image.open(OUTPUT/'verification/baseline'/y['screen']) as q:
            check(ImageChops.difference(p.convert('RGB'),q.convert('RGB')).getbbox() is None,'Japanese special relocation changed pixels')
    return len(expected)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('variant',choices=('english','japanese','baseline','compare'));a=p.parse_args()
    print(compare()) if a.variant=='compare' else verify(a.variant)
