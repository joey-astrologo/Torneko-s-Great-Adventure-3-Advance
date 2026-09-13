"""Accept only complete native evidence and exact owned prose changes."""
import argparse
import copy
import json
from pathlib import Path

from tools import build_prose_review as b
from tools.prose_review import REVIEW, REVISIONS, effective_catalog, save
from tools.build_first_label import ROOT, ORIGINAL_ROM, digest
from tools.translation_pipeline import check, load_json
from tools.verify_prose_review import GROUPS


def accept(published=False):
    original=ORIGINAL_ROM.read_bytes();baseline=b.BASELINE.read_bytes();data=b.ROM.read_bytes()
    plan=load_json(b.PLAN);report=load_json(b.OUTPUT/'english-build.json')
    review=load_json(REVIEW);revisions=load_json(REVISIONS)['entries']
    tested_path=b.OUTPUT/'verification/tested-allocation-plan.json'
    tested=load_json(tested_path)
    # Final glossary evidence/status changes only review metadata. The plan
    # actually used for native checks is retained; its payload/owner plan must
    # match the final one exactly, apart from that review-record hash.
    check({k:v for k,v in tested.items() if k!='review_sha256'}==
          {k:v for k,v in plan.items() if k!='review_sha256'}, 'Tested insertion plan changed')
    check(digest(data)==report['rom_sha256'] and digest(baseline)==plan['previous_sha256'], 'ROM hashes differ')
    check(digest(b.PLAN.read_bytes())==report['allocation_plan_sha256'], 'Final plan not built')
    check(digest(REVIEW.read_bytes())==plan['review_sha256'] and digest(REVISIONS.read_bytes())==plan['revisions_sha256'], 'Review inputs changed')
    # Revalidate current pinned catalogs, exact original text and final glossary.
    check(len(list(b.revisions(original)))==len(revisions)==len(plan['entries']), 'Incomplete revision ledger')
    prior=load_json(b.BASELINE.parent/'english-build.json')['ledger'];ledger=report['ledger']
    expected=bytearray(baseline);changed_words={};source_checks=0
    for row in plan['entries']:
        raw=bytes.fromhex(row['source_hex']);at=row['source_start']
        check(data[at:at+len(raw)]==original[at:at+len(raw)]==raw,'Japanese source overwritten')
        source_checks+=1
        if not row['changed_rom_text']:continue
        raw=bytes.fromhex(row['raw_hex']);at=row['offset']
        check(at%4==0 and plan['start']<=at<at+len(raw)<=plan['end_exclusive'],'Invalid new allocation')
        expected[at:at+len(raw)]=raw
        for old in row['previous_pointer_patches']:
            word=old['offset'];check(word not in changed_words,'Duplicate pointer owner')
            check(baseline[word:word+4]==bytes.fromhex(old['after']),'Old pointer changed')
            expected[word:word+4]=(at+0x08000000).to_bytes(4,'little')
            changed_words[word]=old
    check(bytes(expected)==data,'Whole ROM differs beyond explicitly owned prose edits')
    check(ledger['allocations']==prior['allocations']+plan['allocations'],'Allocation ownership changed')
    for a in prior['allocations']:
        at=a['offset'];end=at+a['bytes']
        check(data[at:end]==baseline[at:end],'Earlier allocation bytes changed: '+a['id'])
    by_word={p['offset']:p for p in ledger['patches']}
    check(len(by_word)==len(ledger['patches'])==len(prior['patches']),'Duplicate or unexpected original patch')
    for p in prior['patches']:
        current=by_word[p['offset']]
        if p['offset'] in changed_words:
            check(current['owner']==b.OWNER and current['supersedes']==p,'Lost previous pointer ownership')
        else:check(current==p,'Unrelated original-ROM patch changed')
    check(ledger['memory_reservations']==prior['memory_reservations'],'RAM ownership changed')
    check(not any(plan[k] for k in ('new_ram_reservations','save_changes','code_patches')),'Unexpected runtime change')
    # Only the two documented project-effect terms may differ in the glossary.
    glossary=load_json(ROOT/'translations/glossary.json');restored=copy.deepcopy(glossary)
    terminology=load_json(ROOT/'translations/prose-review/terminology-revisions.json')
    old_terms={c['before']['id']:c['before'] for c in terminology['changes']}
    new_terms={c['after']['id']:c['after'] for c in terminology['changes']}
    check(set(old_terms)=={'effect.001b712d','effect.001b73bb'},'Unexpected terminology revisions')
    for i,t in enumerate(glossary['terms']):
        if t['id'] in old_terms:
            check(t==new_terms[t['id']],'Terminology evidence differs')
            restored['terms'][i]=old_terms[t['id']]
    encoded=(json.dumps(restored,ensure_ascii=False,indent=2)+'\n').encode()
    check(digest(encoded)==review['glossary_sha256'],'Unrecorded glossary change')
    phases={};coverage=set()
    for phase,names in GROUPS.items():
        path=b.OUTPUT/'verification'/phase/'acceptance.json';r=load_json(path)
        wanted={x['id'] for x in revisions if x['catalog'] in names}
        check(set(r['reviewed_revision_ids'])==wanted and not coverage&wanted,'Incomplete/duplicate native phase')
        check(r['rom_sha256']==digest(data) and r['plan_sha256'] in
              (digest(tested_path.read_bytes()),digest(b.PLAN.read_bytes())), 'Native phase used another ROM/plan')
        coverage|=wanted
        phases[phase]={'revisions':len(wanted),'case_records':len(r['cases']),
                       'report':str(path.relative_to(ROOT)),'sha256':digest(path.read_bytes())}
    check(coverage=={r['id'] for r in revisions},'Missing revised reader coverage')
    regressions={}
    for phase in ('render','title','result'):
        path=b.OUTPUT/'verification'/phase/'acceptance.json';r=load_json(path)
        check(r['status']=='passed' and r['rom_sha256']==digest(data),'Regression evidence differs')
        check(r['user_files_unchanged'],'User save preservation failed')
        regressions[phase]={'report':str(path.relative_to(ROOT)),'sha256':digest(path.read_bytes())}
    result={'status':'passed','source_rom':str(ORIGINAL_ROM.relative_to(ROOT)),'source_sha256':digest(original),
        'output_rom':str(b.ROM.relative_to(ROOT)),'rom_sha256':digest(data),'baseline_sha256':digest(baseline),
        'catalogs':len(review['catalogs']),'bilingual_pairs_reviewed':sum(len(x['reviewed_indices']) for x in review['catalogs'].values()),
        'compact_displays_reviewed':review['display_review']['entries'],'revisions':len(revisions),
        'new_payloads':len(plan['allocations']),'pointer_supersessions':len(changed_words),
        'new_bytes_with_alignment':plan['new_bytes_with_padding'],'protected_source_checks':source_checks,
        'whole_rom_matches_owned_changes':True,'prior_allocations_and_other_patches_preserved':True,
        'no_code_graphics_font_ram_or_save_layout_changes':True,'series_entity_names_unchanged':True,
        'native_phases':phases,'regressions':regressions,'review_sha256':digest(REVIEW.read_bytes()),
        'revisions_sha256':digest(REVISIONS.read_bytes()),'plan_sha256':digest(b.PLAN.read_bytes()),
        'tested_plan_sha256':digest(tested_path.read_bytes()),'harness_sha256':digest(Path(__file__).read_bytes()),
        'scope':'Complete bounded prose review, controlled native reader/layout validation and stated natural regressions. Not complete game discovery, a full story playthrough, all choice outcomes, or independent mechanic verification.'}
    if published:
        receipt_path=ROOT/'build/torneko-3-english.json';receipt=load_json(receipt_path)
        check((ROOT/receipt['output_rom']).read_bytes()==data and receipt['rom_sha256']==digest(data),'Published ROM differs')
        check(receipt['validation']['bps_roundtrip_byte_identical'] and
              digest((ROOT/receipt['patch']).read_bytes())==receipt['patch_sha256'],'Patch receipt differs')
        result['published']={'receipt':str(receipt_path.relative_to(ROOT)),
                             'sha256':digest(receipt_path.read_bytes()),'bps_roundtrip_byte_identical':True}
    for name in review['catalogs']:
        check(load_json(b.OUTPUT/'effective'/f'{name}.json')==effective_catalog(name),'Effective export differs')
    save(b.OUTPUT/'acceptance.json',result)
    print('Accepted prose:',result['bilingual_pairs_reviewed'],'reviewed;',len(revisions),'revisions;',digest(data),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--published',action='store_true')
    accept(p.parse_args().published)
