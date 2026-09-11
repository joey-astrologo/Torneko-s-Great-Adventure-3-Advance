"""Ally management, warehouse, bank and merchant service text in one ledger."""
from collections import Counter
import json
import re
import struct
from tools import build_gameplay_help as previous
from tools.build_first_label import ORIGINAL_ROM, ROOT, digest
from tools.game_text import GameTextCodec, PRINTF, rebuild
from tools.translation_pipeline import FontZero, atomic_write, check, load_json
from tools.rom_build import RomBuild

CATALOG = ROOT/'translations/ally-services.json'
OUTPUT = ROOT/'build/ally-services'
SKIP = {0xC3E3B8,0xC3E3C8,0xC3E3D8,0xC3E3DC,0xC3E3E4,0xC3E444,0xC3E44C,
        0xC3EDEC,0xC3EED0,0xC3F010,0xC3F018}
EXTRA = {0xC3DA6C,0xC3DB04,0xC3DB54,0xC411B0,0xC41ACC}
SMALL = {0xC3DF8C:5,0xC411B0:5,0xC41ACC:5,0xC3DF94:16}
STATS = {0xC3E400,0xC3E41C}
MENU_TABLES = ((0xC3E498,4),(0xC3F158,3))
LABELS = {0xC3DB04,0xC3DFE4,0xC3E548,0xC3E550,0xC3EDF4,0xC3EDFC,0xC3F0B0,
          0xC3F334,0xC3F808,0xC3F9EC,0xC3EE08}
TYPED = set(range(0xC3DB7C,0xC3DDF8,8)) | set(range(0xC3F140,0xC3F150,4)) | set(range(0xC3FB5C,0xC3FB6C,4)) | {0xC3ED84,0xC3ED88}
for base,count in MENU_TABLES:TYPED.update(base+12*i for i in range(count))


def extract_catalog(original):
    codec = GameTextCodec(original); master = load_json(ROOT/'translations/master.json')
    owned = {p['offset'] for p in load_json(ROOT/'build/gameplay-help/english-build.json')['ledger']['patches']}
    entries=[]
    for e in master['entries']:
        o=int(e['offset'],0)
        if not (0xC3DE18<=o<0xC3FB9C or o in EXTRA) or o in SKIP:continue
        owners=[]; excluded=[]
        for word in e['pointer_candidates']:
            p=int(word,0)
            if p in owned:excluded.append({'offset':word,'reason':'existing_component_owner'});continue
            if p>=0xF0000 and p not in TYPED:
                excluded.append({'offset':word,'reason':'unreviewed_external_context'});continue
            loads=[i for i in range(max(0,p-1024),p,2) if original[i+1]&0xF8==0x48 and ((i+4)&~3)+original[i]*4==p]
            check(loads or p in TYPED,f'Unreviewed owner {word}')
            check(struct.unpack_from('<I',original,p)[0]==o+0x08000000,'Pointer mismatch')
            owners.append({'offset':word,'evidence':'typed_menu_or_service_table' if p in TYPED else 'thumb_literal',
                           'loads':[f'0x{x+0x08000000:08X}' for x in loads]})
        if not owners:continue
        s=codec.parse(original,o);check(rebuild(s['tokens'])==original[o:s['end']],'Source round trip failed')
        family=('stats' if o in STATS else 'small' if o in SMALL else
                'menu' if any(int(p['offset'],0) in TYPED for p in owners) and o<0xC3DE7C or o in (0xC3E4D4,0xC3E4DC,0xC3E4E8,0xC3E4F8,0xC3F188,0xC3F190,0xC3F19C) else
                'row' if o in (0xC3DA6C,0xC3DB54,0xC3E438,0xC3EDE4,0xC3F150,0xC3F6B4,0xC3FB6C,0xC3FB7C,0xC3FB88) else
                'label' if o in LABELS or o in (0xC3ED8C,0xC3ED94) else 'message')
        entries.append({'id':f'service.{o:08x}','family':family,'offset':e['offset'],'japanese':s['display'],
                        'source_hex':s['raw_hex'],'source_tokens':s['tokens'],'pointer_owners':owners,
                        'excluded_owners':excluded,'master_id':e['id'],'english':None,'display':None,'notes':''})
    return {'schema':1,'base_sha256':digest(original),'font':0,'entries':entries}


def validate_catalog(original,catalog):
    fresh=extract_catalog(original); entries={e['id']:e for e in catalog['entries']}
    check(all(catalog[k]==fresh[k] for k in ('schema','base_sha256','font')),'Header changed')
    check(len(entries)==len(catalog['entries'])==len(fresh['entries']),'Incomplete/duplicate catalog')
    for e in fresh['entries']:
        actual=entries[e['id']]
        check(all(actual[k]==e[k] for k in e.keys()-{'english','display','notes'}),'Source/owner changed')
        check(isinstance(actual['english'],str) and actual['english'],'Missing English')
        check(actual['display'] is None or isinstance(actual['display'],str) and actual['display'],'Bad display')
    return entries


def width(text,font):
    # $j2 is copied into four payload bytes, so any printable value fits this
    # worst case. Other slot limits are inherited from the existing readers.
    return previous.core.text_width(text.replace('$j2','WWWW'),font)


def wrap(text,font):
    lines=[]
    for paragraph in text.split('\n'):
        line=''
        for word in paragraph.split(' '):
            candidate=(line+' '+word) if line else word
            if line and width(candidate,font)>208:lines.append(line);line=word
            else:line=candidate
            check(width(line,font)<=208,'Unbreakable service message word')
        lines.append(line)
    return '\n'.join(lines)


