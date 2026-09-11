"""Trace event operand -> story formatter -> versioned RAM bytes -> native reads."""
import argparse
from collections import Counter
from pathlib import Path
import struct
import mgba.log
from mgba._pylib import ffi,lib
from tools.audit_text_coverage import SourceIndex,cartridge_offset
from tools.build_first_label import ORIGINAL_ROM,ROOT,digest
from tools.game_text import GameTextCodec,DecodeError,character_width
from tools.trace_text_systems import ReaderTrace,hex_address
from tools.translation_pipeline import check,load_json,atomic_write
from tools.verify_expansion import Session

OUTPUT=ROOT/'build/story-provenance'
SAVE=ROOT/'build/text-coverage/runtime/creation/created.sav'
WRAPPERS=(0x08061200,0x08061244,0x0806128C,0x080612D4,0x08061320)
STORY_CALLERS=(0x080618F4,0x08061A9C,0x08061AD2)
PREPARE_CALLS={0x08061228,0x08061278,0x080612C0,0x0806130A,0x08061356}


class StoryTrace(ReaderTrace):
    def __init__(self,core,rom,master):
        self.rom=rom;self.index=SourceIndex(master);self.codec=GameTextCodec(rom)
        self.commands=[];self.latest_command={};self.wrappers=[];self.preparations=[];self.versions=[]
        self.ram_reads={};self.unattributed=[];self.last_wrapper=None;self.last_prepare=None
        super().__init__(core)
        for address in (0x08064E42,0x08061680,*WRAPPERS):
            point=ffi.new('struct mBreakpoint*');point.address=address;point.segment=-1;point.type=lib.BREAKPOINT_HARDWARE
            check(self.debugger.platform.setBreakpoint(self.debugger.platform,point)>=0,'Cannot add story trace breakpoint')

    def source(self,address):
        at=cartridge_offset(address,len(self.rom))
        if not address:return {'kind':'null_source'}
        if at is None:return {'kind':'RAM_or_other','address':hex_address(address)}
        location=self.index.locate(at)
        try:p=self.codec.parse(self.rom,at);preview=p['display'];raw=p['raw_hex']
        except DecodeError as error:preview=str(error);raw=None
        return {'address':hex_address(address),'offset':hex_address(at),**location,'japanese':preview,'source_hex':raw}

    def entered(self,debugger,reason,info):
        try:
            if info!=ffi.NULL and reason==lib.DEBUGGER_ENTER_BREAKPOINT:
                regs=[int(v)&0xFFFFFFFF for v in self.cpu.gprs];pc=info.address;caller=(regs[14]&~1)-4
                if pc==0x08064E42:
                    cursor=regs[0];raw=bytes(self.core.memory[cursor:cursor+8]);command,operand=struct.unpack('<II',raw)
                    at=cartridge_offset(cursor,len(self.rom));same=at is not None and self.rom[at:at+8]==raw
                    row={'serial':len(self.commands),'frame':self.core.frame_counter,'phase':self.phase,'controller':hex_address(regs[7]),
                        'cursor':hex_address(cursor),'command_word':hex_address(command),'opcode':command&255,'operand':hex_address(operand),
                        'operand_word':hex_address(cursor+4),'raw_hex':raw.hex(),'command_in_original_rom':same}
                    self.commands.append(row);self.latest_command[regs[7]]=row
                    check(len(self.commands)<100000,'Unbounded event trace')
                elif pc in WRAPPERS:
                    command=self.latest_command.get(regs[7]);associated=None
                    # A wrapper's direct caller must be in the event dispatch,
                    # and its unchanged argument must equal this controller's operand.
                    if command and 0x08064E28<=caller<0x08066500 and int(command['operand'],0)==regs[0]:associated=command['serial']
                    row={'serial':len(self.wrappers),'frame':self.core.frame_counter,'entry':hex_address(pc),'caller':hex_address(caller),
                        'source':self.source(regs[0]),'event_serial':associated}
                    self.wrappers.append(row);self.last_wrapper=row
                elif pc==0x08061680:
                    wrapper=self.last_wrapper
                    associated=wrapper['serial'] if caller in PREPARE_CALLS and wrapper and wrapper['source'].get('address')==hex_address(regs[3]) else None
                    row={'serial':len(self.preparations),'frame':self.core.frame_counter,'caller':hex_address(caller),'structure':hex_address(regs[0]),
                        'window':regs[1],'flags':hex_address(regs[2]),'source':self.source(regs[3]),'wrapper_serial':associated}
                    self.preparations.append(row);self.last_prepare=row
                elif pc==0x0807D8CC and caller==0x08061726:
                    prepare=self.last_prepare
                    check(prepare and prepare['source'].get('address')==hex_address(regs[0]),'Formatter source lost preparation origin')
                    check(regs[1]==int(prepare['structure'],0)+12 and regs[2]-regs[1]==1023,'Unexpected story buffer layout')
                    version={'serial':len(self.versions),'frame':self.core.frame_counter,'phase':self.phase,'preparation_serial':prepare['serial'],
                        'format_serial':len(self.formats),'source':prepare['source'],'destination':hex_address(regs[1]),'limit':hex_address(regs[2])}
                    self.versions.append(version)
                elif pc==0x0808C72C and caller in STORY_CALLERS:
                    address=regs[0];raw=bytes(self.core.memory[address:address+2]);raw=raw[:character_width(raw[0])]
                    version=next((v for v in reversed(self.versions) if int(v['destination'],0)<=address<=int(v['limit'],0)),None)
                    if version:
                        formatted=self.formats[version['format_serial']];check('output_hex' in formatted,'Story reads unfinished formatter output')
                        offset=address-int(version['destination'],0);payload=bytes.fromhex(formatted['output_hex'])
                        check(payload[offset:offset+len(raw)]==raw,'RAM story bytes differ from their originating formatter output')
                        key=(version['serial'],offset,caller,raw.hex())
                        if key not in self.ram_reads:self.ram_reads[key]={'version_serial':version['serial'],'byte_delta':offset,'caller':hex_address(caller),'raw_hex':raw.hex(),'count':0}
                        self.ram_reads[key]['count']+=1
                    else:self.unattributed.append({'frame':self.core.frame_counter,'address':hex_address(address),'caller':hex_address(caller),'raw_hex':raw.hex()})
            super().entered(debugger,reason,info)
        except Exception as error:self.errors.append(str(error))
        finally:debugger.state=lib.DEBUGGER_RUNNING

    def report(self):
        report=super().report()
        for v in self.versions:
            f=self.formats[v['format_serial']];check('output_hex' in f,'Unfinished story format')
            v['output_hex']=f['output_hex'];v['written_bytes']=f['written_bytes']
        return {**report,'commands':self.commands,'wrappers':self.wrappers,'preparations':self.preparations,
            'versions':self.versions,'story_ram_reads':list(self.ram_reads.values()),'unattributed_story_reads':self.unattributed}


