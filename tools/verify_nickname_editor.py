"""Controlled five-slot nickname editor, real joypad editing, all-row displays."""
import argparse
import string
from pathlib import Path
import mgba.log
from mgba._pylib import ffi,lib
from tools.build_ally_nicknames import CATALOG,OUTPUT,expected_compact
from tools.build_first_label import ORIGINAL_ROM,digest
from tools.build_name_entry import LATIN
from tools.verify_ally_nicknames import STATE,generate
from tools.verify_expansion import Session
from tools.verify_tutorial_gameplay import cold_tables,restore
from tools.verify_dungeon_interface import InterfaceTrace,registers,check_glyphs
from tools.verify_items import install_item,write_json
from tools.verify_name_entry import EDIT_BUFFER,KEY_SELECTION,KEY_PAGE,NAME_CURSOR,select_character
from tools.translation_pipeline import check,load_json,FontZero

SOURCE=0x0203F300

class EditorTrace(InterfaceTrace):
    def __init__(self,core):
        self.editor_entries=0;self.editor_returns=[]
        super().__init__(core)
        for address in (0x0806DCDC,0x0807BB62):
            point=ffi.new('struct mBreakpoint*');point.address=address;point.segment=-1;point.type=lib.BREAKPOINT_HARDWARE
            check(self.debugger.platform.setBreakpoint(self.debugger.platform,point)>=0,'Editor breakpoint failed')
    def entered(self,debugger,reason,info):
        super().entered(debugger,reason,info)
        try:
            if info!=ffi.NULL and reason==lib.DEBUGGER_ENTER_BREAKPOINT:
                if info.address==0x0806DCDC:
                    self.editor_entries+=1
                    sp=int(self.cpu.gprs[13])&0xffffffff
                    self.core.memory.u32[sp]=int(self.cpu.gprs[1])&0xffffffff
                    self.core.memory.u32[sp+4]=0
                    registers(self.core,{'r0':0,'r1':0,'r2':SOURCE,'r3':5,'pc':0x0807BAD4})
                elif info.address==0x0807BB62:
                    self.editor_returns.append({'return':int(self.cpu.gprs[0]),'source_hex':bytes(self.core.memory[SOURCE:SOURCE+6]).hex()})
        except Exception as error:self.errors.append(str(error))
        finally:debugger.state=lib.DEBUGGER_RUNNING


def name_display(trace,phase,text,font):
    visible=text+'＊'*(5-len(text))
    draws=[d for d in trace.payloads if d['phase']==phase and bytes.fromhex(d['raw_hex']).split(b'\0')[0]==visible.encode('cp932')]
    check(draws,f'No nickname editor draw for {text}')
    complete=[]
    for draw in draws:
        glyphs=[g for g in trace.positions if g['draw_serial']==draw['serial']]
        if glyphs:complete.append(check_glyphs(glyphs,visible,font))
    check(complete,'Editor name had no glyphs')
    return complete[-1]


