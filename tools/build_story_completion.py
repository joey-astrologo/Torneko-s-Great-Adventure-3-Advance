"""Append independently reviewed remaining story sources to the journey baseline."""
import argparse
import csv
import io
import json
import struct
from tools import build_early_journey as previous
from tools import build_first_village as speech
from tools import build_opening_story as opening
from tools.build_first_label import ORIGINAL_ROM,ROOT,digest
from tools.translation_pipeline import atomic_write,load_json,check
from tools.game_text import GameTextCodec,rebuild
from tools.rom_build import RomBuild
from tools.verify_story_provenance import ROUTES

OUTPUT=ROOT/'build/completion/story'
CATALOG=ROOT/'translations/story-completion.json'
DRAFTS=ROOT/'translations/story-completion-drafts.tsv'
OWNERS=OUTPUT/'source-owners.json'
OPS=(0x23,0x24,0x25,0x26,0x27,0x28,0x2A,0x2B,0x2C,0x2D,0x96,0x97,0x98)
STORY_TERM_IDS={
    'torneko','enemy_tipper','enemy_rosa','enemy_ines','enemy_hell_justice',
    'enemy.slime','enemy.muddy_hand','enemy_shaman','series_zoom','bread',
    'service.tokens','synthesis','help.order.0','help.order.6','interface.trap.022',
    *(f'combined_item_{i:03d}' for i in
      (11,21,29,41,45,50,80,85,111,132,187,194,286,315,322,326,333,334,344)),
}


def eligible_term(term):
    return (term.get('batch') in ('first-village','early-journey','story-completion')
            or term['id'] in STORY_TERM_IDS or term['id'].startswith('interface.dungeon.'))


def choice_prefix(original,prompt):
    check(prompt>=0x900000 and prompt%4==0 and original[prompt] in (0x96,0x97),'Invalid choice prompt')
    cursor=prompt+8;words=[]
    while cursor+8<=len(original) and original[cursor]==0x98:
        check(len(words)<6,'Choice list exceeds reviewed native capacity')
        words.append(cursor+4);cursor+=8
    check(words,'Empty choice prefix')
    return words


def source_entry(original,master,at,chapter):
    source=master[at];codec=GameTextCodec(original);p=codec.parse(original,at);events=[]
    check(bytes.fromhex(source['source_hex'])==rebuild(p['tokens']),'Story source changed')
    for word in source['pointer_candidates']:
        offset=int(word,0);command,ptr=struct.unpack_from('<II',original,offset-4);op=command&255
        check(offset>=0x900000 and op in OPS and ptr==at+0x08000000,'Unsupported story event owner')
        ev={'command_offset':hex(offset-4),'pointer_offset':word,'command_word':f'0x{command:08X}','opcode':op}
        if op==0x98:
            prompt=offset-12
            while prompt>=0x900000 and original[prompt]==0x98:prompt-=8
            choices=choice_prefix(original,prompt)
            check(offset in choices,'Unowned choice operand')
            ev.update(prompt_command_offset=hex(prompt),choice_index=choices.index(offset),choice_count=len(choices))
        else:
            ev['wrapper']=f'0x{ROUTES[op][1]:08X}'
            if op in (0x96,0x97):ev['choice_count']=len(choice_prefix(original,offset-4))
        events.append(ev)
    check(events,'Missing story owner')
    return {'id':f'completion.{at:08x}','master_id':source['id'],'chapter':chapter,'offset':source['offset'],
            'end_exclusive':hex(p['end']),'source_hex':p['raw_hex'],'source_tokens':p['tokens'],'japanese':p['display'],
            'events':events,'reuse':None,'layout':'choice' if all(ev['opcode']==0x98 for ev in events) else 'centered' if '$c' in p['display'] else 'speech' if '「' in p['display'] else 'observation',
            'english':None,'display':None,'notes':'','references':[]}


def encode(e,original,hero='Torneko'):
    if e['layout']=='choice':return previous.encode(e,original,hero)
    if e['layout']=='centered':return opening.encode(e,original)
    return speech.encode(e,original,hero)


