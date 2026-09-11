"""Disposable button-only continuation of a recorded opening save state."""
import argparse
from pathlib import Path
import mgba.log
from mgba._pylib import ffi
from tools.build_first_label import ROOT, digest
from tools.game_text import GameTextCodec
from tools.translation_pipeline import load_json, check
from tools.trace_story_provenance import StoryTrace
from tools.verify_expansion import Session
from tools.verify_items import write_json

BASE = ROOT/'build/opening-story/torneko3-opening-story-english.gba'
STATE = ROOT/'build/opening-story/verification/natural-yes/final.state'
OUT = ROOT/'build/first-village/exploration'


def source_index(rom):
    entries = list(load_json(ROOT/'translations/master.json')['entries'])
    codec = GameTextCodec(rom)
    build = load_json(ROOT/'build/opening-story/english-build.json')
    for e in load_json(ROOT/'translations/opening-story.json')['entries']:
        at = build['opening']['relocated'][e['id']]['offset']; p = codec.parse(rom, at)
        entries.append({'id':e['master_id'],'offset':hex(at),'source_hex':p['raw_hex'],'source_tokens':p['tokens']})
    return entries


def explore(state, name, commands):
    mgba.log.silence(); state=state.resolve(); data = BASE.read_bytes(); folder = OUT/name
    with Session(data, folder) as s:
        s.frames(5)
        check(s.core.load_raw_state(state.read_bytes()), 'Cannot restore exploration fixture')
        trace = StoryTrace(s.core, data, source_index(data))
        try:
            s.capture('start')
            for i, command in enumerate(commands):
                key, _, count = command.partition(':'); n = int(count or 1)
                trace.phase = f'{i:02d}-{key}'
                for _ in range(n):
                    if '+' not in key:s.press(key, 120, trace)
                    else:
                        mask=0
                        for k in key.split('+'):mask|=getattr(s.core,'KEY_'+k)
                        s.core.set_keys(mask);s.frames(3,trace);s.core.clear_keys(mask);s.frames(120,trace)
                        s.frames_recorded.append({'key':key,'hold':3,'released':120})
                s.capture(trace.phase)
            report = trace.report()
            check(not trace.errors, str(trace.errors))
            report.update(rom_sha256=digest(data), initial_state=str(state.relative_to(ROOT)), initial_state_sha256=digest(state.read_bytes()), inputs=s.frames_recorded)
            write_json(folder/'trace.json', report)
            (folder/'final.state').write_bytes(bytes(ffi.buffer(s.core.save_raw_state())))
            for v in report['versions']:print(v['source'].get('master_id'),v['source']['japanese'].replace('\n',' / '), flush=True)
        finally:trace.close()


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('name');p.add_argument('commands',nargs='*');p.add_argument('--state',type=Path,default=STATE)
    a=p.parse_args();explore(a.state,a.name,a.commands)
