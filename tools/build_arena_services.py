"""Arena, church choices, dungeon entry conditions and save notices."""
import argparse
from collections import Counter
import json
import struct
import subprocess
import tempfile
from pathlib import Path
from tools import build_shared_story as previous
from tools import build_ally_services as service
from tools.build_first_label import ORIGINAL_ROM, ROOT, digest
from tools.game_text import GameTextCodec, PRINTF, rebuild
from tools.translation_pipeline import atomic_write, load_json, check, FontZero
from tools.rom_build import RomBuild

CATALOG=ROOT/'translations/arena-services.json'
OUTPUT=ROOT/'build/completion/arena'
MENU_TABLES=((0xC40260,4),(0xC402F4,4),(0xC40358,4),(0xC403E0,4),
             (0xC4044C,2),(0xC414B8,4),(0xC41530,4),(0xC4158C,3))
TYPED={base+i*12 for base,n in MENU_TABLES for i in range(n)}
SKIP={0xC411B0,0xC41ACC}  # Previously owned bounded ally-service copies.
LABELS={0xC402D0,0xC402D8,0xC411E4,0xC4129C,0xC41FE0,0xC41FE8,0xC42008,0xC42010}
ROWS={0xC41178,0xC414A4}
EXTRA={0x86EF3C,0x86EF7C,0x86EFB4,0x86EFF8}
EXISTING={0x799A8:'enemy.layout.encounter_alternate_header',0x79B84:'enemy.layout.encounter_header'}


def extract(original):
    codec=GameTextCodec(original);entries=[]
    for m in load_json(ROOT/'translations/master.json')['entries']:
        at=int(m['offset'],0)
        if not (0xC4029C<=at<=0xC42094 or at in EXTRA) or at in SKIP:continue
        if not m['pointer_candidates']:continue  # Resource identifiers, not prose.
        # Colour-only template has no new language or layout.
        if at==0xC4149C:continue
        owners=[];excluded=[]
        for word in m['pointer_candidates']:
            p=int(word,0)
            check(struct.unpack_from('<I',original,p)[0]==at+0x08000000,'Arena source pointer differs')
            if p in EXISTING:
                excluded.append({'offset':word,'owner':'enemies','id':EXISTING[p],
                    'reason':'Existing two-line encounter header. Preserve its allocation, pointer and y-position patches.'})
                continue
            loads=[] if p in TYPED else [i for i in range(max(0,p-1024),p,2)
                if original[i+1]&0xF8==0x48 and ((i+4)&~3)+original[i]*4==p]
            check(p in TYPED or p<0xF0000 and loads,f'Unreviewed arena owner {word}')
            owners.append({'offset':word,'evidence':'typed_menu_12_bytes' if p in TYPED else 'thumb_literal',
                           'loads':[f'0x{i+0x08000000:08X}' for i in loads]})
        s=codec.parse(original,at);check(rebuild(s['tokens'])==original[at:s['end']],'Arena source roundtrip')
        family=('menu' if any(int(p['offset'],0) in TYPED for p in owners) else 'label' if at in LABELS
            else 'rule' if 0xC41E64<=at<=0xC41FF0 else 'roster' if at==0xC41484
            else 'name_level' if at==0xC413D4 else 'unit' if at==0xC41314
            else 'row' if at in ROWS else 'message')
        entries.append({'id':f'arena.{at:08x}','family':family,'offset':m['offset'],
            'source_end_exclusive':f'0x{s["end"]:08X}','japanese':s['display'],'source_hex':s['raw_hex'],
            'source_tokens':s['tokens'],'pointer_owners':owners,'excluded_owners':excluded,'master_id':m['id'],
            'english':None,'display':None,'notes':'','references':[]})
    return {'schema':1,'base_sha256':digest(original),'font':0,'entries':entries}


def validate(original,catalog):
    fresh=extract(original);entries={e['id']:e for e in catalog['entries']}
    check(all(catalog[k]==fresh[k] for k in ('schema','base_sha256','font')),'Arena header differs')
    check(len(entries)==len(catalog['entries'])==len(fresh['entries']),'Incomplete arena catalog')
    for e in fresh['entries']:
        a=entries[e['id']];check(all(a[k]==e[k] for k in e.keys()-{'english','display','notes','references'}),'Arena source metadata differs')
        check(isinstance(a['english'],str) and a['english'],'Missing arena translation')
        encode(a,original)
    return list(entries.values())


