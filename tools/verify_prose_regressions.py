"""Check accepted menus/title and the natural defeat route on revised prose."""
import argparse
import mgba.log
from mgba._pylib import ffi, lib
from PIL import Image
from tools import build_prose_review as b
from tools.build_first_label import ROOT, ORIGINAL_ROM, digest
from tools.prose_review import save
from tools.translation_pipeline import check, load_json
from tools.game_text import GameTextCodec

OUT=b.OUTPUT/'verification'


def verify(phase):
    mgba.log.silence();data=b.ROM.read_bytes()
    build=load_json(b.OUTPUT/'english-build.json')
    check(digest(data)==build['rom_sha256'],'Wrong prose ROM')
    before={str(p.relative_to(ROOT)):digest(p.read_bytes()) for p in (ROOT/'saves').rglob('*') if p.is_file()}
    folder=OUT/phase;folder.mkdir(parents=True,exist_ok=True)
    result={'phase':phase,'rom_sha256':digest(data),'source_sha256':digest(ORIGINAL_ROM.read_bytes())}
    if phase=='render':
        from tools import verify_rendering_fixes as v
        accepted=v.OUT;v.OUT=folder
        plan=load_json(v.b.OUTPUT/'allocation-plan.json')
        captures=v.captures(data,'english')
        for kind in ('keyboard','records'):
            r=captures[kind]
            if kind=='keyboard':
                hints=[d for d in r['payloads'] if bytes.fromhex(d['raw_hex']).startswith((b'B: Erase\0',b'B: Cancel\0'))]
                check(hints,'Missing keyboard hints')
                for d in hints:
                    gs=[g for g in r['glyphs'] if g['draw_serial']==d['serial']]
                    if gs:check(d['x']==156 and max(g['x']+g['advance'] for g in gs)<=208,'Hint clips')
            else:
                gs=[g for g in r['glyphs'] if g['window_origin']==[24,16] and g['window_width']==160]
                check(gs and max(g['x']+g['advance'] for g in gs)<=160,'Records clips')
        current=v.formatter_cases(data,'english',plan)
        prior=load_json(accepted/'english/formatter.json')
        for old,new in zip(prior,current,strict=True):
            for k in ('id','raw_hex','return_r0'):
                check(old[k]==new[k],'Accepted XP formatter changed: '+k)
            if 'queue' in old:
                for k in ('rows_hex','history_hex','guards_intact'):
                    check(old['queue'][k]==new['queue'][k],'Accepted XP queue/history changed')
        history=v.live_history(data,'english',plan)
        check([len(e['rows']) for e in history]==[1,1,1],'Live history lines changed')
        locations=v.location_cases(data,plan);save(folder/'locations.json',locations)
        result.update(formatter_cases=len(current),queue_cases=sum('queue' in c for c in current),
                      location_cases=len(locations),live_history=history,menu_hints_and_bounds=True,
                      scope='Native menu navigation, guarded formatter/queue/history and controlled location selectors; real XP awards remain separate.')
    elif phase=='title':
        from tools import verify_title_art as v
        accepted=v.OUT;v.OUT=folder
        profiles=[]
        for profile,initial in (('empty',None),('user-save',(ROOT/'saves/torneko3-english.sav').read_bytes())):
            screens,r=v.run(data,'english-'+profile,initial)
            prior=load_json(accepted/'verification'/('english-'+profile)/'native.json')
            check(r['prompt_phases']==prior['prompt_phases'],'Title prompt timing changed')
            for name,pixels in screens.items():
                path=accepted/'verification'/('english-'+profile)/(name+'.png')
                check(Image.open(path).convert('RGB').tobytes()==pixels,'Accepted title/menu pixels changed: '+name)
            profiles.append({'profile':profile,'unchanged_screens':len(screens),'prompt_frames':len(r['prompt_phases']),
                             'exact_title_pixels_and_palette':True,'save_unchanged':r['save_unchanged']})
        result.update(profiles=profiles,scope='Cold native boot, palette, fade, blink and real Start/Settings/Records/back inputs compared with accepted title captures.')
    else:
        from tools import verify_result_runtime as v
        v.REPLAY=ROOT/'tools/prose-result-replay.json'
        class CurrentResultTrace(v.ResultTrace):
            def __init__(self,*args):
                super().__init__(*args)
                point=ffi.new('struct mBreakpoint*')
                point.address=0x0807D8D8;point.segment=-1;point.type=lib.BREAKPOINT_HARDWARE
                check(self.debugger.platform.setBreakpoint(self.debugger.platform,point)>=0,
                      'Cannot observe accepted XP lookahead')
            def entered(self,debugger,reason,info):
                if info!=ffi.NULL and reason==lib.DEBUGGER_ENTER_BREAKPOINT and info.address==0x0807D8D8:
                    if not self.format_stack:
                        regs=[int(r)&0xffffffff for r in self.cpu.gprs]
                        row=dict(phase=self.phase,caller=hex((regs[14]&~1)-4),source=hex(regs[4]),
                                 destination=hex(regs[5]),payload_end=hex(regs[2]),payload_limit=regs[2]-regs[5],
                                 line_mode=regs[3]&255,frame=self.core.frame_counter,internal_lookahead=True)
                        self.formats.append(row);self.format_stack.append(row)
                    debugger.state=lib.DEBUGGER_RUNNING
                    return
                super().entered(debugger,reason,info)
        v.ResultTrace=CurrentResultTrace
        original_sources=v.sources
        def effective_sources(data,ledger):
            index,by_address,hashes=original_sources(data,ledger)
            codec=GameTextCodec(data)
            for r,e,new in b.revisions(ORIGINAL_ROM.read_bytes()):
                if r['catalog'] not in ('opening-story','first-village','early-journey','shared-story','story-completion','dungeon-events'):continue
                target=int.from_bytes(data[b.pointer_words(e)[0]:b.pointer_words(e)[0]+4],'little')-0x08000000
                parsed=codec.parse(data,target)
                index.append({'id':e['master_id'],'offset':hex(target),'source_hex':parsed['raw_hex'],'source_tokens':parsed['tokens']})
                by_address[target+0x08000000]=(new,r['catalog'])
            return index,by_address,hashes
        v.sources=effective_sources
        v.b.OUTPUT=folder
        r=v.route(data,build,'english')
        target=next(e['offset']+0x08000000 for e in load_json(b.PLAN)['entries'] if e['id']=='result.000dc668')
        # Trace the original ending reader, including its distinct statistics source.
        check(any(int(f['source'],0)==target for f in r['formats']), 'Natural ending did not read revised XP statistics')
        check(not r['cartridge_save_changed'],'Defeat route changed cartridge save')
        result.update(animation_steps=len(r['animation']),pixels=r['pixels'],
                      revised_statistics_source=hex(target),normal_return_to_town=True,cartridge_save_unchanged=True,
                      scope=r['scope'])
    for path,sha in before.items():check(digest((ROOT/path).read_bytes())==sha,'User file changed: '+path)
    result.update(user_files_unchanged=True,user_file_sha256=before,status='passed')
    save(folder/'acceptance.json',result)
    print(phase,'regression PASSED',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('phase',choices=('render','title','result'))
    verify(p.parse_args().phase)
