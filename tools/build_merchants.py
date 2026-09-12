"""World merchant records, prices, Medal King and equipment services."""
import argparse
from collections import Counter
import json
import struct
from tools import build_battle_completion as previous
from tools import build_core_gameplay as core
from tools.build_first_label import ORIGINAL_ROM, ROOT, digest
from tools.game_text import GameTextCodec, PRINTF, rebuild
from tools.translation_pipeline import atomic_write, load_json, check, FontZero
from tools.rom_build import RomBuild

CATALOG=ROOT/'translations/merchants.json'
OUTPUT=ROOT/'build/completion/merchants'
SHOP_BASE=0x86FB34
PLAYER_BASE=0x87185C
MENU_BASE=0x87231C
TYPED={SHOP_BASE+i*0xA4+o for i in range(19) for o in range(4,0x54,4)} | {PLAYER_BASE+i*0x40+o for i in range(2) for o in range(8,0x40,4)} | {MENU_BASE+i*12 for i in range(3)}
LABELS={0x872364,0x872480,0x8729F4,0x872A0C}
OBSERVATIONS={0x8726E8,0x872730,0x872A50,0x872A9C}


def extract(original):
    codec=GameTextCodec(original);entries=[]
    for m in load_json(ROOT/'translations/master.json')['entries']:
        at=int(m['offset'],0)
        if not 0x870760<=at<0x872ABC or at==PLAYER_BASE:continue
        owners=[]
        for word in m['pointer_candidates']:
            p=int(word,0);check(struct.unpack_from('<I',original,p)[0]==at+0x08000000,'Merchant pointer differs')
            kind='typed_text_word' if p in TYPED else 'thumb_literal'
            loads=[] if p in TYPED else [i for i in range(max(0,p-1024),p,2) if original[i+1]&0xF8==0x48 and ((i+4)&~3)+original[i]*4==p]
            check(p in TYPED or p<0xF0000 and loads,'Unreviewed merchant owner '+word)
            owners.append({'offset':word,'evidence':kind,'loads':[hex(i+0x08000000) for i in loads]})
        check(owners,'Merchant source lacks owners');s=codec.parse(original,at);check(rebuild(s['tokens'])==original[at:s['end']],'Merchant source reconstruction')
        family='menu' if 0x87234C<=at<=0x87235C else 'label' if at in LABELS else 'observation' if at in OBSERVATIONS else 'speech'
        entries.append({'id':f'merchant.{at:08x}','family':family,'offset':m['offset'],'source_end_exclusive':hex(s['end']),
            'japanese':s['display'],'source_hex':s['raw_hex'],'source_tokens':s['tokens'],'master_id':m['id'],'pointer_owners':owners,
            'english':None,'display':None,'notes':'','references':[]})
    check(len(entries)==132,'Merchant source count differs')
    return {'schema':1,'base_sha256':digest(original),'font':0,'entries':entries}


def width(text,font):return core.text_width(text.replace('%s','$i0').replace('%d','$d0'),font)


def encode(e,original):
    text=e['display'] or e['english'];font=FontZero(original);codec=GameTextCodec(original);source=bytes.fromhex(e['source_hex'])
    check(isinstance(text,str) and text and all(32<=ord(c)<127 or c=='\n' for c in text),'Merchant printable English required')
    check(not any(c in text for c in '{}`'),'Unsupported merchant controls')
    lines=[]
    for paragraph in text.split('\n'):
        line=''
        for word in paragraph.split(' '):
            candidate=line+' '+word if line else word
            if line and width(candidate,font)>208:lines.append(line);line=word
            else:line=candidate
            check(width(line,font)<=208,'Unbreakable merchant word '+e['id'])
        lines.append(line)
    if e['family'] in ('menu','label'):check(len(lines)==1 and width(lines[0],font)<=(120 if e['family']=='menu' else 208),'Merchant UI label overflow')
    text='\n'.join(lines);raw=text.encode()+b'\0';s=codec.parse(raw,0)
    check(s['end']==len(raw),'Embedded merchant terminator');check(PRINTF.findall(raw)==PRINTF.findall(source),'Merchant printf contract differs')
    dollars=lambda ts:Counter(t['text'] for t in ts if t['kind']=='dollar_command')
    check(dollars(s['tokens'])==dollars(e['source_tokens']),'Merchant substitution contract differs')
    check(all(t['kind'] in ('text','control','dollar_command','printf','terminator') and (t['kind']!='control' or t['raw_hex'] in ('09','0a')) and (t['kind']!='dollar_command' or t['text'] in ('$t','$i0','$d0')) and (t['kind']!='printf' or t['text'] in ('%s','%d')) for t in e['source_tokens']),'Unreviewed merchant source control')
    printf_max=len(raw)+sum(99-len(f) if f==b'%s' else 11-len(f) for f in PRINTF.findall(raw))
    check(not PRINTF.findall(raw) or printf_max<=256,f'Merchant printf overflow {e["id"]}: {printf_max}/256')
    maximum=printf_max+sum(((99 if t['text']=='$i0' else 11 if t['text']=='$d0' else 7)-len(t['text'])) for t in s['tokens'] if t['kind']=='dollar_command')
    check(maximum<=1024,'Merchant world formatter overflow')
    return raw,{'display_template':text,'line_widths':[width(s,font) for s in lines],'lines':len(lines),'capacity':1024,
        'printf_capacity':256 if PRINTF.findall(raw) else None,'printf_byte_upper_bound':printf_max,'formatted_byte_upper_bound':maximum,'bytes_including_nul':len(raw)}


