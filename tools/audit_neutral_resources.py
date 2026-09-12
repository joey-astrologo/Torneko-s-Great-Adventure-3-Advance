"""Verify reviewed neutral/English resources without changing original bytes."""
import json
import struct
from pathlib import Path
import mgba.log
from tools import audit_scene_resources as scene, verify_tutorial_gameplay as queue
from tools.build_first_label import ORIGINAL_ROM,ROOT,digest
from tools.translation_pipeline import check,load_json,atomic_write
from tools.verify_expansion import Session
OUTPUT=ROOT/'build/completion/neutral-resource-audit'
BASELINE=scene.BASELINE

def audit():
    mgba.log.silence();original=ORIGINAL_ROM.read_bytes();data=BASELINE.read_bytes();manifest=load_json(OUTPUT/'source-review.json');cases=[]
    check(manifest['source_sha256']==digest(original) and len(manifest['entries'])==64,'Neutral source review differs')
    with Session(data,OUTPUT/'native') as s:
        for e in manifest['entries']:
            at=int(e['offset'],0);end=int(e['end_exclusive'],0);word=int(e['pointer_word'],0);load=int(e['load_instruction'],0);offset=load-0x08000000
            check(data[at:end]==original[at:end]==bytes.fromhex(e['source_hex']) and data[word:word+4]==original[word:word+4],'Neutral resource/pointer changed')
            opcode=struct.unpack_from('<H',original,offset)[0]
            check(data[offset:offset+2]==original[offset:offset+2] and opcode&0xF800==0x4800 and ((offset+4)&~3)+(opcode&255)*4==word and (opcode>>8)&7==e['load_register'],'Neutral load instruction differs')
            listing=(ROOT/e['listing']).read_bytes();check(digest(listing)==e['listing_sha256'],'Reviewed consumer listing changed')
            check(e['review_excerpt'][0] in listing.decode() and e['review_excerpt'][0].startswith(f'{load:08x}  ldr '),'Missing reviewed disassembly')
            selected=queue.select_slice(s.core,load,load+2,{},e['load_register'])
            check(int(selected['source'],0)==at+0x08000000,'Native neutral literal resolution differs')
            cases.append({**e,'native_selected_pointer':selected['source'],'source_and_pointer_unchanged':True})
    result={'status':'neutral_resources_reviewed_and_literals_verified','source_sha256':digest(original),'verified_rom':str(BASELINE.relative_to(ROOT)),'verified_rom_sha256':digest(data),
        'manifest_sha256':digest((OUTPUT/'source-review.json').read_bytes()),'harness_sha256':digest(Path(__file__).read_bytes()),'helper_sha256':{Path(queue.__file__).name:digest(Path(queue.__file__).read_bytes())},'entries':cases,
        'scope':'Reviewed static consumer role plus native literal resolution and exact unchanged source/pointer bytes. One-instruction native probes are not new full display or natural-gameplay tests. No ROM/RAM mutations or insertion space.'}
    atomic_write(OUTPUT/'native-verification.json',(json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode());print(len(cases),'neutral/English resources reviewed; native literal checks passed',flush=True)

if __name__=='__main__':audit()
