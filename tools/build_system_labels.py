"""Remaining frontend, object, equipment and growth labels with bounded readers."""
import argparse
from collections import Counter
import json
import struct
from tools import build_world_completion as previous,build_arena_services as paged,build_core_gameplay as core
from tools.build_first_label import ORIGINAL_ROM,ROOT,digest
from tools.game_text import GameTextCodec,PRINTF,rebuild
from tools.translation_pipeline import check,load_json,atomic_write,FontZero
from tools.rom_build import RomBuild
CATALOG=ROOT/'translations/system-labels.json'
OUTPUT=ROOT/'build/completion/system-labels'
DRAFTS={0x9B4DC:'Dungeon menu',0x9B4F4:'Entering %s',0x9B51C:'Back to Start Menu',0x9B534:'About Extra Mode',0x9B54C:'Enter Trial of illusion',0x9B564:'Enter Otherworld trial',0x9B578:'Enter Trial of sealing',0x9B58C:'Enter New World trial',0x9B5F8:'Play as Torneko',0x9B60C:'Play as Tipper',0x9B620:'Travel with Ines',0x9B634:'Travel with Rosa',0x9B66C:'Too many monster allies are coming along!',0x9B6A0:'Adventure',0x9B6AC:'Try again?',0x9B6C4:'Restart this dungeon with one Big bread?',0xA6900:'Adventure',0xA690C:'Too many monster allies are coming along!',0xA6940:'Adventure',0xA6948:'Save this adventure to an Adventure Log and quit for now?',0xA6700:'Wind pillar',0xA6708:'Sand pillar',0xA6710:'Ice',0xA6714:'Fire pillar',0xA6720:'Unknown object',0x1B446D:'Max +%d',0x1B447E:"Can't see it.",0x1B4484:'Marks[%d]',0x1B448D:'Power[%d]',0xC3DA2C:'{hex:0312}{hex:030504}Item after synthesis'}
GROWTH=('Torneko','Tipper','Rosa','Ines','Versatile / late','Attack / special','Defence / late','Defence / early','Attack / late','Attack / early','Guard / special','Normal / early')
MESSAGES={0x9B66C,0x9B6AC,0x9B6C4,0xA690C,0xA6948}
SMALL_CONTEXT={0x9B6A0,0xA6900,0xA6940}
TYPED=set(range(0x9B504,0x9B51C,4))|set(range(0xA66F0,0xA6700,4))|set(range(0x1B994C,0x1B997C,4))


def extract(original):
    codec=GameTextCodec(original);master={int(e['offset'],0):e for e in load_json(ROOT/'translations/master.json')['entries']};offsets=list(DRAFTS)+[struct.unpack_from('<I',original,w)[0]-0x08000000 for w in range(0x1B994C,0x1B997C,4)];entries=[]
    for at in offsets:
        m=master[at];s=codec.parse(original,at);check(rebuild(s['tokens'])==original[at:s['end']],'System source roundtrip');owners=[];excluded=[]
        for value in m['pointer_candidates']:
            word=int(value,0);check(struct.unpack_from('<I',original,word)[0]==at+0x08000000,'System source pointer differs')
            if word>=0xCE0000:excluded.append({'offset':hex(word),'reason':'Unreviewed high data-array reference'});continue
            loads=[] if word in TYPED else [i for i in range(max(0,word-1024),word,2) if original[i+1]&0xf8==0x48 and ((i+4)&~3)+original[i]*4==word]
            check(word in TYPED or word<0xF0000 and loads,'System owner lacks reviewed reader');owners.append({'offset':hex(word),'evidence':'typed_pointer_word' if word in TYPED else 'thumb_literal','loads':[hex(i+0x08000000) for i in loads]})
        check(owners,'System source lacks owner');family='visibility' if at==0x1B447E else 'message' if at in MESSAGES else 'extra_menu' if 0x9B51C<=at<=0x9B58C else 'party_menu' if 0x9B5F8<=at<=0x9B634 else 'object' if 0xA6700<=at<=0xA6720 else 'growth' if 0x1B98D6<=at<=0x1B993F else 'entry_summary' if at==0x9B4F4 else 'equipment_cap' if at==0x1B446D else 'equipment_stat' if at in (0x1B4484,0x1B448D) else 'synthesis_heading' if at==0xC3DA2C else 'label'
        entries.append({'id':f'system-label.{at:08x}','family':family,'offset':hex(at),'source_end_exclusive':hex(s['end']),'japanese':s['display'],'source_hex':s['raw_hex'],'source_tokens':s['tokens'],'master_id':m['id'],'pointer_owners':owners,'excluded_owners':excluded,'allocation_min_bytes':23 if at==0x9B4DC else 0,'english':None,'display':None,'notes':'','references':[]})
    check(len(entries)==42,'System source count differs');return {'schema':1,'base_sha256':digest(original),'font':0,'entries':entries}


