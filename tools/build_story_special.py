"""Pet-name story substitutions and a coordinated Latin tree password."""
import argparse
from collections import Counter
import json
import re
import struct
from tools import build_story_completion as previous
from tools.build_first_label import ORIGINAL_ROM,ROOT,digest
from tools.game_text import GameTextCodec,rebuild
from tools.translation_pipeline import FontZero,load_json,atomic_write,check
from tools.rom_build import RomBuild

CATALOG=ROOT/'translations/story-special.json'
OUTPUT=ROOT/'build/completion/special'
PASSWORD='LETMEIN'
COMMANDS=re.compile(r'\$t|\$p[12]')
PET_WIDTH=84 # Seven original Japanese cells; retains compatibility with old names.


def source_entry(original,master,at):
    if at!=0xC15394:return previous.source_entry(original,master,at,'pet_names' if at<0xAB0000 else 'tree_password')
    src=master[at];parsed=GameTextCodec(original).parse(original,at)
    check(src['pointer_candidates']==['0x00C15290'],'Password owner changed')
    check(struct.unpack_from('<II',original,0xC1528C)==(0x00000731,0x08C15394),'Password command changed')
    check(bytes.fromhex(src['source_hex'])==rebuild(parsed['tokens']),'Password source changed')
    return {'id':f'completion.{at:08x}','master_id':src['id'],'chapter':'tree_password',
        'offset':src['offset'],'end_exclusive':hex(parsed['end']),'source_hex':parsed['raw_hex'],
        'source_tokens':parsed['tokens'],'japanese':parsed['display'],
        'events':[{'command_offset':'0xc1528c','pointer_offset':'0x00C15290','command_word':'0x00000731','opcode':0x31}],
        'reuse':None,'layout':'keyword','english':None,'display':None,'notes':'','references':[]}


def encode(e,original,values=None):
    text=e['english'];font=FontZero(original)
    check(all(c=='\n' or 32<=ord(c)<127 for c in text),'Unsupported special-story glyph')
    if e['layout']=='keyword':
        check(text==PASSWORD and len(text)==7 and text.isupper(),'Password must match its input contract')
        return text.encode()+b'\0',{'visible':text,'lines':1,'line_widths':[sum(font.glyph(c)[1] for c in text)],'bytes_including_nul':8,'layout':'keyword'}
    check(Counter(COMMANDS.findall(text))==Counter(COMMANDS.findall(e['japanese'])),'Special substitution contract changed')
    check(not any(c in COMMANDS.sub('',text) for c in '$%`{}'),'Unknown English formatter command')
    check(all(t['kind'] in ('text','control','dollar_command','terminator') and
        (t['kind']!='control' or t['raw_hex'] in ('09','0a')) and
        (t['kind']!='dollar_command' or COMMANDS.fullmatch(t['text'])) for t in e['source_tokens']),'Unreviewed special source grammar')
    speech=e['layout']=='speech'
    check(('"' in text)==speech and (not speech or text.count('"')==2 and ': "' in text and text.endswith('"')),'Special speech presentation changed')
    check(not text.startswith('\n'),'Unreviewed leading blank line')
    def width(line):
        pets=len(re.findall(r'\$p[12]',line))
        plain=re.sub(r'\$p[12]','',line).replace('$t','Torneko')
        return pets*PET_WIDTH+sum(font.glyph(c)[1] for c in plain)
    lines=[]
    for paragraph in text.split('\n'):
        line=''
        for word in paragraph.split(' '):
            trial=(line+' '+word) if line else word
            if line and width(trial)>(184 if speech and lines else 208):lines.append(line);line=word
            else:line=trial
            check(width(line)<=(184 if speech and lines else 208),'Unbreakable special-story word')
        lines.append(line)
    check(len(lines)<=3,f'Special page too long: {e["id"]}: {lines}')
    raw='\n'.join(('\t'+line if speech and i else line) for i,line in enumerate(lines)).encode()+b'\0'
    values={'$t':'Torneko','$p1':'Biscuit','$p2':'Mittens',**(values or {})}
    visible='\n'.join(lines)
    for k,v in values.items():visible=visible.replace(k,v)
    check(GameTextCodec(original).parse(raw,0)['end']==len(raw),'Invalid special encoding')
    check(len(raw)+sum(12 for _ in re.finditer(r'\$p[12]',text))+5*text.count('$t')<=1024,'Special formatter exceeds story buffer')
    return raw,{'visible':visible,'lines':len(lines),'line_widths':[sum(font.glyph(c)[1] for c in line) for line in visible.split('\n')],
        'reserved_line_widths':[width(line) for line in lines],'pet_width_budget':PET_WIDTH,'bytes_including_nul':len(raw),'layout':e['layout']}


