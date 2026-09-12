"""Shared object/service scripts, transition narration and bonus-cave events."""
import argparse
import json
import struct
from tools import build_story_special as previous
from tools import build_story_completion as story
from tools.build_first_label import ORIGINAL_ROM,ROOT,digest
from tools.translation_pipeline import atomic_write,load_json,check
from tools.rom_build import RomBuild

CATALOG=ROOT/'translations/shared-story.json'
OUTPUT=ROOT/'build/completion/shared-story'
encode=story.encode


def validate(original,catalog):
    entries=story.validate(original,catalog)
    check(len(entries)==78 and all(0x910000<=int(e['offset'],0)<0x920000 for e in entries),'Shared-script scope differs')
    return entries


def owners():
    original=ORIGINAL_ROM.read_bytes();catalog=load_json(CATALOG);entries=validate(original,catalog)
    atomic_write(OUTPUT/'source-owners.json',(json.dumps({'source_sha256':digest(original),'scope':'Exact shared-script source ranges and pointer operands. Selection envelopes, script headers, branch words and former source space remain occupied.','entries':[{k:v for k,v in e.items() if k not in ('english','display','notes','references')} for e in entries]},ensure_ascii=False,indent=2)+'\n').encode())
    print(len(entries),'shared sources;',sum(len(e['events']) for e in entries),'operands',flush=True)


def build_rom(original,language='english',catalog=None,*,build=None):
    check(language in ('english','japanese'),'Invalid shared-story language')
    b=RomBuild(original) if build is None else build
    _,prior=previous.build_rom(original,build=b)
    c=load_json(CATALOG) if catalog is None else catalog;entries=validate(original,c);relocated={}
    for e in entries:
        at=int(e['offset'],0);source=bytes.fromhex(e['source_hex']);raw,metrics=encode(e,original)
        b.protect_source(e['id'],at,at+len(source),'shared-story');dest=b.allocate(e['id'],raw if language=='english' else source,'shared-story')
        for ev in e['events']:b.patch(e['id']+'.'+ev['pointer_offset'],int(ev['pointer_offset'],0),struct.pack('<I',at+0x08000000),struct.pack('<I',dest+0x08000000),'shared-story','Reviewed shared-script operand; original command, choice ordinal and branch metadata preserved')
        relocated[e['id']]={'offset':dest,'metrics':metrics}
    data,ledger=b.finish()
    return data,{'source_sha256':digest(original),'rom_sha256':digest(data),'previous_rom_sha256':prior['rom_sha256'],'language':language,
        'story':{'entries':len(entries),'operand_words':sum(len(e['events']) for e in entries),'relocated':relocated},'ledger':ledger}


def build():
    original=ORIGINAL_ROM.read_bytes();catalog=load_json(CATALOG)
    atomic_write(OUTPUT/'catalog.json',(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n').encode())
    for lang in ('english','japanese'):
        data,report=build_rom(original,lang,catalog);report['catalog_sha256']=digest((OUTPUT/'catalog.json').read_bytes())
        atomic_write(OUTPUT/f'torneko3-story-completion-{lang}.gba',data);atomic_write(OUTPUT/f'{lang}-build.json',(json.dumps(report,indent=2)+'\n').encode())
        print(lang,report['rom_sha256'],flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=('owners','build'));a=p.parse_args();owners() if a.mode=='owners' else build()