def verify(limit=None):
    mgba.log.silence();rom=OUTPUT/'torneko3-ally-nicknames-english.gba';out=OUTPUT/'verification/editor'
    catalog=load_json(CATALOG);font=FontZero(ORIGINAL_ROM.read_bytes());cases=[];alphabet=[]
    with Session(rom.read_bytes(),out) as s:
        tables=cold_tables(s);restore(s,STATE.read_bytes(),tables)
        generated=generate(s.core,21,1);raw=bytes.fromhex(generated['compact_hex'])
        for i,b in enumerate(b'\xA5'*8+raw+b'\xA5'*8):s.core.memory.u8[SOURCE-8+i]=b
        install_item(s.core,0x0200A480,1)
        trace=EditorTrace(s.core);frames=s.frames;s.frames=lambda n,unused=None:trace.frames(n)
        try:
            for phase,key in (('menu','B'),('inventory','A'),('actions','A'),('initial','A')):
                trace.phase=phase;s.press(key,120)
            check(trace.editor_entries==1 and not trace.errors,'Editor fixture entry failed: '+str(trace.errors))
            check(bytes(s.core.memory[EDIT_BUFFER:EDIT_BUFFER+6])==raw,'Recruitment default lost at editor entry')
            name_display(trace,'initial','Goot1',font);s.capture('initial-goot1')
            editor_state=bytes(ffi.buffer(s.core.save_raw_state()))
            for e in catalog['entries'][:limit] if limit else catalog['entries']:
                check(s.core.load_raw_state(editor_state),'Editor state restore failed')
                compact,text=expected_compact(e['display'] or e['english'],9)
                # These bytes were independently checked through native generation
                # for every row/suffix; this fixture isolates editor display.
                for i,b in enumerate(compact.ljust(6,b'\0')):s.core.memory.u8[EDIT_BUFFER+i]=b
                trace.phase=e['id'];s.press('L',15)
                checks=name_display(trace,trace.phase,text,font)
                check(bytes(s.core.memory[EDIT_BUFFER+6:EDIT_BUFFER+32])==b'\0'*26,'Editor display exceeded five slots')
                s.capture(e['id']);cases.append({'id':e['id'],'text':text,'compact_hex':compact.hex(),'checks':checks,'screen':e['id']+'.png'})
                # Release bulky observations after each independent case.
                trace.payloads.clear();trace.positions.clear();trace.draws.clear()
                if (e['row']+1)%25==0:print('editor',e['row']+1,flush=True)
            check(s.core.load_raw_state(editor_state),'Editor restore failed')
            trace.phase='erase'
            for _ in range(5):s.press('B',15)
            check(s.core.memory.u8[EDIT_BUFFER]==0,'Could not erase nickname')
            for start in range(0,62,5):
                name=(string.ascii_uppercase+string.ascii_lowercase+string.digits)[start:start+5]
                trace.phase='alphabet-'+name
                for c in name:select_character(s,c);s.press('A',15)
                expected=bytes(LATIN[c] for c in name)+b'\0'
                check(bytes(s.core.memory[EDIT_BUFFER:EDIT_BUFFER+len(expected)])==expected,'Nickname alphabet failed')
                alphabet.append(name)
                for _ in name:s.press('B',15)
            trace.phase='capacity'
            for c in 'Robby':select_character(s,c);s.press('A',15)
            check(s.core.memory.u32[KEY_SELECTION]==4,'Five characters did not select Done')
            s.press('LEFT',15);s.press('LEFT',15);s.press('A',15)
            check(s.core.memory.u32[NAME_CURSOR]==4,'Next exceeded five nickname slots')
            select_character(s,'X');s.press('A',15)
            name_display(trace,'capacity','RobbX',font)
            check(bytes(s.core.memory[EDIT_BUFFER+6:EDIT_BUFFER+32])==b'\0'*26,'Nickname edit exceeded capacity')
            expected=bytes(LATIN[c] for c in 'RobbX')+b'\0'
            s.press('START',15);s.capture('capacity-robbx')
            check(bytes(s.core.memory[EDIT_BUFFER:EDIT_BUFFER+6])==expected,'Kana shortcut changed Latin nickname')
            trace.phase='done';s.press('R',15);s.press('A',30)
            check(trace.editor_returns and trace.editor_returns[-1]['return']==1,'Nickname editor did not accept name')
            check(trace.editor_returns[-1]['source_hex']==expected.hex(),'Nickname editor commit changed name')
            check(bytes(s.core.memory[SOURCE-8:SOURCE])==b'\xA5'*8 and bytes(s.core.memory[SOURCE+6:SOURCE+14])==b'\xA5'*8,'Nickname commit crossed six-byte buffer')
            check(not trace.errors,str(trace.errors));result={'rom_sha256':digest(rom.read_bytes()),'catalog_sha256':digest(CATALOG.read_bytes()),'harness_sha256':digest(Path(__file__).read_bytes()),'fixture_sha256':digest(STATE.read_bytes()),'limited':bool(limit),'cases':cases,'alphabet':alphabet,'entry_default':'Goot1','editor_returns':trace.editor_returns,'capacity':5,'guards_intact':True,'scope':'Live UI callback redirect into original nickname editor. Initial default from actual recruitment encoder; other rows use controlled editor bytes with native repaint. Real joypad alphabet, erase, case, limit, replacement and Done. Natural recruitment is not exercised.'}
        finally:s.frames=frames;trace.close()
    write_json(out/'verification.json',result);return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--limit',type=int);a=p.parse_args();verify(a.limit)
