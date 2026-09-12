"""Seven-slot English scroll inscriptions with original kana matching retained."""
import argparse
import json
import struct
import subprocess
import tempfile
from pathlib import Path
from tools import build_keyboard_completion as previous
from tools.build_first_label import ORIGINAL_ROM,ROOT,digest
from tools.game_text import GameTextCodec,rebuild
from tools.translation_pipeline import atomic_write,load_json,check,FontZero
from tools.rom_build import RomBuild

OUTPUT=ROOT/'build/completion/inscriptions'
CATALOG=ROOT/'translations/inscriptions.json'
TABLE=0xDFCC0
ALIASES={190:'Sheen',191:'Peep',192:'Bang',193:'MthSeal',194:'Evac',195:'Trap',196:'GrtRoom',197:'Monster',199:'Oomphle',200:'Buff',201:'Plating',203:'NoPick',204:'Sanctry',205:'ItemSgt',206:'Bread',207:'Prayer',210:'Glow',211:'Binding',213:'IreLyre',214:'FoeSght',215:'SafePas',216:'Gale',217:'MonBind',218:'Kasap',219:'Rooting',220:'Pulling',221:'Transfm',223:'Zing',225:'MonHast',226:'DeepSlp',227:'PowerUp',228:'Recklss',229:'Fuddle',230:'Poof',231:'LookBck',232:'Chicken',233:'TrapClr',234:'PotFort',235:'MedRoom',236:'MultiHl',237:'BigBlst',238:'Dud',239:'Drought',240:'TrapAct',241:'Blaze',242:'Freeze',243:'TimeBmb',244:'HolyCst',245:'SandPlr'}


def extract(original):
    codec=GameTextCodec(original);master={int(e['offset'],0):e for e in load_json(ROOT/'translations/master.json')['entries']};items=load_json(ROOT/'translations/items.json')['entries'];glossary=load_json(ROOT/'translations/glossary.json')['terms'];entries=[]
    for row in range(49):
        a,z,item=struct.unpack_from('<III',original,TABLE+row*12);check(item in ALIASES,'Unexpected inscription ID');full=next(e for e in items if e['family']=='name' and item in e['item_indices'])
        term=next(t for t in glossary if {'catalog':'translations/items.json','id':full['id']} in t.get('occurrences',[]))
        for variant,address in enumerate((a,z)):
            at=address-0x08000000;s=codec.parse(original,at);check(rebuild(s['tokens'])==original[at:s['end']],'Inscription roundtrip differs')
            entries.append({'id':f'inscription.{row:02d}.{variant}','family':'scroll_alias','row':row,'variant':variant,'item_id':item,'offset':hex(at),'source_end_exclusive':hex(s['end']),'japanese':s['display'],'source_hex':s['raw_hex'],'source_tokens':s['tokens'],'master_id':master[at]['id'],'original_pointer_word':hex(TABLE+row*12+variant*4),'full_item_name':full['english'],'english':None,'notes':'','references':[term['id']]})
    check(original[TABLE+49*12:TABLE+50*12]==b'\0'*12,'Inscription terminator differs')
    return {'schema':1,'base_sha256':digest(original),'font':0,'max_input_characters':7,'entries':entries}


def encode(e,original):
    text=e['english'];check(isinstance(text,str) and 1<=len(text)<=7 and text.isascii() and text.isalnum(),'Inscription must fit seven Latin alphanumeric slots')
    font=FontZero(original);width=sum(font.glyph(ch)[1] for ch in text);check(width<=90,'Inscription exceeds learned-list field');return text.encode()+b'\0'