def encode(entry,original):
    font=FontZero(original);codec=GameTextCodec(original);text=entry['display'] or entry['english'];family=entry['family'];o=int(entry['offset'],0)
    check(all(32<=ord(c)<127 or c=='\n' for c in text),'ASCII/LF and typed controls required')
    if family=='message':text=wrap(text,font)
    if o in (0xC3E548,0xC3E550):check(width(text,font)<=44,'Warehouse transfer popup overflow')
    if o in (0xC3F334,0xC3F808):check(len(text)==1,'Numeric input unit cell overflow')
    raw=b'';last=0
    for m in previous.core.HEX.finditer(text):raw+=text[last:m.start()].encode()+bytes.fromhex(m[1]);last=m.end()
    raw+=text[last:].encode()+b'\0';check(b'{' not in raw and b'}' not in raw,'Unknown control')
    parsed=codec.parse(raw,0);check(parsed['end']==len(raw),'Embedded terminator')
    dollars=lambda ts:Counter(t['text'] for t in ts if t['kind']=='dollar_command' and t['text']!='$x' and not t['text'].startswith('$/'))
    check(dollars(parsed['tokens'])==dollars(entry['source_tokens']),'Substitution contract changed')
    check(PRINTF.findall(raw)==PRINTF.findall(bytes.fromhex(entry['source_hex'])),'Printf contract changed')
    binary=lambda ts:[t['raw_hex'] for t in ts if t['kind']=='binary_control']
    if family!='stats':check(binary(parsed['tokens'])==binary(entry['source_tokens']),'Binary controls changed')
    else:check(binary(parsed['tokens'])==['03082e','030868'],'Unexpected checked stats columns')
    if family=='menu':check(raw.startswith(b'*')==bytes.fromhex(entry['source_hex']).startswith(b'*'),'Default marker changed')
    maximum=sum((99 if t['text'].startswith('$i') else 29 if t['text'].startswith('$m') else 7 if t['text']=='$t' else 4 if t['text']=='$j2' else 11)
                if t['kind']=='dollar_command' else 11 if t['kind']=='printf' else len(bytes.fromhex(t['raw_hex'])) for t in parsed['tokens'])
    cap=SMALL.get(o,512 if 0xC3DE7C<=o<0xC3E334 else 1000 if family=='message' else 100 if o>=0xC3FB6C else 60 if family=='menu' else 256)
    check(maximum<=cap,f'Buffer overflow {entry["id"]}: {maximum}/{cap}')
    widths=[]
    if family=='message':widths=[width(s,font) for s in text.split('\n')]
    else:
        x=right=0;columns=[]
        for t in parsed['tokens']:
            part=''
            if t['kind']=='binary_control':
                b=bytes.fromhex(t['raw_hex'])
                if b[1] in (8,9):
                    check(right<=b[2],f'Column overlap {entry["id"]}');x=b[2];columns.append(x)
            elif t['kind']=='text':part=t['text']
            elif t['kind']=='dollar_command':x+=width(t['text'],font)
            elif t['kind']=='printf':part='-2147483648' if t['text']=='%7d' else '999'
            right=max(right,x)
            for ch in part:
                _,advance,ink=font.glyph(ch);right=max(right,x+ink);x+=advance
        widths=[max(x,right)]
        check(widths[0]<=(188 if family=='stats' else 120 if family=='menu' else 208),f'Row width overflow {entry["id"]}: {widths}')
    return raw,{'display_template':text,'line_widths':widths,'formatted_byte_upper_bound':maximum,'capacity':cap,'bytes_including_nul':len(raw)}


def add_services(build,catalog,language='english'):
    check(language in ('english','japanese'),'Bad language');entries=validate_catalog(build.original,catalog);relocated={}
    for ident,e in entries.items():
        offset=int(e['offset'],0);source=bytes.fromhex(e['source_hex']);english,metrics=encode(e,build.original)
        build.protect_source(ident,offset,offset+len(source),'ally-services')
        payload=english if language=='english' else source;target=build.allocate(ident,payload,'ally-services')
        for p in e['pointer_owners']:
            at=int(p['offset'],0)
            build.patch(f'{ident}.{at:08x}',at,struct.pack('<I',offset+0x08000000),struct.pack('<I',target+0x08000000),'ally-services',p['evidence'])
        relocated[ident]={'offset':target,'bytes':len(payload),'metrics':metrics}
    return {'language':language,'entries':len(entries),'relocated':relocated}


def build_rom(original,language='english',catalog=None):
    b=RomBuild(original);core=previous.core;core.build_name_rom(original,build=b)
    for module,add in ((core.build_items,core.build_items.add_items),(core.build_item_contexts,core.build_item_contexts.add_contexts),
                       (core.build_enemies,core.build_enemies.add_enemies),(core.build_dungeon_interface,core.build_dungeon_interface.add_interface),
                       (core,core.add_gameplay),(previous,previous.add_help)):
        add(b,load_json(module.CATALOG),'english')
    report=add_services(b,load_json(CATALOG) if catalog is None else catalog,language);data,ledger=b.finish()
    return data,{'source_sha256':digest(original),'rom_sha256':digest(data),'services':report,'ledger':ledger}


def build():
    for language in ('japanese','english'):
        data,report=build_rom(ORIGINAL_ROM.read_bytes(),language)
        atomic_write(OUTPUT/f'torneko3-ally-services-{language}.gba',data)
        atomic_write(OUTPUT/f'{language}-build.json',(json.dumps(report,indent=2)+'\n').encode())
        print(language,report['rom_sha256'],report['ledger']['appended_used_with_padding'],flush=True)


if __name__=='__main__':build()
