"""Write English inscriptions with real joypad input through original item caller."""
from pathlib import Path
import mgba.log
from mgba._pylib import ffi,lib
from tools import verify_inscriptions as v
from tools.verify_ally_nicknames import STATE
from tools.verify_name_entry import select_character,EDIT_BUFFER

class InputTrace(v.ui.InterfaceTrace):
    def __init__(self,core):
        self.entries=0;self.results=[]
        super().__init__(core)
        for at in (0x0806DCDC,0x0807014A):
            p=ffi.new('struct mBreakpoint*');p.address=at;p.segment=-1;p.type=lib.BREAKPOINT_HARDWARE
            v.check(self.debugger.platform.setBreakpoint(self.debugger.platform,p)>=0,'Inscription input breakpoint')
    def entered(self,debugger,reason,info):
        super().entered(debugger,reason,info)
        try:
            if info!=ffi.NULL and reason==lib.DEBUGGER_ENTER_BREAKPOINT:
                if info.address==0x0806DCDC:
                    self.entries+=1;callback=int(self.cpu.gprs[1])&0xffffffff;item=int(self.cpu.gprs[0])&0xffffffff
                    v.ui.registers(self.core,{'r0':callback,'r1':item,'r2':0,'pc':0x0807009C})
                elif info.address==0x0807014A:
                    item=int(self.cpu.gprs[4])&0xffffffff;self.results.append({'record':hex(item),'item_id':self.core.memory.u16[item+14],'record_hex':bytes(self.core.memory[item:item+24]).hex()})
        except Exception as e:self.errors.append(str(e))
        finally:debugger.state=lib.DEBUGGER_RUNNING


def verify():
    mgba.log.silence();rom=v.b.OUTPUT/'torneko3-inscriptions-english.gba';data=rom.read_bytes();entries=v.load_json(v.b.CATALOG)['entries'];cases=[]
    with v.Session(data,v.b.OUTPUT/'verification/input') as s:
        caches=v.queue.cold_tables(s)
        for item in (192,193,213,240):
            e=next(e for e in entries if e['item_id']==item);v.queue.restore(s,STATE.read_bytes(),caches);c=s.core;v.old.write_bytes(c,v.LEARNED,b'\xff'*8);v.install_item(c,v.ITEM,198)
            before=bytes(c.memory[v.ITEM-8:v.ITEM+32]);t=InputTrace(c);frames=s.frames;s.frames=lambda n,unused=None:t.frames(n)
            try:
                for key in ('B','A','A','A'):s.press(key,120)
                v.check(t.entries==1 and not t.errors,'Inscription editor entry failed '+str(t.errors));v.check(c.memory.u8[EDIT_BUFFER]==0,'Blank inscription editor not empty')
                for ch in e['english']:select_character(s,ch);s.press('A',15)
                compact=bytes(v.LATIN[ch] for ch in e['english'])+b'\0';v.check(bytes(c.memory[EDIT_BUFFER:EDIT_BUFFER+len(compact)])==compact,'Inscription joypad compact bytes differ');s.capture('entry-'+str(item));s.press('R',15);s.press('A',60)
                v.check(t.results and t.results[-1]['item_id']==item,'Native inscription caller did not convert item');result=t.results[-1];raw=bytes.fromhex(result['record_hex']);v.check(raw[4:4+len(compact)]==compact and raw[11]==0,'Native inscription field/terminator differs')
                v.check(bytes(c.memory[v.ITEM-8:v.ITEM])==before[:8] and bytes(c.memory[v.ITEM+24:v.ITEM+32])==before[32:],'Inscription caller crossed item record');v.check(not t.errors,str(t.errors));s.capture('result-'+str(item));cases.append({'item_id':item,'input':e['english'],'compact_hex':compact.hex(),'native_result':result,'guards_intact':True,'screens':['entry-'+str(item)+'.png','result-'+str(item)+'.png']});print('joypad inscription',e['english'],'passed',flush=True)
            finally:s.frames=frames;t.close()
        result={'rom_sha256':v.digest(data),'catalog_sha256':v.digest(v.b.CATALOG.read_bytes()),'harness_sha256':v.digest(Path(__file__).read_bytes()),'fixture_sha256':v.digest(STATE.read_bytes()),'cases':cases,'scope':'Four controlled inventory callback redirects into complete native item-name caller 0807009C, then real joypad entry, original seven-slot stack buffer, compact item-field commit and English matcher conversion. Original callback drives UI. Scroll effect consumption and persistent save remain separate.'};v.write_json(s.output/'verification.json',result)
    return result

if __name__=='__main__':verify()