def validate(original,catalog):
    check(catalog['base_sha256']==digest(original),'Wrong story base')
    master={int(e['offset'],0):e for e in load_json(ROOT/'translations/master.json')['entries']};seen=set();words=set()
    for e in catalog['entries']:
        check(e['id'] not in seen,'Duplicate story source');seen.add(e['id'])
        fresh=source_entry(original,master,int(e['offset'],0),e['chapter'])
        check(all(e[k]==fresh[k] for k in fresh.keys()-{'english','display','notes','references'}),'Changed story source/owner')
        check(e['english'] and e['notes'] and e['display'] is None,'Missing full reviewed story')
        for ev in e['events']:
            check(ev['pointer_offset'] not in words,'Duplicate story operand');words.add(ev['pointer_offset'])
        encode(e,original)
    return catalog['entries']


def prepare():
    original=ORIGINAL_ROM.read_bytes();master={int(e['offset'],0):e for e in load_json(ROOT/'translations/master.json')['entries']}
    old=load_json(CATALOG) if CATALOG.exists() else {'schema':1,'base_sha256':digest(original),'font':0,'scope':'Independently reviewed remaining ordinary story messages; completion is in progress and special controls/other families remain separate.','entries':[]}
    c=json.loads(json.dumps(old));by_at={int(e['offset'],0):e for e in c['entries']};g=load_json(ROOT/'translations/glossary.json');terms={t['id']:t for t in g['terms']}
    with DRAFTS.open() as f:rows=list(csv.DictReader(f,delimiter='\t'))
    check(len(rows)==len({int(x['offset'],16) for x in rows}),'Duplicate authored draft')
    for row in rows:
        at=int(row['offset'],16);english=row['english'].replace('\\n','\n')
        if at in by_at:
            check(by_at[at]['english']==english and by_at[at]['chapter']==row['chapter'],'Earlier authored story changed');continue
        e=source_entry(original,master,at,row['chapter']);e['english']=english
        e['notes']='Independent translation from the pinned Japanese GBA script. Preserve original event parameters, protagonist substitutions and page meaning. '+row.get('notes','')
        if e['japanese'].startswith('＊'):e['notes']+=' Anonymous speaker remains ???.'
        if e['layout']=='centered':e['notes']+=' Centered narration retains the native centering control on each displayed line.'
        # Exact Japanese identity matches only; compounds remain scoped terms.
        eligible=[t for t in terms.values() if eligible_term(t)]
        e['references']=list(dict.fromkeys(t['id'] for t in eligible if any(j.replace('\\u3000','\u3000') in e['japanese'] for j in t['japanese'])))
        if '$t' in e['japanese']:e['references']=list(dict.fromkeys(e['references']+['torneko','enemy_tipper']))
        for ident in e['references']:terms[ident].setdefault('occurrences',[]).append({'catalog':'translations/story-completion.json','id':e['id']})
        c['entries'].append(e);by_at[at]=e
    # Add evidence links for terms introduced later in the same continuous pass
    # without replacing earlier English, notes, references or occurrences.
    for e in c['entries']:
        for t in terms.values():
            relevant=eligible_term(t)
            if relevant and any(j.replace('\\u3000','\u3000') in e['japanese'] for j in t['japanese']):
                if t['id'] not in e['references']:e['references'].append(t['id'])
                occurrence={'catalog':'translations/story-completion.json','id':e['id']}
                if occurrence not in t.setdefault('occurrences',[]):t['occurrences'].append(occurrence)
    c['scope']='Independently reviewed remaining story messages and bounded native choice prefixes. Completion is in progress; positioned text, special formatter grammars and other resource families remain separate.'
    validate(original,c)
    atomic_write(CATALOG,(json.dumps(c,ensure_ascii=False,indent=2)+'\n').encode())
    owners={'schema':1,'source_sha256':digest(original),'scope':'Exact independently reviewed ordinary story operands. This report authorizes only its listed pointer words, not surrounding event/source ranges.','entries':[{k:v for k,v in e.items() if k not in ('english','display','notes','references')} for e in c['entries']]}
    atomic_write(OWNERS,(json.dumps(owners,ensure_ascii=False,indent=2)+'\n').encode())
    prior=g['current_review']
    if prior['id']!='story-completion' and not any(x['id']==prior['id'] for x in g['batches']):g['batches'].append(prior)
    g['current_review']={'id':'story-completion','reviewed_on':'2026-09-11','status':'in_progress_drafts_pending_native_acceptance',
        'scope':c['scope'],'source_rom_sha256':digest(original),'catalogs':{'translations/story-completion.json':digest(CATALOG.read_bytes())},
        'new_terms':[t['id'] for t in g['terms'] if t.get('batch')=='story-completion'],'terminology_review':'translations/story-completion-terminology-review.tsv'}
    atomic_write(ROOT/'translations/glossary.json',(json.dumps(g,ensure_ascii=False,indent=2)+'\n').encode())
    out=io.StringIO();w=csv.writer(out,delimiter='\t',lineterminator='\n');w.writerow(['id','chapter','japanese','full_english','glossary_references','notes'])
    for e in c['entries']:w.writerow([e['id'],e['chapter'],e['japanese'].replace('\n','<LF>'),e['english'].replace('\n','<LF>'),','.join(e['references']),e['notes']])
    atomic_write(ROOT/'translations/story-completion-terminology-review.tsv',out.getvalue().encode())
    print(len(c['entries']),'reviewed story entries;',sum(len(e['events']) for e in c['entries']),'owned operands',flush=True)


