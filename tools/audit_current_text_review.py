"""Pin the remaining language review without inventing runtime ownership."""
import json
import re
from collections import defaultdict
from pathlib import Path
from tools.audit_text_coverage import translated_ids
from tools.audit_scene_resources import BASELINE
from tools.build_first_label import ROOT,ORIGINAL_ROM,digest
from tools.translation_pipeline import check,load_json,atomic_write

OUTPUT=ROOT/'build/completion/current-text-review.json'

def audit():
    original=ORIGINAL_ROM.read_bytes();current=BASELINE.read_bytes()
    master=load_json(ROOT/'translations/master.json')['entries'];done,families=translated_ids(master)
    retained=load_json(ROOT/'build/completion/retained-resources.json')
    check(retained['verified_rom_sha256']==digest(current),'Retained proof is stale')
    retained_ids={e['master_id'] for e in retained['entries'] if e['master_id']}
    remaining=[e for e in master if e['id'] not in done|retained_ids]
    drafts=load_json(ROOT/'translations/unowned-text-review.json')['entries']
    # Review entries have their own IDs and retain the master identity explicitly.
    draft_ids={e['master_id'] for e in drafts}
    check(len(draft_ids)==31 and draft_ids<={e['id'] for e in remaining},'Unowned review coverage differs')
    originals={e['id']:e for e in master}
    for e in drafts:
        source=originals[e['master_id']]
        check(all(e[k]==source[k] for k in ('source_hex','source_tokens','japanese')) and
              int(e['offset'],0)==int(source['offset'],0),'Unowned draft source changed')
        check(not e['verified_pointer_owners'] and e['insertion_status']=='not_inserted_reader_unconfirmed','Unowned draft gained unverified insertion ownership')
    check(sum(isinstance(e['english'],str) and bool(e['english']) for e in drafts)==30 and
          [e['master_id'] for e in drafts if e['english'] is None]==['jp_001b551c'],'Unowned draft language count differs')
    by_raw=defaultdict(list)
    for e in master:by_raw[e['source_hex']].append(e)
    rows=[]
    for e in remaining:
        at=int(e['offset'],0);raw=bytes.fromhex(e['source_hex'])
        check(original[at:at+len(raw)]==current[at:at+len(raw)]==raw,'Unowned source bytes changed')
        for word in e['pointer_candidates']:
            p=int(word,0);check(current[p:p+4]==original[p:p+4],'Unowned candidate pointer changed')
        if e['id'] in draft_ids:role='japanese_draft_awaiting_reader_context'
        elif e['japanese'].isascii():
            check(raw==e['japanese'].encode('ascii')+b'\0','Original ASCII text bytes differ')
            role='original_ascii_awaiting_reader_context'
        else:role='other_unclassified_resource'
        matches=[x['id'] for x in by_raw[e['source_hex']] if int(x['offset'],0)<0xCB1B64 and x['id']!=e['id']]
        rows.append({'master_id':e['id'],'offset':e['offset'],'end_exclusive':hex(at+len(raw)),
            'source_hex':raw.hex(),'japanese':e['japanese'],'role':role,
            'source_unchanged':True,'candidate_pointer_words':e['pointer_candidates'],
            'exact_earlier_inventory_matches':matches,'runtime_owner_verified':False})
    terms=load_json(ROOT/'translations/glossary.json')['terms']
    retired=[(old,t['english']) for t in terms for old in t.get('superseded_project_drafts',[])]
    paths=[ROOT/'translations/catalog.json']+[ROOT/'translations'/f'{name}.json' for name in families if (ROOT/'translations'/f'{name}.json').is_file()]
    scanned=0;internal=[];hashes={}
    for p in paths:
        hashes[str(p.relative_to(ROOT))]=digest(p.read_bytes())
        for e in load_json(p).get('entries',[]):
            for field in ('english','display'):
                text=e.get(field)
                if not isinstance(text,str):continue
                scanned+=1
                for old,new in retired:
                    check(not re.search(r'(?<![A-Za-z])'+re.escape(old)+r'(?![A-Za-z])',text,re.I),f'Retired term {old}: {p.name}/{e["id"]}/{field}')
                for match in re.finditer(r'\b(?:Popolo|Nene|wands?)\b',text,re.I):
                    check(p.name=='enemies.json' and e['id']=='enemy.trait.198' and e['source_hex']=='706f706f6c6f0d4e6f2e31333700' and text in ('popolo\nNo.137','popolo No.137'),'Unreviewed legacy-name/staff wording')
                    internal.append({'catalog':p.name,'id':e['id'],'field':field,'reason':'Explicitly retained original internal diagnostic; species name uses Tipper.'})
    counts={role:sum(e['role']==role for e in rows) for role in ('japanese_draft_awaiting_reader_context','original_ascii_awaiting_reader_context','other_unclassified_resource')}
    check(counts=={'japanese_draft_awaiting_reader_context':31,'original_ascii_awaiting_reader_context':42,'other_unclassified_resource':6},'Open review categories differ')
    result={'status':'current_text_review_pinned','source_sha256':digest(original),'verified_rom_sha256':digest(current),
        'harness_sha256':digest(Path(__file__).read_bytes()),'master_sha256':digest((ROOT/'translations/master.json').read_bytes()),
        'retained_report_sha256':digest((ROOT/'build/completion/retained-resources.json').read_bytes()),
        'glossary_sha256':digest((ROOT/'translations/glossary.json').read_bytes()),
        'unowned_review_sha256':digest((ROOT/'translations/unowned-text-review.json').read_bytes()),
        'authored_build_catalog_sources':len(done),'retained_reader_confirmed_sources':len(retained_ids),
        'unclassified_sources':len(rows),'unclassified_categories':counts,'entries':rows,
        'terminology':{'catalog_sha256':hashes,'english_display_fields_checked':scanned,'retired_project_terms_checked':retired,
            'documented_original_diagnostic_exceptions':internal,'scope':'Consistency with recorded retired drafts and selected legacy protagonist/staff spellings. This is not a fresh verification of every external terminology reference.'},
        'scope':'All unclassified source/candidate-pointer bytes remain intact. Thirty Japanese drafts and one unresolved line are separate from build catalogs. Forty-two original ASCII strings need no newly authored English, but their runtime ownership remains unverified. Six other resources remain technically unclassified. Exact duplicate text does not establish shared pointers, reachability or free space. Graphics work is deferred by user.'}
    atomic_write(OUTPUT,(json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode());print(counts,';',scanned,'English/display fields checked',flush=True)

if __name__=='__main__':audit()
