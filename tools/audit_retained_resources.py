"""Record reader-confirmed resources intentionally retained without English prose."""
import json
import struct
from pathlib import Path
from tools.build_first_label import ORIGINAL_ROM,ROOT,digest
from tools.game_text import GameTextCodec,rebuild
from tools.audit_text_coverage import translated_ids
from tools.translation_pipeline import check,load_json,atomic_write

OUTPUT=ROOT/'build/completion/retained-resources.json'
BASELINE=ROOT/'build/completion/inventory-notice/torneko3-inventory-notice-english.gba'


def audit():
    original=ORIGINAL_ROM.read_bytes();data=BASELINE.read_bytes();codec=GameTextCodec(original);master={int(e['offset'],0):e for e in load_json(ROOT/'translations/master.json')['entries']};entries=[]
    check(struct.unpack_from('<I',original,0x7D1BC)[0]==0x08C45DE4 and original[0xC46078:0xC4607C]==b'\0'*4,'Name-filter ownership differs')
    for row in range(165):
        word=0xC45DE4+row*4;at=struct.unpack_from('<I',original,word)[0]-0x08000000;p=codec.parse(original,at);raw=original[at:p['end']];check(rebuild(p['tokens'])==raw and data[at:p['end']]==raw and data[word:word+4]==original[word:word+4],'Retained filter bytes changed')
        entries.append({'master_id':master[at]['id'],'offset':hex(at),'end_exclusive':hex(p['end']),'source_hex':raw.hex(),'japanese':p['display'],'kind':'original_name_filter','status':'retained_program_matching_data','pointer_word':hex(word),'consumer':hex(0x0807D1A0),'evidence':'build/completion/remaining-ui/research/keyboard-context.txt','reason':'Original compact-name filter data, not displayed language. Preserve the original matching policy.'})
    at=0xC46748;p=codec.parse(original,at);raw=original[at:p['end']];check(data[at:p['end']]==raw and struct.unpack_from('<I',original,0x7CDD0)[0]==0x08000000+at,'History format ownership differs')
    entries.append({'master_id':master[at]['id'],'offset':hex(at),'end_exclusive':hex(p['end']),'source_hex':raw.hex(),'japanese':p['display'],'kind':'history_row_format','status':'retained_language_neutral_format','pointer_word':hex(0x7CDD0),'consumer':hex(0x0807CD14),'evidence':'build/completion/keyboard/component-checkpoint.json','reason':'Number/position/separator/name printf format; native Latin and kana rows already verified.'})
    for kind,start,end,consumer,evidence in (
        ('adventure_history_key',0xC4D250,0xC4D5B8,0x08087788,'build/completion/history/table-checkpoint.json'),
        ('dungeon_tutorial_key',0xA536C,0xA546C,0x0807DC98,'build/completion/dungeon-events/component-checkpoint.json'),
        ('adventure_result_key',0xDB3B8,0xDB6E8,0x0800177C,'build/completion/results/component-checkpoint.json')):
        check((ROOT/evidence).is_file(),'Missing accepted key-reader evidence')
        for word in range(start,end-8,8):
            address,value=struct.unpack_from('<II',original,word);check(address and value,'Unexpected key terminator');at=address-0x08000000;p=codec.parse(original,at);raw=original[at:p['end']]
            check(raw[:-1].isascii() and rebuild(p['tokens'])==raw,'Internal key grammar differs');check(data[at:p['end']]==raw and data[word:word+4]==original[word:word+4],'Internal key bytes changed')
            entries.append({'master_id':master[at]['id'] if at in master else None,'offset':hex(at),'end_exclusive':hex(p['end']),'source_hex':raw.hex(),'japanese':p['display'],'kind':kind,'status':'retained_program_lookup_key','pointer_word':hex(word),'consumer':hex(consumer),'evidence':evidence,'reason':'Typed dictionary lookup identifier. The separate value is displayed and has its own translation/acceptance; changing the key would break lookup.'})

    def add(at,kind,status,evidence,reason,**metadata):
        m=master[at];raw=bytes.fromhex(m['source_hex'])
        check(data[at:at+len(raw)]==original[at:at+len(raw)]==raw,'Retained resource bytes changed')
        entries.append({'master_id':m['id'],'offset':hex(at),'end_exclusive':hex(at+len(raw)),
            'source_hex':raw.hex(),'japanese':m['japanese'],'kind':kind,'status':status,
            'evidence':evidence,'reason':reason,**metadata})

    # The original church table has ASCII identifier placeholders in unused
    # service slots; these are positional values, not dictionary keys.
    placeholders={}
    for word in range(0xC78B04,0xC78CA8,4):
        at=struct.unpack_from('<I',original,word)[0]-0x08000000
        p=codec.parse(original,at)
        if p['display'].isascii():
            check(data[word:word+4]==original[word:word+4],'Church placeholder word changed')
            placeholders.setdefault(at,[]).append(hex(word))
    check(len(placeholders)==17,'Church placeholder count changed')
    for at,words in placeholders.items():
        add(at,'church_ascii_placeholder','retained_original_ascii_placeholder',
            'build/completion/church/component-checkpoint.json',
            'Original ASCII placeholder in the typed five-by-21 positional service table. Preserve separately from translated prose; this is not a displayed-language translation or a lookup-key claim.',pointer_words=words)

    for word in range(0xCB0630,0xCB0640,4):
        at=struct.unpack_from('<I',original,word)[0]-0x08000000
        check(data[word:word+4]==original[word:word+4],'Original kana grid pointer changed')
        add(at,'original_kana_grid','retained_character_input_asset',
            'build/completion/keyboard/component-checkpoint.json',
            'Original character-entry grid. Type-zero entry uses appended Latin pages; original type-one kana input and its font are preserved. These are input alphabets, not prose needing English.',pointer_word=hex(word),consumer='0x0807BB74')
    for at,word,extended in ((0xC467EC,0xC467E8,False),(0xC4696C,0xC467E4,True)):
        pointer=struct.unpack_from('<I',data,word)[0]-0x08000000
        check(data[pointer:pointer+382]==original[at:at+382],'Original compact-map prefix changed')
        if not extended:check(pointer==at,'Type-one compact map moved')
        add(at,'original_compact_character_map','retained_character_input_asset',
            'build/completion/keyboard/component-checkpoint.json',
            'Original compact-ID mapping retained for Japanese name/password compatibility. Type-zero extension preserves all original 191 entries before appended Latin IDs.',pointer_word=hex(word),extended_copy=extended,consumer='0x0807D20C')

    check(struct.unpack_from('<I',original,0x87185C)[0]==50000 and data[0x87185C:0x871860]==original[0x87185C:0x871860],'Merchant cash field changed')
    add(0x87185C,'merchant_initial_cash','retained_numeric_record_field',
        'build/completion/merchants/component-checkpoint.json',
        'The apparent P/kana string is the low bytes of integer 50000, the original cash field in a typed player-shop record.',record_field={'start':'0x87185c','end_exclusive':'0x871860','u32_value':50000})

    from tools import audit_scene_resources as scene
    proof_path=scene.OUTPUT/'native-verification.json';proof=load_json(proof_path)
    check(proof['status']=='scene_program_candidates_native_verified' and proof['source_sha256']==digest(original) and
          proof['verified_rom_sha256']==digest(data),'Scene program proof belongs to another ROM')
    check(proof['harness_sha256']==digest(Path(scene.__file__).read_bytes())==digest((scene.OUTPUT/'audit_scene_resources.py').read_bytes()) and
          proof['candidates_sha256']==digest((scene.OUTPUT/'source-candidates.json').read_bytes()),'Scene program proof inputs changed')
    check(proof['fixture_sha256']==digest(scene.system.STATE.read_bytes()) and proof['helper_sha256']==
          {Path(m.__file__).name:digest(Path(m.__file__).read_bytes()) for m in (scene.ui,scene.queue,scene.old,scene.system)},'Scene native proof helpers changed')
    check(len(proof['entries'])==205 and len({e['master_id'] for e in proof['entries']})==205,'Scene proof coverage changed')
    for e in proof['entries']:
        at=int(e['offset'],0);check(e['guards_intact'] and e['command_bytes_unchanged'] and
            data[at:at+8]==original[at:at+8]==bytes.fromhex(e['command_hex']),'Scene command proof differs')
        add(at,'scene_script_command','retained_program_command',str(proof_path.relative_to(ROOT)),
            'Typed scene/group/record selection and native script registration, activation, fetch and dispatch identify this prefix as an event command. It is not displayed text. Natural event reachability remains separate.',
            native_owner=e['selected_owner'],command_hex=e['command_hex'],opcode=e['opcode'],dispatch_target=e['dispatch_target'])

    # One further prefix was fetched naturally in the original opening route.
    natural_path=ROOT/'build/story-provenance/natural/trace.json';natural=load_json(natural_path)
    check(natural['source_sha256']==digest(original),'Original natural event trace source differs')
    at=0x91B688;rows=[e for e in natural['commands'] if int(e['cursor'],0)==at+0x08000000]
    check(rows and all(e['command_in_original_rom'] and bytes.fromhex(e['raw_hex'])==original[at:at+8] for e in rows) and data[at:at+8]==original[at:at+8],'Natural command evidence differs')
    add(at,'naturally_observed_script_command','retained_program_command',str(natural_path.relative_to(ROOT)),
        'Original opening-route trace fetched these exact eight bytes as an event command; the apparent single-character string is its opcode.',command_hex=original[at:at+8].hex(),observed_fetches=len(rows))

    classified={e['master_id'] for e in entries};interior_count=0
    for at,m in master.items():
        if m['id'] in classified:continue
        end=at+len(bytes.fromhex(m['source_hex']))
        enclosing=[e for e in proof['entries'] if int(e['offset'],0)<at and end<=int(e['offset'],0)+8]
        if not enclosing:continue
        check(len(enclosing)==1,'Ambiguous native command containment')
        parent=enclosing[0];interior_count+=1
        add(at,'scene_command_operand','retained_program_command_field',str(proof_path.relative_to(ROOT)),
            'This apparent string lies wholly inside the parameter/operand bytes of an independently verified native eight-byte event fetch.',
            enclosing_command=parent['offset'],enclosing_master_id=parent['master_id'],command_hex=parent['command_hex'])
    check(interior_count==8,'Native command interior coverage changed')

    from tools import audit_scene_graphics as graphics
    graphics_path=graphics.OUTPUT/'native-verification.json';gp=load_json(graphics_path)
    check(gp['status']=='scene_graphics_candidates_native_verified' and gp['source_sha256']==digest(original) and
          gp['verified_rom_sha256']==digest(data),'Scene graphics proof ROM differs')
    check(gp['harness_sha256']==digest(Path(graphics.__file__).read_bytes())==digest((graphics.OUTPUT/'audit_scene_graphics.py').read_bytes()) and
          gp['candidate_manifest_sha256']==digest((ROOT/'build/completion/remaining-ui/research/scene-graphics-candidates.json').read_bytes()),'Scene graphics proof inputs changed')
    check(gp['fixture_sha256']==digest(graphics.system.STATE.read_bytes()) and gp['helper_sha256']==
          {Path(m.__file__).name:digest(Path(m.__file__).read_bytes()) for m in (graphics.ui,graphics.queue,graphics.system,graphics.old)},'Scene graphics proof helpers changed')
    check(len(gp['entries'])==71 and len({e['master_id'] for e in gp['entries']})==71,'Scene graphics proof count differs')
    for e in gp['entries']:
        at=int(e['offset'],0);check(e['guards_intact'] and e['descriptor_and_format_checks'],'Missing graphics native evidence')
        for part in e['copies']:
            start,end=int(part['start'],0),int(part['end_exclusive'],0)
            check(part['guards_intact'] and data[start:end]==original[start:end]==bytes.fromhex(part['raw_hex']),'Scene graphics copy evidence differs')
        add(at,'scene_background_graphics','retained_graphic_asset',str(graphics_path.relative_to(ROOT)),
            'Native scene/header and format selection identify these bytes as 4-bpp tile pixels or metatile indexes; guarded native copies cover the entire extraction candidate. No prose or free space is represented.',asset=e['asset'])
    from tools import audit_aux_resources as auxiliary, audit_neutral_resources as neutral, audit_remaining_fields as fields
    for module, expected, status in ((auxiliary,22,'auxiliary_resources_native_verified'),
                                    (neutral,64,'neutral_resources_reviewed_and_literals_verified'),
                                    (fields,17,'remaining_fields_native_verified')):
        path=module.OUTPUT/'native-verification.json';p=load_json(path)
        check(p['status']==status and p['source_sha256']==digest(original) and p['verified_rom_sha256']==digest(data),'Auxiliary/neutral proof ROM differs')
        check(p['harness_sha256']==digest(Path(module.__file__).read_bytes())==digest((module.OUTPUT/Path(module.__file__).name).read_bytes()),'Auxiliary/neutral harness changed')
        check(len(p['entries'])==expected,'Auxiliary/neutral coverage differs')
        helpers=(module.queue,) if module is neutral else (module.ui,module.queue,module.old,module.system)
        check(p['helper_sha256']=={Path(m.__file__).name:digest(Path(m.__file__).read_bytes()) for m in helpers},'Auxiliary/neutral proof helpers changed')
        if module is neutral:check(p['manifest_sha256']==digest((module.OUTPUT/'source-review.json').read_bytes()),'Neutral review changed')
        else:check(p['fixture_sha256']==digest(module.system.STATE.read_bytes()),'Auxiliary fixture changed')
        for e in p['entries']:
            at=int(e['offset'],0)
            if module is neutral:
                word=int(e['pointer_word'],0);check(data[word:word+4]==original[word:word+4] and e['source_and_pointer_unchanged'],'Neutral pointer changed')
                check(e['listing_sha256']==digest((ROOT/e['listing']).read_bytes()),'Neutral consumer listing changed')
            add(at,e['kind'],'retained_reviewed_resource',str(path.relative_to(ROOT)),
                e.get('reason','Bounded native reader identifies numeric program data or an original character/name asset. Preserve original bytes; no prose translation or free-space claim.'),
                native_evidence=e)
    from tools import audit_resource_boundaries as boundaries
    path=boundaries.OUT/'native-verification.json';p=load_json(path)
    check(p['status']=='resource_boundaries_native_verified' and p['source_sha256']==digest(original)
          and p['verified_rom_sha256']==digest(data),'Resource boundary proof ROM differs')
    check(p['harness_sha256']==digest(Path(boundaries.__file__).read_bytes())==
          digest((boundaries.OUT/'audit_resource_boundaries.py').read_bytes()),'Resource boundary harness changed')
    check(p['fixture_sha256']==digest(boundaries.system.STATE.read_bytes()) and p['helper_sha256']==
          {Path(m.__file__).name:digest(Path(m.__file__).read_bytes()) for m in (boundaries.ui,boundaries.queue,boundaries.system)},
          'Resource boundary fixture/helpers changed')
    check(all(digest((ROOT/name).read_bytes())==value for name,value in p['listing_sha256'].items()),
          'Resource boundary listings changed')
    check({e['master_id'] for e in p['entries']}=={'jp_0092c610','jp_00aa6678','jp_00a00bf8','jp_00a00bfc','jp_00a00c00'},
          'Resource boundary coverage differs')
    for e in p['entries']:
        at=int(e['offset'],0)
        check(data[at:int(e['end_exclusive'],0)]==bytes.fromhex(e['source_hex']),'Resource boundary source differs')
        add(at,e['kind'],'retained_graphic_resource',str(path.relative_to(ROOT)),e['reason'],native_evidence=e)
    check(len({e['offset'] for e in entries})==len(entries),'Retained sources repeated')
    done,_=translated_ids(list(master.values()));retained={e['master_id'] for e in entries if e['master_id']};check(not done & retained,'Retained data already counted as authored English')
    result={'schema':1,'source_sha256':digest(original),'verified_rom':str(BASELINE.relative_to(ROOT)),'verified_rom_sha256':digest(data),'entries':entries,
        'evidence_sha256':{e['evidence']:digest((ROOT/e['evidence']).read_bytes()) for e in entries},
        'counts':{'retained_without_authored_english':len(retained),'reviewed_resources_outside_inventory':sum(e['master_id'] is None for e in entries),'typed_lookup_keys':sum(e['status']=='retained_program_lookup_key' for e in entries),'name_filter':165,'language_neutral_history_format':1,
        'church_ascii_placeholders':17,'character_input_assets':6,'numeric_record_fields':1,'native_scene_command_prefixes':205,'additional_natural_command_prefixes':1,
        'native_command_operand_candidates':8,'background_graphic_candidates':71,'auxiliary_resources':22,'neutral_and_original_english_resources':64,'additional_typed_fields_and_ascii_values':17,'resource_boundary_candidates':5,
        'authored_english_sources':len(done),'still_unclassified_without_english':len(master)-len(done)-len(retained)},'scope':'Positive reader evidence only. These entries retain original bytes and are not counted as authored English. This report grants no insertion space, and unclassified inventory entries remain open.'};atomic_write(OUTPUT,(json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode());print(len(entries),'reader-confirmed retained resources',flush=True)

if __name__=='__main__':audit()
