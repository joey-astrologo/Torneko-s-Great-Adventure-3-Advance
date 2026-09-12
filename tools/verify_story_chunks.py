"""Run a frozen story checkpoint in short subprocesses and prove full coverage."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
from tools import verify_story_completion as v
from tools.build_first_label import ROOT,ORIGINAL_ROM,digest
from tools.translation_pipeline import check,load_json,atomic_write


def run(checkpoint,size=75):
    folder=ROOT/'build/completion/checkpoints'/checkpoint
    v.OUTPUT=folder;v.CATALOG=folder/'catalog.json'
    catalog=load_json(v.CATALOG);n=len(catalog['entries']);check(1<=size<=100,'Chunk size must be 1..100')
    harness=Path(v.__file__);frozen=folder/'verify_story_completion.py'
    if frozen.exists():check(frozen.read_bytes()==harness.read_bytes(),'Frozen harness changed')
    else:atomic_write(frozen,harness.read_bytes())
    expected=v.expected_cases();prompts={ev['prompt_command_offset'] for e in catalog['entries'] for ev in e['events'] if ev['opcode']==0x98}
    hashes={'source_sha256':digest(ORIGINAL_ROM.read_bytes()),'catalog_sha256':digest(v.CATALOG.read_bytes()),'harness_sha256':digest(harness.read_bytes()),'fixture_sha256':digest(v.STATE.read_bytes())}
    for variant in ('english','japanese','baseline'):
        rom=v.BASELINE if variant=='baseline' else folder/f'torneko3-story-completion-{variant}.gba'
        required={**hashes,'rom_sha256':digest(rom.read_bytes())};cases=[];menus=[];proofs=[]
        for start in range(0,n,size):
            end=min(start+size,n);part=folder/'verification'/variant/'chunks'/f'{start:04d}-{end:04d}';path=part/'verification.json';part.mkdir(parents=True,exist_ok=True)
            if not path.exists():
                with (part/'run.log').open('w') as log:
                    code=subprocess.run([sys.executable,'-m','tools.verify_story_completion','--checkpoint',checkpoint,'--variant',variant,'--range-start',str(start),'--range-end',str(end)],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT).returncode
                check(code==0,f'Story chunk failed: {variant} {start}:{end}, exit {code}; see {part}/run.log')
            r=load_json(path);check(all(r[k]==x for k,x in required.items()),'Chunk evidence/input mismatch')
            check(r['limited'] and r['range']==[start,end],'Unexpected chunk range')
            ids={e['id'] for e in catalog['entries'][start:end]};keys={(x['id'],x['pointer_offset'],x['hero']) for x in r['cases']}
            check(keys=={k for k in expected if k[0] in ids} and len(keys)==len(r['cases']),'Incomplete or repeated chunk cases')
            check({m['prompt_command_offset'] for m in r['menus']}==(prompts if end==n else set()),'Missing/unexpected chunk menus')
            prefix=part.relative_to(folder/'verification'/variant)
            for x in r['cases']:cases.append({**x,'screen':str(prefix/x['screen'])})
            for x in r['menus']:menus.append({**x,'screen':str(prefix/x['screen'])})
            proofs.append({'range':[start,end],'report':str(path.relative_to(ROOT)),'sha256':digest(path.read_bytes())})
            print(variant,end,'/',n,'sources completed',flush=True)
        check({(x['id'],x['pointer_offset'],x['hero']) for x in cases}==expected and len(cases)==len(expected),'Incomplete aggregate story coverage')
        check({x['prompt_command_offset'] for x in menus}==prompts and len(menus)==len(prompts),'Incomplete aggregate menus')
        result={**required,'variant':variant,'limited':False,'cases':cases,'menus':menus,'chunks':proofs,'aggregator_sha256':digest(Path(__file__).read_bytes()),'scope':'Complete coverage aggregated from hash-matched, exact-range native subprocesses. Each subprocess releases all emulator resources on exit. Interrupted earlier runs are excluded. Controlled event rendering/menu coverage; natural gameplay remains separate.'}
        atomic_write(folder/'verification'/variant/'verification.json',(json.dumps(result,indent=2)+'\n').encode())
    from tools.summarize_story_checkpoint import summarize
    summarize(checkpoint)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('checkpoint');p.add_argument('--size',type=int,default=75);a=p.parse_args();run(a.checkpoint,a.size)
