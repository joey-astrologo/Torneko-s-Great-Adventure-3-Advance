"""Checked complete adventure-history key/value prose table."""
import argparse
from collections import Counter
import csv
import io
import json
import struct
from tools import build_arena_services as previous
from tools.build_first_label import ORIGINAL_ROM,ROOT,digest
from tools.game_text import GameTextCodec,PRINTF,rebuild
from tools.translation_pipeline import FontZero,load_json,check,atomic_write
from tools.rom_build import RomBuild

CATALOG=ROOT/'translations/adventure-history.json'
OUTPUT=ROOT/'build/completion/history'
TABLE=0xC4D250;END=0xC4D5B8
HEX=previous.service.previous.core.HEX


def extract(original):
    codec=GameTextCodec(original);master={int(e['offset'],0):e for e in load_json(ROOT/'translations/master.json')['entries']};entries={}
    for at in range(TABLE,END,8):
        k,v=struct.unpack_from('<II',original,at)
        if at==END-8:check(k==v==0,'History terminator differs');continue
        check(k and v,'Early history terminator');key=codec.parse(original,k-0x08000000);s=codec.parse(original,v-0x08000000)
        if not s['display'] or key['display']=='log_error':continue
        offset=v-0x08000000;check(rebuild(s['tokens'])==original[offset:s['end']],'History source roundtrip')
        if offset not in entries:
            m=master[offset];entries[offset]={'id':f'history.{offset:08x}','offset':m['offset'],'source_end_exclusive':hex(s['end']),
                'master_id':m['id'],'japanese':s['display'],'source_hex':s['raw_hex'],'source_tokens':s['tokens'],'pointer_owners':[],
                'english':None,'display':None,'notes':'','references':[]}
        entries[offset]['pointer_owners'].append({'offset':hex(at+4),'key':key['display'],'key_offset':hex(k-0x08000000)})
    return {'schema':1,'base_sha256':digest(original),'font':0,'entries':list(entries.values())}


def values(e,profile='normal',hero='Torneko'):
    # Layout fixtures, not a claim that every stored counter has this upper bound.
    floor=(any(p['key'].startswith('log_3_') for p in e['pointer_owners']) and int(e['offset'],0)!=0xC4E20C) or int(e['offset'],0)==0xC4D5C0
    return {'$t':hero,'$d0':('999' if floor else '9999999') if profile=='stress' else '7',
        '$d1':'59' if profile=='stress' else '12','$i0':'32767:59:59' if profile=='stress' else '   1:02:03',
        '$v07':f'{9999999 if profile=="stress" else 7:7d}'}


def payload(e):
    text=e['display'] or e['english'];check(isinstance(text,str) and text,'Missing history English')
    check(all(32<=ord(c)<127 for c in text),'History uses one ASCII row and typed controls')
    raw=b'';last=0
    for m in HEX.finditer(text):raw+=text[last:m.start()].encode()+bytes.fromhex(m[1]);last=m.end()
    raw+=text[last:].encode()+b'\0';check(b'{' not in raw and b'}' not in raw,'Unknown history control')
    return raw


def encode(e,original):
    raw=payload(e);codec=GameTextCodec(original);parsed=codec.parse(raw,0);check(parsed['end']==len(raw),'History embedded terminator')
    dollars=lambda ts:Counter(t['text'] for t in ts if t['kind']=='dollar_command')
    controls=lambda ts:[(t['kind'],t['raw_hex']) for t in ts if t['kind'] in ('binary_control','opaque_control')]
    check(dollars(parsed['tokens'])==dollars(e['source_tokens']),'History substitution contract differs')
    check(controls(parsed['tokens'])==controls(e['source_tokens']),'History control sequence differs')
    check(PRINTF.findall(raw)==PRINTF.findall(bytes.fromhex(e['source_hex']))==[],'Unexpected history printf')
    # 32-bit formatting guard remains independent of the seven-digit layout fixture.
    upper=sum(11 if t['kind']=='dollar_command' and t['text']!='$t' else 7 if t['text']=='$t' else len(bytes.fromhex(t['raw_hex'])) for t in parsed['tokens'])
    check(upper<=512,'History formatter capacity exceeded');font=FontZero(original);measure=previous.service.previous.core.measure;widths=[]
    for hero in ('Torneko','Tipper'):
        for profile in ('normal','stress'):
            expanded=raw
            for key,value in values(e,profile,hero).items():expanded=expanded.replace(key.encode(),value.encode())
            tokens=codec.parse(expanded,0)['tokens'];x=right=4
            for t in tokens:
                if t['kind']=='binary_control' and bytes.fromhex(t['raw_hex'])[1] in (8,9):
                    column=bytes.fromhex(t['raw_hex'])[2];check(right<=column,f'History column overlap {e["id"]}: {right}/{column}');x=column
                elif t['kind']=='text':
                    for ch in t['text']:
                        _,advance,ink=font.glyph(ch);right=max(right,x+ink);x+=advance
                    right=max(x,right)
            widths.append(right)
    check(max(widths)<=208,f'History row overflow {e["id"]}: {widths}')
    return raw,{'display_template':e['display'] or e['english'],'width_fixtures':widths,'capacity':512,'formatted_byte_upper_bound':upper,
        'bytes_including_nul':len(raw),'width_scope':'Both protagonists; seven-digit non-floor counters, three-digit floor and two-digit minutes. Numeric storage limits require their reader/gameplay evidence separately.'}


