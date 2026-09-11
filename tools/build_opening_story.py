"""Insert the opening event section, preserving the existing first narration."""
import json
import struct
from tools import build_ally_nicknames as nick
from tools.build_first_label import ORIGINAL_ROM,ROOT,digest
from tools.game_text import GameTextCodec,rebuild
from tools.rom_build import RomBuild
from tools.translation_pipeline import FontZero,atomic_write,check,load_json,encode_english
from tools.verify_story_provenance import ROUTES

OUTPUT=ROOT/'build/opening-story'
CATALOG=ROOT/'translations/opening-story.json'
OWNERS=OUTPUT/'source-owners.json'
EXTRAS=(0xC2F4A8,0x9C1EB0,0x9C1FBC,0x9C2000,0x9C2044,0x9C209C,0x9C20F8,0x9C213C)
CHOICES=((0x86F4C8,0x86F49C,1),(0x86F4C0,0x86F4A8,0))


def extract_catalog(original):
    provenance=load_json(ROOT/'build/story-provenance/natural/trace.json')
    offsets=list(dict.fromkeys(int(v['source']['offset'],0) for v in provenance['versions']))+list(EXTRAS)
    master={int(e['offset'],0):e for e in load_json(ROOT/'translations/master.json')['entries']};codec=GameTextCodec(original);entries=[]
    for offset in offsets:
        source=codec.parse(original,offset);e=master[offset];events=[]
        check(rebuild(source['tokens'])==original[offset:source['end']],'Opening source round trip failed')
        for word in e['pointer_candidates']:
            at=int(word,0);command,ptr=struct.unpack_from('<II',original,at-4);opcode=command&255
            check(ptr==offset+0x08000000 and opcode in (0x23,0x25,0x27,0x2C),'Unreviewed opening operand')
            events.append({'command_offset':f'0x{at-4:08X}','pointer_offset':word,'command_word':f'0x{command:08X}',
                'opcode':opcode,'wrapper':f'0x{ROUTES[opcode][1]:08X}','naturally_observed':any(int(c['cursor'],0)==at-4+0x08000000 for c in provenance['commands'])})
        entries.append({'id':f'opening.{offset:08x}','master_id':e['id'],'offset':e['offset'],'source_hex':source['raw_hex'],
            'source_tokens':source['tokens'],'japanese':source['display'],'events':events,'reuse':'story.opening_01' if offset==0x91BBB4 else None,
            'layout':'centered' if events[0]['opcode']==0x27 else 'speech' if '「' in source['display'] else 'observation',
            'english':None,'display':None,'notes':'','references':[]})
    for offset,word,value in CHOICES:
        source=codec.parse(original,offset)
        check(struct.unpack_from('<III',original,word)==(offset+0x08000000,0,value),'Event choice record changed')
        entries.append({'id':f'opening.{offset:08x}','master_id':master[offset]['id'],'offset':f'0x{offset:08X}','source_hex':source['raw_hex'],
            'source_tokens':source['tokens'],'japanese':source['display'],'events':[],'reuse':None,'layout':'choice',
            'choice_owners':[{'pointer_offset':f'0x{word:08X}','table_base':'0x0086F49C','record_stride':12,'return_value':value}],
            'english':None,'display':None,'notes':'','references':[]})
    return {'schema':1,'base_sha256':digest(original),'font':0,'scope':'Opening voyage, birthday/dream/storm, arrival and first-bedroom dialogue, including refusal/rest choices and the shared sleeping-son line. 44 story sources plus two shared event-choice labels; first narration reused.','entries':entries}


def validate_catalog(original,catalog):
    fresh=extract_catalog(original);entries={e['id']:e for e in catalog['entries']}
    check(len(entries)==len(catalog['entries'])==46,'Incomplete/duplicate opening section')
    check(all(catalog[k]==fresh[k] for k in ('schema','base_sha256','font','scope')),'Opening header changed')
    for source in fresh['entries']:
        e=entries[source['id']]
        check(all(e[k]==source[k] for k in source.keys()-{'english','display','notes','references'}),'Opening source/owner changed')
        check(isinstance(e['english'],str) and e['english'] and e['display'] is None,'Missing full opening translation')
        check(isinstance(e['notes'],str) and e['notes'],'Missing opening review note')
        encode(e,original)
    return entries