def capture(advances=48):
    mgba.log.silence();rom=ORIGINAL_ROM.read_bytes();master=load_json(ROOT/'translations/master.json')['entries'];save=SAVE.read_bytes()
    folder=OUTPUT/'natural';screens=[]
    with Session(rom,folder,save) as session:
        session.frames(600);trace=StoryTrace(session.core,rom,master)
        try:
            for phase,key,wait in (('title','START',240),('slots','A',120),('load','A',120),('opening','A',600)):
                trace.phase=phase;session.press(key,wait,trace)
                session.capture(phase);screens.append(phase+'.png')
            for i in range(advances):
                trace.phase=f'advance-{i+1:02d}';before=len(trace.versions);session.press('A',300,trace)
                if len(trace.versions)!=before or i%8==7:
                    session.capture(trace.phase);screens.append(trace.phase+'.png')
                if (i+1)%8==0:print('Advances',i+1,'story versions',len(trace.versions),'commands',len(trace.commands),flush=True)
            report=trace.report()
            report.update({'source_sha256':digest(rom),'initial_save_sha256':digest(save),'master_sha256':digest((ROOT/'translations/master.json').read_bytes()),
                'harness_sha256':digest(Path(__file__).read_bytes()),'reader_helper_sha256':digest((ROOT/'tools/trace_text_systems.py').read_bytes()),
                'boot_frames_before_trace':600,'advances':advances,'inputs':session.frames_recorded,'screens':screens,
                'scope':'Unmodified Japanese ROM with disposable earlier new-log save. Normal button inputs; no ROM/register/text redirects. Tracks original event fetch, text wrappers, formatter and story RAM reads; coverage is limited to the reached route.'})
            check(not trace.errors,'Native trace errors')
            state=session.core.save_raw_state();check(state is not None,'Cannot save final route fixture')
            atomic_write(folder/'final.state',bytes(ffi.buffer(state)))
            atomic_write(folder/'trace.json',( __import__('json').dumps(report,ensure_ascii=False,indent=2)+'\n').encode())
        finally:trace.close()
    print('Natural trace:',len(report['versions']),'versions;',len(report['story_ram_reads']),'attributed RAM reads;',len(report['unattributed_story_reads']),'unattributed',flush=True)
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--advances',type=int,default=48)
    capture(p.parse_args().advances)
