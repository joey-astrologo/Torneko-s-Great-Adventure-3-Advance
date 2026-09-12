"""Validate and summarize a frozen continuous-story native checkpoint."""
import argparse
import json
from tools import verify_story_completion as v
from tools.build_first_label import ROOT, ORIGINAL_ROM, digest
from tools.translation_pipeline import atomic_write, check, load_json


def summarize(name):
    folder=ROOT/'build/completion/checkpoints'/name
    v.OUTPUT=folder;v.CATALOG=folder/'catalog.json'
    catalog=load_json(v.CATALOG);expected=v.expected_cases();original=ORIGINAL_ROM.read_bytes()
    prompts={ev['prompt_command_offset'] for e in catalog['entries'] for ev in e['events'] if ev['opcode']==0x98}
    proofs={};baseline=v.BASELINE.read_bytes()
    for variant in ('english','japanese','baseline'):
        path=folder/'verification'/variant/'verification.json';r=load_json(path)
        rom=baseline if variant=='baseline' else (folder/f'torneko3-story-completion-{variant}.gba').read_bytes()
        check(not r['limited'] and len(r['cases'])==len(expected),'Incomplete or repeated story cases')
        check({(x['id'],x['pointer_offset'],x['hero']) for x in r['cases']}==expected,'Different story cases')
        check({m['prompt_command_offset'] for m in r.get('menus',[])}==prompts,'Incomplete choice menus')
        check(r['catalog_sha256']==digest(v.CATALOG.read_bytes()),'Checkpoint catalog mismatch')
        check(r['rom_sha256']==digest(rom) and r['source_sha256']==digest(original),'Checkpoint ROM mismatch')
        check(r['harness_sha256']==digest((folder/'verify_story_completion.py').read_bytes()),'Checkpoint harness mismatch')
        check(r['fixture_sha256']==digest(v.STATE.read_bytes()),'Checkpoint fixture mismatch')
        if variant!='baseline':
            build=load_json(folder/f'{variant}-build.json');ledger=build['ledger']
            check(build['previous_rom_sha256']==digest(baseline),'Earlier components changed')
            check(build['story']['entries']==len(catalog['entries']),'Built catalog count differs')
            check(build.get('catalog_sha256',digest(v.CATALOG.read_bytes()))==digest(v.CATALOG.read_bytes()),'Built catalog hash differs')
            rebuilt=bytearray(original+b'\xff'*(len(rom)-len(original)))
            for a in ledger['allocations']:
                at=a['offset'];payload=rom[at:at+a['bytes']]
                check(digest(payload)==a['sha256'],'Allocation hash differs')
                rebuilt[at:at+len(payload)]=payload
            for p in ledger['patches']:
                at=p['offset'];before=bytes.fromhex(p['before']);after=bytes.fromhex(p['after'])
                check(bytes(rebuilt[at:at+len(before)])==before,'Patch source or ownership differs')
                rebuilt[at:at+len(after)]=after
            check(bytes(rebuilt)==rom,'Unexplained image bytes')
            check(rom[0x1000000:0x1034789]==baseline[0x1000000:0x1034789],'Prior appended bytes changed')
            for source in ledger['protected_sources']:
                a=source['start'];b=source['end_exclusive']
                check(rom[a:b]==original[a:b],'Protected source changed')
        proofs[variant]={'report_sha256':digest(path.read_bytes()),'rom_sha256':r['rom_sha256'],'cases':len(r['cases']),'menus':len(r.get('menus',[]))}
    result={'status':'controlled_native_checkpoint_passed','sources':len(catalog['entries']),
        'operand_words':sum(len(e['events']) for e in catalog['entries']),
        'japanese_story_pixel_pairs':v.compare(),'japanese_menu_pixel_pairs':len(prompts),
        'proofs':proofs,'catalog_sha256':digest(v.CATALOG.read_bytes()),
        'prior_appended_bytes_preserved':True,'complete_images_reconstructed_from_ledgers':True,
        'scope':'Controlled native story and choice rendering plus Japanese relocation. Natural/save regression on this cumulative ROM remains pending; not complete-game acceptance.'}
    atomic_write(folder/'checkpoint.json',(json.dumps(result,indent=2)+'\n').encode())
    print(name,result['sources'],'sources;',result['japanese_story_pixel_pairs']+len(prompts),'native/pixel cases',flush=True)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('checkpoint');summarize(p.parse_args().checkpoint)
