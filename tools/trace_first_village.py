"""Fresh-core opening replay and natural village escort/first chief conversation."""
import argparse
from pathlib import Path
import mgba.log
from mgba._pylib import ffi
from tools.build_first_village import CATALOG,OUTPUT,encode
from tools.build_first_label import ROOT,ORIGINAL_ROM,digest
from tools.trace_opening_story import OpeningTrace
from tools.trace_story_provenance import SAVE
from tools.verify_story_provenance import check_natural
from tools.verify_expansion import Session
from tools.verify_items import write_json,distinct_glyph_observations
from tools.verify_dungeon_interface import check_glyphs
from tools.translation_pipeline import load_json,check,FontZero
from tools.game_text import GameTextCodec
from tools.build_opening_story import encode as encode_opening


def source_index(rom,build):
    entries=list(load_json(ROOT/'translations/master.json')['entries']);by_master={};codec=GameTextCodec(rom)
    old=load_json(ROOT/'build/opening-story/english-build.json')
    for name,relocated in (('opening-story',old['opening']['relocated']),('first-village',build['village']['relocated'])):
        for e in load_json(ROOT/f'translations/{name}.json')['entries']:
            by_master[e['master_id']]=e;at=relocated[e['id']]['offset'];p=codec.parse(rom,at)
            entries.append({'id':e['master_id'],'offset':hex(at),'source_hex':p['raw_hex'],'source_tokens':p['tokens']})
    return entries,by_master


def check_route(report,rom,build):
    index,by_master=source_index(rom,build);proof=check_natural(report,rom,index);font=FontZero(ORIGINAL_ROM.read_bytes());checks=[]
    for v in report['versions']:
        e=by_master[v['source']['master_id']]
        raw,m=(encode if e['id'].startswith('village.') else encode_opening)(e,ORIGINAL_ROM.read_bytes())
        check(v['output_hex']==raw.replace(b'$t',b'Torneko').hex(),'Natural village formatter lost text')
        gs,_=distinct_glyph_observations([g for g in report['positions'] if g['version']==v['serial']])
        checks.append({'id':e['id'],'version':v['serial'],**check_glyphs(gs,m['visible'],font)})
    required={'jp_009ea804','jp_009ea7d0','jp_009ea78c','jp_009d5834','jp_009d5800','jp_009d57c4','jp_009d5774','jp_009d5710','jp_009d56a8','jp_009d5660'}
    old=set(load_json(ROOT/'build/opening-story/verification/natural-yes/trace.json')['proof']['master_ids'])
    check(set(proof['master_ids'])==old|required,'Natural village source sequence differs')
    return proof,checks


def capture():
    mgba.log.silence();rom=(OUTPUT/'torneko3-first-village-english.gba').read_bytes();build=load_json(OUTPUT/'english-build.json')
    index,by_master=source_index(rom,build);folder=OUTPUT/'verification/natural';screens=[]
    replay=ROOT/'build/opening-story/verification/natural-yes/trace.json';inputs=load_json(replay)['inputs']
    with Session(rom,folder,SAVE.read_bytes()) as s:
        s.frames(600);trace=OpeningTrace(s.core,rom,index)
        try:
            trace.phase='opening-replay'
            for row in inputs:
                check(row['hold']==3,'Opening input duration changed')
                s.press(row['key'],row['released'],trace)
            s.capture('opening-bedroom');screens.append('opening-bedroom.png')
            for phase,key,n in (('dismiss','A',1),('to-door','DOWN',16),('align-door','RIGHT',4),('exit','DOWN',20)):
                trace.phase=phase
                for _ in range(n):s.press(key,120,trace)
                s.capture(phase);screens.append(phase+'.png')
            for i in range(30):
                trace.phase=f'village-{i:02d}';s.frames(300,trace)
                last=trace.versions[-1]
                if last['source'].get('master_id')=='jp_009d5660':
                    _,metrics=encode(by_master['jp_009d5660'],ORIGINAL_ROM.read_bytes())
                    gs,_=distinct_glyph_observations([g for g in trace.positions if g['version']==last['serial']])
                    if len(gs)==len(metrics['visible'].replace('\n','')):break
                s.press('A',300,trace);s.capture(trace.phase);screens.append(trace.phase+'.png')
            else:raise ValueError('Natural village route did not finish chief meeting')
            s.frames(300,trace);s.capture('chief-final');screens.append('chief-final.png')
            report=trace.report();write_json(folder/'raw-trace.json',report)
            check(not trace.errors,str(trace.errors));proof,checks=check_route(report,rom,build)
            report.update(rom_sha256=digest(rom),source_sha256=digest(ORIGINAL_ROM.read_bytes()),catalog_sha256=digest(CATALOG.read_bytes()),
                harness_sha256=digest(Path(__file__).read_bytes()),trace_helper_sha256=digest((ROOT/'tools/trace_opening_story.py').read_bytes()),
                initial_save_sha256=digest(SAVE.read_bytes()),opening_replay_sha256=digest(replay.read_bytes()),
                inputs=s.frames_recorded,screens=screens,proof=proof,glyph_checks=checks,
                scope='Fresh emulator and disposable Japanese Adventure Log. Replays the accepted opening then exits the house, follows the escort and completes the first chief meeting using only normal buttons. No state, RAM, register, coordinate or scenario-flag injections. Later village/shrine/companion-choice branches have controlled display coverage only.')
            (folder/'final.state').write_bytes(bytes(ffi.buffer(s.core.save_raw_state())))
            write_json(folder/'trace.json',report)
        finally:trace.close()
    print('Natural village:',proof['buffer_versions'],'messages,',proof['unattributed_ram_reads'],'unattributed reads',flush=True)
    return report


if __name__=='__main__':capture()
