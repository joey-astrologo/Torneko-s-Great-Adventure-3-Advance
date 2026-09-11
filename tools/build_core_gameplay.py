"""Core command/settings menus and common gameplay feedback, in one ROM ledger."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import struct

from tools.build_first_label import ORIGINAL_ROM, ROOT, digest
from tools.build_name_entry import build_name_rom
from tools import build_items, build_item_contexts, build_enemies, build_dungeon_interface
from tools.game_text import GameTextCodec, PRINTF, rebuild
from tools.rom_build import RomBuild
from tools.translation_pipeline import FontZero, atomic_write, check, load_json
from tools.build_dungeon_interface import measure

CATALOG = ROOT / 'translations/core-gameplay.json'
OUTPUT = ROOT / 'build/core-gameplay'
BLOCKS = ((0x1B3BF0,0x1B3DB1),(0x1B4060,0x1B40D6),(0x1B44B7,0x1B47EA),
          (0x1B4B44,0x1B4EA6),(0x1B51AF,0x1B5B1D),(0xC3FF04,0xC40254))
EXCLUDE = {0x1B453E,0x1B4548,0x1B4563,0x1B530A,0x1B551C,0x1B565D}
CHOICES = (0x1B40D6,0x1B40F6,0x1B4116)
COMMAND_RECORDS = tuple(0x1B3CAB + 30*i for i in range(4))
SHARED = {0xC400AC:'settings.reset',0xC40100:'settings.message_speed',0xC401E0:'settings.display'}
TABLE_WORDS = set(range(0xA6518,0xA6528,4)) | set(range(0xA6534,0xA655C,4)) | {
    0xD90A4,0xD90A8,0xD90AC,0xA6D40,0xA6D64,0xA6D88,0xA6DAC,0xA7C28}
SLOTS = re.compile(r'\$(?:[imdv][0-9]|t)')
HEX = re.compile(r'\{hex:([0-9a-fA-F]+)\}')


def extract_catalog(original):
    master = load_json(ROOT / 'translations/master.json')
    check(digest(original) == master['base_sha256'], 'Wrong source ROM')
    sources = {int(e['offset'],0): e for e in master['entries']
               if any(a <= int(e['offset'],0) < b for a,b in BLOCKS) and int(e['offset'],0) not in EXCLUDE}
    codec, entries = GameTextCodec(original), []
    for offset in sorted(set(sources) | set(CHOICES) | set(COMMAND_RECORDS) | {0x1B4136}):
        s = codec.parse(original,offset)
        check(rebuild(s['tokens']) == original[offset:s['end']], 'Source round-trip failed')
        refs = sources.get(offset,{}).get('pointer_candidates',[])
        if offset == 0x1B4136: refs = ['0x000205A4']
        if offset in CHOICES or offset in COMMAND_RECORDS: refs = []
        owners, excluded = [], []
        for word in refs:
            p = int(word,0)
            check(struct.unpack_from('<I',original,p)[0] == offset + 0x08000000, 'Source pointer mismatch')
            if p >= 0xF0000:
                excluded.append(word)
                continue
            loads = [i for i in range(max(0,p-1024),p,2)
                     if original[i+1]&0xF8 == 0x48 and ((i+4)&~3)+original[i]*4 == p]
            check(loads or p in TABLE_WORDS, f'Unreviewed pointer owner {word}')
            owners.append({'offset':word,'evidence':'typed_data_table' if p in TABLE_WORDS else 'thumb_literal',
                           'literal_loads':[f'0x{i+0x08000000:08X}' for i in loads]})
        check(owners or offset in CHOICES or offset in COMMAND_RECORDS, 'Source lacks an insertion owner')
        family = ('choice' if offset in CHOICES or offset == 0x1B4136 else
                  'stats' if 0x1B3C16 <= offset < 0x1B3CAB else
                  'command' if 0x1B3CAB <= offset < 0x1B3DB1 else
                  'actor' if offset in (0x1B4552,0x1B4558) else
                  'label' if offset in (0x1B44B7,0x1B44C4,0xC3FFA4) else
                  'setting' if offset >= 0xC3FFAC else 'message')
        entries.append({'id':f'gameplay.{offset:08x}','family':family,'offset':f'0x{offset:08X}',
                        'japanese':s['display'],'source_hex':s['raw_hex'],'source_tokens':s['tokens'],
                        'pointer_owners':owners,'excluded_pointer_candidates':excluded,
                        'master_id':f'jp_{offset:08x}','english':None,'display':None,'notes':''})
    return {'schema':1,'base_sha256':digest(original),'font':0,'entries':entries}


def validate_catalog(original,catalog):
    fresh=extract_catalog(original)
    check(all(catalog[k]==fresh[k] for k in ('schema','base_sha256','font')), 'Catalog header changed')
    check(len(catalog['entries'])==len(fresh['entries'])==262,'Incomplete core gameplay scope')
    entries={e['id']:e for e in catalog['entries']}
    check(len(entries)==262,'Duplicate entry ID')
    for s in fresh['entries']:
        e=entries[s['id']]
        check(all(e[k]==s[k] for k in s.keys()-{'english','display','notes'}),f"Source metadata changed: {s['id']}")
        check(isinstance(e['english'],str) and e['english'],'Missing English')
        check(e['display'] is None or isinstance(e['display'],str) and e['display'],'Bad display override')
    return entries


def slot_width(token,font):
    return 144 if token.startswith('$i') else 120 if token.startswith('$m') else (
        max(measure('Torneko',font),measure('Tipper',font)) if token=='$t' else measure('-2147483648',font))


def text_width(text,font):
    result=0;last=0
    for m in SLOTS.finditer(text):
        result+=measure(text[last:m.start()],font)+slot_width(m[0],font);last=m.end()
    return result+measure(text[last:],font)


def wrap(text,font,limit=208):
    lines=[]
    for paragraph in text.split('\n'):
        line=''
        for word in paragraph.split(' '):
            candidate=(line+' '+word) if line else word
            if line and text_width(candidate,font)>limit:
                lines.append(line);line=word
            else:line=candidate
            check(text_width(line,font)<=limit,f'Unbreakable word exceeds message width: {word}')
        lines.append(line)
    check(len(lines)<=3,f'Message needs more than three lines: {text}')
    return '\n'.join(lines)


def row_metrics(entry,tokens,font):
    """Check fixed columns, including menu arrows and printf stress values."""
    limits={'stats':208,'command':80,'setting':152,'actor':120,'choice':208,'label':208}
    numbers={0x1B3C16:[999,200,200],0x1B3C3C:[999,2147483647],
             0x1B3C5D:[99,99,99,59,59],0x1B3C84:[99,99,999,59,59]}
    values=iter(numbers.get(int(entry['offset'],0),[]))
    x=right=0;columns=[]
    for token in tokens:
        raw=bytes.fromhex(token['raw_hex']);text=''
        if token['kind']=='binary_control' and raw[:2]==b'\x03\x08':
            check(right<=raw[2],f"Fixed columns overlap: {entry['id']}")
            columns.append({'end':raw[2],'used_right':right});x=raw[2]
        elif token['kind']=='text':text=token['text']
        elif token['kind']=='dollar_command' and token['text']=='$t':text='Torneko'
        elif token['kind']=='printf':text=token['text'] % next(values)
        for character in text:
            _,advance,ink=font.glyph(character)
            right=max(right,x+ink);x+=advance
    check(max(x,right)<=limits[entry['family']],f"Gameplay row exceeds its native width: {entry['id']}")
    return {'right':max(x,right),'pixel_limit':limits[entry['family']],'columns':columns,
            'numeric_fixture':numbers.get(int(entry['offset'],0))}


def encode(entry,original,message_wrap=None):
    font=FontZero(original);codec=GameTextCodec(original)
    text=entry['display'] or entry['english']
    check(all(32<=ord(c)<127 or c=='\n' for c in text),'English must use ASCII and typed controls')
    if entry['family']=='message':
        check(not any(c in text for c in '{}%*'), 'Unsupported message control')
        text=(message_wrap or wrap)(text,font)
    raw=b'';last=0
    text=text.replace('{arrow}','{hex:83c1}')
    for m in HEX.finditer(text):
        raw+=text[last:m.start()].encode()+bytes.fromhex(m[1]);last=m.end()
    raw+=text[last:].encode()+b'\0'
    check(not any(c in raw for c in (b'{',b'}')),'Unknown typed control')
    parsed=codec.parse(raw,0)
    check(parsed['end']==len(raw),'Embedded terminator in English')
    source=bytes.fromhex(entry['source_hex'])
    check(PRINTF.findall(source)==PRINTF.findall(raw),f"Printf argument contract changed: {entry['id']}")
    def dollars(tokens):return Counter(t['text'] for t in tokens if t['kind']=='dollar_command' and not t['text'].startswith('$/'))
    check(dollars(parsed['tokens'])==dollars(entry['source_tokens']),f"Substitution contract changed: {entry['id']}")
    def binary(tokens):return [t['raw_hex'] for t in tokens if t['kind']=='binary_control']
    check(binary(parsed['tokens'])==binary(entry['source_tokens']),f"Menu control contract changed: {entry['id']}")
    check(raw.count(b'\x83\xc1')==source.count(b'\x83\xc1'),'Submenu glyph lost')
    if entry['family']=='setting':check(raw.startswith(b'*')==source.startswith(b'*'),'Default marker lost')
    if entry['family']=='message':
        widths=[text_width(x,font) for x in text.split('\n')]
        maximum=0
        for token in parsed['tokens']:
            if token['kind']=='dollar_command':maximum+=100 if token['text'].startswith('$i') else 30 if token['text'].startswith('$m') else 11
            else:maximum+=len(bytes.fromhex(token['raw_hex']))
        check(maximum<=1000,'Message output exceeds bounded buffer')
    else:
        widths=[];maximum=len(raw)+128
        check(maximum<=256,'Menu formatter/wrapper buffer exceeded')
        row=row_metrics(entry,parsed['tokens'],font)
    if entry['family']=='actor':check(len(raw)<=30 and measure(text,font)<=120,'Actor copy exceeds fixed budget')
    if int(entry['offset'],0) in CHOICES:check(len(raw)<=32,'Choice exceeds fixed stride')
    if int(entry['offset'],0) in COMMAND_RECORDS:check(len(raw)<=30,'Command exceeds fixed stride')
    return raw,{'worst_line_widths':widths,'formatted_byte_upper_bound':maximum,'bytes_including_nul':len(raw),
                'display_template':text,'row_layout':None if entry['family']=='message' else row}


def add_gameplay(build,catalog,language='english',message_wrap=None):
    check(language in ('english','japanese'),'Bad language')
    entries=validate_catalog(build.original,catalog);prepared={};metrics={};relocated={}
    for ident,e in entries.items():
        offset=int(e['offset'],0);raw=bytes.fromhex(e['source_hex'])
        build.protect_source(ident,offset,offset+len(raw),'core-gameplay')
        en,metrics[ident]=encode(e,build.original,message_wrap)
        prepared[ident]=en if language=='english' else raw
    choice=b''.join(prepared[f'gameplay.{o:08x}'].ljust(32,b'\0') for o in CHOICES)
    build.protect_source('gameplay.stair-records',CHOICES[0],0x1B4136,'core-gameplay')
    at=build.allocate('gameplay.stair-records',choice,'core-gameplay')
    build.patch('gameplay.stair-base',0x207EC,struct.pack('<I',0x081B40D6),struct.pack('<I',at+0x08000000),'core-gameplay','Relocate all three 32-byte records, preserving stride')
    command=b''.join(prepared[f'gameplay.{o:08x}'].ljust(30,b'\0') for o in COMMAND_RECORDS)
    build.protect_source('gameplay.command-records',COMMAND_RECORDS[0],0x1B3D23,'core-gameplay')
    command_at=build.allocate('gameplay.command-records',command,'core-gameplay')
    build.patch('gameplay.command-base',0x6CC04,struct.pack('<I',0x081B3CAB),struct.pack('<I',command_at+0x08000000),
                'core-gameplay','Complete four-record command table; preserve 30-byte stride')
    for ident,e in entries.items():
        offset=int(e['offset'],0)
        if offset in SHARED:
            owner=[p for p in build.patches if p['id']==SHARED[offset] and p['owner']=='curated']
            check(len(owner)==1 and owner[0]['offset']==int(e['pointer_owners'][0]['offset'],0), 'Shared owner changed')
            target=struct.unpack('<I',bytes.fromhex(owner[0]['after']))[0]-0x08000000
            english,_=encode(e,build.original)
            check(build.data[target:target+len(english)]==english,'Shared curated English differs')
            relocated[ident]={'offset':target,'bytes':len(english),'metrics':metrics[ident],'shared_owner':SHARED[offset]}
            continue
        target=(at+(offset-CHOICES[0]) if offset in CHOICES else command_at+(offset-COMMAND_RECORDS[0])
                if offset in COMMAND_RECORDS else build.allocate(ident,prepared[ident],'core-gameplay'))
        for owner in e['pointer_owners']:
            word=int(owner['offset'],0)
            build.patch(f'{ident}.{word:08x}',word,struct.pack('<I',offset+0x08000000),struct.pack('<I',target+0x08000000),'core-gameplay',owner['evidence'])
        relocated[ident]={'offset':target,'bytes':len(prepared[ident]),'metrics':metrics[ident]}
    windows=[]
    if language=='english':
        for word in (0xCA28B8,0xCA2978):
            build.patch(f'gameplay.command-width.{word:08x}',word,b'\x09\x00',b'\x0a\x00',
                        'core-gameplay','Stock window records 1/4: 80px command panel; keep cursor columns')
        for pointer in (0x76234,):
            source=struct.unpack_from('<I',build.original,pointer)[0]-0x08000000
            raw=bytearray(build.original[source:source+64])
            check(struct.unpack_from('<3h',raw)==(2,3,9),'Unexpected command panel')
            build.protect_source(f'gameplay.window.{pointer:08x}',source,source+64,'core-gameplay')
            struct.pack_into('<h',raw,4,10)
            target=build.allocate(f'gameplay.window.{pointer:08x}',raw,'core-gameplay')
            build.patch(f'gameplay.window.{pointer:08x}',pointer,struct.pack('<I',source+0x08000000),struct.pack('<I',target+0x08000000),'core-gameplay','Widen main command panel to 80px; preserve columns/cursor positions')
            windows.append({'source':source,'pointer':pointer,'offset':target})
    return {'language':language,'entries':len(entries),'catalog_sha256':digest(json.dumps(catalog,sort_keys=True,ensure_ascii=False).encode()),'relocated':relocated,'windows':windows}


def build_rom(original,language='english',catalog=None):
    b=RomBuild(original);build_name_rom(original,build=b)
    for module,add in ((build_items,build_items.add_items),(build_item_contexts,build_item_contexts.add_contexts),(build_enemies,build_enemies.add_enemies),(build_dungeon_interface,build_dungeon_interface.add_interface)):
        add(b,load_json(module.CATALOG),'english')
    report=add_gameplay(b,load_json(CATALOG) if catalog is None else catalog,language)
    data,ledger=b.finish()
    return data,{'source_sha256':digest(original),'rom_sha256':digest(data),'gameplay':report,'ledger':ledger}


def build(output=OUTPUT):
    result={lang:build_rom(ORIGINAL_ROM.read_bytes(),lang) for lang in ('japanese','english')}
    for lang,(data,report) in result.items():
        atomic_write(Path(output)/f'{lang}-build.json',(json.dumps(report,indent=2)+'\n').encode())
        atomic_write(Path(output)/f'torneko3-core-gameplay-{lang}.gba',data)
        print(lang,report['rom_sha256'],report['ledger']['appended_used_with_padding'],flush=True)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,default=OUTPUT)
    build(parser.parse_args().output)
