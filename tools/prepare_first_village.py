"""Import independently authored village drafts once; preserve earlier work."""
import csv
import io
import json
from tools.build_first_village import CATALOG,OUTPUT,OWNERS,extract_catalog,validate_catalog
from tools.build_first_label import ORIGINAL_ROM,ROOT,digest
from tools.translation_pipeline import load_json,check,atomic_write


def prepare():
    check(not CATALOG.exists(),'Do not overwrite authored village catalog')
    original=ORIGINAL_ROM.read_bytes();c=extract_catalog(original)
    with (ROOT/'translations/first-village-drafts.tsv').open() as f:rows=list(csv.DictReader(f,delimiter='\t'))
    drafts={int(r['offset'],16):r['english'].replace('\\n','\n') for r in rows}
    check(len(rows)==len(drafts)==len(c['entries']) and set(drafts)=={int(e['offset'],0) for e in c['entries']},'Incomplete or duplicate drafts')
    glossary=load_json(ROOT/'translations/glossary.json');terms={t['id']:t for t in glossary['terms']}
    glossary['sources']['village_story_primary']={'url':'https://www.spike-chunsoft.co.jp/pages/games/torneco3/story02.html','reference_game':'Torneko no Daibouken 3 (Japanese PS2 publisher synopsis)','reviewed_on':'2026-09-11','evidence':'Primary Japanese island identity バリナボ and Ines accompanying Torneko to seek help for his sleeping son. No official English localization supplied; GBA script is the prose/mechanics authority.'}
    additions=[('place.barinabo',['バリナボ','バリナボの村','バリナボ島'],'Barinabo','project_transliteration',['village_story_primary'],'Japanese island/village identity corroborated by publisher. English transliteration is a project choice, not a verified modern official localization.'),
        ('place.shrine_of_the_gods',['神々のほこら'],'Shrine of the Gods','project_place_translation',[],'Named northern shrine in the original script. The descriptive northern shrine is an alias in dialogue; no verified official English equivalent.'),
        ('lore.earth_god',['大地の神'],'Earth God','project_lore_translation',[],'This story\'s deity; do not identify with another Dragon Quest deity without evidence.'),
        ('lore.divine_path',['神の道'],'divine path','project_lore_translation',[],'Story description of the route beneath the sea. Distinct from the existing dungeon name 神々の道 / Path of the gods; no identity merger inferred.'),
        ('lore.gate_of_truth',['真実のトビラ'],'Gate of Truth','project_lore_translation',[],'Gate named in the shrine and related return dialogue; no verified official English equivalent.'),
        ('character.viola',['ヴィオラ'],'Viola','project_transliteration',[],'Chief Gamlan\'s daughter, named in a related return conversation. Project transliteration from the original; no official localization or other-character identity claimed.')]
    check(not any(i in terms for i,*_ in additions),'Village glossary identity already exists')
    for ident,jp,en,status,sources,notes in additions:
        t={'id':ident,'japanese':jp,'english':en,'status':status,'sources':sources,'notes':notes,'occurrences':[],'batch':'first-village'}
        glossary['terms'].append(t);terms[ident]=t
    pairs=[('トルネコ','torneko'),('ポポロ','enemy_tipper'),('ネネ','character.tessie'),('族長','role.village_chief'),('ガムラン','character.gamlan'),('ロサ','enemy_rosa'),('イネス','enemy_ines'),('パン','bread'),('旅の扉','interface.trap.022')]
    pairs += [(jp,ident) for ident,jps,*_ in additions for jp in jps]
    review=[]
    for e in c['entries']:
        e['english']=drafts[int(e['offset'],0)];e['references']=list(dict.fromkeys(ident for jp,ident in pairs if jp in e['japanese']))
        if '$t' in e['japanese']:e['references']+=['torneko','enemy_tipper']
        if '北のほこら' in e['japanese'] and 'place.shrine_of_the_gods' not in e['references']:e['references'].append('place.shrine_of_the_gods')
        e['notes']='Independent translation from the pinned Japanese GBA script. Full message fits the original three-line page; preserve event parameters, speaker identity, and shared operand ownership.'
        if e['japanese'].startswith('＊'):e['notes']+=' Anonymous speaker remains ??? until identified by the source.'
        if any(x['opcode'] in (0x2a,0x2c) for x in e['events']):e['notes']+=' Original Yes/No meaning and defaults retained.'
        if int(e['offset'],0) in (0x9cdf38,0x9cdfdc):e['notes']+=' Child playing house: light childish pronunciation adapts the Japanese baby talk.'
        if int(e['offset'],0)==0x9eb540:e['notes']+=' Original short sailor chant independently adapted; no borrowed song lyrics.'
        if int(e['offset'],0)==0x9ebf28:e['notes']+=' Child\'s familiar nickname for the dungeon traveller, not a prehistoric-person identity.'
        if e['group']=='chief' and 0x9d6998<=int(e['offset'],0)<=0x9d6bb0:e['notes']+=' Related return conversation; not claimed to occur before first departure.'
        for ident in e['references']:terms[ident]['occurrences'].append({'catalog':'translations/first-village.json','id':e['id']})
        review.append([e['id'],e['japanese'].replace('\n','<LF>'),e['english'].replace('\n','<LF>'),','.join(e['references']),e['notes']])
    validate_catalog(original,c)
    atomic_write(CATALOG,(json.dumps(c,ensure_ascii=False,indent=2)+'\n').encode())
    old=glossary['current_review']
    if not any(b['id']==old['id'] for b in glossary['batches']):glossary['batches'].append(old)
    glossary['current_review']={'id':'first-village','reviewed_on':'2026-09-11','status':'translated_pending_native_acceptance','scope':c['scope'],'source_rom_sha256':digest(original),'catalogs':{'translations/first-village.json':digest(CATALOG.read_bytes())},'new_terms':[a[0] for a in additions],'terminology_review':'translations/first-village-terminology-review.tsv','next_scope':'Continue the first dungeon journey and rest stops; later village story states remain separate.'}
    atomic_write(ROOT/'translations/glossary.json',(json.dumps(glossary,ensure_ascii=False,indent=2)+'\n').encode())
    buf=io.StringIO();w=csv.writer(buf,delimiter='\t',lineterminator='\n');w.writerow(['id','japanese','full_english','glossary_references','notes']);w.writerows(review)
    atomic_write(ROOT/'translations/first-village-terminology-review.tsv',buf.getvalue().encode())
    print(len(c['entries']),'prepared; glossary',len(terms))


if __name__=='__main__':prepare()
