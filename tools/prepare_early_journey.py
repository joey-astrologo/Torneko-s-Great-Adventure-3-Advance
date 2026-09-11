"""One-time import of independent journey drafts and scoped terminology review."""
import csv
import io
import json
from tools.build_early_journey import CATALOG,OUTPUT,extract_catalog,validate_catalog
from tools.build_first_label import ORIGINAL_ROM,ROOT,digest
from tools.translation_pipeline import load_json,check,atomic_write


def prepare():
    check(not CATALOG.exists(),'Do not overwrite authored journey catalog')
    original=ORIGINAL_ROM.read_bytes();c=extract_catalog(original)
    with (ROOT/'translations/early-journey-drafts.tsv').open() as f:rows=list(csv.DictReader(f,delimiter='\t'))
    drafts={int(r['offset'],16):r['english'].replace('\\n','\n') for r in rows}
    check(len(rows)==len(drafts)==len(c['entries']) and set(drafts)=={int(e['offset'],0) for e in c['entries']},'Incomplete/duplicate journey drafts')
    g=load_json(ROOT/'translations/glossary.json');terms={t['id']:t for t in g['terms']};new=[]
    sources={
        'journey_story_primary':('https://www.spike-chunsoft.co.jp/pages/games/torneco3/story03.html','Torneko 3 Japanese publisher synopsis','Primary Japanese route and location identities: 海竜島, グレートバレイナ島, コスタリベラ and グレートバレイナ城. No official English supplied.'),
        'journey_conklave_secondary':('https://dragon-quest.org/wiki/Conklave','Dragon Quest Monsters: Joker 2','Secondary Japanese プチット族 / modern English Conklave group match. Applying the group name to this GBA village is a project inference, not an official location name.'),
        'journey_gracos_secondary':('https://dragon-quest.org/wiki/Gracos','Dragon Quest VI / VII modern localizations','Secondary exact グラコス / Gracos stem evidence. Madame Gracos is a distinct Torneko character; no identity merger with a main-series boss.'),
        'journey_medal_king_secondary':('https://dragon-quest.org/w/index.php?title=Medal_King','Dragon Quest series','Secondary recurring メダル王 role evidence. Modern individual kings have distinct names; no evidence identifies this Torneko king as Minikin, Dominicus or another named king.')}
    for key,(url,game,evidence) in sources.items():g['sources'][key]={'url':url,'reference_game':game,'reviewed_on':'2026-09-11','evidence':evidence}
    def add(ident,jp,en,status='project_translation',sources=(),notes='Independent Torneko 3 wording; no verified official English name.'):
        check(ident not in terms,'Duplicate glossary identity')
        t={'id':ident,'japanese':jp,'english':en,'status':status,'sources':list(sources),'notes':notes,'occurrences':[],'batch':'early-journey'}
        g['terms'].append(t);terms[ident]=t;new.append(ident)
    reuse={0x873000:'interface.dungeon.006',0x8730C8:'place.shrine_of_the_gods',0x873114:'place.barinabo',0x8731C0:'place.barinabo'}
    place_terms={}
    for e in c['entries']:
        at=int(e['offset'],0);e['english']=drafts[at]
        if e['layout']!='place':continue
        ident=reuse.get(at,f'place.journey.{at:08x}');place_terms[at]=ident
        if at in reuse:continue
        src=[];note='Project place/UI label translated from the original GBA table. Full label fits the existing 30-byte selection substitution; no abbreviation. No verified official English location name.'
        if at in (0x8730D8,0x8730F8,0x87310C,0x873120,0x873188):src=['journey_story_primary'];note+=' Publisher corroborates the Japanese identity only. Great Baleina and Costa Libera are project transliterations.'
        if at==0x873134:src=['journey_conklave_secondary'];note+=' Conklave stem is an inference from the modern localized プチット族 group; the village name is project wording.'
        if at==0x87315C:src=['journey_gracos_secondary'];note+=' Gracos stem follows modern secondary evidence. Madame Gracos remains a distinct Torneko NPC.'
        if at==0x8731B0:src=['journey_medal_king_secondary'];note+=' Generic Medal King role; do not import another king\'s personal name.'
        if at in (0x872FEC,0x872FF4):note+=' Administrative table row, not asserted to be a reachable place.'
        add(ident,[e['japanese']],e['english'],'project_place_translation',src,note)
    add('lore.star_of_the_gods',['神々の星'],'Star of the Gods','project_lore_translation')
    add('lore.sea_dragon',['海竜さま'],'Sea Dragon','project_lore_translation',notes='Story deity addressed by the residents; do not merge with a monster species. Sea Dragon Isle stem already established in the dungeon-name catalog.')
    add('lore.sea_dragon_flame',['海竜の聖火','海竜さまの聖火','聖なる炎'],'sacred flame','project_lore_translation',notes='This story\'s flame and related light. Independently translated from the GBA scenes, with no imported spell identity or mechanics.')
    add('character.inatts',['イナッツ'],'Inatts','project_transliteration',notes='Monster elder\'s assistant named by the GBA source. Project transliteration; no verified official English identity.')
    add('role.monster_elder',['モンスターじいさん'],'monster elder','project_role_translation',notes='Descriptive Torneko role. No evidence equates him with a named monster recruiter from another title.')
    add('role.medal_king',['メダル王'],'Medal King','project_role_translation',['journey_medal_king_secondary'],'Generic recurring role retained. This character is not identified as Minikin, Dominicus or another named king.')
    add('interface.journey.destination',['行き先'],'Destination','project_ui_translation',notes='Full UI term. Native heading window is 32px; Destination measures 53px, so the displayed Go to (26px) is a project short form.')
    ids=['torneko','enemy_tipper','enemy_rosa','enemy_ines','enemy.slime','series_zoom','combined_item_116',
         'combined_item_040','combined_item_045','combined_item_083','combined_item_194','combined_item_247',
         'combined_item_249','combined_item_292','interface.dungeon.001','interface.dungeon.002',
         'interface.dungeon.003','interface.dungeon.004','interface.dungeon.005','interface.dungeon.023',
         'interface.dungeon.013','interface.trap.011','place.barinabo','lore.gate_of_truth','character.viola']+new
    pairs=[(jp.replace('\\u3000','\u3000'),ident) for ident in ids for jp in terms[ident]['japanese']]
    review=[]
    for e in c['entries']:
        at=int(e['offset'],0)
        e['references']=list(dict.fromkeys(ident for jp,ident in pairs if jp in e['japanese']))
        if e['layout']=='place' and place_terms[at] not in e['references']:e['references'].append(place_terms[at])
        if '$t' in e['japanese']:e['references']+=['torneko','enemy_tipper']
        e['references']=list(dict.fromkeys(e['references']))
        e['notes']='Independent translation from the pinned Japanese GBA source. Preserve mechanics, command parameters and shared pointer ownership.'
        if e['japanese'].startswith('＊'):e['notes']+=' Anonymous speaker remains ???; do not reveal a later identity.'
        if e['layout']=='place':e['notes']+=' Complete project label fits the native 29-byte payload and font 0; original coordinates and record index remain unchanged.'
        if e['layout']=='choice':e['notes']+=' Original six-topic order and return ordinals retained across all four prompt lists.'
        if e['layout']=='place_prompt':
            e['references']=['series_zoom'];e['notes']+=' Existing $m0 substitution receives the native bounded place-name copy; original question semantics retained.'
        if e['layout']=='place_heading':
            e['display']='Go to';e['notes']+=' Full Destination measures 53px in font 0; use Go to (26px) in the native 32px heading window. No window/code expansion.'
        if any(x['opcode'] in (0x2a,0x2c) for x in e['events']):e['notes']+=' Original Yes/No question meaning and parameters retained.'
        if e['group'] in ('shrine_depths','advice_and_undersea_day','undersea_night','temple','mountain_rest'):e['notes']+=' Scope includes related return/later protagonist states; not all messages belong to the first visit.'
        if at==0xB93CF0:e['notes']+=' The extinguished flame is the suspected cause of the evil blocking progress, not asserted as confirmed.'
        if at in (0xBA8AB0,0xBA8B5C):e['notes']+=' Retain each sibling\'s stated timing separately: over ten years ago versus just after their birth.'
        for ident in e['references']:terms[ident]['occurrences'].append({'catalog':'translations/early-journey.json','id':e['id']})
        review.append([e['id'],e['japanese'].replace('\n','<LF>'),e['english'].replace('\n','<LF>'),','.join(e['references']),e['notes']])
    validate_catalog(original,c);atomic_write(CATALOG,(json.dumps(c,ensure_ascii=False,indent=2)+'\n').encode())
    old=g['current_review']
    if not any(b['id']==old['id'] for b in g['batches']):g['batches'].append(old)
    g['current_review']={'id':'early-journey','reviewed_on':'2026-09-11','status':'translated_pending_native_acceptance','scope':c['scope'],'source_rom_sha256':digest(original),'catalogs':{'translations/early-journey.json':digest(CATALOG.read_bytes())},'new_terms':new,'terminology_review':'translations/early-journey-terminology-review.tsv','next_scope':'Sea Dragon Lighthouse story and adjoining services; natural rest-stop outcomes remain on the backlog.'}
    atomic_write(ROOT/'translations/glossary.json',(json.dumps(g,ensure_ascii=False,indent=2)+'\n').encode())
    buf=io.StringIO();w=csv.writer(buf,delimiter='\t',lineterminator='\n');w.writerow(['id','japanese','full_english','glossary_references','notes']);w.writerows(review)
    atomic_write(ROOT/'translations/early-journey-terminology-review.tsv',buf.getvalue().encode())
    print(len(c['entries']),'prepared;',len(new),'new terms;',len(terms),'total glossary terms')


if __name__=='__main__':prepare()
