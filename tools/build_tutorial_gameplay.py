"""Tutorials, dungeon feedback and effect labels, composed with all prior work."""
from collections import Counter
import json
import re
import struct
from tools import build_ally_services as previous
from tools.build_first_label import ORIGINAL_ROM, ROOT, digest
from tools.game_text import GameTextCodec, PRINTF, rebuild
from tools.translation_pipeline import FontZero, atomic_write, check, load_json
from tools.rom_build import RomBuild

CATALOG = ROOT/'translations/tutorial-gameplay.json'
OUTPUT = ROOT/'build/tutorial-gameplay'
CORE = previous.previous.core
INIT_SOURCE, INIT_END = 0xCAFE88, 0xCB0F44
INIT_TABLES = ((0xCAFEE8,0xCAFF08),(0xCAFF80,0xCAFF8C),
               (0xCAFF8C,0xCAFFF0),(0xCAFFF4,0xCB0094))
TUTORIAL_TABLE = (0x1B4AF8,0x1B4B1C)
EFFECT_TABLE = (0x1B7590,0x1B7720)
TYPED = (set(range(*TUTORIAL_TABLE,4)) | set(range(*EFFECT_TABLE,4)) |
         set(range(0xA6C8C,0xA7C44,36)) | set(range(0xA6C90,0xA7C44,36)))
INITIALIZERS = {p for a,b in INIT_TABLES for p in range(a,b,4)}
SLOTS = re.compile(r'\$[im]\d|\$d\d|\$t|\$w')


def extract_catalog(original):
    codec=GameTextCodec(original);master=load_json(ROOT/'translations/master.json')
    owned={p['offset'] for p in load_json(ROOT/'build/ally-services/english-build.json')['ledger']['patches']}
    entries=[]
    for e in master['entries']:
        o=int(e['offset'],0)
        if not 0x1B47EA<=o<0x1B780D or 0x1B4F38<=o<0x1B5021:continue
        if any(int(p,0) in owned for p in e['pointer_candidates']):continue
        owners=[];excluded=[]
        for word in e['pointer_candidates']:
            p=int(word,0)
            if p>=0xF0000 and p not in TYPED|INITIALIZERS:
                excluded.append({'offset':word,'reason':'unreviewed_external_context'});continue
            loads=[i for i in range(max(0,p-1024),p,2) if original[i+1]&0xF8==0x48 and ((i+4)&~3)+original[i]*4==p]
            check(loads or p in TYPED|INITIALIZERS,f'Unreviewed owner {word}')
            check(struct.unpack_from('<I',original,p)[0]==o+0x08000000,'Pointer mismatch')
            owners.append({'offset':word,'evidence':'startup_initialized_pointer' if p in INITIALIZERS else 'typed_pointer_table' if p in TYPED else 'thumb_literal',
                           'loads':[f'0x{x+0x08000000:08X}' for x in loads]})
        if not owners:continue
        source=codec.parse(original,o);check(rebuild(source['tokens'])==original[o:source['end']],'Source round trip failed')
        family=('tutorial' if o<0x1B4AF8 else 'joined_damage' if 0x1B5021<=o<0x1B5096 else
                'object' if 0x1B5124<=o<0x1B516F else 'effect' if 0x1B70D0<=o<0x1B7590 else 'message')
        entries.append({'id':f'tutorial.{o:08x}','family':family,'offset':e['offset'],'japanese':source['display'],
                        'source_hex':source['raw_hex'],'source_tokens':source['tokens'],'pointer_owners':owners,
                        'excluded_owners':excluded,'master_id':e['id'],'english':None,'display':None,'notes':''})
    return {'schema':1,'base_sha256':digest(original),'font':0,'entries':entries}


def validate_catalog(original,catalog):
    fresh=extract_catalog(original);entries={e['id']:e for e in catalog['entries']}
    check(all(catalog[k]==fresh[k] for k in ('schema','base_sha256','font')),'Header changed')
    check(len(entries)==len(catalog['entries'])==len(fresh['entries']),'Incomplete/duplicate catalog')
    for e in fresh['entries']:
        actual=entries[e['id']]
        check(all(actual[k]==e[k] for k in e.keys()-{'english','display','notes'}),'Source/owner changed')
        check(isinstance(actual['english'],str) and actual['english'],'Missing English')
        check(actual['display'] is None or isinstance(actual['display'],str) and actual['display'],'Bad display')
    return entries


def width(text,font):
    return CORE.text_width(text.replace('$w','').lstrip('!'),font)


def line_bytes(text):
    """Worst formatted payload, excluding NUL; bounded names AND glyph widths.

    Accepted item names/effect labels are <=144px; the minimum font-0 ASCII
    advance is 3px, so at most 48 payload bytes. Actor slots cap at 29 bytes.
    The 64-byte history record has only 59 payload bytes, tighter than the
    live 80-byte queue row. The pause command formats to two binary bytes.
    """
    n=0;last=0;text=text.lstrip('!')
    for m in SLOTS.finditer(text):
        n+=len(text[last:m.start()])+ (48 if m[0].startswith('$i') else 29 if m[0].startswith('$m') else 7 if m[0]=='$t' else 2 if m[0]=='$w' else 11)
        last=m.end()
    return n+len(text[last:])


