"""Remaining Zoom restrictions, world item observations and inline warehouse text."""
import argparse
import json
import struct
from tools import build_inscriptions as previous,build_arena_services as paged,build_merchants as world
from tools.build_first_label import ORIGINAL_ROM,ROOT,digest
from tools.game_text import GameTextCodec,rebuild
from tools.translation_pipeline import check,load_json,atomic_write
from tools.rom_build import RomBuild
CATALOG=ROOT/'translations/world-completion.json'
OUTPUT=ROOT/'build/completion/world-completion'
ZOOM_CACHE=(0xCB0288,0xCB02B4)
WAREHOUSE={0xCB04E8:(0x7394C,0x02000660),0xCB057C:(0x73994,0x020006F4)}
DRAFTS={
0x86F0AC:"-You've been invited to the castle celebration. Better not wander off.",
0x86F0F0:"-The Fortune-teller is ill in bed. You should go outside and use Zoom quietly...",
0x86F148:"-You can't go home until you've spoken to the Fortune-teller!",
0x86F178:"-First, you should go and see Torneko.",
0x86F1B0:"-The villagers went to all this trouble to hold a feast for you. You can't just slip away...",
0x86F20C:"*Fortune-teller: Don't make an old woman overdo it! Zooming aggravates my aching joints.",
0x86F270:"-You can't leave the Fortune-teller behind!",
0x86F2A4:"-You can't go home until the Fortune-teller has made the medicine!",
0x86F2E0:"-You should take the sacred flame to the lighthouse at once, before going anywhere else.",
0x86F338:"-You can't leave before giving the Chief your answer!",
0x86F374:"-You don't even know where you are. It doesn't look like you can go anywhere...",
0x86F3BC:"-Use Zoom?",
0x86F3D0:"-You haven't explored anywhere new on your own yet. There's nowhere you can Zoom to...",
0x86FAA4:"You found %s!",
0x86FAC0:"But $t can't carry any more gold...",
0x86FAEC:"But $t's inventory is full...",
0x86FB1C:"$t obtained %s!",
0xCB04E8:"The warehouse is full. We cannot store any more items.\nTry discarding or selling unwanted items to make room.",
0xCB057C:"Thank you!"}


def extract(original):
    codec=GameTextCodec(original);master={int(e['offset'],0):e for e in load_json(ROOT/'translations/master.json')['entries']};entries=[]
    for at in DRAFTS:
        m=master[at];s=codec.parse(original,at);check(rebuild(s['tokens'])==original[at:s['end']],'World completion source roundtrip');owners=[]
        if at in WAREHOUSE:
            word,target=WAREHOUSE[at];candidates=[(word,target,'inline_startup_string_literal')]
        else:candidates=[(int(p,0),at+0x08000000,'initialized_zoom_pointer' if ZOOM_CACHE[0]<=int(p,0)<ZOOM_CACHE[1] else 'thumb_literal') for p in m['pointer_candidates']]
        for word,target,kind in candidates:
            check(struct.unpack_from('<I',original,word)[0]==target,'World completion source pointer differs');check(kind!='thumb_literal' or word in (0x604CC,0x604E0,0x604E8,0x62E74,0x62E78,0x62E7C,0x62E80,0x62F34),'Unreviewed world completion literal');owners.append({'offset':hex(word),'expected_address':hex(target),'evidence':kind})
        entries.append({'id':f'world-completion.{at:08x}','family':'warehouse' if at in WAREHOUSE else 'zoom' if at<0x86FAA4 else 'observation','offset':hex(at),'source_end_exclusive':hex(s['end']),'japanese':s['display'],'source_hex':s['raw_hex'],'source_tokens':s['tokens'],'master_id':m['id'],'pointer_owners':owners,'english':None,'display':None,'notes':'','references':[]})
    check(len(entries)==19 and sum(len(e['pointer_owners']) for e in entries)==21,'World completion owner count differs')
    return {'schema':1,'base_sha256':digest(original),'font':0,'entries':entries}


