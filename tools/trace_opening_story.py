"""Cold-load the translated opening and follow native events with normal inputs."""
import argparse
from pathlib import Path
import struct
import mgba.log
from mgba._pylib import ffi,lib
from tools.trace_story_provenance import StoryTrace,SAVE
from tools.verify_story_provenance import check_natural
from tools.verify_expansion import Session
from tools.verify_items import write_json,distinct_glyph_observations
from tools.verify_dungeon_interface import check_glyphs
from tools.game_text import GameTextCodec
from tools.build_opening_story import OUTPUT,CATALOG,encode
from tools.build_first_label import ORIGINAL_ROM,ROOT,digest
from tools.translation_pipeline import load_json,FontZero,check

class OpeningTrace(StoryTrace):
    def __init__(self,core,rom,master):
        self.positions=[];self.glyph_caller=None;self.menu_positions=[];self.menu_label=None;self.menu_serial=0
        super().__init__(core,rom,master)
        point=ffi.new('struct mBreakpoint*');point.address=0x0808BC78;point.segment=-1;point.type=lib.BREAKPOINT_HARDWARE
        check(self.debugger.platform.setBreakpoint(self.debugger.platform,point)>=0,'Opening glyph probe failed')
    def entered(self,debugger,reason,info):
        try:
            if info!=ffi.NULL and reason==lib.DEBUGGER_ENTER_BREAKPOINT:
                regs=[int(x)&0xffffffff for x in self.cpu.gprs]
                if info.address==0x0808CBA0:
                    raw=bytes(self.core.memory[regs[2]:regs[2]+64]).split(b'\0')[0]
                    self.menu_label=next((s for s in ('Yes','No') if raw==b'\x03\x05\x07'+s.encode()),None)
                    self.menu_serial+=1
                if info.address==0x0808BC4C:self.glyph_caller=(regs[14]&~1)-4
                if info.address==0x0808BC78:
                    if self.glyph_caller==0x08061B4E:
                        check(self.versions,'Glyph lacks source version')
                        _,code,advance=struct.unpack('<IHh',bytes(self.core.memory[regs[0]:regs[0]+8]))
                        window=regs[4];x,y,w,h=struct.unpack('<hhhh',bytes(self.core.memory[window:window+8]))
                        self.positions.append({'version':len(self.versions)-1,'frame':self.core.frame_counter,'caller':'0x08061B4E','code':code,'advance':advance,'x':regs[6],'y':regs[8],
                            'font':self.core.memory.u32[0x020398F8],'spacing':self.core.memory.u16[0x020398DC],'window_origin':[x*8,y*8],'window_width':w*8,'window_height':h*8,'draw_serial':len(self.versions)-1})
                    elif self.menu_label and self.glyph_caller in (0x0808CD04,0x0808CD38):
                        _,code,advance=struct.unpack('<IHh',bytes(self.core.memory[regs[0]:regs[0]+8]))
                        x,y,w,h=struct.unpack('<hhhh',bytes(self.core.memory[regs[4]:regs[4]+8]))
                        self.menu_positions.append({'label':self.menu_label,'frame':self.core.frame_counter,'draw_serial':self.menu_serial,'caller':hex(self.glyph_caller),'code':code,'advance':advance,'x':regs[6],'y':regs[8],
                            'font':self.core.memory.u32[0x020398F8],'spacing':self.core.memory.u16[0x020398DC],'window_origin':[x*8,y*8],'window_width':w*8,'window_height':h*8})
                    return
            super().entered(debugger,reason,info)
        except Exception as error:self.errors.append(str(error))
        finally:debugger.state=lib.DEBUGGER_RUNNING
    def report(self):return {**super().report(),'positions':self.positions,'menu_positions':self.menu_positions}


