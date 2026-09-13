"""Combine uninterrupted gameplay and cold-save evidence for the first cave clear."""
from pathlib import Path
import shutil
from tools import verify_cave_clear as route, verify_cave_clear_save as cold
from tools import verify_roundtrip as trip
from tools.build_first_label import ROOT, ORIGINAL_ROM, digest
from tools.audit_scene_resources import BASELINE
from tools.translation_pipeline import check,load_json


def accept():
    out=route.OUT;replay=load_json(out/'replay.json');play=load_json(out/'verification/trace.json')
    loaded=load_json(out/'cold-verification.json');data=BASELINE.read_bytes()
    for r,key in ((replay,'rom_sha256'),(play,'rom_sha256'),(loaded,'verified_rom_sha256')):
        check(r[key]==digest(data),'Clear reports disagree on ROM')
    prior=load_json(ROOT/'build/completion/roundtrip/accepted-inputs.json')
    for path,sha in prior['files'].items():check(digest((ROOT/path).read_bytes())==sha,'Accepted opening/helper changed: '+path)
    check(play['replay_sha256']==digest((out/'replay.json').read_bytes()) and play['inputs']==replay['inputs'],'Replay provenance differs')
    check(len(play['inputs'])==435 and play['inputs'][-1]['end_frame']==125827 and play['final_pixels_match'],'Recorded clear route differs')
    # The replay rejects callback errors before writing its checked report.
    check(not play['source_reads'] and not play['unattributed_story_reads'],'Clear has unresolved reader errors')
    check(len(play['result_events'])==1 and len(play['animation'])==17 and
          all(x['mismatches']==0 and x['outside_window_unchanged'] for x in play['animation']),'Clear reveal differs')
    saved=(out/'verification/earned.sav').read_bytes()
    check(saved==(out/'clear-route/latest.sav').read_bytes() and
          digest(saved)==loaded['input_save_sha256']==replay['expected_final_save_sha256']==play['output_save_sha256'],
          'Replayed and cold-loaded cartridge saves differ')
    earned=bytes.fromhex(loaded['earned_record_hex'])
    check(bytes.fromhex(play['result_events'][0]['profile_hex'])[20:68]==earned==saved[0xE014:0xE044],
          'Native ending and saved/cold records differ')
    check(bytes.fromhex(play['profile_hex'])==saved[0xE000:0xFFAC],'Saved profile differs from final RAM')
    events=play['save_events'];writes=[e for e in events if e['pc']=='0x80027d0']
    check(any(e['pc']=='0x80011f0' for e in events) and any(e['pc']=='0x80016dc' for e in events),'Native record/write path missing')
    check(writes and all(e['name_hex']==e['record_name_hex']==trip.EXPECTED_NAME.hex() for e in writes),'Seven-letter native save copy differs')
    check(loaded['status']=='cold_cave_clear_save_verified' and loaded['log_2_sectors_unchanged'],'Cold save verification incomplete')
    check(loaded['harness_sha256']==digest(Path(cold.__file__).read_bytes()),'Cold harness changed')
    for path,sha in loaded['reports'].items():check(digest((out/path).read_bytes())==sha,'Cold report changed')
    for m in (route,cold):shutil.copyfile(m.__file__,out/Path(m.__file__).name)
    shutil.copyfile(__file__,out/Path(__file__).name)
    files=[Path(route.__file__),Path(cold.__file__),Path(__file__),ROOT/'tools/explore_cave_clear.py',
           ROOT/'build/completion/roundtrip/accepted-inputs.json',out/'replay.json',out/'verification/trace.json',
           out/'verification/earned.sav',out/'cold-verification.json',out/'cold/trace.json',out/'cold-log-2/trace.json',
           out/'clear-route/third-floor-exit.png',out/'clear-route/final.png',out/'cold/detail.png',out/'cold/world-menu.png']
    result={'status':'native_cave_clear_save_roundtrip_passed','source_sha256':digest(ORIGINAL_ROM.read_bytes()),
            'verified_rom':str(BASELINE.relative_to(ROOT)),'verified_rom_sha256':digest(data),
            'input_save_sha256':replay['initial_save_sha256'],'output_save_sha256':digest(saved),'save_bytes':len(saved),
            'normal_inputs':435,'story_messages':len(play['checks']['story']),
            'paged_messages':len(play['checks']['paged_messages']),'whole_string_draws':len(play['checks']['whole_string_draws']),
            'cold_whole_string_draws':loaded['whole_string_draws'],'animation_steps':17,'map_cells_per_step':459,
            'cold_detail_pixels':loaded['detail_pixels'],'score':4002,'floor':3,'cause':91,
            'name':'Torneko','logs_checked':[1,2],'log_2_sectors_unchanged':True,'unowned_japanese_reads':0,
            'files':{str(p.relative_to(ROOT)):digest(p.read_bytes()) for p in files},
            'scope':'435 uninterrupted normal inputs from the accepted native fresh two-Log opening: three-floor Mysterious cave clear, Shrine of the Gods meeting, Ines joining, map handover, village priest save, title return. Fresh-core records/history and progressed Log 1 load, independent unchanged Log 2 load. No mid-route state restore, game-value injection, ROM patch, save layout change or graphics edit. Later dungeons, suspend/resume and full-game discovery remain separate.'}
    route.save(out/'component-checkpoint.json',result)
    print(result['status'],result['story_messages'],result['paged_messages'],result['whole_string_draws'],result['cold_whole_string_draws'],flush=True)


if __name__=='__main__':accept()
