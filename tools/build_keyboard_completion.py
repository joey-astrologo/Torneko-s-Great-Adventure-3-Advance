"""Correct shared keyboard headers and translate the history popup."""
import argparse
import json
import struct
import subprocess
import tempfile
from pathlib import Path
from tools import build_merchants as previous
from tools import build_core_gameplay as core
from tools.build_first_label import ORIGINAL_ROM,ROOT,digest
from tools.game_text import GameTextCodec,rebuild
from tools.translation_pipeline import atomic_write,load_json,check,FontZero
from tools.rom_build import RomBuild

OUTPUT=ROOT/'build/completion/keyboard'
CATALOG=ROOT/'translations/keyboard-completion.json'
HEADERS=(0xC454A4,0xC45474,0xC4544C,0xC45424)
SHARED={0x7BEE4:'name.patch-0007bee4',0x7BEEC:'name.patch-0007beec'}


def extract(original):
    codec=GameTextCodec(original);entries=[];master={int(e['offset'],0):e for e in load_json(ROOT/'translations/master.json')['entries']}
    for at in HEADERS+(0xC46740,0xC46758):
        s=codec.parse(original,at);check(rebuild(s['tokens'])==original[at:s['end']],'Keyboard source differs')
        index=HEADERS.index(at) if at in HEADERS else None
        entries.append({'id':f'keyboard.{at:08x}','family':'header' if index is not None else 'hint' if at==0xC46740 else 'popup','offset':hex(at),'source_end_exclusive':hex(s['end']),
            'japanese':s['display'],'source_hex':s['raw_hex'],'source_tokens':s['tokens'],'master_id':master[at]['id'],
            'original_pointer_word':hex(0xCB0620+4*index if index is not None else 0x7BEEC if at==0xC46740 else 0x7CF18),
            'header_index':index,'english':None,'notes':'','references':[]})
    return {'schema':1,'base_sha256':digest(original),'font':0,'entries':entries}


def encode(e,original):
    text=e['english'];check(text and all(32<=ord(c)<127 or c=='\n' for c in text),'Keyboard English glyphs')
    raw=b'';last=0
    for m in core.HEX.finditer(text):raw+=text[last:m.start()].encode()+bytes.fromhex(m[1]);last=m.end()
    raw+=text[last:].encode()+b'\0';check(b'{' not in raw and b'}' not in raw,'Unknown keyboard markup')
    if e['family']=='popup':raw=raw.replace(b'\n',b'\r')
    parsed=GameTextCodec(original).parse(raw,0);check(parsed['end']==len(raw),'Embedded keyboard terminator')
    font=FontZero(original);x=0;right=0;segments=[]
    for t in parsed['tokens']:
        if t['kind']=='binary_control':
            b=bytes.fromhex(t['raw_hex']);check(b[:2]==b'\x03\x09' and right<=b[2],'Keyboard columns overlap');x=b[2]
        elif t['kind']=='text':
            for c in t['text']:
                code,advance,ink=font.glyph(c);right=max(right,x+ink);x+=advance
            segments.append({'text':t['text'],'end':x,'ink_right':right})
        elif t['kind']=='control':check(e['family']=='popup' and t['raw_hex']=='0d','Keyboard control differs');x=0;right=0
        else:check(t['kind']=='terminator','Unsupported keyboard token')
        check(max(x,right)<=(32 if e['family']=='popup' else 208),'Keyboard label exceeds field')
    return raw,{'segments':segments,'bytes_including_nul':len(raw)}


def prepare():
    original=ORIGINAL_ROM.read_bytes();c=extract(original);old=load_json(CATALOG) if CATALOG.exists() else None;existing={e['id']:e for e in old['entries']} if old else {}
    for e in c['entries']:
        if e['family']=='header':
            labels=[(4,'Page'),(52,'Next')]+([(92,'History')] if e['header_index']<2 else [])+[(136,'Back'),(176,'Done')]
            e['english']=''.join('{hex:0309'+f'{x:02x}'+'}'+s for x,s in labels)
        elif e['family']=='hint':e['english']='A: Enter  L: Page  R: Done'
        else:e['english']='Select\nErase'
        e['notes']='Independent original UI translation. Page describes both Latin case switching and preserved kana password pages; History appears only when the original caller allows it. Existing compact mappings and name/save limits are unchanged.'
        if e['id'] in existing:
            for k in ('english','notes','references'):e[k]=existing[e['id']][k]
        encode(e,original)
    atomic_write(CATALOG,(json.dumps(c,ensure_ascii=False,indent=2)+'\n').encode())
    atomic_write(OUTPUT/'source-owners.json',(json.dumps({'source_sha256':digest(original),'entries':extract(original)['entries'],
        'superseded_literal_patches':[{'offset':hex(a),'previous_id':ident,'previous_owner':'name-entry'} for a,ident in SHARED.items()],
        'new_grid_font_hooks':[{'offset':hex(a),'bytes':8} for a in (0x7BE08,0x7BE30)],
        'new_literal':{'offset':hex(0x7CF18),'source':hex(0xC46758)},'retained_history_format':{'source':hex(0xC46748),'literal':hex(0x7CDD0)},
        'scope':'Six resources; two exact name-component patch corrections and one newly owned popup pointer. Original header startup words and grids stay untouched. Control variant keeps earlier headers/hint and relocates unchanged Japanese popup.'},ensure_ascii=False,indent=2)+'\n').encode())
    print(len(c['entries']),'keyboard resources prepared',flush=True)