def capture(choice='yes'):
    mgba.log.silence();rompath=OUTPUT/'torneko3-opening-story-english.gba';rom=rompath.read_bytes();catalog=load_json(CATALOG);build=load_json(OUTPUT/'english-build.json')
    master=load_json(ROOT/'translations/master.json')['entries'];augmented=list(master);codec=GameTextCodec(rom)
    by_master={e['master_id']:e for e in catalog['entries']};font=FontZero(ORIGINAL_ROM.read_bytes())
    for e in catalog['entries']:
        at=build['opening']['relocated'][e['id']]['offset'];p=codec.parse(rom,at)
        augmented.append({'id':e['master_id'],'offset':hex(at),'source_hex':p['raw_hex'],'source_tokens':p['tokens']})
    out=OUTPUT/f'verification/natural-{choice}';screens=[];selected=False
    with Session(rom,out,SAVE.read_bytes()) as s:
        s.frames(600);trace=OpeningTrace(s.core,rom,augmented)
        try:
            for phase,key,wait in (('title','START',240),('slots','A',120),('load','A',120),('opening','A',600)):
                trace.phase=phase;s.press(key,wait,trace);s.capture(phase);screens.append(phase+'.png')
            for i in range(70):
                trace.phase=f'advance-{i+1:02d}'
                current=trace.versions[-1] if trace.versions else None
                is_question=current and current['source'].get('master_id')=='jp_00c2f4e4'
                menu=is_question and any(d['first_frame']>=current['frame'] and d['preview'].endswith('Yes') for d in trace.draws.values())
                if menu and not selected:
                    s.capture('dream-choice');screens.append('dream-choice.png')
                    if choice=='no':s.press('DOWN',30,trace)
                    selected=True
                before=len(trace.versions);s.press('A',300,trace)
                if len(trace.versions)!=before or i%8==7:s.capture(trace.phase);screens.append(trace.phase+'.png')
                reached={v['source'].get('master_id') for v in trace.versions}
                if {'jp_009c1de4','jp_009c1da4'}<=reached:
                    # Preparing a message precedes its first glyph. The bedroom
                    # handoff still needs the normal acknowledgement input.
                    s.frames(300,trace)
                    last=trace.versions[-1];e=by_master[last['source']['master_id']]
                    _,metrics=encode(e,ORIGINAL_ROM.read_bytes())
                    glyphs,_=distinct_glyph_observations([g for g in trace.positions if g['version']==last['serial']])
                    if len(glyphs)==len(metrics['visible'].replace('\n','')):
                        s.capture('bedroom');screens.append('bedroom.png');break
            else:raise ValueError('Translated opening did not reach bedroom conversation')
            if not selected:
                write_json(out/'menu-diagnostic.json',{'versions':trace.versions,'draws':list(trace.draws.values()),'reads':list(trace.reads.values()),'formats':trace.formats})
            check(selected,'Dream Yes/No menu was not reached')
            report=trace.report();write_json(out/'raw-trace.json',report)
            proof=check_natural(report,rom,augmented);expected=set(load_json(ROOT/'build/story-provenance/natural-coverage.json')['master_ids'])
            if choice=='no':expected.add('jp_00c2f4a8')
            check(set(proof['master_ids'])==expected,'Opening route source coverage differs')
            checks=[]
            for v in report['versions']:
                e=by_master[v['source']['master_id']];raw,metrics=encode(e,ORIGINAL_ROM.read_bytes())
                check(v['output_hex']==raw.hex(),'Natural formatter lost translated text')
                glyphs,_=distinct_glyph_observations([g for g in report['positions'] if g['version']==v['serial']])
                checks.append({'version':v['serial'],'id':e['id'],**check_glyphs(glyphs,metrics['visible'],font)})
            menu_checks=[]
            for serial in sorted({g['draw_serial'] for g in trace.menu_positions}):
                glyphs=[g for g in trace.menu_positions if g['draw_serial']==serial];label=glyphs[0]['label']
                menu_checks.append({'label':label,**check_glyphs(glyphs,label,font)})
            check({c['label'] for c in menu_checks}=={'Yes','No'},'Event choices lack complete Latin glyphs')
            check(not trace.errors,str(trace.errors));(out/'final.state').write_bytes(bytes(ffi.buffer(s.core.save_raw_state())))
            report.update({'rom_sha256':digest(rom),'source_sha256':digest(ORIGINAL_ROM.read_bytes()),'catalog_sha256':digest(CATALOG.read_bytes()),'initial_save_sha256':digest(SAVE.read_bytes()),'harness_sha256':digest(Path(__file__).read_bytes()),'choice':choice,'proof':proof,'glyph_checks':checks,'menu_label_checks':menu_checks,'inputs':s.frames_recorded,'screens':screens,'scope':'Fresh emulator with disposable previously created Japanese Adventure Log. Normal joypad input through narration, birthday, dream Yes/No, storm, arrival and bedroom; no ROM/RAM/register redirects or skipped waits. Source index also maps the built payloads to their original master IDs.'})
            write_json(out/'trace.json',report)
        finally:trace.close()
    print('Natural opening',choice,proof['buffer_versions'],'messages;',proof['unattributed_ram_reads'],'unattributed reads',flush=True);return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--choice',choices=['yes','no'],default='yes');a=p.parse_args();capture(a.choice)