def encode(e,original):
    if e['family']=='message':return paged.encode(e,original)
    text=e['display'] or e['english'];check(isinstance(text,str) and text and all(32<=ord(ch)<127 for ch in text),'System label must be one ASCII line with typed controls');raw=b'';last=0
    for m in core.HEX.finditer(text):raw+=text[last:m.start()].encode()+bytes.fromhex(m[1]);last=m.end()
    raw+=text[last:].encode()+b'\0';check(b'{' not in raw and b'}' not in raw,'Unknown system markup');p=GameTextCodec(original).parse(raw,0);check(p['end']==len(raw),'Embedded system terminator')
    check(PRINTF.findall(raw)==PRINTF.findall(bytes.fromhex(e['source_hex'])),'System printf arguments changed');binary=lambda ts:[t['raw_hex'] for t in ts if t['kind']=='binary_control'];check(binary(p['tokens'])==binary(e['source_tokens']),'System binary controls changed')
    check(not any(t['kind']=='dollar_command' for t in p['tokens']+e['source_tokens']),'Unreviewed system dollar command')
    plain=core.HEX.sub('',text);values=[plain]
    if '%s' in plain:
        names=[x['display'] or x['english'] for x in load_json(ROOT/'translations/dungeon-interface.json')['entries'] if x['family']=='dungeon' for _ in x['rows']];check(len(names)==64,'System summary dungeon inventory differs');values=[plain%n for n in names]
    elif '%d' in plain:values=[plain%n for n in ((0,99) if e['family']=='equipment_cap' else (-2147483648,2147483647))]
    font=FontZero(original);widths=[sum(font.glyph(ch)[1] for ch in value) for value in values];limit=48 if e['family']=='equipment_cap' else 92 if e['family']=='growth' else 140 if e['family'] in ('extra_menu','party_menu') else 208
    check(max(widths)<=limit,'System label exceeds field '+e['id']+' '+str(max(widths)))
    cap=5 if int(e['offset'],0) in SMALL_CONTEXT else 30 if e['family']=='object' else 64 if e['family'] in ('entry_summary','equipment_stat','equipment_cap') else 23 if e['allocation_min_bytes'] else 512
    check(max(len(v.encode())+1 for v in values)<=cap,'System label exceeds byte buffer');return raw,{'line_widths':widths,'width_limit':limit,'capacity':cap,'bytes_including_nul':len(raw),'formatted_byte_upper_bound':max(len(v.encode())+1 for v in values),'allocation_min_bytes':e['allocation_min_bytes']}


