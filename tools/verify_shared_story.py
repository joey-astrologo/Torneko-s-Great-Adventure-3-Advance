"""Apply the native story/menu harness to all shared event sources."""
import argparse
from pathlib import Path
from tools import build_shared_story as b
from tools import build_story_special as prior
from tools import verify_story_completion as v
from tools.build_first_label import ORIGINAL_ROM,digest
from tools.translation_pipeline import load_json,check,atomic_write

v.OUTPUT=b.OUTPUT
v.CATALOG=b.OUTPUT/'catalog.json'
v.BASELINE=prior.OUTPUT/'torneko3-story-special-english.gba'


def summarize():
    import json
    original=ORIGINAL_ROM.read_bytes();expected=v.expected_cases();catalog=load_json(v.CATALOG);prompts={ev['prompt_command_offset'] for e in catalog['entries'] for ev in e['events'] if ev['opcode']==0x98};proofs={};baseline=v.BASELINE.read_bytes()
    prior_ledger=load_json(prior.OUTPUT/'english-build.json')['ledger'];end=max(a['offset']+a['bytes'] for a in prior_ledger['allocations'])
    for variant in ('english','japanese','baseline'):
        path=b.OUTPUT/'verification'/variant/'verification.json';r=load_json(path);data=baseline if variant=='baseline' else (b.OUTPUT/f'torneko3-story-completion-{variant}.gba').read_bytes()
        check(r['rom_sha256']==digest(data) and r['source_sha256']==digest(original),'Shared-story ROM proof differs')
        check(r['catalog_sha256']==digest(v.CATALOG.read_bytes()),'Shared catalog proof differs')
        check(r['harness_sha256']==digest((b.OUTPUT/'verify_story_completion.py').read_bytes()),'Shared harness proof differs')
        check(r['fixture_sha256']==digest(v.STATE.read_bytes()),'Shared fixture differs')
        check(not r['limited'] and len(r['cases'])==len(expected) and {(x['id'],x['pointer_offset'],x['hero']) for x in r['cases']}==expected,'Incomplete shared cases')
        check(len(r['menus'])==len(prompts) and {m['prompt_command_offset'] for m in r['menus']}==prompts,'Missing shared menus')
        if variant!='baseline':
            report=load_json(b.OUTPUT/f'{variant}-build.json');check(report['previous_rom_sha256']==digest(baseline),'Shared build baseline changed');ledger=report['ledger'];rebuilt=bytearray(original+b'\xff'*(len(data)-len(original)))
            for a in ledger['allocations']:
                at=a['offset'];raw=data[at:at+a['bytes']];check(digest(raw)==a['sha256'],'Shared allocation hash mismatch');rebuilt[at:at+len(raw)]=raw
            for p in ledger['patches']:
                at=p['offset'];before=bytes.fromhex(p['before']);after=bytes.fromhex(p['after']);check(rebuilt[at:at+len(before)]==before,'Unexpected shared patch');rebuilt[at:at+len(after)]=after
            check(bytes(rebuilt)==data,'Unexplained shared ROM bytes');check(data[0x1000000:end]==baseline[0x1000000:end],'Earlier appended data changed')
            for src in ledger['protected_sources']:
                a=src['start'];z=src['end_exclusive'];check(data[a:z]==original[a:z],'Protected source changed')
        proofs[variant]={'rom_sha256':digest(data),'report_sha256':digest(path.read_bytes()),'cases':len(r['cases']),'menus':len(r['menus'])}
    result={'status':'shared_story_component_native_checks_passed','sources':len(catalog['entries']),'operand_words':sum(len(e['events']) for e in catalog['entries']),'japanese_story_pixel_pairs':v.compare(),'japanese_menu_pixel_pairs':len(prompts),'proofs':proofs,'complete_images_reconstructed_from_ledgers':True,'previous_appended_bytes_preserved':True,'scope':'Shared-event component controlled native story/menu and Japanese relocation checks. Complete story-pages baseline acceptance and natural shared-service/cave event reachability remain separately tracked.'}
    atomic_write(b.OUTPUT/'component-checkpoint.json',(json.dumps(result,indent=2)+'\n').encode());print(result['status'],len(expected),'story cases;',len(prompts),'menu',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('variant',choices=('english','japanese','baseline','summarize'));a=p.parse_args()
    summarize() if a.variant=='summarize' else v.verify(a.variant)
