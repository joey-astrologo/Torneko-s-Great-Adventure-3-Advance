"""Real joypad regression checks for both shared keyboard codecs."""
import argparse
from pathlib import Path
import mgba.log
from mgba._pylib import ffi,lib
from tools import verify_keyboard_completion as v
from tools.verify_ally_nicknames import STATE
from tools.verify_name_entry import select_character,EDIT_BUFFER,KEY_PAGE,KEY_SELECTION
from tools.verify_items import install_item,write_json
from tools.translation_pipeline import check

class InputTrace(v.ui.InterfaceTrace):
    def __init__(self,core,codec,history):
        self.codec=codec;self.history=history;self.entries=0;self.returns=[]
        super().__init__(core)
        for at in (0x0806DCDC,0x0807BB62):
            p=ffi.new('struct mBreakpoint*');p.address=at;p.segment=-1;p.type=lib.BREAKPOINT_HARDWARE
            check(self.debugger.platform.setBreakpoint(self.debugger.platform,p)>=0,'Keyboard input breakpoint')
    def entered(self,debugger,reason,info):
        super().entered(debugger,reason,info)
        try:
            if info!=ffi.NULL and reason==lib.DEBUGGER_ENTER_BREAKPOINT:
                if info.address==0x0806DCDC:
                    self.entries+=1;sp=int(self.cpu.gprs[13])&0xffffffff
                    self.core.memory.u32[sp]=int(self.cpu.gprs[1])&0xffffffff;self.core.memory.u32[sp+4]=0 if self.history else 0xffffffff
                    v.ui.registers(self.core,{'r0':5,'r1':self.codec,'r2':v.INPUT,'r3':18 if self.codec else 7,'pc':0x0807BAD4})
                elif info.address==0x0807BB62:self.returns.append({'return':int(self.cpu.gprs[0])&0xffffffff,'source_hex':bytes(self.core.memory[v.INPUT:v.INPUT+32]).hex()})
        except Exception as e:self.errors.append(str(e))
        finally:debugger.state=lib.DEBUGGER_RUNNING


def verify(variant):
    mgba.log.silence();rom=v.BASELINE if variant=='baseline' else v.b.OUTPUT/'torneko3-keyboard-completion-english.gba';data=rom.read_bytes();cases=[]
    with v.Session(data,v.b.OUTPUT/'verification'/('input-'+variant)) as s:
        caches=v.queue.cold_tables(s)
        for codec in (0,1):
            for history in (False,True):
                v.queue.restore(s,STATE.read_bytes(),caches);c=s.core;v.old.write_bytes(c,v.INPUT-8,v.old.GUARD+b'\0'*32+v.old.GUARD);install_item(c,0x0200A480,1)
                t=InputTrace(c,codec,history);frames=s.frames;s.frames=lambda n,unused=None:t.frames(n);events=[];name=f'input-c{codec}-h{int(history)}'
                try:
                    for phase,key in (('menu','B'),('inventory','A'),('actions','A'),('initial','A')):t.phase=phase;s.press(key,120)
                    check(t.entries==1 and not t.errors,'Keyboard input fixture entry failed '+str(t.errors));check(c.memory.u8[EDIT_BUFFER]==0,'Keyboard initial source changed')
                    if codec==0:
                        for ch in 'Torneko':select_character(s,ch);s.press('A',15)
                        check(bytes(c.memory[EDIT_BUFFER:EDIT_BUFFER+8])==bytes(v.LATIN[ch] for ch in 'Torneko')+b'\0','Latin keyboard input differs')
                        check(c.memory.u32[KEY_SELECTION]==4,'Seven-position keyboard did not select Done')
                    else:
                        for key in ('A','L','A','RIGHT','A','B','START','DOWN','A'):
                            s.press(key,15);events.append({'key':key,'page':c.memory.u32[KEY_PAGE],'selection':c.memory.u32[KEY_SELECTION],'compact_hex':bytes(c.memory[EDIT_BUFFER:EDIT_BUFFER+32]).hex()})
                        check(c.memory.u8[EDIT_BUFFER]!=0,'Kana keyboard entered no characters')
                    expected=bytes(c.memory[EDIT_BUFFER:EDIT_BUFFER+32]);s.capture(name);s.press('R',15);s.press('A',30)
                    check(t.returns and t.returns[-1]['return']==1,'Keyboard Done return differs');check(bytes(c.memory[v.INPUT:v.INPUT+32])==expected,'Keyboard commit differs')
                    check(bytes(c.memory[v.INPUT-8:v.INPUT])==v.old.GUARD and bytes(c.memory[v.INPUT+32:v.INPUT+40])==v.old.GUARD,'Keyboard source guard changed');check(not t.errors,str(t.errors))
                    cases.append({'id':name,'codec':codec,'history':history,'events':events,'returns':t.returns,'guards_intact':True,'screen':name+'.png'});print(variant,name,'passed',flush=True)
                finally:s.frames=frames;t.close()
        result={'variant':variant,'rom_sha256':v.digest(data),'harness_sha256':v.digest(Path(__file__).read_bytes()),'fixture_sha256':v.digest(STATE.read_bytes()),'cases':cases,'scope':'Controlled live inventory callback redirected to the native editor, with actual frame callback and real joypad events. Both codecs/history flags, Latin Torneko seven-slot limit, kana case/selection/erase/shortcut and Done. No user save modified.'};write_json(s.output/'verification.json',result)
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('variant',choices=('english','baseline'));verify(p.parse_args().variant)
