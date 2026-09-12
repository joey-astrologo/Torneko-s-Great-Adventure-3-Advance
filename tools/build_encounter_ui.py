"""Themed monster-house names and original companion action/spell menus."""
import argparse
import json
import struct
from tools import build_system_labels as previous
from tools.build_first_label import ORIGINAL_ROM,ROOT,digest
from tools.game_text import GameTextCodec,rebuild
from tools.translation_pipeline import check,load_json,atomic_write,FontZero
from tools.rom_build import RomBuild
CATALOG=ROOT/'translations/encounter-ui.json'
OUTPUT=ROOT/'build/completion/encounter-ui'
HOUSES=(0xAE574,0xC5E44)
MENUS=((0xD9340,3),(0xD93C8,3),(0xD9580,3),(0xD9638,3),(0xD9680,4))
HOUSE_DRAFTS=('Monster house?','Zombie house','Power house','Drain house','Throwing house','Magic house','Aquatic house','Multiplying house','Warp house','Bomb house','Dragon house','Thief house','Pip & Conk house','Slime house','Antimagic house','Demon house','Standoff house','Swordmaster house','Fickle house','Speed house')
MENU_DRAFTS={0xD9370:'Cancel',0xD9378:'Kaclang',0xD9384:'*Talk',0xD93F8:'Cancel',0xD9400:'Call allies',0xD940C:'*Talk',0xD95B0:'Cancel',0xD95B8:'Warp somewhere',0xD95C8:'*Talk',0xD9668:'Cancel',0xD9670:'Talk',0xD9678:'*Spells',0xD96BC:'Squelch',0xD96C8:'Bang',0xD96D0:'*Heal'}


def extract(original):
    codec=GameTextCodec(original);master={int(e['offset'],0):e for e in load_json(ROOT/'translations/master.json')['entries']};entries={}
    def add(word,family,**metadata):
        at=struct.unpack_from('<I',original,word)[0]-0x08000000;s=codec.parse(original,at);check(at in master and rebuild(s['tokens'])==original[at:s['end']],'Encounter source differs')
        if at not in entries:entries[at]={'id':f'encounter.{at:08x}','family':family,'offset':hex(at),'source_end_exclusive':hex(s['end']),'source_hex':s['raw_hex'],'source_tokens':s['tokens'],'japanese':s['display'],'master_id':master[at]['id'],'pointer_owners':[],'english':None,'display':None,'notes':'','references':[]}
        check(entries[at]['family']==family,'Encounter source family conflict');entries[at]['pointer_owners'].append({'offset':hex(word),**metadata})
    for hero,base in enumerate(HOUSES):
        for row in range(20):add(base+row*44,'house',evidence='typed_44_byte_house_record',hero=hero,row=row)
    add(0x34B00,'house',evidence='thumb_literal_fallback',loads=['0x08034A96'],row=-1)
    add(0x337C0,'announcement',evidence='explicit_tutorial_pointer_supersession',loads=['0x08033784'],row=-1)
    for base,count in MENUS:
        for row in range(count):add(base+row*12,'menu',evidence='typed_12_byte_menu_record',table=hex(base),row=row)
        check(original[base+count*12:base+(count+1)*12]==b'\0'*12,'Companion menu terminator differs')
    check(len(entries)==37 and sum(len(e['pointer_owners']) for e in entries.values())==58,'Encounter source count differs');return {'schema':1,'base_sha256':digest(original),'font':0,'entries':sorted(entries.values(),key=lambda e:int(e['offset'],0))}


def encode(e,original):
    text=e['display'] or e['english'];check(isinstance(text,str) and text and all(32<=ord(ch)<127 for ch in text),'Encounter labels must be one ASCII line');raw=text.encode()+b'\0';check((text=="It's a $m0!") if e['family']=='announcement' else not any(ch in text for ch in '$%{}'),'Encounter label introduces controls')
    check(raw.startswith(b'*')==bytes.fromhex(e['source_hex']).startswith(b'*'),'Companion default marker changed');cap=30 if e['family']=='house' else 512;check(len(raw)<=cap,'Encounter label exceeds native copy');font=FontZero(original);width=sum(font.glyph(ch)[1] for ch in text.lstrip('*').replace('$m0','Swordmaster house'));check(width<=192,'Encounter label exceeds display width');return raw,{'bytes_including_nul':len(raw),'capacity':cap,'width':width}


