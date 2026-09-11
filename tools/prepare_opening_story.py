"""Prepare independently authored opening prose and scoped terminology review."""
import csv
import io
import json
from tools.build_opening_story import OUTPUT,CATALOG,extract_catalog,validate_catalog
from tools.build_first_label import ORIGINAL_ROM,ROOT,digest
from tools.translation_pipeline import load_json,atomic_write,check

DRAFTS={
0x86F4C8: 'Yes', 0x86F4C0: 'No',
0x91BB3C: 'Torneko later opened a shop of his own.\nHe lived peacefully with his wife Tessie\nand their only son, Tipper.',
0x91BACC: 'Several years passed. Then one day,\na chance encounter led Torneko\nto a mysterious cave...',
0x91BA54: 'Exploring one cave after another,\nTorneko fought monsters and brought\nfresh happiness to the people.',
0x91B9E8: 'At last, the ever-busy Torneko decided\nto take a break from work\nand travel with his family.',
0x91B9C8: '\nAnd so began a very, very long journey.',
0x91B970: "Now they are far away, out at sea.\nToday is Tipper's twelfth birthday.",
0x91B90C: '???: "There, the candles are lit.\nShall we call Tipper in now, dear?"',
0x91B8C8: '???: "Tipper! Come along!\nYour cake is ready!"',
0xC2F660: 'Tessie: "Tipper! What are you doing?\nCome along, now!"',
0xC2F618: 'Tessie: "Come here, Tipper.\nBlow out the candles!"',
0xC2F5B8: 'Tessie: "What is it, Tipper?\nYou seem so glum,\nand on your birthday, too."',
0xC2F560: 'Tessie: "Are you still worried\nabout that scary dream\nyou had last night?"',
0xC2F524: 'Tipper: "...Yes.\nIt was such a strange dream."',
0xC2F4E4: 'Tipper: "Do you want to hear\nabout my scary dream too, Dad?"',
0xC2F4A8: 'Tipper: "Aww!\nPlease, Dad! Listen to it!"',
0xC2F440: 'Tipper: "Well... I was standing\nin this big, open place. Suddenly,\nthe sky went dark."',
0xC2F408: 'Tipper: "Then there was this\nreally loud clap of thunder..."',
0xC2F3EC: 'Tipper: "...H-huh?!"',
0xC2F398: 'Tessie: "Eek! T-Tipper...\nWas it anything like\nwhat just happened...?"',
0xC2F37C: 'Tipper: "Aaaaaaah!"',
0x9FDED8: '???: "...Ah!\nYou are awake at last!"',
0x9FDE8C: '???: "I am Gamlan,\nchief of this village.\nWhat a terrible storm that was."',
0x9FDE60: 'Chief: "...Ah, you should\nkeep still for now."',
0x9FDE10: 'Chief: "You washed up\non our village beach\nin the middle of that storm."',
0x9FDDC0: 'Chief: "It is still before dawn.\nStay where you are\nand get some rest."',
0xA0025C: '???: "Hey! Looks like that\nold guy is awake!"',
0xA00364: '???: "Hey!\nStop peeking in there!"',
0xA00320: '???: "Have you even finished\nthe work Grandfather\nasked you to do?"',
0xA00208: '???: "Sheesh, Sis. Always nagging!\nAll right, all right, I will!\nHappy to help!"',
0x91BDC4: 'And so Torneko and his family\nwashed ashore near a village\nwhose name they did not know.',
0x91BD6C: 'Torneko, Tessie and Tipper\nslept on and on...\nThen dawn broke.',
0x9C1D2C: 'Tessie: "Oh! You are awake too!\nThank goodness..."',
0x9C1CC8: 'Tessie: "What on earth happened?\nIt was all so sudden,\nI can hardly remember..."',
0x9C1C80: 'Tessie: "But Tipper still\nhas not woken up.\nI am so worried..."',
0x9C1DE4: 'Tessie: "It is strange...\nNone of us seems hurt at all.\nNot even Tipper."',
0x9C1DA4: 'Tessie: "I will stay here\nand watch over Tipper\nuntil he wakes up."',
0x9C1EB0: 'Tipper seems to be sleeping peacefully...',
0x9C1FBC: 'Tessie: "Then get some rest.\nGood night, dear..."',
0x9C2000: 'Tessie: "All right. Just let me know\nwhenever you feel like resting."',
0x9C2044: 'Tessie: "If this is a dream,\nperhaps we could wake up.\nWould you like some more rest too?"',
0x9C209C: 'Tessie: "I feel so tired...\nPerhaps I should try\nsleeping for a little while."',
0x9C20F8: 'Tessie: "Tell me, dear...\nThis could not all be\na dream, could it?"',
0x9C213C: 'Tessie: "Oh, you are back!\nTipper is still asleep.\nWhat could be wrong with him?"',
}