def validate(original,c):
    fresh=extract(original);check(all(c[k]==fresh[k] for k in ('schema','base_sha256','font')),'Keyboard catalog header differs')
    check(len(c['entries'])==len(fresh['entries']),'Keyboard source count differs')
    for e,f in zip(c['entries'],fresh['entries'],strict=True):
        check(all(e[k]==f[k] for k in f.keys()-{'english','notes','references'}),'Keyboard source metadata differs');encode(e,original)
    return c['entries']


def build_rom(original,language='english',catalog=None,*,build=None):
    check(language in ('english','japanese'),'Keyboard language');b=RomBuild(original) if build is None else build
    _,prior=previous.build_rom(original,build=b);c=load_json(CATALOG) if catalog is None else catalog;entries=validate(original,c);relocated={};supersessions=[]
    frozen=load_json(previous.OUTPUT/'english-build.json')['ledger'];old={p['id']:p for p in frozen['patches']}
    for e in entries:
        at=int(e['offset'],0);source=bytes.fromhex(e['source_hex']);b.protect_source(e['id'],at,at+len(source),'keyboard-completion')
        if language=='japanese' and e['family']!='popup':continue
        raw,metrics=encode(e,original);dest=b.allocate(e['id'],raw if language=='english' else source,'keyboard-completion');relocated[e['id']]={'offset':dest,'metrics':metrics}
        if e['family']=='popup':b.patch(e['id']+'.literal',0x7CF18,struct.pack('<I',at+0x08000000),struct.pack('<I',dest+0x08000000),'keyboard-completion','Original history popup consumer')
    if language=='english':
        headers=[0x08000000+relocated[f'keyboard.{at:08x}']['offset'] for at in HEADERS]
        table=b.allocate('keyboard.header-table',struct.pack('<4I',*headers),'keyboard-completion')+0x08000000
        for at,target in ((0x7BEE4,table),(0x7BEEC,relocated['keyboard.00c46740']['offset']+0x08000000)):
            ident=SHARED[at];p=old[ident];check(p['offset']==at and p['owner']=='name-entry','Wrong prior keyboard owner')
            current=next(x for x in b.patches if x['id']==ident);check(current==p,'Prior keyboard patch metadata changed')
            supersessions.append(b.supersede_patch(f'keyboard.correct-{at:08x}',ident,'name-entry',bytes.fromhex(p['after']),struct.pack('<I',target),'keyboard-completion','Show Page for both codecs and restore the caller-controlled History label'))
        address=0x08000000+((b.allocator.cursor+3)&~3)
        with tempfile.TemporaryDirectory(prefix='torneko-keyboard-asm-') as directory:
            run=subprocess.run([str(ROOT/'.tools/bin/armips'),str(ROOT/'tools/keyboard_grid_font.asm'),'-equ','CODE_ADDRESS',hex(address),'-sym2','symbols.txt'],cwd=directory,capture_output=True,text=True)
            check(run.returncode==0,'Keyboard assembler: '+run.stdout+run.stderr)
            code=(Path(directory)/'keyboard-grid-font.bin').read_bytes();symbols={}
            for line in (Path(directory)/'symbols.txt').read_text().splitlines():
                fields=line.split()
                if len(fields)==2 and fields[1] in ('SelectGridFont','RestoreFontZero'):symbols[fields[1]]=int(fields[0],16)
        check(b.allocate('keyboard.grid-font-code',code,'keyboard-completion')+0x08000000==address,'Keyboard code address changed')
        for at,symbol in ((0x7BE08,'SelectGridFont'),(0x7BE30,'RestoreFontZero')):
            check(at%4==0,'Keyboard hook literal alignment')
            hook=bytes.fromhex('004b1847')+struct.pack('<I',symbols[symbol]|1)
            b.patch(f'keyboard.grid-font-{at:08x}',at,original[at:at+8],hook,'keyboard-completion','Use original font 1 for kana grids, then restore selected English font 0')
    data,ledger=b.finish()
    return data,{'source_sha256':digest(original),'rom_sha256':digest(data),'previous_rom_sha256':prior['rom_sha256'],'language':language,'keyboard':{'resources':len(entries),'relocated':relocated,'supersessions':supersessions},'ledger':ledger}


def build():
    original=ORIGINAL_ROM.read_bytes();c=load_json(CATALOG);atomic_write(OUTPUT/'catalog.json',(json.dumps(c,ensure_ascii=False,indent=2)+'\n').encode())
    for language in ('english','japanese'):
        data,report=build_rom(original,language,c);report['catalog_sha256']=digest((OUTPUT/'catalog.json').read_bytes());atomic_write(OUTPUT/f'torneko3-keyboard-completion-{language}.gba',data);atomic_write(OUTPUT/f'{language}-build.json',(json.dumps(report,indent=2)+'\n').encode());print(language,report['rom_sha256'],flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=('prepare','build'));prepare() if p.parse_args().mode=='prepare' else build()