def validate(original,catalog):
    fresh=extract(original);entries={e['id']:e for e in catalog['entries']}
    check(all(catalog[k]==fresh[k] for k in ('schema','base_sha256','font')),'History header differs')
    check(len(entries)==len(catalog['entries'])==len(fresh['entries'])==100,'History table incomplete')
    for e in fresh['entries']:
        a=entries[e['id']];check(all(a[k]==e[k] for k in e.keys()-{'english','display','notes','references'}),'History metadata differs');encode(a,original)
    return list(entries.values())


def prepare():
    original=ORIGINAL_ROM.read_bytes();catalog=extract(original);drafts={int(e['offset'],16):e for e in csv.DictReader((ROOT/'translations/adventure-history-drafts.tsv').open(),delimiter='\t')}
    check(len(drafts)==100,'History drafts incomplete');prior={e['id']:e for e in load_json(CATALOG)['entries']} if CATALOG.exists() else {}
    glossary=load_json(ROOT/'translations/glossary.json')
    for e in catalog['entries']:
        d=drafts[int(e['offset'],0)];e.update(english=d['english'],display=d['display'] or None,
            notes='Independent translation from the pinned Japanese history entry. Full English retained; display wording is shortened only for the original single-row layout.')
        if e['id'] in prior:
            check(all(e[k]==prior[e['id']][k] for k in ('english','display')),'Refusing to overwrite authored history wording');e.update({k:prior[e['id']][k] for k in ('notes','references')})
        for t in glossary['terms']:
            if any(j in e['japanese'] for j in t['japanese']) and (t.get('batch') not in ('ally-nicknames',) and len(max(t['japanese'],key=len))>=3):
                if t['id'] not in e['references']:e['references'].append(t['id'])
    validate(original,catalog);atomic_write(CATALOG,(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n').encode())
    print('Prepared',len(catalog['entries']),'history entries',flush=True)


def build_rom(original,language='english',catalog=None,*,build=None):
    check(language in ('english','japanese'),'Invalid history language');b=RomBuild(original) if build is None else build
    _,prior=previous.build_rom(original,build=b);c=load_json(CATALOG) if catalog is None else catalog;entries=validate(original,c);relocated={}
    for e in entries:
        at=int(e['offset'],0);source=bytes.fromhex(e['source_hex']);raw,metrics=encode(e,original)
        b.protect_source(e['id'],at,at+len(source),'adventure-history');dest=b.allocate(e['id'],raw if language=='english' else source,'adventure-history')
        for p in e['pointer_owners']:
            word=int(p['offset'],0);b.patch(e['id']+'.'+p['offset'],word,struct.pack('<I',at+0x08000000),struct.pack('<I',dest+0x08000000),'adventure-history','Typed history value pointer; key, stride, original source and counter semantics preserved')
        relocated[e['id']]={'offset':dest,'metrics':metrics}
    data,ledger=b.finish();return data,{'source_sha256':digest(original),'rom_sha256':digest(data),'previous_rom_sha256':prior['rom_sha256'],'language':language,
        'history':{'sources':len(entries),'pointer_words':sum(len(e['pointer_owners']) for e in entries),'relocated':relocated},'ledger':ledger}


def build():
    catalog=load_json(CATALOG);original=ORIGINAL_ROM.read_bytes();atomic_write(OUTPUT/'catalog.json',(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n').encode())
    for language in ('english','japanese'):
        data,report=build_rom(original,language,catalog);report['catalog_sha256']=digest((OUTPUT/'catalog.json').read_bytes());atomic_write(OUTPUT/f'torneko3-adventure-history-{language}.gba',data);atomic_write(OUTPUT/f'{language}-build.json',(json.dumps(report,indent=2)+'\n').encode());print(language,report['rom_sha256'],flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=('prepare','build'));a=p.parse_args();prepare() if a.mode=='prepare' else build()
