"""Complete dialogue sets for 50 allies, with safe prior-message history layout."""
from collections import Counter
import json
import struct
from tools import build_tutorial_gameplay as previous
from tools.build_first_label import ORIGINAL_ROM,ROOT,digest
from tools.game_text import GameTextCodec,rebuild,PRINTF
from tools.translation_pipeline import FontZero,atomic_write,check,load_json
from tools.rom_build import RomBuild

CATALOG=ROOT/'translations/ally-dialogue.json'
OUTPUT=ROOT/'build/ally-dialogue'
TABLE=0x1A60B0
ROWS=range(1,51)
FIELDS=range(8)
CORE=previous.CORE
HELP=previous.previous.previous


def extract_catalog(original):
    codec=GameTextCodec(original);entries=[]
    for row in ROWS:
        for field in FIELDS:
            word=TABLE+row*80+field*4;offset=struct.unpack_from('<I',original,word)[0]-0x08000000
            source=codec.parse(original,offset)
            check(rebuild(source['tokens'])==original[offset:source['end']],'Source round trip failed')
            entries.append({'id':f'ally.dialogue.{row:03d}.{field}','family':'dialogue','row':row,'field':field,
                'offset':f'0x{offset:08X}','pointer_offset':f'0x{word:08X}',
                'japanese':source['display'],'source_hex':source['raw_hex'],'source_tokens':source['tokens'],
                'master_id':f'jp_{offset:08x}','english':None,'display':None,'notes':''})
    return {'schema':1,'base_sha256':digest(original),'font':0,'scope':{'first_row':1,'last_row_inclusive':50,'fields':list(FIELDS)},'entries':entries}


def validate_catalog(original,catalog):
    fresh=extract_catalog(original);entries={e['id']:e for e in catalog['entries']}
    check(all(catalog[k]==fresh[k] for k in ('schema','base_sha256','font','scope')),'Catalog header changed')
    check(len(entries)==len(catalog['entries'])==400,'Incomplete/duplicate dialogue set')
    for source in fresh['entries']:
        e=entries[source['id']]
        check(all(e[k]==source[k] for k in source.keys()-{'english','display','notes'}),'Dialogue source/owner changed')
        check(isinstance(e['english'],str) and e['english'],'Missing dialogue')
        check(e['display'] is None,'Dialogue keeps full wording; use measured native pages')
        check(isinstance(e['notes'],str),'Bad notes')
    return entries