def prepare():
    check(not CATALOG.exists(),'Do not overwrite authored opening catalog')
    original=ORIGINAL_ROM.read_bytes();catalog=extract_catalog(original);glossary=load_json(ROOT/'translations/glossary.json');terms={t['id']:t for t in glossary['terms']}
    source_id='opening_tessie';glossary['sources'][source_id]={'url':'https://dragon-quest.org/wiki/Tessie_Taloon','reference_game':'Dragon Quest IV: Chapters of the Chosen (modern English)','reviewed_on':'2026-09-11','evidence':'Secondary explicit ネネ/Tessie pairing, Torneko spouse identity. Older Neta/Nina names distinguished. No dialogue or accent copied.'}
    additions=[{'id':'character.tessie','japanese':['ネネ'],'english':'Tessie','status':'modern_official_name_secondary_evidence','sources':[source_id],'notes':'Modern DQ IV name of Torneko\'s wife. Story prose is independently translated in a warm conversational voice; no borrowed accent or dialogue.','occurrences':[],'batch':'opening-story'},
        {'id':'character.gamlan','japanese':['ガムラン'],'english':'Gamlan','status':'torneko_specific_project_transliteration','sources':[],'notes':'Project transliteration from the original opening self-introduction. No established modern official English name verified.','occurrences':[],'batch':'opening-story'},
        {'id':'role.village_chief','japanese':['族長'],'english':'Chief','status':'project_role_translation','sources':[],'notes':'Speaker title of Gamlan in this section; generic role translation, not a personal-name alias.','occurrences':[],'batch':'opening-story'},
        *[{'id':'ui.event_'+name.lower(),'japanese':[jp],'english':name,'status':'project_ui_translation','sources':[],'notes':'Shared event Yes/No label; retain original return value and initial-selection behavior.','occurrences':[],'batch':'opening-story'} for jp,name in [('はい','Yes'),('いいえ','No')]]
    check(not any(t['id'] in terms for t in additions),'New opening identity already exists')
    for t in additions:glossary['terms'].append(t);terms[t['id']]=t
    reviews=[]
    for e in catalog['entries']:
        at=int(e['offset'],0)
        e['english']=next(x['english'] for x in load_json(ROOT/'translations/catalog.json')['entries'] if x['id']==e['reuse']) if e['reuse'] else DRAFTS[at]
        refs=[]
        for jp,ident in [('トルネコ','torneko'),('ポポロ','enemy_tipper'),('ネネ','character.tessie'),('ガムラン','character.gamlan'),('族長','role.village_chief')]:
            if jp in e['japanese']:refs.append(ident)
        if e['layout']=='choice':refs.append('ui.event_'+e['english'].lower())
        e['references']=refs
        e['notes']='Existing first narration and allocation reused without edits.' if e['reuse'] else 'Independent translation of the Japanese event source. Manual line breaks preserve sentence rhythm; native wrapping/centering and continuation tabs are measured separately.'
        if e['japanese'].startswith('＊'):e['notes']+=' The original anonymous speaker marker remains anonymous as ???; no identity is revealed early.'
        if at==0xA00208:e['notes']+=' Boy addresses his elder sister; the final cheerful words are sarcastic in context.'
        if at==0x9C1EB0:e['notes']+=' One shared observation across nine original event operands; no extra sleep mechanics inferred.'
        if any(x['opcode']==0x2C for x in e['events']):e['notes']+=' Preserve the original Yes/No command parameters and branch behavior.'
        for ident in refs:terms[ident]['occurrences'].append({'catalog':'translations/opening-story.json','id':e['id']})
        reviews.append([e['id'],e['japanese'].replace('\n','<LF>'),e['english'].replace('\n','<LF>'),','.join(refs),e['notes']])
    validate_catalog(original,catalog);atomic_write(CATALOG,(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n').encode())
    old=glossary['current_review']
    if not any(b['id']==old['id'] for b in glossary['batches']):glossary['batches'].append(old)
    glossary['current_review']={'id':'opening-story','reviewed_on':'2026-09-11','status':'translated_pending_native_acceptance','scope':catalog['scope'],'source_rom_sha256':digest(original),'catalogs':{'translations/opening-story.json':digest(CATALOG.read_bytes())},'new_terms':[t['id'] for t in additions],'terminology_review':'translations/opening-story-terminology-review.tsv','next_scope':'First-village story progression and NPC conversations; preserve coherent scenes and validate event ownership.'}
    atomic_write(ROOT/'translations/glossary.json',(json.dumps(glossary,ensure_ascii=False,indent=2)+'\n').encode())
    s=io.StringIO();w=csv.writer(s,delimiter='\t',lineterminator='\n');w.writerow(['id','japanese','full_english','glossary_references','notes']);w.writerows(reviews)
    atomic_write(ROOT/'translations/opening-story-terminology-review.tsv',s.getvalue().encode())
    print('Prepared',len(catalog['entries']),'opening sources')

if __name__=='__main__':prepare()
