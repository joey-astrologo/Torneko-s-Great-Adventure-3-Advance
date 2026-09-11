"""First-village departure arc and related return conversations, shared allocation."""
import argparse
import json
import struct
from tools import build_opening_story as previous
from tools.build_first_label import ORIGINAL_ROM, ROOT, digest
from tools.game_text import GameTextCodec, rebuild
from tools.rom_build import RomBuild
from tools.translation_pipeline import check, load_json, atomic_write, FontZero
from tools.verify_story_provenance import ROUTES

OUTPUT=ROOT/'build/first-village'
CATALOG=ROOT/'translations/first-village.json'
OWNERS=OUTPUT/'source-owners.json'
RANGES=(('family',0x9C2264,0x9C4820),('fisher_home',0x9CDA68,0x9CE000),
        ('chief',0x9D5660,0x9D7201),('house',0x9E178C,0x9E1F60),
        ('village',0x9EA22C,0x9EBFC0),('shrine',0xB6E5A8,0xB6F95F),
        ('shrine_exit',0xB6FC08,0xB6FD50),('shrine_inside',0xB7A904,0xB7A9F0))
SCOPE='First village departure arc: family follow-up, chief and shrine explanation, both companion choices, map/food preparation, village NPC advice and related Torneko return conversations. Later Tipper, celebration and ending states are separate.'


def extract_catalog(original):
    codec=GameTextCodec(original);entries=[]
    earlier={e['master_id'] for e in load_json(previous.CATALOG)['entries']}
    for e in load_json(ROOT/'translations/master.json')['entries']:
        at=int(e['offset'],0);group=next((g for g,a,b in RANGES if a<=at<b),None)
        if group is None or e['id'] in earlier or len(e['japanese'])<=3:continue
        parsed=codec.parse(original,at);raw=bytes.fromhex(parsed['raw_hex']);events=[]
        check(raw==bytes.fromhex(e['source_hex'])==rebuild(parsed['tokens']),'Village source differs')
        for word in e['pointer_candidates']:
            offset=int(word,0);command,pointer=struct.unpack_from('<II',original,offset-4);opcode=command&255
            check(opcode in (0x23,0x25,0x26,0x2A,0x2C) and pointer==at+0x08000000,'Unreviewed village text operand')
            events.append({'command_offset':f'0x{offset-4:08X}','pointer_offset':word,'command_word':f'0x{command:08X}',
                           'opcode':opcode,'wrapper':f'0x{ROUTES[opcode][1]:08X}'})
        check(events,'Village source has no reviewed owner')
        entries.append({'id':f'village.{at:08x}','master_id':e['id'],'group':group,'offset':e['offset'],
            'end_exclusive':f'0x{at+len(raw):08X}','source_hex':raw.hex(),'source_tokens':parsed['tokens'],
            'japanese':parsed['display'],'events':events,'reuse':None,
            'layout':'speech' if '「' in parsed['display'] else 'observation',
            'english':None,'display':None,'notes':'','references':[]})
    check(len(entries)==281,'Village inventory changed')
    return {'schema':1,'base_sha256':digest(original),'font':0,'scope':SCOPE,'entries':entries}


