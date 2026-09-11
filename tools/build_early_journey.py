"""Early dungeon rest stops, advice choices and global place-name records."""
import argparse
import json
import struct
from tools import build_first_village as previous
from tools.build_first_label import ORIGINAL_ROM, ROOT, digest
from tools.game_text import GameTextCodec, rebuild
from tools.rom_build import RomBuild
from tools.translation_pipeline import check, load_json, atomic_write, FontZero
from tools.verify_story_provenance import ROUTES

OUTPUT=ROOT/'build/early-journey'
CATALOG=ROOT/'translations/early-journey.json'
OWNERS=OUTPUT/'source-owners.json'
RANGES=(('shrine_depths',0xB7A55C,0xB7AD80),('advice_and_undersea_day',0xB84F18,0xB87E00),
        ('undersea_night',0xB92D68,0xB93E00),('temple',0xB9EACC,0xB9F200),
        ('mountain_rest',0xBA871C,0xBA8E80))
PLACE_BASE=0x872E84
PLACE_COUNT=30
PLACE_UI={0xC3F010:(0x767E8,'place_heading'),0xC3F018:(0x7682C,'place_prompt')}
SCOPE='Shrine depths, dungeon advice and all six topic choices, Undersea House day/night and related return states, temple passages and mountain rest stop; global place-name table and Zoom picker heading/confirmation. Lighthouse scenes and dungeon traversal remain separate.'


def extract_catalog(original):
    codec=GameTextCodec(original);entries=[]
    master=load_json(ROOT/'translations/master.json')['entries']
    prior={e['master_id'] for e in load_json(previous.CATALOG)['entries']}
    places={struct.unpack_from('<I',original,PLACE_BASE+i*12)[0]-0x08000000:(i,PLACE_BASE+i*12) for i in range(PLACE_COUNT)}
    for e in master:
        at=int(e['offset'],0);group=next((g for g,a,b in RANGES if a<=at<b),None)
        if at in places:group='place'
        if at in PLACE_UI:group='place_ui'
        if group is None or e['id'] in prior:continue
        # Short candidates below point into event data, not text operands.
        if at in (0xB87B04,0xB87BC8,0xB93180,0xB93D90,0xB9F01C,0xB9F020,0xB9F024,0xB9F1E4,0xBA8C60):continue
        parsed=codec.parse(original,at);raw=bytes.fromhex(parsed['raw_hex']);events=[];owners=[]
        check(raw==bytes.fromhex(e['source_hex'])==rebuild(parsed['tokens']),'Journey source differs')
        if group=='place_ui':
            word,layout=PLACE_UI[at]
            check(e['pointer_candidates']==[f'0x{word:08X}'],'Unreviewed place UI reference')
            owners=[{'pointer_offset':f'0x{word:08X}','reader':'0x08076624','kind':'literal'}]
        elif group=='place':
            i,word=places[at]
            check(e['pointer_candidates']==[f'0x{word:08X}'],'Unreviewed place reference')
            owners=[{'pointer_offset':f'0x{word:08X}','index':i,'record_stride':12,
                     'record_hex':original[word:word+12].hex(),'reader':'0x08066CC8'}]
            layout='place'
        else:
            for word in e['pointer_candidates']:
                offset=int(word,0);command,pointer=struct.unpack_from('<II',original,offset-4);opcode=command&255
                check(opcode in (0x23,0x25,0x2A,0x2C,0x97,0x98) and pointer==at+0x08000000,'Unreviewed journey operand: '+e['id'])
                ev={'command_offset':f'0x{offset-4:08X}','pointer_offset':word,'command_word':f'0x{command:08X}','opcode':opcode}
                if opcode==0x98:
                    prompt=offset-12
                    while original[prompt]==0x98:prompt-=8
                    check(original[prompt]==0x97,'Choice is not in a reviewed 97/98 prefix')
                    ev['prompt_command_offset']=f'0x{prompt:08X}';ev['choice_index']=(offset-4-prompt)//8-1
                else:ev['wrapper']=f'0x{ROUTES[opcode][1]:08X}'
                events.append(ev)
            check(events,'Journey source has no owner')
            layout='choice' if all(ev['opcode']==0x98 for ev in events) else 'speech' if '「' in parsed['display'] else 'observation'
        entries.append({'id':f'journey.{at:08x}','master_id':e['id'],'group':group,'offset':e['offset'],
            'end_exclusive':f'0x{at+len(raw):08X}','source_hex':raw.hex(),'source_tokens':parsed['tokens'],
            'japanese':parsed['display'],'events':events,'place_owners':owners,'reuse':None,'layout':layout,
            'english':None,'display':None,'notes':'','references':[]})
    check(sum(e['layout']=='place' for e in entries)==PLACE_COUNT,'Incomplete place table')
    return {'schema':1,'base_sha256':digest(original),'font':0,'scope':SCOPE,'entries':entries}