def validate(original,catalog):
    master={int(e['offset'],0):e for e in load_json(ROOT/'translations/master.json')['entries']};seen=set();words=set()
    check(catalog['base_sha256']==digest(original),'Wrong special-story base')
    for e in catalog['entries']:
        fresh=source_entry(original,master,int(e['offset'],0))
        check(all(e[k]==fresh[k] for k in fresh.keys()-{'english','display','notes','references'}),'Changed special source/owner')
        check(e['id'] not in seen and e['english'] and e['notes'] and e['display'] is None,'Invalid authored special entry');seen.add(e['id'])
        for ev in e['events']:
            check(ev['pointer_offset'] not in words,'Duplicate special operand');words.add(ev['pointer_offset'])
        encode(e,original)
    check(len(seen)==32,'Incomplete special-story family')
    check(next(e for e in catalog['entries'] if e['layout']=='keyword')['english']==PASSWORD,'Keyword mismatch')
    check(all(PASSWORD in e['english'] for e in catalog['entries'] if e['chapter']=='tree_password'),'Hint/keyword mismatch')
    return catalog['entries']


def owners():
    original=ORIGINAL_ROM.read_bytes();catalog=load_json(CATALOG);validate(original,catalog)
    report={'source_sha256':digest(original),'scope':'Exact pet-story operands and all three tree-password sources, including opcode-31 comparison operand. No neighboring code/source bytes are writable.',
        'entries':[{k:v for k,v in e.items() if k not in ('english','display','notes','references')} for e in catalog['entries']]}
    atomic_write(OUTPUT/'source-owners.json',(json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode())
    print(len(catalog['entries']),'special sources;',sum(len(e['events']) for e in catalog['entries']),'operands',flush=True)


def build_rom(original,language='english',catalog=None,story_catalog=None,*,build=None):
    b=RomBuild(original) if build is None else build
    _,prior=previous.build_rom(original,catalog=story_catalog,build=b)
    c=load_json(CATALOG) if catalog is None else catalog;entries=validate(original,c);relocated={}
    for e in entries:
        at=int(e['offset'],0);source=bytes.fromhex(e['source_hex']);raw,metrics=encode(e,original)
        b.protect_source(e['id'],at,at+len(source),'story-special')
        dest=b.allocate(e['id'],raw if language=='english' else source,'story-special')
        for ev in e['events']:b.patch(e['id']+'.'+ev['pointer_offset'],int(ev['pointer_offset'],0),struct.pack('<I',at+0x08000000),struct.pack('<I',dest+0x08000000),'story-special','Exact pet-story or password operand; native input, compare, branch and save code preserved')
        relocated[e['id']]={'offset':dest,'metrics':metrics}
    data,ledger=b.finish()
    return data,{'source_sha256':digest(original),'rom_sha256':digest(data),'language':language,'previous_rom_sha256':prior['rom_sha256'],
        'special':{'entries':len(entries),'operand_words':sum(len(e['events']) for e in entries),'relocated':relocated},'ledger':ledger}


def build():
    catalog=load_json(CATALOG);story=load_json(previous.CATALOG);original=ORIGINAL_ROM.read_bytes()
    atomic_write(OUTPUT/'catalog.json',(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n').encode())
    atomic_write(OUTPUT/'story-catalog.json',(json.dumps(story,ensure_ascii=False,indent=2)+'\n').encode())
    for lang in ('english','japanese'):
        data,report=build_rom(original,lang,catalog,story)
        report['catalog_sha256']=digest((OUTPUT/'catalog.json').read_bytes());report['story_catalog_sha256']=digest((OUTPUT/'story-catalog.json').read_bytes())
        atomic_write(OUTPUT/f'torneko3-story-special-{lang}.gba',data)
        atomic_write(OUTPUT/f'{lang}-build.json',(json.dumps(report,indent=2)+'\n').encode())
        print(lang,report['rom_sha256'],flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=('owners','build'));args=p.parse_args()
    owners() if args.mode=='owners' else build()
