"""Native complete dialogue reader, NPC response rules and page verification."""
import argparse
from pathlib import Path
import mgba.log
from mgba._pylib import ffi
from PIL import Image,ImageChops
from tools import verify_ally_dialogue as prior
from tools import verify_tutorial_gameplay as queue
from tools import verify_core_gameplay as old,verify_dungeon_interface as ui
from tools.verify_ally_services import context
from tools.build_companion_dialogue import CATALOG,OUTPUT,ALTERNATES,encode
from tools.build_first_label import ORIGINAL_ROM,ROOT,digest
from tools.translation_pipeline import FontZero,load_json
from tools.verify_expansion import Session
from tools.verify_first_label import require
from tools.verify_items import write_json

BASELINE=ROOT/'build/ally-dialogue/torneko3-ally-dialogue-english.gba'
STATE=ROOT/'build/ally-dialogue/verification/save/world.state'
ACTOR=0x0203F000


def run_to(core,entry,stop,values,random_value=None):
    saved=context(core);cpu=ffi.cast('struct ARMCore*',core._core.cpu);random_calls=[]
    try:
        ui.registers(core,{'cpsr':255,'sp':0x03007E00,'lr':0x08000001,'pc':entry,**values})
        for steps in range(10000):
            pc=(int(cpu.gprs[15])&0xffffffff)-(2 if cpu.cpsr.packed&32 else 4)
            if pc==stop:return {'steps':steps,'registers':[int(cpu.gprs[i])&0xffffffff for i in range(13)],'random_calls':random_calls}
            if random_value is not None and pc in (0x0808DE30,0x0808DEC0):
                bound=int(cpu.gprs[0]) if pc==0x0808DE30 else 100
                require(0<=random_value<bound,'Invalid controlled PRNG return')
                random_calls.append({'entry':hex(pc),'bound':bound,'value':random_value})
                ui.registers(core,{'r0':random_value,'pc':int(cpu.gprs[14])&~1});continue
            core.step()
        raise RuntimeError(f'Native selector stalled: {entry:08x}/{pc:08x}')
    finally:ui.registers(core,saved)


def select(core,row,response,alternate=False):
    old.write_bytes(core,ACTOR,b'\0'*0x150);core.memory.u16[ACTOR+8]=row
    core.memory.u16[ACTOR+0xC4]=1;core.memory.u32[ACTOR]=2 if alternate else 0
    result=run_to(core,0x0803C3C8,0x0803C414,{'r0':ACTOR,'r1':response})
    return {'source':hex(result['registers'][6]),'steps':result['steps'],'row':row,'response':response,'controlled_rosa_flag':alternate}


def case(session,state,tables,e,variant,report,font,profile,species,prior_entry=False):
    queue.restore(session,state,tables);core=session.core
    values=prior.set_values(core,font,'normal' if profile=='tipper' else profile,species)
    if profile=='tipper':core.memory.u16[0x020014CE]=1;values['$t']='Tipper'
    if prior_entry:source=core.memory.u32[0x08000000+int(e['pointer_offset'],0)]
    else:source=0x08000000+(int(e['offset'],0) if variant=='baseline' else report['dialogue']['relocated'][e['id']]['offset'])
    alternate=e['family']=='rosa_alt';response=e['field']*5 if alternate else e['field']
    selected=select(core,e['row'],response,alternate)
    require(int(selected['source'],0)==source,'Full native dialogue selector chose wrong pointer')
    actor_slots=bytes(core.memory[old.ACTOR:old.ACTOR+60]);trace=ui.InterfaceTrace(core)
    try:raw=old.guarded_format(session,trace,source)
    finally:trace.close()
    english=variant=='english' or prior_entry
    if english:
        expected=(prior.encode if prior_entry else encode)(e,ORIGINAL_ROM.read_bytes())[0]
        for k,v in values.items():expected=expected.replace(k.encode(),v.encode())
        require(raw==expected,'Native formatter lost text/substitution')
    require(bytes(core.memory[old.ACTOR:old.ACTOR+60])==actor_slots,'Formatter changed adjacent name slots')
    name=f'{e["id"]}-{profile}';result={'id':e['id'],'row':e['row'],'field':e['field'],'family':e['family'],'profile':profile,
        'source':hex(source),'selector':selected,'formatted_hex':raw.hex(),'guards_intact':True,'screens':[]}
    if profile!='narrow':
        result.update(prior.dialogue_pages(session,source,name,font,raw[:-1].decode() if english else None))
        require(len(result['formats'])==1 and result['formats'][0]['output_hex']==raw.hex(),'Paged reader formatted differently')
    write_json(session.output/(name+'.json'),result)
    return {k:v for k,v in result.items() if k not in ('pages','formats')}|{'pages':len(result.get('pages',[]))}


