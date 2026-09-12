"""Remaining sound-test help and dungeon-floor log summary."""
import argparse
import json
import struct
from tools import build_arena_graphics as previous
from tools.build_first_label import ORIGINAL_ROM,ROOT,digest
from tools.game_text import GameTextCodec,PRINTF,rebuild
from tools.translation_pipeline import check,load_json,atomic_write,FontZero
from tools.rom_build import RomBuild
CATALOG=ROOT/'translations/remaining-display.json'
OUTPUT=ROOT/'build/completion/remaining-display'
OWNERS={0x9B4FC:0x29F0,0xCAF2E0:0xCB07EC,0xCAF2CC:0xCB07F0,0xCAF2B8:0xCB07F4,0xCAF29C:0xCB07F8}
DRAFTS={0x9B4FC:'%s %dF',0xCAF2E0:'Play background music.',0xCAF2CC:'Play music effects.',0xCAF2B8:'Play sound effects.',0xCAF29C:'Return to main menu.'}

def extract(original):
    codec=GameTextCodec(original);master={int(e['offset'],0):e for e in load_json(ROOT/'translations/master.json')['entries']};entries=[]
    for at,word in OWNERS.items():
        p=codec.parse(original,at);check(rebuild(p['tokens'])==original[at:p['end']] and struct.unpack_from('<I',original,word)[0]==at+0x08000000,'Remaining display source/owner differs')
        entries.append({'id':f'remaining-display.{at:08x}','family':'floor_summary' if at==0x9B4FC else 'sound_help','offset':hex(at),'source_end_exclusive':hex(p['end']),'source_hex':p['raw_hex'],'source_tokens':p['tokens'],'japanese':p['display'],'master_id':master[at]['id'],'pointer_owners':[{'offset':hex(word),'evidence':'thumb_literal' if word<0x97000 else 'startup_sound_help_pointer','loads':['0x080029ca'] if word<0x97000 else ['0x08090cce']}],'english':None,'display':None,'notes':'','references':[]})
    return {'schema':1,'base_sha256':digest(original),'font':0,'entries':entries}

def encode(e,original):
    text=e['display'] or e['english'];check(isinstance(text,str) and text and all(32<=ord(ch)<127 for ch in text),'Remaining display requires plain ASCII');raw=text.encode()+b'\0'
    check(PRINTF.findall(raw)==PRINTF.findall(bytes.fromhex(e['source_hex'])),'Remaining display printf contract differs')
    values=[text]
    if e['family']=='floor_summary':
        names=[n['display'] or n['english'] for n in load_json(ROOT/'translations/dungeon-interface.json')['entries'] if n['family']=='dungeon'];values=[text%(n,f) for n in names for f in (0,255)]
    font=FontZero(original);widths=[sum(font.glyph(c)[1] for c in value) for value in values];cap=64 if e['family']=='floor_summary' else 256
    check(max(len(v.encode())+1 for v in values)<=cap and max(widths)<=184,'Remaining display field overflow')
    return raw,{'bytes_including_nul':len(raw),'formatted_byte_upper_bound':max(len(v.encode())+1 for v in values),'capacity':cap,'maximum_width':max(widths),'width_limit':184}

def prepare():
    original=ORIGINAL_ROM.read_bytes();c=extract(original);old={e['id']:e for e in load_json(CATALOG)['entries']} if CATALOG.exists() else {}
    for e in c['entries']:
        e['english']=DRAFTS[int(e['offset'],0)];e['notes']='Independent original-source translation. Preserve native selector, font and window; no changes to audio IDs, save layout or floor values. Native display verification pending.'
        if e['id'] in old:
            for k in ('english','display','notes','references'):e[k]=old[e['id']][k]
        encode(e,original)
    for p,value in ((CATALOG,c),(OUTPUT/'source-owners.json',extract(original))):atomic_write(p,(json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode())
    print('Prepared five remaining display sources',flush=True)

def validate(original,c):
    fresh=extract(original);check(all(c[k]==fresh[k] for k in ('schema','base_sha256','font')) and len(c['entries'])==5,'Remaining display catalog differs')
    for e,f in zip(c['entries'],fresh['entries'],strict=True):check(all(e[k]==f[k] for k in f.keys()-{'english','display','notes','references'}),'Remaining display source metadata differs');encode(e,original)
    return c['entries']

def build_rom(original,language='english',catalog=None,*,build=None):
    check(language in ('english','japanese'),'Remaining display language');b=RomBuild(original) if build is None else build;_,prior=previous.build_rom(original,build=b);c=load_json(CATALOG) if catalog is None else catalog;entries=validate(original,c);relocated={}
    for e in entries:
        at=int(e['offset'],0);source=bytes.fromhex(e['source_hex']);raw,metrics=encode(e,original);b.protect_source(e['id'],at,at+len(source),'remaining-display');dest=b.allocate(e['id'],raw if language=='english' else source,'remaining-display')
        for p in e['pointer_owners']:b.patch(e['id']+'.'+p['offset'],int(p['offset'],0),struct.pack('<I',at+0x08000000),struct.pack('<I',dest+0x08000000),'remaining-display',p['evidence'])
        relocated[e['id']]={'offset':dest,'metrics':metrics}
    data,ledger=b.finish();return data,{'source_sha256':digest(original),'rom_sha256':digest(data),'previous_rom_sha256':prior['rom_sha256'],'language':language,'remaining_display':{'resources':5,'pointer_words':5,'relocated':relocated},'ledger':ledger}

def build():
    original=ORIGINAL_ROM.read_bytes();c=load_json(CATALOG);atomic_write(OUTPUT/'catalog.json',(json.dumps(c,ensure_ascii=False,indent=2)+'\n').encode())
    for language in ('english','japanese'):
        data,r=build_rom(original,language,c);r['catalog_sha256']=digest((OUTPUT/'catalog.json').read_bytes());atomic_write(OUTPUT/f'torneko3-remaining-display-{language}.gba',data);atomic_write(OUTPUT/f'{language}-build.json',(json.dumps(r,indent=2)+'\n').encode());print(language,r['rom_sha256'],flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=('prepare','build'));prepare() if p.parse_args().mode=='prepare' else build()
