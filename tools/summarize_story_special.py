"""Check special-story component evidence independently of cumulative baseline QA."""
import json
from pathlib import Path
from tools import build_story_special as b
from tools import verify_story_special as v
from tools.verify_story_inputs import scenarios
from tools.build_first_label import ORIGINAL_ROM,digest
from tools.translation_pipeline import load_json,check,atomic_write


def summarize():
    original=ORIGINAL_ROM.read_bytes();catalog=load_json(b.OUTPUT/'catalog.json');expected=v.expected_cases(catalog);proofs={};baseline=v.BASELINE.read_bytes()
    for variant in ('english','japanese','baseline'):
        path=b.OUTPUT/'verification'/variant/'verification.json';r=load_json(path)
        data=baseline if variant=='baseline' else (b.OUTPUT/f'torneko3-story-special-{variant}.gba').read_bytes()
        check(r['rom_sha256']==digest(data) and r['source_sha256']==digest(original),'Special ROM/source proof mismatch')
        check(r['catalog_sha256']==digest((b.OUTPUT/'catalog.json').read_bytes()),'Special catalog proof mismatch')
        check(r['harness_sha256']==digest((b.OUTPUT/'verify_story_special.py').read_bytes()),'Special harness proof mismatch')
        check(r['fixture_sha256']==digest(v.STATE.read_bytes()),'Special fixture mismatch')
        check(len(r['cases'])==len(expected) and {(x['id'],x['pointer_offset'],x['hero'],x['profile']) for x in r['cases']}==expected,'Incomplete special render cases')
        if variant!='baseline':
            build=load_json(b.OUTPUT/f'{variant}-build.json');check(build['previous_rom_sha256']==digest(baseline),'Special baseline differs')
            check(build['catalog_sha256']==r['catalog_sha256'],'Built special catalog differs');ledger=build['ledger'];reconstructed=bytearray(original+b'\xff'*(len(data)-len(original)))
            for a in ledger['allocations']:
                at=a['offset'];raw=data[at:at+a['bytes']];check(digest(raw)==a['sha256'],'Special allocation hash mismatch');reconstructed[at:at+len(raw)]=raw
            for p in ledger['patches']:
                at=p['offset'];before=bytes.fromhex(p['before']);after=bytes.fromhex(p['after']);check(reconstructed[at:at+len(before)]==before,'Unexpected special patch source');reconstructed[at:at+len(after)]=after
            check(bytes(reconstructed)==data,'Unexplained special ROM bytes')
            for src in ledger['protected_sources']:
                a=src['start'];z=src['end_exclusive'];check(data[a:z]==original[a:z],'Protected special source changed')
            prior=load_json(v.BASELINE.parent/'english-build.json')['ledger'];end=max(a['offset']+a['bytes'] for a in prior['allocations'])
            check(data[0x1000000:end]==baseline[0x1000000:end],'Earlier appended bytes changed')
        proofs[variant]={'report_sha256':digest(path.read_bytes()),'rom_sha256':digest(data),'cases':len(r['cases'])}
    english_sha=proofs['english']['rom_sha256']
    inp_path=b.OUTPUT/'verification/inputs/verification.json';inp=load_json(inp_path)
    check(inp['rom_sha256']==english_sha and inp['source_sha256']==digest(original),'Input proof ROM differs')
    check(inp['harness_sha256']==digest((b.OUTPUT/'verify_story_inputs.py').read_bytes()),'Input harness changed')
    check({c['id'] for c in inp['cases']}=={c['id'] for c in scenarios(original)} and len(inp['cases'])==15,'Missing input cases')
    save_path=b.OUTPUT/'verification/pet-saves/verification.json';saves=load_json(save_path)
    check(saves['rom_sha256']==english_sha and saves['source_sha256']==digest(original),'Pet save proof ROM differs')
    check(saves['harness_sha256']==digest((b.OUTPUT/'verify_pet_saves.py').read_bytes()),'Pet save harness changed')
    check(saves['input_proof_sha256']==digest(inp_path.read_bytes()),'Pet save/input evidence differs')
    check(saves['save_bytes']==65536 and [c['slot'] for c in saves['cases']]==[1,2] and saves['first_slot_preserved'],'Incomplete pet save proof')
    result={'status':'special_component_native_checks_passed','source_sha256':digest(original),'rom_sha256':english_sha,'sources':32,'operand_words':33,'story_cases':len(expected),'japanese_pixel_pairs':v.compare(),'input_cases':len(inp['cases']),'native_save_slots':2,'proofs':proofs,'input_report_sha256':digest(inp_path.read_bytes()),'save_report_sha256':digest(save_path.read_bytes()),'complete_images_reconstructed_from_ledgers':True,'previous_appended_bytes_preserved':True,'scope':'Pet-story and tree-password component passed controlled native checks and native pet-variable FLASH saves/cold loads. Cumulative story-pages baseline acceptance is tracked separately; no complete-game or natural adoption/gate traversal claim.'}
    atomic_write(b.OUTPUT/'component-checkpoint.json',(json.dumps(result,indent=2)+'\n').encode());print(result['status'],result['story_cases'],'story cases;',result['input_cases'],'input cases',flush=True);return result


if __name__=='__main__':summarize()