def wrap(text,font):
    lines=[]
    for paragraph in text.split('\n'):
        line=''
        for word in paragraph.split(' '):
            candidate=(line+' '+word) if line else word
            if line and (width(candidate,font)>208 or line_bytes(candidate)>59):lines.append(line);line=word
            else:line=candidate
            check(width(line,font)<=208 and line_bytes(line)<=59,f'Unbreakable message word: {word}')
        lines.append(line)
    return '\n'.join(lines)


def encode(entry,original):
    font=FontZero(original);codec=GameTextCodec(original);text=entry['display'] or entry['english'];family=entry['family']
    check(all(32<=ord(c)<127 or c=='\n' for c in text),'ASCII/LF and typed controls required')
    check(not any(c in text for c in '{}'),'Unknown control')
    source=bytes.fromhex(entry['source_hex'])
    check(text.startswith('!')==source.startswith(b'!'),'Continuation marker changed')
    if family=='tutorial':
        check(text.count('$w')==1,'Tutorial pause contract changed')
        first,second=text.split('$w');check(first.strip() and second.strip(),'Empty tutorial segment')
        first=wrap(first.rstrip('\n'),font);second=wrap('$w'+second.lstrip('\n'),font)
        check(all(len(s.split('\n'))<=3 for s in (first,second)),'Tutorial segment exceeds three lines')
        text=first+'\n'+second
    elif family in ('message','joined_damage'):
        text=wrap(text,font);check(len(text.split('\n'))<=3,f'Message exceeds three lines: {entry["id"]}: {text}')
    else:
        check('\n' not in text and width(text,font)<=144,'Copied label exceeds 144 pixels')
        check(len(text)+1<=100,'Copied label exceeds 100 bytes')
    raw=text.encode()+b'\0';parsed=codec.parse(raw,0)
    dollars=lambda ts:Counter(t['text'] for t in ts if t['kind']=='dollar_command' and t['text']!='$x' and not t['text'].startswith('$/'))
    check(dollars(parsed['tokens'])==dollars(entry['source_tokens']),'Substitution contract changed')
    check(not PRINTF.findall(source) and not any(t['kind']=='binary_control' for t in entry['source_tokens']),'Unreviewed control')
    check(parsed['end']==len(raw),'Embedded terminator')
    return raw,{'display_template':text,'line_widths':[width(s,font) for s in text.split('\n')],
                'history_payload_upper_bounds':[line_bytes(s) for s in text.split('\n')],
                'history_payload_capacity':59,'queue_row_capacity':80,'bytes_including_nul':len(raw)}


def add_tutorials(build,catalog,language='english'):
    check(language in ('english','japanese'),'Bad language');entries=validate_catalog(build.original,catalog);relocated={}
    for ident,e in entries.items():
        offset=int(e['offset'],0);source=bytes.fromhex(e['source_hex']);english,metrics=encode(e,build.original)
        build.protect_source(ident,offset,offset+len(source),'tutorial-gameplay')
        payload=english if language=='english' else source;target=build.allocate(ident,payload,'tutorial-gameplay')
        for p in e['pointer_owners']:
            at=int(p['offset'],0)
            build.patch(f'{ident}.{at:08x}',at,struct.pack('<I',offset+0x08000000),struct.pack('<I',target+0x08000000),'tutorial-gameplay',p['evidence'])
        relocated[ident]={'offset':target,'bytes':len(payload),'metrics':metrics}
    return {'language':language,'entries':len(entries),'relocated':relocated}


def build_rom(original,language='english',catalog=None):
    b=RomBuild(original);CORE.build_name_rom(original,build=b)
    for module,add in ((CORE.build_items,CORE.build_items.add_items),(CORE.build_item_contexts,CORE.build_item_contexts.add_contexts),
                       (CORE.build_enemies,CORE.build_enemies.add_enemies),(CORE.build_dungeon_interface,CORE.build_dungeon_interface.add_interface),
                       (CORE,CORE.add_gameplay),(previous.previous,previous.previous.add_help),(previous,previous.add_services)):
        add(b,load_json(module.CATALOG),'english')
    report=add_tutorials(b,load_json(CATALOG) if catalog is None else catalog,language);data,ledger=b.finish()
    return data,{'source_sha256':digest(original),'rom_sha256':digest(data),'tutorials':report,'ledger':ledger}


def build():
    for language in ('japanese','english'):
        data,report=build_rom(ORIGINAL_ROM.read_bytes(),language)
        atomic_write(OUTPUT/f'torneko3-tutorial-gameplay-{language}.gba',data)
        atomic_write(OUTPUT/f'{language}-build.json',(json.dumps(report,indent=2)+'\n').encode())
        print(language,report['rom_sha256'],report['ledger']['appended_used_with_padding'],flush=True)


if __name__=='__main__':build()
