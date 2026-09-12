"""Owned result causes, score rows and both result-detail readers."""
import argparse
from collections import Counter
import csv
import json
import struct
import subprocess
import tempfile
from pathlib import Path
from tools import build_adventure_history as previous
from tools.build_first_label import ORIGINAL_ROM, ROOT, digest
from tools.game_text import GameTextCodec, PRINTF, rebuild
from tools.translation_pipeline import atomic_write, load_json, check, FontZero
from tools.build_enemies import measure
from tools.rom_build import RomBuild

CATALOG = ROOT/'translations/adventure-results.json'
OUTPUT = ROOT/'build/completion/results'
CAUSE_TABLE, CAUSE_END = 0xDB3B8, 0xDB6E8
RELATION_TABLE, RELATION_END = 0xDB17C, 0xDB308
CATEGORIES = ((0xDB33C, 8), (0xC4CF68, 11))
UNKNOWN_RELATIONS = (0x1AA0, 0x5C53C, 0x86914)
EDITABLE = {'english', 'display', 'notes', 'references'}
ITEM_TABLE_WORDS=(0x1B60,0x5C668,0x86A04)
ITEM_DISPLAYS={78:('Double-edged staff','Double-edged stf.'),
    215:('Safe Passage scroll','Safe Passage scr.'),224:('Spoiled blank scroll','Spoiled blank scr.'),
    225:('Monster haste scroll','Monster haste scr'),240:('Trap trigger scroll','Trap trigger scr.'),
    320:('Throw effect statue','Throw effect st.'),335:('Trap growth statue','Trap growth st.'),
    338:('Trap breaker statue','Trap breaker st.')}