def encode(e,original,hero='Torneko'):
    if e['layout']=='place_prompt':
        check(e['english']=='Zoom to\n$m0?' and e['display'] is None,'Unreviewed Zoom prompt')
        check(bytes.fromhex(e['source_hex']).count(b'$m0')==1,'Zoom substitution changed')
        raw=e['english'].encode()+b'\0'
        return raw,{'visible_template':e['english'],'lines':2,'bytes_including_nul':len(raw),'payload_limit':1023,'layout':e['layout']}
    if e['layout']=='place_heading':
        copy=dict(e,layout='place');raw,metrics=encode(copy,original,hero)
        check(metrics['line_widths'][0]<=32,'Zoom heading exceeds native 32px window')
        return raw,metrics
    if e['layout'] not in ('choice','place'):return previous.encode(e,original,hero)
    text=e['display'] or e['english'];font=FontZero(original)
    check(text and all(32<=ord(c)<127 and c not in '$%`{}' for c in text),'Invalid journey label')
    width=sum(font.glyph(c)[1] for c in text)
    check(width<=(156 if e['layout']=='place' else 208),'Journey label exceeds native width: '+e['id'])
    raw=text.encode()+b'\0'
    if e['layout']=='place':check(len(raw)<=30,'Place name exceeds native substitution slot')
    return raw,{'visible':text,'line_widths':[width],'lines':1,'bytes_including_nul':len(raw),'payload_limit':1023,'layout':e['layout']}


def validate_catalog(original,catalog):
    fresh=extract_catalog(original);entries={e['id']:e for e in catalog['entries']}
    check(len(entries)==len(catalog['entries'])==len(fresh['entries']),'Incomplete/duplicate journey entries')
    check(all(catalog[k]==fresh[k] for k in ('schema','base_sha256','font','scope')),'Journey header changed')
    for f in fresh['entries']:
        e=entries[f['id']]
        check(all(e[k]==f[k] for k in f.keys()-{'english','display','notes','references'}),'Journey source/owner changed')
        check(isinstance(e['english'],str) and e['english'],'Missing journey translation')
        check(e['display'] is None or e['layout'] in ('place','place_heading'),'Unreviewed display override')
        check(isinstance(e['notes'],str) and e['notes'],'Missing journey language review')
        encode(e,original)
    return entries


def build_rom(original,language='english',catalog=None):
    check(language in ('english','japanese'),'Bad journey language');b=RomBuild(original)
    _,prior=previous.build_rom(original,build=b)
    entries=validate_catalog(original,load_json(CATALOG) if catalog is None else catalog);relocated={}
    for e in entries.values():
        at=int(e['offset'],0);source=bytes.fromhex(e['source_hex']);raw,metrics=encode(e,original)
        b.protect_source(e['id'],at,at+len(source),'early-journey')
        target=b.allocate(e['id'],raw if language=='english' else source,'early-journey')
        for owner in e['events']+e['place_owners']:
            b.patch(e['id']+'.'+owner['pointer_offset'],int(owner['pointer_offset'],0),struct.pack('<I',at+0x08000000),
                struct.pack('<I',target+0x08000000),'early-journey','Verified event operand or 12-byte place record; command, choice parameters and map coordinates preserved')
        relocated[e['id']]={'offset':target,'metrics':metrics}
    data,ledger=b.finish()
    return data,{'source_sha256':digest(original),'rom_sha256':digest(data),'language':language,
        'journey':{'entries':len(entries),'pointer_words':sum(len(e['events'])+len(e['place_owners']) for e in entries.values()),'relocated':relocated},
        'previous_rom_sha256':prior['rom_sha256'],'ledger':ledger}


def build():
    for language in ('english','japanese'):
        data,report=build_rom(ORIGINAL_ROM.read_bytes(),language)
        atomic_write(OUTPUT/f'torneko3-early-journey-{language}.gba',data)
        atomic_write(OUTPUT/f'{language}-build.json',(json.dumps(report,indent=2)+'\n').encode())
        print(language,report['rom_sha256'],report['ledger']['appended_used_with_padding'],flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--owners',action='store_true')
    if p.parse_args().owners:
        c=extract_catalog(ORIGINAL_ROM.read_bytes());atomic_write(OWNERS,(json.dumps(c,ensure_ascii=False,indent=2)+'\n').encode())
        print(len(c['entries']),'sources',sum(len(e['events']) for e in c['entries']),'event operands',sum(len(e['place_owners']) for e in c['entries']),'place/UI pointers')
    else:build()