def prepare():
    original=ORIGINAL_ROM.read_bytes();c=extract(original);existing={e['id']:e for e in load_json(CATALOG)['entries']} if CATALOG.exists() else {};g=load_json(ROOT/'translations/glossary.json')['terms'];growth=0
    for e in c['entries']:
        if e['family']=='growth':e['english']=GROWTH[growth];growth+=1
        else:e['english']=DRAFTS[int(e['offset'],0)]
        e['notes']='Independent original-source label; original table identities, pointer owners and reader capacities are retained. Native layout/copy checks required before acceptance.'
        if e['family']=='growth':e['notes']+=' Growth categories are project labels; Tipper retains the row-1 character identity despite the original glyph-decoder display ポポ口.'
        for term in g:
            if any(j in e['japanese'] and len(j)>=3 for j in term['japanese']) and term['english'].lower() in e['english'].lower():e['references'].append(term['id'])
        if int(e['offset'],0)==0x1B4484:e['references']=['effect.001b728e']
        if int(e['offset'],0)==0x1B98DF:e['references']=[next(t['id'] for t in g if t['english']=='Tipper' and 'ポポロ' in t['japanese'])]
        if e['id'] in existing:
            for k in ('english','display','notes','references'):e[k]=existing[e['id']][k]
        encode(e,original)
    atomic_write(CATALOG,(json.dumps(c,ensure_ascii=False,indent=2)+'\n').encode());atomic_write(OUTPUT/'source-owners.json',(json.dumps({'source_sha256':digest(original),'entries':extract(original)['entries'],'scope':'42 resources with checked literal/typed pointer owners; high data-array references excluded. Original tables, source text, byte capacities and save fields stay occupied. Fixed 23-byte summary copy requires allocated padding.'},ensure_ascii=False,indent=2)+'\n').encode());print('Prepared',len(c['entries']),'system resources',flush=True)


def validate(original,c):
    fresh=extract(original);check(all(c[k]==fresh[k] for k in ('schema','base_sha256','font')),'System catalog header differs');check(len(c['entries'])==42,'System catalog count differs')
    for e,f in zip(c['entries'],fresh['entries'],strict=True):check(all(e[k]==f[k] for k in f.keys()-{'english','display','notes','references'}),'System source metadata differs');encode(e,original)
    return c['entries']


def build_rom(original,language='english',catalog=None,*,build=None):
    check(language in ('english','japanese'),'System build language');b=RomBuild(original) if build is None else build;_,prior=previous.build_rom(original,build=b);c=load_json(CATALOG) if catalog is None else catalog;entries=validate(original,c);relocated={}
    for e in entries:
        at=int(e['offset'],0);source=bytes.fromhex(e['source_hex']);raw,metrics=encode(e,original);b.protect_source(e['id'],at,at+len(source),'system-labels');payload=(raw if language=='english' else source).ljust(e['allocation_min_bytes'],b'\0');dest=b.allocate(e['id'],payload,'system-labels')
        for p in e['pointer_owners']:b.patch(e['id']+'.'+p['offset'],int(p['offset'],0),struct.pack('<I',at+0x08000000),struct.pack('<I',dest+0x08000000),'system-labels',p['evidence'])
        relocated[e['id']]={'offset':dest,'metrics':metrics}
    data,ledger=b.finish();return data,{'source_sha256':digest(original),'rom_sha256':digest(data),'previous_rom_sha256':prior['rom_sha256'],'language':language,'system_labels':{'resources':42,'pointer_words':sum(len(e['pointer_owners']) for e in entries),'relocated':relocated},'ledger':ledger}


def build():
    original=ORIGINAL_ROM.read_bytes();c=load_json(CATALOG);atomic_write(OUTPUT/'catalog.json',(json.dumps(c,ensure_ascii=False,indent=2)+'\n').encode())
    for language in ('english','japanese'):
        data,r=build_rom(original,language,c);r['catalog_sha256']=digest((OUTPUT/'catalog.json').read_bytes());atomic_write(OUTPUT/f'torneko3-system-labels-{language}.gba',data);atomic_write(OUTPUT/f'{language}-build.json',(json.dumps(r,indent=2)+'\n').encode());print(language,r['rom_sha256'],flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=('prepare','build'));prepare() if p.parse_args().mode=='prepare' else build()
