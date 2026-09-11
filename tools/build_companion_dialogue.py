"""Complete the known ally dialogue table and its conditional Rosa alternatives."""
from collections import Counter
import json
import struct
from tools import build_ally_dialogue as previous
from tools.build_first_label import ORIGINAL_ROM,ROOT,digest
from tools.game_text import GameTextCodec,rebuild,PRINTF
from tools.translation_pipeline import FontZero,atomic_write,check,load_json
from tools.rom_build import RomBuild

CATALOG=ROOT/'translations/companion-dialogue.json'
OUTPUT=ROOT/'build/companion-dialogue'
TABLE=previous.TABLE
ALTERNATES=0x1B4FE4
ROWS=(0,*range(51,200))


def extract_catalog(original):
    codec=GameTextCodec(original);entries=[]
    fields=[('dialogue',r,f,TABLE+r*80+f*4) for r in ROWS for f in range(20)]
    fields += [('rosa_alt',191,f,ALTERNATES+f*4) for f in range(3)]
    for family,row,field,word in fields:
        pointer=struct.unpack_from('<I',original,word)[0]
        if not pointer:continue
        offset=pointer-0x08000000;source=codec.parse(original,offset)
        check(rebuild(source['tokens'])==original[offset:source['end']],'Source round trip failed')
        ident=f'companion.dialogue.{row:03d}.{field:02d}' if family=='dialogue' else f'companion.rosa_alt.{field}'
        entries.append({'id':ident,'family':family,'row':row,'field':field,'offset':f'0x{offset:08X}',
            'pointer_offset':f'0x{word:08X}','japanese':source['display'],'source_hex':source['raw_hex'],'source_tokens':source['tokens'],
            'master_id':f'jp_{offset:08x}','english':None,'display':None,'notes':''})
    return {'schema':1,'base_sha256':digest(original),'font':0,'scope':'All remaining ally dialogue table fields plus three conditional Rosa alternatives','entries':entries}


def validate_catalog(original,catalog):
    fresh=extract_catalog(original);entries={e['id']:e for e in catalog['entries']}
    check(all(catalog[k]==fresh[k] for k in ('schema','base_sha256','font','scope')),'Catalog header changed')
    check(len(entries)==len(catalog['entries'])==1227,'Incomplete/duplicate dialogue inventory')
    for source in fresh['entries']:
        e=entries[source['id']]
        check(all(e[k]==source[k] for k in source.keys()-{'english','display','notes'}),'Dialogue source/owner changed')
        check(isinstance(e['english'],str) and e['english'],'Missing English')
        check(e['display'] is None,'Keep full dialogue wording')
        check(isinstance(e['notes'],str),'Bad notes')
    return entries


def encode(entry,original):
    text=entry['english'];codec=GameTextCodec(original);font=FontZero(original)
    check(all(32<=ord(c)<127 or c=='\n' for c in text),'ASCII/LF required')
    check(not any(c in text for c in '{}%`'),'Unsupported dialogue control')
    speech=entry['japanese'].startswith('$m0「')
    check((text.startswith('$m0: "') and text.endswith('"'))==speech,'Speaker/quotation contract changed')
    text=previous.previous.wrap(text,font);raw=text.encode()+b'\0';parsed=codec.parse(raw,0)
    commands=lambda ts:Counter(t['text'] for t in ts if t['kind']=='dollar_command' and t['text']!='$x')
    source_commands=commands(entry['source_tokens'])
    check(set(source_commands)<={'$m0','$m1','$t'},'Unreviewed substitution')
    check(commands(parsed['tokens'])==source_commands,'Dialogue substitutions changed')
    check(not PRINTF.findall(bytes.fromhex(entry['source_hex'])) and not any(t['kind']=='binary_control' for t in entry['source_tokens']),'Unreviewed dialogue controls')
    maximum=sum((7 if t['text']=='$t' else 29) if t['kind']=='dollar_command' else len(bytes.fromhex(t['raw_hex'])) for t in parsed['tokens'])
    check(maximum<=1000 and parsed['end']==len(raw),'Dialogue formatter capacity/terminator differs')
    lines=text.split('\n');check(len(lines)<=6,'Dialogue exceeds two measured pages')
    return raw,{'display_template':text,'line_widths':[previous.previous.width(s,font) for s in lines],
        'formatted_byte_upper_bound':maximum,'capacity':1000,'pages':(len(lines)+2)//3,'bytes_including_nul':len(raw)}


def add_dialogue(build,catalog,language='english'):
    check(language in ('english','japanese'),'Bad language');entries=validate_catalog(build.original,catalog);relocated={}
    for ident,e in entries.items():
        offset=int(e['offset'],0);source=bytes.fromhex(e['source_hex']);english,metrics=encode(e,build.original)
        build.protect_source(ident,offset,offset+len(source),'companion-dialogue')
        raw=english if language=='english' else source;target=build.allocate(ident,raw,'companion-dialogue')
        build.patch(ident,int(e['pointer_offset'],0),struct.pack('<I',offset+0x08000000),struct.pack('<I',target+0x08000000),
            'companion-dialogue','Original ally row/response pointer or conditional Rosa table; native reader 0803C3C8')
        relocated[ident]={'offset':target,'bytes':len(raw),'metrics':metrics}
    return {'language':language,'entries':len(entries),'relocated':relocated}


def build_rom(original,language='english',catalog=None):
    b=RomBuild(original);_,prior=previous.build_rom(original,build=b)
    report=add_dialogue(b,load_json(CATALOG) if catalog is None else catalog,language);data,ledger=b.finish()
    return data,{'source_sha256':digest(original),'rom_sha256':digest(data),'dialogue':report,'prior_dialogue':prior['dialogue'],
        'history':prior['history'],'ledger':ledger}


def build():
    for language in ('japanese','english'):
        data,report=build_rom(ORIGINAL_ROM.read_bytes(),language)
        atomic_write(OUTPUT/f'torneko3-companion-dialogue-{language}.gba',data)
        atomic_write(OUTPUT/f'{language}-build.json',(json.dumps(report,indent=2)+'\n').encode())
        print(language,report['rom_sha256'],report['ledger']['appended_used_with_padding'],flush=True)


if __name__=='__main__':build()
