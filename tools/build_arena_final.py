"""Remaining arena outcome labels and positioned winner/odds rows."""
import argparse
import json
import struct
from tools import build_encounter_ui as previous,build_core_gameplay as core
from tools.build_first_label import ORIGINAL_ROM,ROOT,digest
from tools.game_text import GameTextCodec,PRINTF,rebuild
from tools.translation_pipeline import check,load_json,atomic_write,FontZero
from tools.rom_build import RomBuild
CATALOG=ROOT/'translations/arena-final.json'
OUTPUT=ROOT/'build/completion/arena-final'
OWNERS={0xDC870:(0x5CB7C,0x5CB58),0xDC884:(0x5CC8C,0x5CC38),0xDC8A0:(0x5CB94,0x5CB86)}
DRAFTS={0xDC870:'<<< No winner >>>',0xDC884:'{hex:0305}%cNo.%d{hex:03082c}%s{hex:0308a4}%d.%dx',0xDC8A0:'... others'}


def extract(original):
    codec=GameTextCodec(original);master={int(e['offset'],0):e for e in load_json(ROOT/'translations/master.json')['entries']};entries=[]
    for at,(word,load) in OWNERS.items():
        s=codec.parse(original,at);check(rebuild(s['tokens'])==original[at:s['end']] and struct.unpack_from('<I',original,word)[0]==at+0x08000000,'Arena-final source/owner differs')
        entries.append({'id':f'arena-final.{at:08x}','family':'row' if at==0xDC884 else 'label','offset':hex(at),'source_end_exclusive':hex(s['end']),'source_hex':s['raw_hex'],'source_tokens':s['tokens'],'japanese':s['display'],'master_id':master[at]['id'],'pointer_owners':[{'offset':hex(word),'evidence':'thumb_literal','loads':[hex(load+0x08000000)]}],'english':None,'display':None,'notes':'','references':[]})
    return {'schema':1,'base_sha256':digest(original),'font':0,'entries':entries}


def names():
    entries=[e for e in load_json(ROOT/'translations/enemies.json')['entries'] if e['family']=='name'];check(len(entries)==200 and {e['row'] for e in entries}==set(range(200)),'Arena actor-name inventory differs');return sorted(entries,key=lambda e:e['row'])


def encode(e,original):
    text=e['display'] or e['english'];check(isinstance(text,str) and text and all(32<=ord(ch)<127 for ch in text),'Arena-final text must be one ASCII line with typed controls');raw=b'';last=0
    for m in core.HEX.finditer(text):raw+=text[last:m.start()].encode()+bytes.fromhex(m[1]);last=m.end()
    raw+=text[last:].encode()+b'\0';check(b'{' not in raw and b'}' not in raw,'Unknown arena-final markup');p=GameTextCodec(original).parse(raw,0);check(p['end']==len(raw),'Arena-final embedded terminator');check(PRINTF.findall(raw)==PRINTF.findall(bytes.fromhex(e['source_hex'])),'Arena-final printf contract changed');binary=lambda ts:[t['raw_hex'] for t in ts if t['kind']=='binary_control'];check(binary(p['tokens'])==binary(e['source_tokens']),'Arena-final controls changed')
    font=FontZero(original);width=lambda s:sum(font.glyph(ch)[1] for ch in s);bounds=[]
    if e['family']=='row':
        check(width('No.10')<=44 and 12+164+width('999.9x')<=208,'Arena-final number/odds fields overflow')
        for n in [e['display'] or e['english'] for e in names()]+['WWWWWWW']:
            check(width(n)<=120,'Arena-final name crosses odds');payload=raw%(7,10,n.encode(),999,9);check(len(payload)<=200,'Arena-final printf overrun');bounds.append(len(payload))
        # The actual inputs are bounded above; a general byte-only printf
        # envelope remains well within the native 200-byte buffer too.
        check(len(raw%(7,2147483647,b'i'*29,2147483647,2147483647))<=200,'Arena-final general printf bound')
    else:check(width(text)+(160 if int(e['offset'],0)==0xDC8A0 else 48)<=208,'Arena-final label field overflow');bounds=[len(raw)]
    return raw,{'bytes_including_nul':len(raw),'capacity':200,'formatted_byte_upper_bound':max(bounds),'native_odds_max_tenths':9999 if e['family']=='row' else None}


def prepare():
    original=ORIGINAL_ROM.read_bytes();c=extract(original);existing={e['id']:e for e in load_json(CATALOG)['entries']} if CATALOG.exists() else {}
    for e in c['entries']:
        e['english']=DRAFTS[int(e['offset'],0)];e['notes']='Independent original-source translation. Preserve dynamic colour, original name/odds columns, row order, 200-byte printf buffer and odds generator. Native winner presentation required before acceptance.'
        if e['id'] in existing:
            for k in ('english','display','notes','references'):e[k]=existing[e['id']][k]
        encode(e,original)
    atomic_write(CATALOG,(json.dumps(c,ensure_ascii=False,indent=2)+'\n').encode());atomic_write(OUTPUT/'source-owners.json',(json.dumps(extract(original),ensure_ascii=False,indent=2)+'\n').encode());print('Prepared three arena-final sources',flush=True)


def validate(original,c):
    fresh=extract(original);check(all(c[k]==fresh[k] for k in ('schema','base_sha256','font')) and len(c['entries'])==3,'Arena-final catalog header/count differs')
    for e,f in zip(c['entries'],fresh['entries'],strict=True):check(all(e[k]==f[k] for k in f.keys()-{'english','display','notes','references'}),'Arena-final metadata differs');encode(e,original)
    return c['entries']


def build_rom(original,language='english',catalog=None,*,build=None):
    check(language in ('english','japanese'),'Arena-final language');b=RomBuild(original) if build is None else build;_,prior=previous.build_rom(original,build=b);c=load_json(CATALOG) if catalog is None else catalog;entries=validate(original,c);relocated={}
    for e in entries:
        at=int(e['offset'],0);source=bytes.fromhex(e['source_hex']);raw,metrics=encode(e,original);b.protect_source(e['id'],at,at+len(source),'arena-final');dest=b.allocate(e['id'],raw if language=='english' else source,'arena-final')
        for p in e['pointer_owners']:b.patch(e['id']+'.'+p['offset'],int(p['offset'],0),struct.pack('<I',at+0x08000000),struct.pack('<I',dest+0x08000000),'arena-final',p['evidence'])
        relocated[e['id']]={'offset':dest,'metrics':metrics}
    data,ledger=b.finish();return data,{'source_sha256':digest(original),'rom_sha256':digest(data),'previous_rom_sha256':prior['rom_sha256'],'language':language,'arena_final':{'resources':3,'pointer_words':3,'relocated':relocated},'ledger':ledger}


def build():
    original=ORIGINAL_ROM.read_bytes();c=load_json(CATALOG);atomic_write(OUTPUT/'catalog.json',(json.dumps(c,ensure_ascii=False,indent=2)+'\n').encode())
    for language in ('english','japanese'):
        data,r=build_rom(original,language,c);r['catalog_sha256']=digest((OUTPUT/'catalog.json').read_bytes());atomic_write(OUTPUT/f'torneko3-arena-final-{language}.gba',data);atomic_write(OUTPUT/f'{language}-build.json',(json.dumps(r,indent=2)+'\n').encode());print(language,r['rom_sha256'],flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=('prepare','build'));prepare() if p.parse_args().mode=='prepare' else build()