def encode(e,original):
    font=FontZero(original);text=e['english'];source=bytes.fromhex(e['source_hex'])
    if e['reuse']:
        old=next(x for x in load_json(ROOT/'translations/catalog.json')['entries'] if x['id']==e['reuse'])
        check(text==old['english'],'Earlier narration wording changed')
        raw=encode_english(text);visible=text.replace('{center}','');widths=[sum(font.glyph(c)[1] for c in s) for s in visible.split('\n')]
    else:
        check(all(c=='\n' or 32<=ord(c)<127 for c in text) and not any(c in text for c in '$%`{}'),'Unsupported opening control')
        check(text.startswith('\n')==source.startswith(b'\n'),'Narrative pause/leading blank line changed')
        speech=e['layout']=='speech'
        check(('"' in text)==speech and (not speech or text.count('"')==2 and ': "' in text and text.endswith('"')),'Speech quotation/label contract changed')
        lines=[]
        for paragraph in text.split('\n'):
            line=''
            for word in paragraph.split(' '):
                trial=(line+' '+word) if line else word
                # Conservative inset for continuation TAB, verified in native UI.
                limit=184 if speech and lines else 208
                if line and sum(font.glyph(c)[1] for c in trial)>limit:lines.append(line);line=word
                else:line=trial
                check(sum(font.glyph(c)[1] for c in line)<=limit,'Unbreakable story word')
            lines.append(line)
        check(len(lines)<=3,f'Opening message exceeds one three-line page: {e["id"]}: {lines}')
        raw_lines=[('$c'+line if e['layout']=='centered' and line else '\t'+line if speech and i else line) for i,line in enumerate(lines)]
        raw='\n'.join(raw_lines).encode()+b'\0';visible='\n'.join(lines)
        widths=[sum(font.glyph(c)[1] for c in s) for s in lines]
    check(len(raw)<=1024,'Story output exceeds native RAM capacity')
    parsed=GameTextCodec(original).parse(raw,0);check(parsed['end']==len(raw),'Opening text terminator differs')
    check(all(t['kind'] in ('text','control','dollar_command','terminator') and
        (t['kind']!='dollar_command' or t['text']=='$c') and
        (t['kind']!='control' or t['raw_hex'] in ('09','0a')) for t in e['source_tokens']),'Unreviewed source command')
    return raw,{'visible':visible,'line_widths':widths,'lines':len(visible.split('\n')),'bytes_including_nul':len(raw),'payload_limit':1023,'layout':e['layout']}


def build_rom(original,language='english',catalog=None,*,build=None):
    check(language in ('english','japanese'),'Bad opening language');b=RomBuild(original) if build is None else build
    _,old=nick.previous.previous.build_rom(original,build=b)
    companion=nick.previous.add_dialogue(b,load_json(nick.previous.CATALOG),'english')
    nickname=nick.add_nicknames(b,load_json(nick.CATALOG),'english')
    entries=validate_catalog(original,load_json(CATALOG) if catalog is None else catalog);relocated={}
    for e in entries.values():
        source=bytes.fromhex(e['source_hex']);at=int(e['offset'],0);english,metrics=encode(e,original)
        b.protect_source(e['id'],at,at+len(source),'opening-story')
        if e['reuse']:
            target=next(a['offset'] for a in b.allocator.allocations if a['id']==e['reuse'])
            check(bytes(b.data[target:target+len(english)])==english,'Shared first narration differs')
            check(struct.unpack_from('<I',b.data,int(e['events'][0]['pointer_offset'],0))[0]==target+0x08000000,'Shared narration owner missing')
        else:
            target=b.allocate(e['id'],english if language=='english' else source,'opening-story')
            for event in e['events']+e.get('choice_owners',[]):
                b.patch(e['id']+'.'+event['pointer_offset'],int(event['pointer_offset'],0),struct.pack('<I',at+0x08000000),struct.pack('<I',target+0x08000000),'opening-story','Original story event operand; command word/choice parameters preserved')
        relocated[e['id']]={'offset':target,'reuse':e['reuse'],'metrics':metrics}
    data,ledger=b.finish()
    return data,{'source_sha256':digest(original),'rom_sha256':digest(data),'language':language,'opening':{'entries':46,'story_sources':44,'choice_labels':2,'new_sources':45,'new_operand_words':53,'relocated':relocated},'nicknames':nickname,'dialogue':companion,'prior_dialogue':old['dialogue'],'history':old['history'],'ledger':ledger}


def build():
    for language in ('english','japanese'):
        data,report=build_rom(ORIGINAL_ROM.read_bytes(),language)
        atomic_write(OUTPUT/f'torneko3-opening-story-{language}.gba',data)
        atomic_write(OUTPUT/f'{language}-build.json',(json.dumps(report,indent=2)+'\n').encode())
        print(language,report['rom_sha256'],report['ledger']['appended_used_with_padding'],flush=True)

if __name__=='__main__':build()