def encode(e,original):
    if e['family']=='observation':return world.encode(e,original)
    proxy=dict(e,family='message');prefix=b''
    if e['family']=='zoom':
        text=e['display'] or e['english'];source=bytes.fromhex(e['source_hex']);check(text and text[0] in '-*' and text[0]==chr(source[0]),'Zoom protocol marker changed');prefix=text[0].encode();proxy['english']=text[1:];proxy['display']=None
    raw,metrics=paged.encode(proxy,original);return prefix+raw,dict(metrics,protocol_prefix=prefix.decode(),speech=e['family']=='warehouse' or prefix==b'*')


def prepare():
    original=ORIGINAL_ROM.read_bytes();c=extract(original);old={e['id']:e for e in load_json(CATALOG)['entries']} if CATALOG.exists() else {};g=load_json(ROOT/'translations/glossary.json')['terms']
    for e in c['entries']:
        e['english']=DRAFTS[int(e['offset'],0)];e['notes']='Independent original-source translation; prefixes and runtime text pointers preserve their separate consumer contracts. Warehouse wording reuses the previously reviewed matching source in ally-services.'
        for term in g:
            if any(j in e['japanese'] and (len(j)>=3 or j=='族長') for j in term['japanese']) and any(x in term['english'].lower() for x in ('fortune','torneko','sacred flame','zoom','chief')):e['references'].append(term['id'])
        if e['id'] in old:
            for k in ('english','display','notes','references'):e[k]=old[e['id']][k]
        encode(e,original)
    atomic_write(CATALOG,(json.dumps(c,ensure_ascii=False,indent=2)+'\n').encode());atomic_write(OUTPUT/'source-owners.json',(json.dumps({'source_sha256':digest(original),'entries':extract(original)['entries'],'zoom_cache':{'rom_start':hex(ZOOM_CACHE[0]),'rom_end_exclusive':hex(ZOOM_CACHE[1]),'ram_start':hex(0x02000400)},'scope':'19 sources / 21 pointer words. Zoom markers are consumed before paged display. Four item messages use world observations. Warehouse literals originally point to inline initialized RAM strings; source/startup bytes remain unchanged.'},ensure_ascii=False,indent=2)+'\n').encode());print('19 world sources / 21 pointers prepared',flush=True)


def validate(original,c):
    fresh=extract(original);check(all(c[k]==fresh[k] for k in ('schema','base_sha256','font')),'World completion header differs');check(len(c['entries'])==19,'World completion source count differs')
    for e,f in zip(c['entries'],fresh['entries'],strict=True):check(all(e[k]==f[k] for k in f.keys()-{'english','display','notes','references'}),'World completion source metadata differs');encode(e,original)
    return c['entries']


def build_rom(original,language='english',catalog=None,*,build=None):
    check(language in ('english','japanese'),'World completion language');b=RomBuild(original) if build is None else build;_,prior=previous.build_rom(original,build=b);c=load_json(CATALOG) if catalog is None else catalog;entries=validate(original,c);relocated={}
    for e in entries:
        at=int(e['offset'],0);source=bytes.fromhex(e['source_hex']);raw,metrics=encode(e,original);b.protect_source(e['id'],at,at+len(source),'world-completion');dest=b.allocate(e['id'],raw if language=='english' else source,'world-completion')
        for p in e['pointer_owners']:b.patch(e['id']+'.'+p['offset'],int(p['offset'],0),struct.pack('<I',int(p['expected_address'],0)),struct.pack('<I',dest+0x08000000),'world-completion',p['evidence'])
        relocated[e['id']]={'offset':dest,'metrics':metrics}
    data,ledger=b.finish();return data,{'source_sha256':digest(original),'rom_sha256':digest(data),'previous_rom_sha256':prior['rom_sha256'],'language':language,'world_completion':{'resources':19,'pointer_words':21,'relocated':relocated},'ledger':ledger}


def build():
    original=ORIGINAL_ROM.read_bytes();c=load_json(CATALOG);atomic_write(OUTPUT/'catalog.json',(json.dumps(c,ensure_ascii=False,indent=2)+'\n').encode())
    for language in ('english','japanese'):
        data,r=build_rom(original,language,c);r['catalog_sha256']=digest((OUTPUT/'catalog.json').read_bytes());atomic_write(OUTPUT/f'torneko3-world-completion-{language}.gba',data);atomic_write(OUTPUT/f'{language}-build.json',(json.dumps(r,indent=2)+'\n').encode());print(language,r['rom_sha256'],flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=('prepare','build'));prepare() if p.parse_args().mode=='prepare' else build()
