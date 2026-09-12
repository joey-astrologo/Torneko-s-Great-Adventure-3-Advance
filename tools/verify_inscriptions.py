"""All English and legacy kana inscriptions through native matching/list readers."""
import argparse
import struct
from pathlib import Path
import mgba.log
from tools import build_inscriptions as b,verify_keyboard_completion as keyboard
from tools import verify_core_gameplay as old,verify_dungeon_interface as ui,verify_tutorial_gameplay as queue
from tools.build_first_label import ORIGINAL_ROM,digest
from tools.build_name_entry import LATIN
from tools.game_text import GameTextCodec
from tools.translation_pipeline import check,load_json,FontZero
from tools.verify_items import install_item,write_json
from tools.verify_expansion import Session
from tools.verify_opening_story import STATE

BASELINE=b.previous.OUTPUT/'torneko3-keyboard-completion-english.gba'
ITEM=0x0200A480
INPUT=0x0203F300
DECODE=0x0203F400
SOURCE=0x0203F000
IDS=0x0203F600
LEARNED=0x02002549


def restore(s,caches):queue.restore(s,STATE.read_bytes(),caches)


def test_cases(entries,variant,original):
    cases=[]
    for e in entries[::2]:
        row=e['row'];a,z=struct.unpack_from('<II',original,b.TABLE+row*12);h=old_rom_string(original,a-0x08000000);k=old_rom_string(original,z-0x08000000)
        check(len(h)==len(k) and (len(h)-1)%2==0,'Kana aliases are not paired characters')
        mixed=b''.join((h if i%4==0 else k)[i:i+2] for i in range(0,len(h)-1,2))+b'\0'
        for spelling,raw in (('hira',h),('kata',k),('mixed',mixed)):
            cases.append({'id':f'legacy-{row:02d}-{spelling}','row':row,'input_japanese_hex':raw.hex(),'learned':True,'flags':0x81800000,'item_before':198,'item_after':e['item_id']})
        for spelling,raw in (('hira',h),('kata',k)):
            cases.append({'id':f'legacy-unlearned-{row:02d}-{spelling}','row':row,'input_japanese_hex':raw.hex(),'learned':False,'flags':0x81800000,'item_before':198,'item_after':224})
        if variant=='english':
            for case,text in (('display',e['english']),('lower',e['english'].lower()),('upper',e['english'].upper()),('mixed',''.join(ch.lower() if i%2 else ch.upper() for i,ch in enumerate(e['english'])))):
                cases.append({'id':f'english-{row:02d}-{case}','row':row,'input_english':text,'learned':True,'flags':0x81800000,'item_before':198,'item_after':e['item_id']})
            for key in ('unlearned','only-other-learned'):
                cases.append({'id':f'english-{row:02d}-{key}','row':row,'input_english':e['english'],'learned':False,'other_learned':key=='only-other-learned','flags':0x81800000,'item_before':198,'item_after':224})
    for label,flags,item,expected in (('ordinary',0x81800000,1,1),('already-inscribed',0x81880000,198,198),('blocked',0x81840000,198,224),('bare',0,198,192)):
        cases.append({'id':'flags-'+label,'row':0,'input_japanese_hex':old_rom_string(original,int(entries[0]['offset'],0)).hex(),'learned':True,'flags':flags,'item_before':item,'item_after':expected})
    for i,text in enumerate(('','X','WWWWWWW','BangX','Ban','BANG123')):
        cases.append({'id':f'unknown-{i}','row':0,'input_english':text,'learned':True,'flags':0x81800000,'item_before':198,'item_after':224})
    return cases


def old_rom_string(original,at):return original[at:original.index(0,at)+1]