def response_rules(session,state,tables):
    core=session.core;health=[];level=[];alternates=[]
    for row in range(200):
        special=row in (191,192)
        for hp in (39,40,79,80):
            for counter in ((0,3,4) if special else (0,)):
                choices=(0,) if counter==4 else range(5) if special else (0,99)
                for random_value in choices:
                    queue.restore(session,state,tables);old.write_bytes(core,ACTOR,b'\0'*0x150)
                    core.memory.u16[ACTOR+8]=row;core.memory.u32[ACTOR+0x54]=hp;core.memory.u32[ACTOR+0x58]=100;core.memory.u8[ACTOR+0x13B]=counter
                    result=run_to(core,0x0803C2BC,0x0803C34A,{'r0':ACTOR},random_value)
                    band=2 if hp<40 else 1 if hp<80 else 0
                    expected=(19 if counter==4 else band*5+random_value) if special else band*2+(random_value<50)
                    require(result['registers'][6]==expected,'Wrong native health/NPC response')
                    require(len(result['random_calls'])==(0 if counter==4 else 1),'Unexpected PRNG use')
                    require(core.memory.u8[ACTOR+0x13B]==counter+int(special),'NPC talk counter differs')
                    health.append({'row':row,'hp':hp,'max_hp':100,'counter_before':counter,'counter_after':core.memory.u8[ACTOR+0x13B],
                        'random_value':random_value,'response':expected,'random_calls':result['random_calls']})
        for entry,stop,actor_reg,result_reg in ((0x08025EDA,0x08025F04,'r4',7),(0x080378C0,0x080378F4,'r5',4)):
            for random_value in range(4 if special else 2):
                queue.restore(session,state,tables);old.write_bytes(core,ACTOR,b'\0'*0x150);core.memory.u16[ACTOR+8]=row
                result=run_to(core,entry,stop,{actor_reg:ACTOR},random_value);expected=(15 if special else 6)+random_value
                require(result['registers'][result_reg]==expected and len(result['random_calls'])==1,'Wrong native level-up index')
                require(result['random_calls'][0]['bound']==(4 if special else 2),'Wrong level-up choice range')
                level.append({'row':row,'entry':hex(entry),'random_value':random_value,'response':expected})
    for response in (*range(20),-1,20):
        for flag in (False,True):
            # Out-of-row inputs test the clamp only with the override enabled.
            # The preliminary word load still runs; only the final pointer is used.
            if not flag and not 0<=response<20:continue
            queue.restore(session,state,tables);result=select(core,191,response,flag)
            offset=ALTERNATES+max(0,min(2,int(response/5)))*4 if flag else 0x1A60B0+191*80+response*4
            require(int(result['source'],0)==core.memory.u32[0x08000000+offset],'Rosa override/clamp differs')
            alternates.append(result)
    return {'health':health,'level_up':level,'rosa_overrides':alternates}


def profiles(e,variant):
    result=['normal','stress','narrow'] if variant=='english' else ['normal']
    if any(t['kind']=='dollar_command' and t['text']=='$t' for t in e['source_tokens']):result.append('tipper')
    return result


def verify(variant='english',limit=None):
    mgba.log.silence();rom=BASELINE if variant=='baseline' else OUTPUT/f'torneko3-companion-dialogue-{variant}.gba'
    report={} if variant=='baseline' else load_json(OUTPUT/f'{variant}-build.json');folder=OUTPUT/'verification'/variant
    catalog=load_json(CATALOG);font=FontZero(ORIGINAL_ROM.read_bytes());cases=[]
    names={e['row']:e['english'] for e in load_json(ROOT/'translations/enemies.json')['entries'] if e['family']=='name'}
    with Session(rom.read_bytes(),folder) as session:
        tables=queue.cold_tables(session);state=STATE.read_bytes()
        for index,e in enumerate(catalog['entries'][:limit] if limit else catalog['entries']):
            for profile in profiles(e,variant):cases.append(case(session,state,tables,e,variant,report,font,profile,names[e['row']]))
            if (index+1)%100==0:print(variant,index+1,'dialogue sources',flush=True)
        rules=response_rules(session,state,tables) if not limit else {}
        history=prior.history_cases(session,state,tables,report,font) if variant=='english' and not limit else []
        regression=[]
        if variant=='english' and not limit:
            for e in load_json(prior.CATALOG)['entries']:
                if e['row'] in (1,18,35,50) and e['field'] in (0,7):regression.append(case(session,state,tables,e,variant,report,font,'normal',names[e['row']],True))
    result={'source_sha256':digest(ORIGINAL_ROM.read_bytes()),'rom_sha256':digest(rom.read_bytes()),'catalog_sha256':digest(CATALOG.read_bytes()),
        'harness_sha256':digest(Path(__file__).read_bytes()),'page_helper_sha256':digest((ROOT/'tools/verify_ally_dialogue.py').read_bytes()),
        'queue_helper_sha256':digest((ROOT/'tools/verify_tutorial_gameplay.py').read_bytes()),'fixture_state_sha256':digest(STATE.read_bytes()),
        'limited':bool(limit),'cases':cases,'response_rules':rules,'cold_initialized_tables':tables,'history_cases':history,'prior_dialogue_cases':regression,
        'screens':[s for c in cases+history+regression for s in c['screens']],
        'scope':'Original dialogue selector through Rosa override, guarded formatter and paged engine. Controlled actor/name slots and Rosa condition; glyph delay, frame yield and input waits bypassed. Native HP, talk-counter and both level-up selector slices use controlled PRNG returns. Natural recruitment, inventory condition, abilities, nickname copying, progression and history persistence remain separate.'}
    write_json(folder/'verification.json',result);print(variant,'passed',len(cases),'dialogue profiles',flush=True);return result


def compare():
    ja=load_json(OUTPUT/'verification/japanese/verification.json');base=load_json(OUTPUT/'verification/baseline/verification.json')
    require(not ja['limited'] and not base['limited'] and ja['screens']==base['screens'],'Incomplete Japanese controls')
    for name in ja['screens']:
        with Image.open(OUTPUT/'verification/japanese'/name) as x,Image.open(OUTPUT/'verification/baseline'/name) as y:
            require(ImageChops.difference(x.convert('RGB'),y.convert('RGB')).getbbox() is None,f'Japanese relocation changed pixels: {name}')
    return len(ja['screens'])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--variant',choices=['english','japanese','baseline'],default='english');p.add_argument('--limit',type=int)
    args=p.parse_args();verify(args.variant,args.limit)