def prepare():
    original=ORIGINAL_ROM.read_bytes();c=extract(original);old={e['id']:e for e in load_json(CATALOG)['entries']} if CATALOG.exists() else {}
    for e in c['entries']:
        e['english']=ALIASES[e['item_id']];e['notes']='Seven-slot inscription/display abbreviation of '+e['full_item_name']+'. Full item/glossary name is unchanged. Both original kana aliases remain valid through the legacy matcher; English matching ignores letter case. The learned-list displays this spelling.'
        if e['id'] in old:
            for k in ('english','notes','references'):e[k]=old[e['id']][k]
        encode(e,original)
    atomic_write(CATALOG,(json.dumps(c,ensure_ascii=False,indent=2)+'\n').encode());report={'source_sha256':digest(original),'entries':extract(original)['entries'],'original_dictionary':{'start':hex(TABLE),'end_exclusive':hex(TABLE+600),'records':49,'stride':12,'preserved':True},'patches':[{'start':hex(0x707E0),'end_exclusive':hex(0x707E4),'kind':'learned-list dictionary literal'},{'start':hex(0x7F170),'end_exclusive':hex(0x7F178),'kind':'English match preflight / original kana fallback'}],'scope':'98 original kana aliases, 49 item identities. Original source bytes and dictionary remain intact; appended English aliases are used by list display and an additional learned-only matcher.'};atomic_write(OUTPUT/'source-owners.json',(json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode());print('Prepared 49 inscription identities / 98 kana sources',flush=True)


def validate(original,c):
    fresh=extract(original);check(all(c[k]==fresh[k] for k in ('schema','base_sha256','font','max_input_characters')),'Inscription catalog metadata differs');check(len(c['entries'])==98,'Inscription source count differs');seen=set()
    for e,f in zip(c['entries'],fresh['entries'],strict=True):
        check(all(e[k]==f[k] for k in f.keys()-{'english','notes','references'}),'Inscription source metadata differs');encode(e,original)
        if e['variant']==0:check(e['english'].lower() not in seen,'Ambiguous English inscription');seen.add(e['english'].lower())
        else:check(e['english']==c['entries'][2*e['row']]['english'],'Kana variants need the same English inscription')
    return c['entries']


def build_rom(original,language='english',catalog=None,*,build=None):
    check(language in ('english','japanese'),'Inscription language');b=RomBuild(original) if build is None else build;_,prior=previous.build_rom(original,build=b);c=load_json(CATALOG) if catalog is None else catalog;entries=validate(original,c);relocated={};records=[]
    b.protect_source('inscriptions.original-dictionary',TABLE,TABLE+600,'inscriptions')
    for e in entries:
        at=int(e['offset'],0);raw=bytes.fromhex(e['source_hex']);b.protect_source(e['id'],at,at+len(raw),'inscriptions');payload=encode(e,original) if language=='english' else raw
        dest=b.allocate(e['id'],payload,'inscriptions');relocated[e['id']]={'offset':dest,'bytes':len(payload)}
    for row in range(49):records.extend((0x08000000+relocated[f'inscription.{row:02d}.0']['offset'],0x08000000+relocated[f'inscription.{row:02d}.1']['offset'],entries[row*2]['item_id']))
    table=b.allocate('inscriptions.alias-table',struct.pack('<'+str(len(records))+'I',*records)+b'\0'*12,'inscriptions')+0x08000000
    b.patch('inscriptions.list-literal',0x707E0,struct.pack('<I',0x08000000+TABLE),struct.pack('<I',table),'inscriptions','Show input spellings in the original learned-scroll list')
    if language=='english':
        address=0x08000000+((b.allocator.cursor+3)&~3)
        with tempfile.TemporaryDirectory(prefix='torneko-inscriptions-') as directory:
            run=subprocess.run([str(ROOT/'.tools/bin/armips'),str(ROOT/'tools/inscription_matcher.asm'),'-equ','CODE_ADDRESS',hex(address),'-equ','ALIAS_TABLE',hex(table)],cwd=directory,capture_output=True,text=True);check(run.returncode==0,'Inscription assembler: '+run.stdout+run.stderr);code=(Path(directory)/'inscription-matcher.bin').read_bytes()
        check(b.allocate('inscriptions.matcher-code',code,'inscriptions')+0x08000000==address,'Inscription code address differs')
        b.patch('inscriptions.matcher-hook',0x7F170,original[0x7F170:0x7F178],bytes.fromhex('004b1847')+struct.pack('<I',address|1),'inscriptions','Learned English matching before original Japanese fallback')
    data,ledger=b.finish();return data,{'source_sha256':digest(original),'rom_sha256':digest(data),'previous_rom_sha256':prior['rom_sha256'],'language':language,'inscriptions':{'resources':98,'identities':49,'relocated':relocated,'table':hex(table)},'ledger':ledger}


def build():
    original=ORIGINAL_ROM.read_bytes();c=load_json(CATALOG);atomic_write(OUTPUT/'catalog.json',(json.dumps(c,ensure_ascii=False,indent=2)+'\n').encode())
    for language in ('english','japanese'):
        data,r=build_rom(original,language,c);r['catalog_sha256']=digest((OUTPUT/'catalog.json').read_bytes());atomic_write(OUTPUT/f'torneko3-inscriptions-{language}.gba',data);atomic_write(OUTPUT/f'{language}-build.json',(json.dumps(r,indent=2)+'\n').encode());print(language,r['rom_sha256'],flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=('prepare','build'));prepare() if p.parse_args().mode=='prepare' else build()