def validate(original,catalog):
    fresh=extract(original);entries={e['id']:e for e in catalog['entries']}
    check(all(catalog[k]==fresh[k] for k in ('schema','base_sha256','font')),'Merchant header differs')
    check(len(entries)==len(catalog['entries'])==len(fresh['entries']),'Incomplete merchant catalog')
    for e in fresh['entries']:
        a=entries[e['id']];check(all(a[k]==e[k] for k in e.keys()-{'english','display','notes','references'}),'Merchant source metadata differs');encode(a,original)
    return list(entries.values())


def owners():
    original=ORIGINAL_ROM.read_bytes();c=extract(original)
    tables=[{'start':hex(a),'end_exclusive':hex(z),'source_hex':original[a:z].hex()} for a,z in ((SHOP_BASE,0x870760),(PLAYER_BASE,0x8718DC),(MENU_BASE,0x87234C))]
    atomic_write(OUTPUT/'source-owners.json',(json.dumps({'source_sha256':digest(original),'entries':c['entries'],'tables':tables,
        'excluded_binary':{'master_id':'jp_0087185c','offset':hex(PLAYER_BASE),'u32':50000,'literal':hex(0x63B94),'reason':'Native initial player-shop gold; not prose'},
        'scope':'Exact sources and literal/typed text pointers only. Record identifiers, starting cash, stock, menu flags and original sources remain occupied.'},ensure_ascii=False,indent=2)+'\n').encode())
    print(len(c['entries']),'merchant sources;',sum(len(e['pointer_owners']) for e in c['entries']),'pointers',flush=True)


def build_rom(original,language='english',catalog=None,*,build=None):
    check(language in ('english','japanese'),'Invalid merchant language');b=RomBuild(original) if build is None else build
    _,prior=previous.build_rom(original,build=b);c=load_json(CATALOG) if catalog is None else catalog;entries=validate(original,c);relocated={}
    for e in entries:
        at=int(e['offset'],0);source=bytes.fromhex(e['source_hex']);raw,metrics=encode(e,original)
        b.protect_source(e['id'],at,at+len(source),'merchants');dest=b.allocate(e['id'],raw if language=='english' else source,'merchants')
        for p in e['pointer_owners']:b.patch(e['id']+'.'+p['offset'],int(p['offset'],0),struct.pack('<I',at+0x08000000),struct.pack('<I',dest+0x08000000),'merchants',p['evidence'])
        relocated[e['id']]={'offset':dest,'metrics':metrics}
    data,ledger=b.finish()
    return data,{'source_sha256':digest(original),'rom_sha256':digest(data),'previous_rom_sha256':prior['rom_sha256'],'language':language,
        'merchants':{'entries':len(entries),'pointer_words':sum(len(e['pointer_owners']) for e in entries),'relocated':relocated},'ledger':ledger}


def build():
    original=ORIGINAL_ROM.read_bytes();catalog=load_json(CATALOG);atomic_write(OUTPUT/'catalog.json',(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n').encode())
    for language in ('english','japanese'):
        data,report=build_rom(original,language,catalog);report['catalog_sha256']=digest((OUTPUT/'catalog.json').read_bytes())
        atomic_write(OUTPUT/f'torneko3-merchants-{language}.gba',data);atomic_write(OUTPUT/f'{language}-build.json',(json.dumps(report,indent=2)+'\n').encode());print(language,report['rom_sha256'],flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=('owners','build'));owners() if p.parse_args().mode=='owners' else build()