def extract(original):
    codec = GameTextCodec(original)
    master = {int(e['offset'], 0): e for e in load_json(ROOT/'translations/master.json')['entries']}
    entries = {}
    def add(at, word, family, evidence, **extra):
        check(struct.unpack_from('<I', original, word)[0] == at+0x08000000, 'Result pointer differs')
        if at not in entries:
            s = codec.parse(original, at)
            check(rebuild(s['tokens']) == original[at:s['end']], 'Result source roundtrip')
            entries[at] = {'id': f'result.{at:08x}', 'family': family, 'offset': hex(at),
                'source_end_exclusive': hex(s['end']), 'japanese': s['display'],
                'source_hex': s['raw_hex'], 'source_tokens': s['tokens'],
                'pointer_owners': [], 'english': None, 'display': None, 'notes': '', 'references': []}
            if at in master: entries[at]['master_id'] = master[at]['id']
        check(entries[at]['family'] == family, 'Result source has incompatible readers')
        entries[at]['pointer_owners'].append({'offset': hex(word), 'evidence': evidence, **extra})
    for word in range(CAUSE_TABLE, CAUSE_END-8, 8):
        key, value = struct.unpack_from('<II', original, word)
        add(value-0x08000000, word+4, 'cause', 'typed_result_key_value',
            key=codec.parse(original, key-0x08000000)['display'], key_offset=hex(key-0x08000000))
    check(original[CAUSE_END-8:CAUSE_END] == bytes(8), 'Result table terminator differs')
    for word in range(RELATION_TABLE, RELATION_END, 4):
        add(struct.unpack_from('<I', original, word)[0]-0x08000000, word, 'relation',
            'typed_cause_relation', cause=(word-RELATION_TABLE)//4)
    for table, count in CATEGORIES:
        for row in range(count):
            word = table+4*row
            add(struct.unpack_from('<I', original, word)[0]-0x08000000, word,
                'compact_category' if table==0xDB33C else 'category', 'typed_category_array', row=row)
    for at, m in master.items():
        if not (0x9B35C <= at < 0x9B4B0 or 0xDC648 <= at < 0xDC834 or 0xC4D08C <= at < 0xC4D250): continue
        if m['japanese'].startswith('result_') or m['japanese']=='η%s': continue
        family = 'prefix' if '$i1' in m['japanese'] and ('$t' in m['japanese'] or at<0x9B3EC) else 'remark' if at>=0xC4D1BC or 0xDC7A4<=at<0xDC834 or 0x9B418<=at<0x9B4B0 else 'label'
        # Floor-only list variants carry no $i1 substitution.
        if at in (0x9B3BC, 0x9B3E4): family='prefix'
        for p in m['pointer_candidates']:
            word=int(p, 0)
            loads=[i for i in range(max(0, word-1024), word, 2)
                if original[i+1]&0xF8==0x48 and ((i+4)&~3)+original[i]*4==word]
            check(word<0xF0000 and loads, f'Unreviewed result literal {p}')
            add(at, word, family, 'thumb_literal', loads=[hex(i+0x08000000) for i in loads])
    for word in UNKNOWN_RELATIONS:
        add(struct.unpack_from('<I', original, word)[0]-0x08000000, word, 'unknown_relation',
            'thumb_literal_unknown_actor_relation', reason='English result phrases require an explicit unknown source; scoped empty copy only.')
    return {'schema':1, 'base_sha256':digest(original), 'font':0, 'entries':sorted(entries.values(), key=lambda e:int(e['offset'],0))}


def encode(e, original):
    text=e['display'] or e['english']
    check(isinstance(text,str) and text, 'Missing result English '+e['id'])
    check(all(32<=ord(c)<127 or c=='\r' for c in text), 'Result requires ASCII/CR/typed controls')
    raw=b'';last=0
    for m in previous.HEX.finditer(text):raw+=text[last:m.start()].encode()+bytes.fromhex(m[1]);last=m.end()
    raw+=text[last:].encode()+b'\0'
    check(b'{' not in raw and b'}' not in raw, 'Unknown result control')
    s=GameTextCodec(original).parse(raw,0);check(s['end']==len(raw),'Embedded result terminator')
    dollars=lambda ts:Counter(t['text'] for t in ts if t['kind']=='dollar_command')
    binary=lambda ts:[(t['kind'],t['raw_hex']) for t in ts if t['kind'] in ('binary_control','opaque_control')]
    check(dollars(s['tokens'])==dollars(e['source_tokens']), 'Result substitution contract differs '+e['id'])
    check(binary(s['tokens'])==binary(e['source_tokens']), 'Result binary contract differs '+e['id'])
    check(PRINTF.findall(raw)==PRINTF.findall(bytes.fromhex(e['source_hex'])), 'Result printf contract differs')
    check(raw.count(b'\r')==bytes.fromhex(e['source_hex']).count(b'\r'), 'Result line contract differs '+e['id'])
    cap=30 if e['family'] in ('relation','unknown_relation') or e['japanese']=='何者か' else 200
    maximum=sum((99 if t['text'].startswith('$i') else 29 if t['text'].startswith('$m') else 7 if t['text']=='$t' else 11)
        if t['kind']=='dollar_command' else 29 if t['kind']=='printf' and t['text']=='%s'
        else len(bytes.fromhex(t['raw_hex'])) for t in s['tokens'])
    # The native formatter bounds substituted output. Actual table names and
    # record numeric fields are enumerated in runtime/layout verification.
    check(maximum<=cap, f'Result buffer upper bound {e["id"]}: {maximum}/{cap}')
    return raw, {'display_template':text, 'capacity':cap, 'formatted_byte_upper_bound':maximum,
        'bytes_including_nul':len(raw), 'layout_status':'requires_native_result_contexts'}


def validate(original, catalog):
    fresh=extract(original);entries={e['id']:e for e in catalog['entries']}
    check(all(catalog[k]==fresh[k] for k in ('schema','base_sha256','font')), 'Result header differs')
    check(len(entries)==len(catalog['entries'])==len(fresh['entries']), 'Result catalog incomplete')
    for e in fresh['entries']:
        a=entries[e['id']];check(all(a[k]==e[k] for k in e.keys()-EDITABLE),'Result metadata differs');encode(a,original)
    return list(entries.values())


def owners():
    original=ORIGINAL_ROM.read_bytes();c=extract(original)
    atomic_write(OUTPUT/'source-owners.json',(json.dumps(c,ensure_ascii=False,indent=2)+'\n').encode())
    print(len(c['entries']),'result resources;',sum(len(e['pointer_owners']) for e in c['entries']),'pointer words')


def prepare():
    original=ORIGINAL_ROM.read_bytes();catalog=extract(original)
    drafts={int(d['offset'],16):d for d in csv.DictReader((ROOT/'translations/adventure-results-drafts.tsv').open(),delimiter='\t')}
    check(set(drafts)=={int(e['offset'],0) for e in catalog['entries']},'Result draft/source set differs')
    prior={e['id']:e for e in load_json(CATALOG)['entries']} if CATALOG.exists() else {}
    for e in catalog['entries']:
        d=drafts[int(e['offset'],0)];e.update(english=d['english'].replace('<CR>','\r'),display=d['display'].replace('<CR>','\r') or None,
            notes=d['notes'], references=d['references'].split() if d['references'] else [])
        if e['id'] in prior:check(all(e[k]==prior[e['id']][k] for k in EDITABLE),'Existing result English changed without a revision '+e['id'])
    validate(original,catalog);atomic_write(CATALOG,(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n').encode())
    print(len(catalog['entries']),'result resources prepared')


def build_rom(original, language='english', catalog=None, *, build=None):
    check(language in ('english','japanese'),'Invalid result language');b=RomBuild(original) if build is None else build
    _,prior=previous.build_rom(original,build=b);catalog=load_json(CATALOG) if catalog is None else catalog
    entries=validate(original,catalog);relocated={}
    for e in entries:
        at=int(e['offset'],0);source=bytes.fromhex(e['source_hex']);raw,metrics=encode(e,original)
        b.protect_source(e['id'],at,at+len(source),'adventure-results')
        dest=b.allocate(e['id'],raw if language=='english' else source,'adventure-results')
        for owner in e['pointer_owners']:
            word=int(owner['offset'],0);b.patch(e['id']+'.'+owner['offset'],word,struct.pack('<I',at+0x08000000),
                struct.pack('<I',dest+0x08000000),'adventure-results',owner['evidence'])
        relocated[e['id']]={'offset':dest,'metrics':metrics}
    before_items=bytes(b.data)
    item_table=bytearray(before_items[0x18F16C:0x18F734]);font=FontZero(original);codec=GameTextCodec(original);item_forms=[]
    for row in range(370):
        pointer=struct.unpack_from('<I',item_table,row*4)[0]
        full=codec.parse(before_items,pointer-0x08000000)['display'];display=full
        if row in ITEM_DISPLAYS:
            expected,compact=ITEM_DISPLAYS[row];check(full==expected,'Result item authority differs')
            if language=='english':
                display=compact;at=b.allocate(f'result.item_display.{row:03}',compact.encode()+b'\0','adventure-results')
                struct.pack_into('<I',item_table,row*4,at+0x08000000)
        if language=='english':check(measure(display,font)<=91,'Result item display width '+str(row))
        item_forms.append({'row':row,'full':full,'display':display,'width':measure(display,font),'prior_pointer':hex(pointer)})
    item_at=b.allocate('result.item_display.table',bytes(item_table),'adventure-results')
    for word in ITEM_TABLE_WORDS:
        b.patch('result.item_display.'+hex(word),word,struct.pack('<I',0x0818F16C),struct.pack('<I',0x08000000+item_at),
            'adventure-results','Private result item display table; original inventory names and saved IDs preserved')
    layout={}
    if language=='english':
        start=0xCA2D74;descriptor=bytearray(original[start:start+64])
        check(struct.unpack_from('<5H',descriptor)==(2,2,26,17,17),'Original result window differs')
        b.protect_source('result.window.source',start,start+64,'adventure-results')
        struct.pack_into('<H',descriptor,0,1);struct.pack_into('<H',descriptor,4,27)
        window=b.allocate('result.window',descriptor,'adventure-results')+0x08000000
        hooks=[]
        for name,at,expected in [('score',0x8651A,'142000210122e6f76af9'),('ending',0x5C0AC,'14200021012210f0a1fb')]:
            address=((b.allocator.cursor+3)&~3)+0x08000000
            with tempfile.TemporaryDirectory(prefix='torneko-result-asm-') as directory:
                run=subprocess.run([str(ROOT/'.tools/bin/armips'),str(ROOT/'tools/result_window.asm'),
                    '-equ','CODE_ADDRESS',hex(address),'-equ','DESCRIPTOR_ADDRESS',hex(window),
                    '-equ','RESUME_ADDRESS',hex(0x08000000+at+10+1)],cwd=directory,capture_output=True,text=True)
                check(run.returncode==0,'Result assembler: '+run.stdout+run.stderr)
                code=(Path(directory)/'result-window.bin').read_bytes()
            check(b.allocate('result.window.'+name,code,'adventure-results')+0x08000000==address,'Result code moved')
            # Literal must be word aligned, including the halfword-aligned score hook.
            hook=(bytes.fromhex('014b1847c046')+struct.pack('<I',address|1) if at&2
                else bytes.fromhex('004b1847')+struct.pack('<I',address|1)+bytes.fromhex('c046'))
            b.patch('result.window.'+name,at,bytes.fromhex(expected),hook,'adventure-results',
                'Private 216px result-detail descriptor through the original custom constructor')
            hooks.append({'name':name,'hook':hex(at+0x08000000),'code':hex(address),'resume':hex(at+10+0x08000000)})
        layout={'window':hex(window),'width':216,'height':136,'x':8,'y':16,'hooks':hooks}
        b.patch('result.categories.width',0x85FCC,bytes.fromhex('1220'),bytes.fromhex('1a20'),
            'adventure-results','208px private category selector; dynamic height and original menu behavior preserved')
        layout['category_width']=208
    data,ledger=b.finish();return data,{'source_sha256':digest(original),'rom_sha256':digest(data),'previous_rom_sha256':prior['rom_sha256'],
        'language':language,'results':{'resources':len(entries),'inventory_sources':sum('master_id' in e for e in entries),
        'pointer_words':sum(len(e['pointer_owners']) for e in entries),'relocated':relocated,'layout':layout,
        'item_display_table':hex(item_at+0x08000000),'item_displays':item_forms},'ledger':ledger}


def build():
    original=ORIGINAL_ROM.read_bytes();catalog=load_json(CATALOG)
    atomic_write(OUTPUT/'catalog.json',(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n').encode())
    for language in ('english','japanese'):
        data,report=build_rom(original,language,catalog);report['catalog_sha256']=digest((OUTPUT/'catalog.json').read_bytes())
        atomic_write(OUTPUT/f'torneko3-adventure-results-{language}.gba',data)
        atomic_write(OUTPUT/f'{language}-build.json',(json.dumps(report,indent=2)+'\n').encode());print(language,report['rom_sha256'],flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=('owners','prepare','build'));a=p.parse_args();globals()[a.mode]()
