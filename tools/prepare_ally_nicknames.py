"""Create reviewed nickname rows; preserve full names apart from short displays."""
import csv
import json
from tools.build_ally_nicknames import CATALOG, OUTPUT, extract_catalog, validate_catalog
from tools.build_first_label import ORIGINAL_ROM, ROOT, digest
from tools.translation_pipeline import atomic_write, check, load_json

JP_NAMES = 'https://w.atwiki.jp/dq5mon/pages/19.html'
EN_NAMES = 'https://gamefaqs.gamespot.com/ds/942423-dragon-quest-v-hand-of-the-heavenly-bride/faqs/59379'
REFERENCES = {
    'nickname_dq5_japanese': {'url':JP_NAMES,'reference_game':'Dragon Quest V, Japanese recruitment names',
        'evidence':'Secondary Japanese table. Compare the exact species, kana-normalized nickname and recruitment ordinal; not evidence of Torneko character identity.'},
    'nickname_dq5_english': {'url':EN_NAMES,'reference_game':'Dragon Quest V: Hand of the Heavenly Bride (DS)',
        'evidence':'Secondary English recruitment guide. Names and ordered defaults only; no mechanics or description prose imported.'},
    'nickname_healie': {'url':'https://dragon-quest.org/wiki/Healie','reference_game':'Dragon Quest IV/VI/VIII modern English',
        'evidence':'Secondary explicit ホイミン / Healie pair. Chosen as a shared healslime nickname; does not identify this recruit as the story character. DQ V uses a different first default.'},
}
# Exact matching Japanese nickname + species; ordinal correspondence is an
# inference across the two language references, not a bilingual game capture.
MATCHES = {3:('Merc',1),5:('Sloth',1),15:('Mason',1),19:('Curetis',1),21:('Gootrude',1),
    38:('Hork',1),52:('Gumdrops',1),59:('Thamthon',1),68:('Vlad',1),80:('Roborg',2),
    92:('Hoody',1),105:('Brontes',1),156:('Kingoo',1),196:('Goodian',1)}
EXISTING = {0:'torneko',191:'enemy_rosa',192:'enemy_ines',198:'placeholder.paulo'}


def prepare():
    original = ORIGINAL_ROM.read_bytes(); catalog = extract_catalog(original)
    with (ROOT/'translations/ally-nickname-drafts.tsv').open() as file:
        drafts = list(csv.DictReader(file,delimiter='\t'))
    check(len(drafts)==200 and [int(d['row']) for d in drafts]==list(range(200)), 'Incomplete nickname drafts')
    glossary = load_json(ROOT/'translations/glossary.json'); terms = {t['id']:t for t in glossary['terms']}
    check(not CATALOG.exists(), 'Catalog already exists; edit it directly instead of replacing authored work')
    for ident, source in REFERENCES.items():
        glossary['sources'][ident] = {**source,'reviewed_on':'2026-09-11'}
    new_terms=[]; review=[]
    for e,d in zip(catalog['entries'],drafts):
        row=e['row']; e['english']=d['full_english']; e['display']=d['display'] if d['display']!=d['full_english'] else None
        status='project_nickname_adaptation'; refs=[]
        note='Independent adaptation of the original personal nickname, preserving phonetic or wordplay cues; not an official species-name replacement.'
        if row in MATCHES:
            full,ordinal=MATCHES[row]; check(e['english']==full,'Reference name differs')
            status='modern_official_nickname_secondary_inferred_ordinal'; refs=['nickname_dq5_japanese','nickname_dq5_english']
            note=f'Exact Japanese nickname/species matches DQ V recruit number {ordinal}. English counterpart inferred from the same ordinal in the DS guide; secondary evidence, not a direct bilingual capture. Other DQ V defaults are not substituted merely because the species matches.'
        elif row==18:
            status='modern_shared_nickname_secondary_editorial_reuse'; refs=['nickname_healie']
            note='Use the explicit modern ホイミン/Healie pairing as a shared nickname. DQ V first-recruit naming differs; no claim this Torneko recruit is the IV/VI character.'
        if row in EXISTING:
            term_id=EXISTING[row]; note='Retains the existing scoped glossary identity. '+('Source is パウロ, a test-style placeholder; do not replace with the separate ポポロ/Tipper identity.' if row==198 else 'This table row is not proof of ordinary monster recruitment.')
        else:
            term_id=f'ally.nickname.source-{int(e["offset"],0):08x}'
            if term_id not in terms:
                term={'id':term_id,'japanese':[e['japanese']],'english':e['english'],'status':status,'sources':refs,
                    'notes':note,'superseded_project_drafts':[],'occurrences':[],'batch':'ally-nicknames'}
                glossary['terms'].append(term); terms[term_id]=term; new_terms.append(term_id)
        check(terms[term_id]['english']==e['english'],'Shared glossary identity differs')
        terms[term_id]['occurrences'].append({'catalog':'translations/ally-nicknames.json','id':e['id']})
        if e['display']:
            note+=f' Full name retained as {e["english"]}; {e["display"]} is an explicit project short display for the five-character stored field, not another official localization.'
        note+=' Duplicate recruits retain their numeric suffix; a five-letter base loses its last letter before adding the digit.'
        if row in range(186,191) or row in (198,199):note+=' Reserved/boss/test-style row: natural reachability unverified.'
        e['notes']=note; e['references']=[term_id]
        review.append([e['id'],e['japanese'],e['species_japanese'],e['english'],e['display'] or '',term_id,terms[term_id]['status'],','.join(refs),note])
    validate_catalog(original,catalog)
    atomic_write(CATALOG,(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n').encode())
    previous=glossary['current_review']
    if not any(b['id']==previous['id'] for b in glossary['batches']):glossary['batches'].append(previous)
    glossary['current_review']={'id':'ally-nicknames','reviewed_on':'2026-09-11','status':'translated_pending_native_acceptance',
        'scope':'200 default-name rows / 198 sources; preserve five-character field and full/reference names separately from short displays.',
        'source_rom_sha256':digest(original),'catalogs':{'translations/ally-nicknames.json':digest(CATALOG.read_bytes())},
        'new_terms':new_terms,'terminology_review':'translations/ally-nickname-terminology-review.tsv',
        'preservation':'All prior term identities, English, confidence, notes and references retained. Four existing identities gain nickname occurrences; short displays are local catalog choices.',
        'next_scope':'Remaining story/event translation; natural recruitment/renaming and later nickname consumers remain gameplay coverage.'}
    atomic_write(ROOT/'translations/glossary.json',(json.dumps(glossary,ensure_ascii=False,indent=2)+'\n').encode())
    import io
    stream=io.StringIO(); writer=csv.writer(stream,delimiter='\t',lineterminator='\n')
    writer.writerow(['id','japanese','species_japanese','full_english','display','glossary_references','status','source_ids','notes']);writer.writerows(review)
    atomic_write(ROOT/'translations/ally-nickname-terminology-review.tsv',stream.getvalue().encode())
    print('Prepared',len(review),'nickname rows;',len(new_terms),'new scoped glossary entries')


if __name__=='__main__':prepare()
