"""Record normal-button cave exploration from a pinned, native opening checkpoint."""
import json
import argparse
import sys
from mgba._pylib import ffi
import mgba.log
from tools.build_first_label import ROOT, digest
from tools.audit_scene_resources import BASELINE
from tools.verify_expansion import Session
from tools.verify_inventory_notice import NoticeTrace
from tools.verify_natural_cave import sources
from tools.verify_first_label import battery_snapshot
from tools.translation_pipeline import load_json, check

OUT = ROOT/'build/completion/cave-clear/exploration'
SETUP = ROOT/'build/completion/roundtrip/verification/setup'
STATE = SETUP/'opening/natural/final.state'
SAVE = SETUP/'both-logs.sav'


def run():
    global STATE, OUT
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--resume-start',action='store_true')
    parser.add_argument('--state')
    parser.add_argument('--output')
    args=parser.parse_args();resume=args.resume_start or bool(args.state)
    if resume:
        STATE = OUT/'floor-one-start.state'
        OUT = OUT.parent/'continued'
    if args.state: STATE=ROOT/args.state
    if args.output: OUT=ROOT/args.output
    mgba.log.silence(); data = BASELINE.read_bytes(); state = STATE.read_bytes(); initial = SAVE.read_bytes()
    check(digest(data) == '8757bf5cd89e6b935c8f99c431600eb6b5367ad9e9078158a84c047cf6d6e960', 'Exploration ROM differs')
    index, _, _ = sources(data, load_json(BASELINE.parent/'english-build.json')['ledger'])
    watch = [0x08000000+int(e['offset'], 0) for e in load_json(ROOT/'translations/unowned-text-review.json')['entries']]
    with Session(data, OUT, initial) as s:
        c = s.core; check(c.load_raw_state(state), 'Native checkpoint restore failed')
        t = NoticeTrace(c, data, index, watch)
        def snapshot(name):
            s.capture(name)
            report = t.report(); report.update(rom_sha256=digest(data), initial_state=str(STATE.relative_to(ROOT)),
                initial_state_sha256=digest(state), initial_save=str(SAVE.relative_to(ROOT)), initial_save_sha256=digest(initial),
                inputs=s.frames_recorded, scope='Exploratory normal buttons from the native two-Log opening. No game-state edits; acceptance requires a separate replay.')
            (OUT/'readers.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
            raw = bytes(ffi.buffer(c.save_raw_state())); (OUT/'latest.state').write_bytes(raw); (OUT/(name+'.state')).write_bytes(raw)
            (OUT/'latest.sav').write_bytes(battery_snapshot(c))
            root = c.memory.u32[0x0200000C]; actor = c.memory.u32[root+0x19EE4] if root else 0
            info = {'name': name, 'frame': c.frame_counter, 'unowned_reads': len(t.source_reads), 'errors': t.errors,
                'dungeon_root': hex(root), 'player': hex(actor),
                'last_messages': [bytes.fromhex(v['output_hex']).decode('ascii','replace') for v in t.versions[-2:]],
                'last_draws': [d['preview'] for d in list(t.draws.values())[-8:]]}
            if actor:
                info.update(hp=c.memory.u32[actor+0x54], max_hp=c.memory.u32[actor+0x58],
                            player_prefix_hex=bytes(c.memory[actor:actor+0x30]).hex())
            print(json.dumps(info, ensure_ascii=False), flush=True)
        try:
            replay = [] if resume else load_json(ROOT/'build/completion/roundtrip/verification/adventure/trace.json')['inputs'][:71]
            for i, a in enumerate(replay):
                t.phase=f'setup-{i:03d}'; key=getattr(c,'KEY_'+a['key']); c.set_keys(key);t.frames(a['hold']);c.clear_keys(key);t.frames(a['released'])
                check(c.frame_counter==a['end_frame'],'Setup timing differs');s.frames_recorded.append(dict(a))
            snapshot('floor-one-start')
            for line in sys.stdin:
                command=json.loads(line)
                if command.get('quit'):break
                for action in command.get('actions',[command]):
                    name=action.get('name',f'input-{len(s.frames_recorded):03d}');t.phase=name
                    keys=action.get('keys',[action['key']] if action.get('key') else [])
                    codes=[getattr(c,'KEY_'+k) for k in keys]
                    for _ in range(action.get('repeat',1)):
                        hold=action.get('hold',3) if keys else 0;wait=action.get('wait',120)
                        if keys:c.set_keys(*codes);t.frames(hold);c.clear_keys(*codes)
                        t.frames(wait);s.frames_recorded.append({'keys':keys,'hold':hold,'released':wait,'end_frame':c.frame_counter})
                    snapshot(name)
        finally:t.close()
    print('Closed native save',digest(s.disk_save),flush=True)


if __name__=='__main__':run()