def encode(e,original,hero='Torneko'):
    check(hero in ('Torneko','Tipper'),'Unsupported protagonist')
    text=e['english'];source=bytes.fromhex(e['source_hex']);font=FontZero(original)
    check(all(c=='\n' or 32<=ord(c)<127 for c in text),'Unsupported village glyph')
    check(text.count('$t')==source.count(b'$t') and not any(c in text.replace('$t','') for c in '$%`{}'),'Village formatter contract changed')
    speech=e['layout']=='speech'
    check(('"' in text)==speech and (not speech or text.count('"')==2 and ': "' in text and text.endswith('"')),'Speech presentation changed')
    check(text.startswith('\n')==source.startswith(b'\n'),'Leading blank line changed')
    lines=[]
    width=lambda s:sum(font.glyph(c)[1] for c in s.replace('$t','Torneko'))
    for paragraph in text.split('\n'):
        line=''
        for word in paragraph.split(' '):
            trial=(line+' '+word) if line else word
            limit=184 if speech and lines else 208
            if line and width(trial)>limit:lines.append(line);line=word
            else:line=trial
            check(width(line)<=(184 if speech and lines else 208),'Unbreakable village word')
        lines.append(line)
    check(len(lines)<=3,f'Village page too long: {e["id"]}: {lines}')
    raw='\n'.join(('\t'+line if speech and i else line) for i,line in enumerate(lines)).encode()+b'\0'
    visible='\n'.join(lines).replace('$t',hero)
    check(len(raw.replace(b'$t',hero.encode()))<=1024,'Village formatter exceeds RAM')
    check(all(t['kind'] in ('text','control','dollar_command','terminator') and
        (t['kind']!='control' or t['raw_hex'] in ('09','0a')) and
        (t['kind']!='dollar_command' or t['text']=='$t') for t in e['source_tokens']),'Unreviewed source control')
    check(GameTextCodec(original).parse(raw,0)['end']==len(raw),'Invalid encoded village source')
    return raw,{'visible':visible,'line_widths':[sum(font.glyph(c)[1] for c in s) for s in visible.split('\n')],
                'lines':len(lines),'bytes_including_nul':len(raw),'payload_limit':1023,'layout':e['layout']}


def validate_catalog(original,catalog):
    fresh=extract_catalog(original);entries={e['id']:e for e in catalog['entries']}
    check(len(entries)==len(catalog['entries'])==281,'Incomplete/duplicate village entries')
    check(all(catalog[k]==fresh[k] for k in ('schema','base_sha256','font','scope')),'Village header changed')
    for f in fresh['entries']:
        e=entries[f['id']]
        check(all(e[k]==f[k] for k in f.keys()-{'english','display','notes','references'}),'Village source/owner changed')
        check(isinstance(e['english'],str) and e['english'] and e['display'] is None,'Missing full village translation')
        check(isinstance(e['notes'],str) and e['notes'],'Missing village language review')
        encode(e,original)
    return entries


def build_rom(original,language='english',catalog=None,*,build=None):
    check(language in ('english','japanese'),'Bad village language');b=RomBuild(original) if build is None else build
    _,prior=previous.build_rom(original,build=b)
    entries=validate_catalog(original,load_json(CATALOG) if catalog is None else catalog);relocated={}
    for e in entries.values():
        at=int(e['offset'],0);source=bytes.fromhex(e['source_hex']);raw,metrics=encode(e,original)
        b.protect_source(e['id'],at,at+len(source),'first-village')
        target=b.allocate(e['id'],raw if language=='english' else source,'first-village')
        for event in e['events']:
            b.patch(e['id']+'.'+event['pointer_offset'],int(event['pointer_offset'],0),struct.pack('<I',at+0x08000000),
                struct.pack('<I',target+0x08000000),'first-village','Verified story source operand; command, choice and following script bytes preserved')
        relocated[e['id']]={'offset':target,'metrics':metrics}
    data,ledger=b.finish()
    return data,{'source_sha256':digest(original),'rom_sha256':digest(data),'language':language,
        'village':{'entries':len(entries),'operand_words':sum(len(e['events']) for e in entries.values()),'relocated':relocated},
        'previous_rom_sha256':prior['rom_sha256'],'ledger':ledger}


def build():
    for language in ('english','japanese'):
        data,report=build_rom(ORIGINAL_ROM.read_bytes(),language)
        atomic_write(OUTPUT/f'torneko3-first-village-{language}.gba',data)
        atomic_write(OUTPUT/f'{language}-build.json',(json.dumps(report,indent=2)+'\n').encode())
        print(language,report['rom_sha256'],report['ledger']['appended_used_with_padding'],flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--owners',action='store_true')
    if p.parse_args().owners:
        c=extract_catalog(ORIGINAL_ROM.read_bytes())
        atomic_write(OWNERS,(json.dumps(c,ensure_ascii=False,indent=2)+'\n').encode())
        print(len(c['entries']),'sources',sum(len(e['events']) for e in c['entries']),'operands')
    else:build()