def matching(s,caches,case,entries,original):
    restore(s,caches);c=s.core;t=ui.InterfaceTrace(c)
    try:
        old.write_bytes(c,LEARNED,b'\xff'*8 if case['learned'] else b'\0'*8)
        if case.get('other_learned'):
            index=entries[(case['row']+1)%49*2]['item_id']-190;c.memory.u8[LEARNED+index//8]|=1<<(index%8)
        learned=bytes(c.memory[LEARNED:LEARNED+8]);old.write_bytes(c,INPUT-8,old.GUARD+b'\0'*32+old.GUARD)
        if 'input_japanese_hex' in case:
            raw=bytes.fromhex(case['input_japanese_hex']);old.write_bytes(c,SOURCE,raw);ui.native_step(s,t,0x0807D29C,[0,INPUT,SOURCE]);compact=old.cstring(c,INPUT,32)
        else:raw=case['input_english'].encode()+b'\0';compact=bytes(LATIN[ch] for ch in case['input_english'])+b'\0';old.write_bytes(c,INPUT,compact)
        check(len(compact)<=8,'Inscription fixture exceeded original compact field')
        old.write_bytes(c,DECODE-8,old.GUARD+b'\xa5'*64+old.GUARD);ui.native_step(s,t,0x0807D228,[0,DECODE,INPUT]);decoded=old.cstring(c,DECODE,64);check(decoded==raw,'Inscription codec roundtrip differs '+case['id'])
        install_item(c,ITEM,case['item_before']);c.memory.u32[ITEM]=case['flags'];old.write_bytes(c,ITEM+4,compact.ljust(8,b'\0'));before=bytes(c.memory[ITEM-8:ITEM+32]);call=ui.native_step(s,t,0x0807F130,[ITEM,INPUT]);after=bytes(c.memory[ITEM-8:ITEM+32])
        check(c.memory.u16[ITEM+14]==case['item_after'],'Wrong inscription item '+case['id']+' '+str(c.memory.u16[ITEM+14]))
        check(before[:8]==after[:8] and before[32:]==after[32:],'Inscription crossed item record')
        check(bytes(c.memory[ITEM+4:ITEM+12])==compact.ljust(8,b'\0'),'Matcher changed inscription bytes')
        check(bytes(c.memory[LEARNED:LEARNED+8])==learned,'Matching changed learned flags')
        for at,size in ((INPUT,32),(DECODE,64)):check(bytes(c.memory[at-8:at])==old.GUARD and bytes(c.memory[at+size:at+size+8])==old.GUARD,'Inscription guard overwrite')
        return dict(case,compact_hex=compact.hex(),decoded_hex=decoded.hex(),item_before_hex=before[8:32].hex(),item_after_hex=after[8:32].hex(),learned_hex=learned.hex(),guards_intact=True,call=call)
    finally:t.close()


def lists(s,caches,variant,entries,original):
    results=[];font=FontZero(original)
    for start in range(0,49,8):
        restore(s,caches);c=s.core;t=ui.InterfaceTrace(c);name=f'learned-list-{start:02d}'
        try:
            raw=struct.pack('<49H',*[e['item_id'] for e in entries[::2]]);old.write_bytes(c,IDS-8,old.GUARD+raw+old.GUARD)
            # Original constructor supplies the real window descriptor and rows.
            old.write_bytes(c,LEARNED,b'\xff'*8);ui.native_step(s,t,0x08070540,[0,ITEM,0],stop=0x080705C2)
            t.positions.clear();t.payloads.clear();ui.native_step(s,t,0x08070798,[0,min(8,49-start),start,IDS,49]);check(len(t.payloads)==min(8,49-start),'Learned list lost rows');rows=[]
            for index,d in enumerate(t.payloads):
                e=entries[(start+index)*2];source=old.cstring(c,c.memory.u32[c.memory.u32[0x080707E0]+e['row']*12],64);expected=b'%2d\x03\x09\x14: %s\0'%(start+index+1,source[:-1]);check(bytes.fromhex(d['raw_hex']).startswith(expected),'Native learned-list format differs');gs=[g for g in t.positions if g['draw_serial']==d['serial']];ink=keyboard.ink_check(gs,original,vertical=False)
                if variant=='english':check(source==b.encode(e,original),'Wrong displayed inscription');check([g['code'] for g in gs]==[font.glyph(ch)[0] for ch in old.visible(expected,GameTextCodec(original))],'English inscription glyphs differ')
                check(len(expected)<=32,'Learned-list stack printf overflow');rows.append({'row':e['row'],'item_id':e['item_id'],'formatted_hex':expected.hex(),'ink':ink})
            check(bytes(c.memory[IDS-8:IDS])==old.GUARD and bytes(c.memory[IDS+98:IDS+106])==old.GUARD and bytes(c.memory[IDS:IDS+98])==raw,'Learned-list array changed');s.frames(2);s.capture(name);result={'id':name,'rows':rows,'screen':name+'.png','guards_intact':True};write_json(s.output/(name+'.json'),dict(result,payloads=t.payloads,glyphs=t.positions));results.append(result)
        finally:t.close()
    return results


def learned_selections(s,caches,entries):
    results=[];ids=[e['item_id'] for e in entries[::2]]
    for label,wanted in [('all',ids),('none',[])]+[(str(i),[i]) for i in ids]:
        restore(s,caches);c=s.core;old.write_bytes(c,LEARNED,b'\0'*8)
        for item in wanted:
            bit=item-190;c.memory.u8[LEARNED+bit//8]|=1<<(bit%8)
        t=ui.InterfaceTrace(c)
        try:ui.native_step(s,t,0x08070540,[0,ITEM,0],stop=0x080705A6)
        finally:t.close()
        selected=[c.memory.u16[0x03007AE4+i*2] for i in range(370)]
        check(selected==wanted+[0]*(370-len(wanted)),'Native learned-list selection differs')
        results.append({'case':label,'selected_item_ids':wanted,'unused_slots_zero':True})
    return results


def verify(variant,limit=None):
    mgba.log.silence();original=ORIGINAL_ROM.read_bytes();rom=BASELINE if variant=='baseline' else b.OUTPUT/f'torneko3-inscriptions-{variant}.gba';data=rom.read_bytes();entries=load_json(b.OUTPUT/'catalog.json')['entries'];cases=[]
    with Session(data,b.OUTPUT/'verification'/variant) as s:
        caches=queue.cold_tables(s);allcases=test_cases(entries,variant,original)
        for case in allcases[:limit] if limit else allcases:
            cases.append(matching(s,caches,case,entries,original))
            if len(cases)%49==0:print(variant,len(cases),'matching cases passed',flush=True)
        pages=[] if limit else lists(s,caches,variant,entries,original);selections=[] if limit else learned_selections(s,caches,entries)
        result={'variant':variant,'rom_sha256':digest(data),'source_sha256':digest(original),'catalog_sha256':digest((b.OUTPUT/'catalog.json').read_bytes()),'harness_sha256':digest(Path(__file__).read_bytes()),'fixture_sha256':digest(STATE.read_bytes()),'limited':bool(limit),'cases':cases,'lists':pages,'learned_selections':selections,'screens':[p['screen'] for p in pages],'scope':'Controlled native matcher: 49 identities, both original kana spellings/mixed kana, learned/unlearned English letter cases, other learned IDs, eligibility flags and unknown names. Original compact decoder, guarded 24-byte records/input/64-byte decode, unchanged learned flags. All 49 native learned-list rows. Full inscription gameplay/effect consumption and save persistence are separate.'};write_json(s.output/'verification.json',result);print(variant,len(cases),'inscription cases passed',flush=True)
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('variant',choices=('english','japanese','baseline'));p.add_argument('--limit',type=int);a=p.parse_args();verify(a.variant,a.limit)
