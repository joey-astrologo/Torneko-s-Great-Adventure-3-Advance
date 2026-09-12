"""Natural opening and seven-letter save regression on the combined text build."""
import json
from pathlib import Path
import mgba.log
from mgba._pylib import ffi
from tools import trace_early_journey as journey,verify_name_entry as names
from tools import trace_opening_story,trace_story_provenance,verify_expansion
from tools.audit_scene_resources import BASELINE
from tools.build_first_label import ROOT,ORIGINAL_ROM,digest
from tools.build_name_entry import compact_name
from tools.translation_pipeline import check,load_json,atomic_write
from tools.verify_items import distinct_glyph_observations

OUT=ROOT/'build/completion/current-text-regression'

def save(path,value):
    atomic_write(path,(json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode())

def natural(data):
    build=load_json(ROOT/'build/early-journey/english-build.json')
    index,by_master=journey.source_index(data,build)
    replay=ROOT/'build/opening-story/verification/natural-yes/trace.json'
    folder=OUT/'natural';screens=[]
    with verify_expansion.Session(data,folder,trace_story_provenance.SAVE.read_bytes()) as s:
        s.frames(600);trace=trace_opening_story.OpeningTrace(s.core,data,index)
        try:
            trace.phase='opening-replay'
            for row in load_json(replay)['inputs']:
                check(row['hold']==3,'Opening input duration changed');s.press(row['key'],row['released'],trace)
            s.capture('opening-bedroom');screens.append('opening-bedroom.png')
            for phase,key,n in (('dismiss','A',1),('to-door','DOWN',16),('align-door','RIGHT',4),('exit','DOWN',20)):
                trace.phase=phase
                for _ in range(n):s.press(key,120,trace)
                s.capture(phase);screens.append(phase+'.png')
            for i in range(30):
                trace.phase=f'village-{i:02d}';s.frames(300,trace);last=trace.versions[-1]
                if last['source'].get('master_id')=='jp_009d5660':
                    _,metrics=journey.encode(by_master['jp_009d5660'],ORIGINAL_ROM.read_bytes())
                    gs,_=distinct_glyph_observations([g for g in trace.positions if g['version']==last['serial']])
                    if len(gs)==len(metrics['visible'].replace('\n','')):break
                s.press('A',300,trace);s.capture(trace.phase);screens.append(trace.phase+'.png')
            else:raise ValueError('Natural route did not finish the first chief meeting')
            s.frames(300,trace);s.capture('chief-final');screens.append('chief-final.png')
            report=trace.report();save(folder/'raw-trace.json',report)
            check(not trace.errors,str(trace.errors));proof,checks=journey.check_route(report,data,build)
            report.update(rom_sha256=digest(data),source_sha256=digest(ORIGINAL_ROM.read_bytes()),
                initial_save_sha256=digest(trace_story_provenance.SAVE.read_bytes()),opening_replay_sha256=digest(replay.read_bytes()),
                historical_journey_build_sha256=digest((ROOT/'build/early-journey/english-build.json').read_bytes()),
                inputs=s.frames_recorded,screens=screens,proof=proof,glyph_checks=checks,
                scope='Fresh core and disposable original Adventure Log; normal buttons only through opening, escort and first chief meeting. No forced entry, RAM/state/flag injection. This is a regression route, not complete-game coverage.')
            (folder/'final.state').write_bytes(bytes(ffi.buffer(s.core.save_raw_state())));save(folder/'trace.json',report)
        finally:trace.close()
    print('Natural current build:',proof['buffer_versions'],'messages;',proof['unattributed_ram_reads'],'unattributed reads',flush=True)
    return report

def verify():
    mgba.log.silence();data=BASELINE.read_bytes();original=ORIGINAL_ROM.read_bytes()
    check(digest(data)==load_json(BASELINE.parent/'english-build.json')['rom_sha256'],'Combined build hash differs')
    report=natural(data);folder=OUT/'save'
    first,_=names.creation(data,folder/'create-1',1)
    second,_=names.creation(data,folder/'create-2',2,initial_save=first)
    check(len(second)==65536,'Cartridge save size changed')
    for slot in (1,2):names.reload_name(data,second,folder/f'reload-{slot}',compact_name('Torneko'),slot=slot,select_slot=slot==2)
    (folder/'both-logs.sav').write_bytes(second)
    result={'status':'natural_opening_and_both_logs_passed','rom':str(BASELINE.relative_to(ROOT)),
        'rom_sha256':digest(data),'source_sha256':digest(original),'harness_sha256':digest(Path(__file__).read_bytes()),
        'helper_sha256':{Path(m.__file__).name:digest(Path(m.__file__).read_bytes()) for m in (journey,names,trace_opening_story,trace_story_provenance,verify_expansion)},
        'natural_messages':report['proof']['buffer_versions'],'unattributed_ram_reads':report['proof']['unattributed_ram_reads'],
        'natural_report_sha256':digest((OUT/'natural/trace.json').read_bytes()),'save_bytes':len(second),
        'final_save_sha256':digest(second),'slots':[1,2],'name':'Torneko','first_slot_survives_second_slot_write':True,
        'save_evidence_sha256':{str(p.relative_to(folder)):digest(p.read_bytes()) for p in folder.rglob('*') if p.is_file() and p.name in ('trace.json','created.sav')},
        'scope':'Normal opening/escort/chief buttons, fresh seven-letter name entry and native FLASH saves in both logs, then cold loads of both from the final save. No item/ranking edits; later gameplay, dungeon suspend and graphics work remain separate.'}
    check(BASELINE.read_bytes()==data and ORIGINAL_ROM.read_bytes()==original,'Input ROM changed')
    save(OUT/'verification.json',result);print('Both Adventure Logs: Torneko saved and cold-loaded on current build',flush=True)

if __name__=='__main__':verify()
