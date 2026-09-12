"""Reuse our authored prose only for exact Japanese ordinary-story duplicates."""
import csv
import io
import json
from collections import defaultdict
from tools.build_story_completion import DRAFTS,CATALOG,source_entry,encode,prepare
from tools.build_first_label import ROOT,ORIGINAL_ROM,digest
from tools.translation_pipeline import load_json,atomic_write


def main():
    original=ORIGINAL_ROM.read_bytes();master={int(e['offset'],0):e for e in load_json(ROOT/'translations/master.json')['entries']}
    with DRAFTS.open() as f:r=csv.DictReader(f,delimiter='\t');fields=r.fieldnames;rows=list(r)
    seen={int(r['offset'],16) for r in rows};matches=defaultdict(list)
    for name in ('opening-story','first-village','early-journey','story-completion'):
        path=ROOT/f'translations/{name}.json'
        for e in load_json(path)['entries']:
            if e.get('english') and e.get('display') is None:matches[e['japanese']].append((name,e))
    additions=[]
    for lead in load_json(ROOT/'build/completion/remaining.json')['entries']:
        at=int(lead['offset'],0);found=matches.get(lead['japanese'],[])
        if at in seen or lead['group']!='story_review' or not found or len({e['english'] for _,e in found})!=1:continue
        try:
            entry=source_entry(original,master,at,'shared_repeats')
            if any(ev['opcode'] in (0x96,0x97,0x98) for ev in entry['events']):continue
            name,prior=found[0];entry['english']=prior['english'];encode(entry,original)
        except ValueError:continue
        note=f"Exact Japanese match to our independent translation in translations/{name}.json, {prior['id']}. No external patch text used."
        rows.append({'offset':f'{at:08X}','chapter':'shared_repeats','english':prior['english'].replace('\n','\\n'),'notes':note})
        additions.append({'offset':hex(at),'prior_catalog':name,'prior_id':prior['id'],'english':prior['english']});seen.add(at)
    out=io.StringIO();w=csv.DictWriter(out,fieldnames=fields,delimiter='\t',lineterminator='\n');w.writeheader();w.writerows(rows)
    atomic_write(DRAFTS,out.getvalue().encode())
    folder=ROOT/'build/completion/reuse';folder.mkdir(parents=True,exist_ok=True)
    report={'base_sha256':digest(original),'rule':'Exact Japanese, one unambiguous authored English, supported ordinary native owner, successful control/page encoding. Choice prefixes and unknown owners excluded.','additions':additions}
    atomic_write(folder/f'{digest(DRAFTS.read_bytes())[:12]}.json',(json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode())
    print('Added',len(additions),'exact Japanese repeats',flush=True);prepare()


if __name__=='__main__':main()