def encode(entry,original):
    text=entry['english'];codec=GameTextCodec(original);font=FontZero(original)
    check(all(32<=ord(c)<127 or c=='\n' for c in text),'ASCII/LF required')
    check(not any(c in text for c in '{}%`'),'Unsupported dialogue control')
    check(text.startswith('$m0: "') and text.endswith('"'),'Speaker/quotation contract changed')
    text=previous.wrap(text,font);raw=text.encode()+b'\0';parsed=codec.parse(raw,0)
    commands=lambda ts:Counter(t['text'] for t in ts if t['kind']=='dollar_command' and t['text']!='$x')
    check(commands(parsed['tokens'])==commands(entry['source_tokens']),'Dialogue substitutions changed')
    check(not PRINTF.findall(bytes.fromhex(entry['source_hex'])) and not any(t['kind']=='binary_control' for t in entry['source_tokens']),'Unreviewed dialogue controls')
    maximum=sum(29 if t['kind']=='dollar_command' else len(bytes.fromhex(t['raw_hex'])) for t in parsed['tokens'])
    check(maximum<=1000,'Dialogue formatter capacity exceeded')
    check(len(text.split('\n'))<=6,'Dialogue exceeds two measured pages')
    return raw,{'display_template':text,'line_widths':[previous.width(s,font) for s in text.split('\n')],
                'formatted_byte_upper_bound':maximum,'capacity':1000,'pages':(len(text.split('\n'))+2)//3,'bytes_including_nul':len(raw)}


def history_wrap(text,font):
    """Retain old layout unless its worst-case history payload exceeds 59.

    Reflow only whitespace. The existing component still owns its allocation
    and original pointer patches. Historical builders keep their default layout.
    """
    old=CORE.wrap(text,font)
    if all(previous.line_bytes(s)<=59 for s in old.split('\n')):return old
    new=previous.wrap(' '.join(text.split()),font)
    check(new.split()==text.split(),'History reflow changed wording')
    check(len(new.split('\n'))<=3,'History reflow exceeds three lines')
    return new


def history_inventory(original):
    rows=[];changed=[]
    for module in (CORE,HELP):
        for e in load_json(module.CATALOG)['entries']:
            if e['family']!='message':continue
            before,old=module.encode(e,original);after,new=module.encode(e,original,history_wrap)
            record={'catalog':module.CATALOG.name,'id':e['id'],'offset':e['offset'],'pointer_owners':e['pointer_owners'],
                    'old_display':old['display_template'],'display_template':new['display_template'],
                    'old_raw_hex':before.hex(),'raw_hex':after.hex(),'changed':before!=after,
                    'history_payload_upper_bounds':[previous.line_bytes(s) for s in new['display_template'].split('\n')]}
            check(all(n<=59 for n in record['history_payload_upper_bounds']),'Unbounded old message')
            rows.append(record)
            if record['changed']:changed.append(e['id'])
    return {'messages':rows,'changed_ids':changed}


def add_dialogue(build,catalog,language='english'):
    check(language in ('english','japanese'),'Bad language');entries=validate_catalog(build.original,catalog);relocated={}
    for ident,e in entries.items():
        offset=int(e['offset'],0);source=bytes.fromhex(e['source_hex']);english,metrics=encode(e,build.original)
        build.protect_source(ident,offset,offset+len(source),'ally-dialogue')
        raw=english if language=='english' else source;target=build.allocate(ident,raw,'ally-dialogue')
        build.patch(ident,int(e['pointer_offset'],0),struct.pack('<I',offset+0x08000000),struct.pack('<I',target+0x08000000),'ally-dialogue','Original 80-byte ally record, field index*4; typed reader 0803C3C8')
        relocated[ident]={'offset':target,'bytes':len(raw),'metrics':metrics}
    return {'language':language,'entries':len(entries),'relocated':relocated}


def build_rom(original,language='english',catalog=None,build=None):
    b=RomBuild(original) if build is None else build;CORE.build_name_rom(original,build=b)
    for module,add in ((CORE.build_items,CORE.build_items.add_items),(CORE.build_item_contexts,CORE.build_item_contexts.add_contexts),
                       (CORE.build_enemies,CORE.build_enemies.add_enemies),(CORE.build_dungeon_interface,CORE.build_dungeon_interface.add_interface)):
        add(b,load_json(module.CATALOG),'english')
    core_report=CORE.add_gameplay(b,load_json(CORE.CATALOG),'english',history_wrap)
    help_report=HELP.add_help(b,load_json(HELP.CATALOG),'english',history_wrap)
    previous.previous.add_services(b,load_json(previous.previous.CATALOG),'english')
    previous.add_tutorials(b,load_json(previous.CATALOG),'english')
    report=add_dialogue(b,load_json(CATALOG) if catalog is None else catalog,language)
    history=history_inventory(original)
    for e in history['messages']:
        e['relocated']=(core_report if e['catalog']=='core-gameplay.json' else help_report)['relocated'][e['id']]['offset']
    data,ledger=b.finish()
    return data,{'source_sha256':digest(original),'rom_sha256':digest(data),'dialogue':report,'history':history,'ledger':ledger}


def build():
    for language in ('japanese','english'):
        data,report=build_rom(ORIGINAL_ROM.read_bytes(),language)
        atomic_write(OUTPUT/f'torneko3-ally-dialogue-{language}.gba',data)
        atomic_write(OUTPUT/f'{language}-build.json',(json.dumps(report,indent=2)+'\n').encode())
        print(language,report['rom_sha256'],report['ledger']['appended_used_with_padding'],flush=True)


if __name__=='__main__':build()