def encode(e,original):
    at=int(e['offset'],0);family=e['family'];text=e['display'] or e['english']
    font=FontZero(original);codec=GameTextCodec(original)
    check(all(32<=ord(c)<127 or c=='\n' for c in text),'Arena requires ASCII/LF and typed controls')
    if family=='message':text=service.wrap(text,font)
    raw=b'';last=0
    for m in service.previous.core.HEX.finditer(text):raw+=text[last:m.start()].encode()+bytes.fromhex(m[1]);last=m.end()
    raw+=text[last:].encode()+b'\0';check(b'{' not in raw and b'}' not in raw,'Unknown arena control')
    s=codec.parse(raw,0);check(s['end']==len(raw),'Embedded arena terminator')
    dollars=lambda ts:Counter(t['text'] for t in ts if t['kind']=='dollar_command' and t['text']!='$x' and not t['text'].startswith('$/'))
    check(dollars(s['tokens'])==dollars(e['source_tokens']),'Arena substitution contract differs')
    check(PRINTF.findall(raw)==PRINTF.findall(bytes.fromhex(e['source_hex'])),'Arena printf contract differs')
    binary=lambda ts:[t['raw_hex'] for t in ts if t['kind']=='binary_control']
    check(binary(s['tokens'])==(['0309a0'] if family=='roster' else binary(e['source_tokens'])),'Arena binary controls differ')
    if family=='menu':check(raw.startswith(b'*')==bytes.fromhex(e['source_hex']).startswith(b'*'),'Arena default marker differs')
    maximum=sum((99 if t['text'].startswith('$i') else 29 if t['text'].startswith('$m') else 7 if t['text']=='$t' else 11)
        if t['kind']=='dollar_command' else (29 if t['text']=='%s' else 1 if t['text']=='%c' else 11)
        if t['kind']=='printf' else len(bytes.fromhex(t['raw_hex'])) for t in s['tokens'])
    # Roster's typed row/level/odds bounds are checked in its native consumers.
    if family=='roster':maximum=len(raw)-sum(map(len,PRINTF.findall(raw)))+2+29+2+4+1+1
    if family=='name_level':maximum=len(raw)-len(b'%s%d')+29+2
    cap=64 if family=='roster' else 30 if family=='name_level' else 2 if family=='unit' else 100 if at==0xC414A4 else 1000 if family=='message' else 256
    # The shared %sLv%d form feeds a 30-byte actor slot: all species plus Lv99
    # are enumerated separately; the general name reader's 29 limit is looser.
    if family!='name_level':check(maximum<=cap,f'Arena buffer bound {e["id"]}: {maximum}/{cap}')
    if family in ('roster','name_level'):
        from tools.build_enemies import measure
        names=[x['display'] or x['english'] for x in load_json(ROOT/'translations/enemies.json')['entries'] if x['family']=='name']
        widths=[]
        for name in names:
            payload=raw%(10,name.encode(),99,9999,46,9) if family=='roster' else raw%(name.encode(),99)
            check(len(payload)<=cap,f'Arena actual species overflow {name}: {len(payload)}/{cap}')
            if family=='roster':
                before,after=payload[:-1].split(b'\x03\x09\xa0');w=measure(before.decode(),font)
                check(w+4<=160,f'Arena name/odds overlap {name}: {w+4}');w=160+measure(after.decode(),font)
            else:w=measure(payload[:-1].decode(),font)
            check(w<=204,'Arena row overflow');widths.append(w)
        maximum=max(len(raw%(10,n.encode(),99,9999,46,9) if family=='roster' else raw%(n.encode(),99)) for n in names)
    else:
        clean=service.previous.core.HEX.sub('',text).replace('%s','Ines').replace('%d','999')
        widths=[service.width(line,font) for line in clean.split('\n')]
        check(max(widths)<=(120 if family=='menu' else 208),f'Arena width overflow {e["id"]}: {widths}')
    return raw,{'display_template':text,'line_widths':widths,'capacity':cap,'formatted_byte_upper_bound':maximum,'bytes_including_nul':len(raw)}