def prepare():
    original=ORIGINAL_ROM.read_bytes();c=extract(original);existing={e['id']:e for e in load_json(CATALOG)['entries']} if CATALOG.exists() else {};g=load_json(ROOT/'translations/glossary.json')['terms']
    for e in c['entries']:
        at=int(e['offset'],0);row=e['pointer_owners'][0]['row'];e['english']="It's a $m0!" if e['family']=='announcement' else ('Monster house' if row<0 else HOUSE_DRAFTS[row]) if e['family']=='house' else MENU_DRAFTS[at]
        e['notes']='Independent Japanese-source translation. Original selector/menu order, flags, return codes and byte capacities are unchanged.'
        if e['family']=='house':e['notes']+=' House categories are project names, not official localization claims. Category cross-check: https://wikiwiki.jp/dqdic3rd/【テーマ別モンスターハウス】 (fan-maintained Japanese reference, not official English).'
        if at==0xAE900:e['notes']+=' ケンゴウ refers to sword-category monsters; do not identify it as a Shiren enemy species.'
        if at==0xAE958:e['references']=['enemy_pip_fighter','enemy_battle_pip','enemy_wiz_pip','enemy_epipany','enemy_conkuistador','enemy_conkerer','enemy_conkjurer','enemy_conkuisitor'];e['notes']+=' Pip/Conk grouping follows the eight exact Japanese enemy identities in the accepted modern glossary; https://peamon.net/toruneko3a/monster/theme-mh.html independently lists that grouping.'
        for t in g:
            if e['english'].lstrip('*')==t['english'] and any(j==e['japanese'].lstrip('*') for j in t['japanese']):e['references'].append(t['id'])
        if e['id'] in existing:
            for k in ('english','display','notes','references'):e[k]=existing[e['id']][k]
        encode(e,original)
    atomic_write(CATALOG,(json.dumps(c,ensure_ascii=False,indent=2)+'\n').encode());atomic_write(OUTPUT/'source-owners.json',(json.dumps(extract(original),ensure_ascii=False,indent=2)+'\n').encode());print('Prepared',len(c['entries']),'encounter sources',flush=True)


def validate(original,c):
    fresh=extract(original);check(all(c[k]==fresh[k] for k in ('schema','base_sha256','font')),'Encounter catalog header differs');check(len(c['entries'])==37,'Encounter catalog count differs')
    for e,f in zip(c['entries'],fresh['entries'],strict=True):check(all(e[k]==f[k] for k in f.keys()-{'english','display','notes','references'}),'Encounter source metadata differs');encode(e,original)
    return c['entries']


def build_rom(original,language='english',catalog=None,*,build=None):
    check(language in ('english','japanese'),'Encounter build language');b=RomBuild(original) if build is None else build;_,prior=previous.build_rom(original,build=b);c=load_json(CATALOG) if catalog is None else catalog;entries=validate(original,c);relocated={};supersessions=[]
    old=next(p for p in load_json(previous.OUTPUT/'english-build.json')['ledger']['patches'] if p['offset']==0x337C0)
    check(old['id']=='tutorial.001b50c5.000337c0' and old['owner']=='tutorial-gameplay','Unexpected house narration owner')
    for e in entries:
        at=int(e['offset'],0);source=bytes.fromhex(e['source_hex']);raw,metrics=encode(e,original);b.protect_source(e['id'],at,at+len(source),'encounter-ui')
        if e['family']=='announcement' and language=='japanese':
            relocated[e['id']]={'offset':int.from_bytes(bytes.fromhex(old['after']),'little')-0x08000000,'metrics':metrics,'retained_prior_english':True};continue
        dest=b.allocate(e['id'],raw if language=='english' else source,'encounter-ui')
        for p in e['pointer_owners']:
            if e['family']=='announcement':
                check(next(p for p in b.patches if p['id']==old['id'])==old,'Prior house narration metadata differs');supersessions.append(b.supersede_patch(e['id']+'.correction',old['id'],old['owner'],bytes.fromhex(old['after']),struct.pack('<I',dest+0x08000000),'encounter-ui','Add the indefinite article to the actual themed-house announcement'))
            else:b.patch(e['id']+'.'+p['offset'],int(p['offset'],0),struct.pack('<I',at+0x08000000),struct.pack('<I',dest+0x08000000),'encounter-ui',p['evidence'])
        relocated[e['id']]={'offset':dest,'metrics':metrics}
    data,ledger=b.finish();return data,{'source_sha256':digest(original),'rom_sha256':digest(data),'previous_rom_sha256':prior['rom_sha256'],'language':language,'encounter_ui':{'resources':37,'new_inventory_sources':36,'pointer_words':58,'supersessions':supersessions,'relocated':relocated},'ledger':ledger}


def build():
    original=ORIGINAL_ROM.read_bytes();c=load_json(CATALOG);atomic_write(OUTPUT/'catalog.json',(json.dumps(c,ensure_ascii=False,indent=2)+'\n').encode())
    for language in ('english','japanese'):
        data,r=build_rom(original,language,c);r['catalog_sha256']=digest((OUTPUT/'catalog.json').read_bytes());atomic_write(OUTPUT/f'torneko3-encounter-ui-{language}.gba',data);atomic_write(OUTPUT/f'{language}-build.json',(json.dumps(r,indent=2)+'\n').encode());print(language,r['rom_sha256'],flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=('prepare','build'));prepare() if p.parse_args().mode=='prepare' else build()