def build_rom(original,language='english',catalog=None,*,build=None):
    check(language in ('english','japanese'),'Invalid story language');b=RomBuild(original) if build is None else build
    _,prior=previous.build_rom(original,build=b);c=load_json(CATALOG) if catalog is None else catalog;entries=validate(original,c);relocated={}
    for e in entries:
        at=int(e['offset'],0);source=bytes.fromhex(e['source_hex']);raw,metrics=encode(e,original)
        b.protect_source(e['id'],at,at+len(source),'story-completion')
        dest=b.allocate(e['id'],raw if language=='english' else source,'story-completion')
        for ev in e['events']:b.patch(e['id']+'.'+ev['pointer_offset'],int(ev['pointer_offset'],0),struct.pack('<I',at+0x08000000),struct.pack('<I',dest+0x08000000),'story-completion','Reviewed story operand; command parameters and original source preserved')
        relocated[e['id']]={'offset':dest,'metrics':metrics}
    data,ledger=b.finish()
    return data,{'source_sha256':digest(original),'rom_sha256':digest(data),'language':language,'previous_rom_sha256':prior['rom_sha256'],
                'story':{'entries':len(entries),'operand_words':sum(len(e['events']) for e in entries),'relocated':relocated},'ledger':ledger}


def build(checkpoint=None):
    # Freeze the reviewed inputs before either language is built. Draft work may
    # continue independently while this slower cumulative build runs.
    catalog=load_json(CATALOG);original=ORIGINAL_ROM.read_bytes()
    output=ROOT/'build/completion/checkpoints'/checkpoint if checkpoint else OUTPUT
    frozen_owners={'schema':1,'source_sha256':digest(original),'scope':'Exact independently reviewed story sources and operands; surrounding gaps remain occupied.','entries':[{k:v for k,v in e.items() if k not in ('english','display','notes','references')} for e in catalog['entries']]}
    atomic_write(output/'catalog.json',(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n').encode())
    atomic_write(output/'source-owners.json',(json.dumps(frozen_owners,ensure_ascii=False,indent=2)+'\n').encode())
    for lang in ('english','japanese'):
        data,report=build_rom(original,lang,catalog)
        report['catalog_sha256']=digest((output/'catalog.json').read_bytes())
        atomic_write(output/f'torneko3-story-completion-{lang}.gba',data)
        atomic_write(output/f'{lang}-build.json',(json.dumps(report,indent=2)+'\n').encode())
        print(lang,report['rom_sha256'],len(report['story']['relocated']),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['prepare','build']);p.add_argument('--checkpoint');a=p.parse_args()
    prepare() if a.mode=='prepare' else build(a.checkpoint)