def owners():
    original=ORIGINAL_ROM.read_bytes();c=extract(original)
    menus=[]
    for base,n in MENU_TABLES:
        rows=[list(struct.unpack_from('<III',original,base+i*12)) for i in range(n+1)]
        check(all(r[0] and r[1]==0 for r in rows[:-1]) and rows[-1]==[0,0,0],'Arena typed menu changed')
        menus.append({'start':hex(base),'end_exclusive':hex(base+12*(n+1)),'count':n,'records':rows})
    atomic_write(OUTPUT/'source-owners.json',(json.dumps({'source_sha256':digest(original),'entries':c['entries'],'menus':menus,
        'scope':'Exact source and literal/typed-menu pointer ownership only. Source envelopes, old strings, menu nonpointer fields, record terminators and gaps remain occupied.'},ensure_ascii=False,indent=2)+'\n').encode())
    print(len(c['entries']),'arena sources;',sum(len(e['pointer_owners']) for e in c['entries']),'pointer words',flush=True)


def build_rom(original,language='english',catalog=None,*,build=None):
    check(language in ('english','japanese'),'Invalid arena language');b=RomBuild(original) if build is None else build
    _,prior=previous.build_rom(original,build=b);c=load_json(CATALOG) if catalog is None else catalog
    entries=validate(original,c);relocated={}
    for e in entries:
        at=int(e['offset'],0);source=bytes.fromhex(e['source_hex']);raw,metrics=encode(e,original)
        b.protect_source(e['id'],at,at+len(source),'arena-services');dest=b.allocate(e['id'],raw if language=='english' else source,'arena-services')
        for owner in e['pointer_owners']:
            p=int(owner['offset'],0);b.patch(e['id']+'.'+owner['offset'],p,struct.pack('<I',at+0x08000000),struct.pack('<I',dest+0x08000000),'arena-services',owner['evidence'])
        relocated[e['id']]={'offset':dest,'metrics':metrics}
    layout={}
    if language=='english':
        src=0xCA2934;descriptor=bytearray(original[src:src+64]);check(struct.unpack_from('<5H',descriptor)==(2,3,20,16,16),'Arena source window differs')
        b.protect_source('arena.list.window.source',src,src+64,'arena-services');struct.pack_into('<H',descriptor,4,26)
        window=b.allocate('arena.list.window',bytes(descriptor),'arena-services')+0x08000000
        address=((b.allocator.cursor+3)&~3)+0x08000000
        with tempfile.TemporaryDirectory(prefix='torneko-arena-asm-') as directory:
            run=subprocess.run([str(ROOT/'.tools/bin/armips'),str(ROOT/'tools/arena_list.asm'),
                '-equ','CODE_ADDRESS',hex(address),'-equ','DESCRIPTOR_ADDRESS',hex(window)],cwd=directory,capture_output=True,text=True)
            check(run.returncode==0,'Arena assembler: '+run.stdout+run.stderr);code=(Path(directory)/'arena-list.bin').read_bytes()
        check(b.allocate('arena.list.code',code,'arena-services')+0x08000000==address,'Arena code allocation moved')
        hook=bytes.fromhex('004b1847')+struct.pack('<I',address|1)
        b.patch('arena.list.constructor',0x79868,bytes.fromhex('f0b5a4b003200121'),hook,'arena-services','Private 208px arena list; original prologue replayed and native descriptor constructor preserved')
        layout={'window':hex(window),'code':hex(address),'width':208,'height':128,'odds_x':160}
    data,ledger=b.finish();return data,{'source_sha256':digest(original),'rom_sha256':digest(data),'previous_rom_sha256':prior['rom_sha256'],
        'language':language,'arena':{'entries':len(entries),'pointer_words':sum(len(e['pointer_owners']) for e in entries),'relocated':relocated,'layout':layout},'ledger':ledger}


def build():
    original=ORIGINAL_ROM.read_bytes();catalog=load_json(CATALOG)
    atomic_write(OUTPUT/'catalog.json',(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n').encode())
    for language in ('english','japanese'):
        data,report=build_rom(original,language,catalog);report['catalog_sha256']=digest((OUTPUT/'catalog.json').read_bytes())
        atomic_write(OUTPUT/f'torneko3-arena-services-{language}.gba',data);atomic_write(OUTPUT/f'{language}-build.json',(json.dumps(report,indent=2)+'\n').encode())
        print(language,report['rom_sha256'],flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=('owners','build'));a=p.parse_args();owners() if a.mode=='owners' else build()
