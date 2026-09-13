"""Replay a recorded normal cave route from the accepted native opening."""
import json
from pathlib import Path
import mgba.log
from mgba._pylib import ffi
from PIL import Image, ImageChops
from tools.build_first_label import ROOT, ORIGINAL_ROM, digest
from tools.audit_scene_resources import BASELINE
from tools import verify_roundtrip as trip
from tools.verify_expansion import Session
from tools.verify_first_label import battery_snapshot
from tools.verify_natural_cave import sources
from tools.build_name_entry import NAME_RAM
from tools.translation_pipeline import check, load_json, atomic_write

OUT=ROOT/'build/completion/cave-clear'
SETUP=ROOT/'build/completion/roundtrip/verification/setup'


def save(path,value):atomic_write(path,(json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode())


def freeze_route():
    """Join native exploration branches; the independent replay uses no mid-route restore."""
    first=ROOT/'build/completion/roundtrip/verification/adventure/trace.json'
    continued=OUT/'continued/readers.json'; final=OUT/'clear-route/readers.json'
    a=load_json(first)['inputs'][:71]
    b=[x for x in load_json(continued)['inputs'] if x['end_frame']<=60317]
    c=load_json(final)['inputs']
    check(a[-1]['end_frame']==51960 and b[-1]['end_frame']==60317,'Exploration joins differ')
    inputs=[];frame=27606
    for row in a+b+c:
        keys=row.get('keys',[row['key']] if row.get('key') else [])
        frame+=row['hold']+row['released'];check(frame==row['end_frame'],'Exploration frame discontinuity')
        inputs.append({'keys':keys,'hold':row['hold'],'released':row['released'],'end_frame':frame})
    state=SETUP/'opening/natural/final.state';initial=SETUP/'both-logs.sav'
    expected=OUT/'clear-route/final.png'
    check(expected.is_file(),'Final exploration image has not been chosen')
    replay={'rom_sha256':digest(BASELINE.read_bytes()),'initial_state':str(state.relative_to(ROOT)),
            'initial_state_sha256':digest(state.read_bytes()),'initial_save':str(initial.relative_to(ROOT)),
            'initial_save_sha256':digest(initial.read_bytes()),'initial_frame':27606,'inputs':inputs,
            'expected_final_frame':frame,'expected_final_png_sha256':digest(expected.read_bytes()),
            'expected_final_save_sha256':digest((OUT/'clear-route/latest.sav').read_bytes()),
            'exploration_reports':{str(p.relative_to(ROOT)):digest(p.read_bytes()) for p in (first,continued,final)},
            'scope':'Accepted native fresh two-Log opening, first 71 adventure inputs, continued route through first pot recovery, then safer cave continuation. Independent replay performs no mid-route restores or game-state edits. Discarded exploration after the pot checkpoint is excluded.'}
    save(OUT/'replay.json',replay);return replay


def verify():
    mgba.log.silence();replay=load_json(OUT/'replay.json');data=BASELINE.read_bytes()
    check(digest(data)==replay['rom_sha256'],'Cave replay ROM changed')
    build=load_json(BASELINE.parent/'english-build.json');index,_,_=sources(data,build['ledger'])
    state=(ROOT/replay['initial_state']).read_bytes();initial=(ROOT/replay['initial_save']).read_bytes()
    check(digest(state)==replay['initial_state_sha256'] and digest(initial)==replay['initial_save_sha256'],'Cave fixture changed')
    watch=[0x08000000+int(e['offset'],0) for e in load_json(ROOT/'translations/unowned-text-review.json')['entries']]
    folder=OUT/'verification'
    with Session(data,folder,initial) as s:
        c=s.core;check(c.load_raw_state(state) and c.frame_counter==replay['initial_frame'],'Cave restore failed')
        check(battery_snapshot(c)==initial,'Native opening save differs')
        t=trip.RoundtripTrace(c,data,index,watch)
        try:
            for i,row in enumerate(replay['inputs']):
                t.phase=f'input-{i:03d}';codes=[getattr(c,'KEY_'+k) for k in row['keys']]
                if codes:c.set_keys(*codes);t.frames(row['hold']);c.clear_keys(*codes)
                t.frames(row['released']);check(c.frame_counter==row['end_frame'],'Cave replay timing differs')
                if i%40==39:print('Cave clear replay',i+1,'/',len(replay['inputs']),flush=True)
            final=s.capture('final');r=t.report();save(folder/'raw-trace.json',r)
            check(not t.errors and not r['source_reads'],'Cave trace error or unowned source read')
            check(digest((OUT/'clear-route/final.png').read_bytes())==replay['expected_final_png_sha256'],'Reference image changed')
            check(ImageChops.difference(final,Image.open(OUT/'clear-route/final.png').convert('RGB')).getbbox() is None,'Cave replay pixels differ')
            checks=trip.language_checks(r,data,index,build['ledger'])
            saved=battery_snapshot(c);check(digest(saved)==replay['expected_final_save_sha256'],'Exploration save differs')
            check(bytes(c.memory[NAME_RAM:NAME_RAM+8])==trip.EXPECTED_NAME,'Cave route changed Torneko name')
            profile=bytes(c.memory[trip.PROFILE:trip.PROFILE+trip.PROFILE_SIZE])
            (folder/'final.state').write_bytes(bytes(ffi.buffer(c.save_raw_state())))
            (folder/'earned.sav').write_bytes(saved)
            r.update(rom_sha256=digest(data),source_sha256=digest(ORIGINAL_ROM.read_bytes()),
                     checks=checks,inputs=replay['inputs'],replay_sha256=digest((OUT/'replay.json').read_bytes()),
                     output_save_sha256=digest(saved),profile_hex=profile.hex(),final_pixels_match=True,
                     scope='Independent uninterrupted normal-button replay from the native opening. Outcome-specific and cold-save acceptance is recorded separately.')
            save(folder/'trace.json',r)
        finally:t.close()
    check(s.disk_save==saved,'File-backed cartridge save differs')
    print('Normal cave route and language checks passed',flush=True)
    return r,saved


if __name__=='__main__':verify()
