"""Reproduce supplied states and verify the screenshot rendering corrections."""
import json
from pathlib import Path
import struct
import mgba.log
import mgba.vfs
from mgba._pylib import ffi, lib
from PIL import Image, ImageDraw

from tools import build_rendering_fixes as b
from tools import verify_core_gameplay as old, verify_dungeon_interface as ui
from tools import verify_tutorial_gameplay as queue
from tools.build_enemies import measure
from tools.build_first_label import ROOT, ORIGINAL_ROM, digest
from tools.translation_pipeline import FontZero, check, load_json
from tools.verify_expansion import Session
from tools.verify_name_entry import EDIT_BUFFER
from tools.verify_first_label import battery_snapshot

OUT=b.OUTPUT/'verification'
STATES={
    'records': ROOT/'saves/records-window-too-long.ss0',
    'status': ROOT/'saves/status-menu-windows-interfere.ss0',
    'history': ROOT/'saves/message-log-exp-gain-improvement-possible.ss0',
}


class FixTrace(ui.InterfaceTrace):
    extra_breaks=(0x0807D8D8,)

    def __init__(self,core):
        super().__init__(core)
        point=ffi.new('struct mBreakpoint*')
        point.address=0x0807D8D8;point.segment=-1;point.type=lib.BREAKPOINT_HARDWARE
        check(self.debugger.platform.setBreakpoint(self.debugger.platform,point)>=0,'Cannot trace native lookahead')

    def entered(self,debugger,reason,info):
        if info!=ffi.NULL and reason==lib.DEBUGGER_ENTER_BREAKPOINT and info.address==0x0807D8D8 and not self.format_stack:
            regs=[int(r)&0xffffffff for r in self.cpu.gprs]
            row=dict(phase=self.phase,caller=f'0x{((regs[14]&~1)-4):08X}',source=f'0x{regs[4]:08X}',
                destination=f'0x{regs[5]:08X}',payload_end=f'0x{regs[2]:08X}',payload_limit=regs[2]-regs[5],
                line_mode=regs[3]&255,frame=self.core.frame_counter,internal_lookahead=True)
            self.formats.append(row);self.format_stack.append(row)
        super().entered(debugger,reason,info)


def restore_file(s,path):
    vf=mgba.vfs.open_path(str(path),'rb')
    try: check(lib.mCoreLoadStateNamed(s.core._core,vf.handle,11),'Cannot load native mGBA state')
    finally:vf.close()


def trace_report(t):
    check(not t.errors,str(t.errors))
    return dict(payloads=t.payloads,glyphs=t.positions)


def captures(data,variant):
    results={}
    for kind in ('records','status'):
        folder=OUT/variant/kind
        with Session(data,folder) as s:
            restore_file(s,STATES[kind]);s.frames(2);s.capture('restored')
            save_before=battery_snapshot(s.core)
            t=FixTrace(s.core)
            try:
                s.press('B',90,t)
                if kind=='status':s.press('B',90,t)
                else:
                    s.press('START',120,t)
                    for _ in range(3):s.press('DOWN',20,t)
                    s.press('A',120,t)
                s.capture('corrected');results[kind]=trace_report(t)
                check(battery_snapshot(s.core)==save_before,'Menu navigation changed save data')
            finally:t.close()
            b.save(folder/'trace.json',results[kind])
    with Session(data,OUT/variant/'keyboard') as s:
        s.frames(600);t=FixTrace(s.core)
        try:
            s.press('START',240,t)
            for _ in range(3):s.press('A',120,t)
            s.capture('erase')
            for _ in range(7):s.press('B',15,t)
            check(s.core.memory.u8[EDIT_BUFFER]==0,'Name field did not erase')
            s.press('L',15,t);s.capture('cancel')
            results['keyboard']=trace_report(t)
        finally:t.close()
        b.save(s.output/'trace.json',results['keyboard'])
    return results


def formatted(s,source,cap=1000,mode=0):
    t=FixTrace(s.core)
    try:
        old.write_bytes(s.core,old.DEST-8,old.GUARD+b'\xA5'*cap+old.GUARD)
        call=ui.native_step(s,t,0x0807D8CC,[source,old.DEST,old.DEST+cap-1,mode])
        raw=old.cstring(s.core,old.DEST,cap)
        check(bytes(s.core.memory[old.DEST-8:old.DEST])==old.GUARD and
              bytes(s.core.memory[old.DEST+cap:old.DEST+cap+8])==old.GUARD,'Formatter bounds changed')
        return raw,call['return_r0']
    finally:t.close()


def formatter_cases(data,variant,plan):
    font=FontZero(ORIGINAL_ROM.read_bytes());results=[]
    names=['Torneko','Ines','WWWWWWW','i'*29,'W'*29,
           "Justice's elder brother",'Crack-billed platypunk']
    with Session(data,OUT/variant/'messages') as s:
        for message in plan['messages']:
            for name in names:
                for number in (0,6,65535,2147483647,-2147483648):
                    check(s.core.load_raw_state(old.STATE.read_bytes()),'Cannot restore formatter fixture')
                    old.slots(s.core,font,'normal')
                    old.write_bytes(s.core,old.ACTOR,name.encode().ljust(30,b'\0'))
                    s.core.memory.u32[old.NUMBER]=number&0xffffffff
                    raw,ret=formatted(s,message['address'])
                    t=FixTrace(s.core)
                    try:
                        queue.prepare_queue(s,t)
                        queued=queue.enqueue(s,t,message['address'],raw)
                    finally:t.close()
                    results.append(dict(id=message['id'],name=name,number=number,raw_hex=raw.hex(),return_r0=ret,
                        widths=[measure(line,font) for line in raw[:-1].decode().split('\n')],queue=queued))
                    if name=='Torneko' and number==6:
                        results[-1]['rendering']=queue.render_queue(s,message['id'],font,queued['rows_hex'],True)
        # Preserve the old wrapping for non-ASCII names, and respect short buffers.
        for name in ('トルネコ','ｱｲｳｴｵ'):
            for cap in (1,8,16,64):
                check(s.core.load_raw_state(old.STATE.read_bytes()),'Cannot restore formatter fixture')
                old.slots(s.core,font,'normal');old.write_bytes(s.core,old.ACTOR,name.encode('cp932').ljust(30,b'\0'))
                raw,ret=formatted(s,plan['messages'][0]['address'],cap)
                results.append(dict(id='compatibility',name=name,capacity=cap,raw_hex=raw.hex(),return_r0=ret))
        # An unrelated template must use the original formatter unchanged.
        for text in (b'$m0 has $d0 HP.\0',b'$m0 reached level\n$d0.\0',b'$i0\n$d0\0'):
            check(s.core.load_raw_state(old.STATE.read_bytes()),'Cannot restore formatter fixture')
            old.slots(s.core,font,'stress');old.write_bytes(s.core,0x0203F100,text)
            raw,ret=formatted(s,0x0203F100)
            results.append(dict(id='unselected',template=text.hex(),raw_hex=raw.hex(),return_r0=ret))
            raw,ret=formatted(s,0x0203F100,mode=1)
            results.append(dict(id='unselected-line',template=text.hex(),raw_hex=raw.hex(),return_r0=ret))
        for message in plan['messages']:
            for cap in (1,8,16):
                check(s.core.load_raw_state(old.STATE.read_bytes()),'Cannot restore short-buffer fixture')
                old.slots(s.core,font,'normal');old.write_bytes(s.core,old.ACTOR,b'Torneko\0');s.core.memory.u32[old.NUMBER]=6
                raw,ret=formatted(s,message['address'],cap,1)
                results.append(dict(id='short-line-buffer',source=message['address'],capacity=cap,raw_hex=raw.hex(),return_r0=ret))
    b.save(OUT/variant/'formatter.json',results)
    return results


def location_cases(data,plan):
    cases=[];font=FontZero(ORIGINAL_ROM.read_bytes())
    with Session(data,OUT/'english/locations') as s:
        for family,rows in [('dungeon',range(64)),('town',plan['town_names'])]:
            for row in rows:
                check(s.core.load_raw_state(old.STATE.read_bytes()),'Cannot restore location fixture')
                t=FixTrace(s.core)
                try:
                    if family=='dungeon':
                        s.core.memory.u32[0x02004F8C]=row//32
                        s.core.memory.u8[0x02004FF0]=row%32
                        s.core.memory.u8[0x02004FF1]=99
                        ui.native_step(s,t,0x0806C8C8,[1])
                        ident=f'dungeon-{row:02d}'
                    else:
                        ui.native_step(s,t,0x0807621C,[1],overrides={0x08066CC8:{'r0':row['index']}})
                        ident=f'town-{row["index"]:02d}'
                        matches=[d for d in t.payloads if bytes.fromhex(d['raw_hex']).split(b'\0')[0]==b'\x03\x12'+row['display'].encode()]
                        check(len(matches)==1,'Incorrect town display: '+row['full'])
                    header=[g for g in t.positions if g['window_origin']==[112,24]]
                    command=[g for g in t.positions if g['window_origin']==[16,24]]
                    check(header and command,'Both status panels must be observed')
                    check(all(g['window_width']==112 and 0<=g['x'] and g['x']+g['advance']<=112 for g in header),
                          'Location clips: '+ident+' '+repr([(g['code'],g['x'],g['advance']) for g in header]))
                    check(all(g['window_width']==80 and g['x']+g['advance']<=80 for g in command),'Command clips')
                    check(16+80+8<=112-8,'Outer window borders intersect')
                    cases.append(dict(id=ident,header_glyphs=len(header),header_right=max(g['x']+g['advance'] for g in header),
                        command_outer_end=104,location_outer_start=104))
                    b.save(s.output/(ident+'.json'),dict(case=cases[-1],payloads=t.payloads,glyphs=t.positions))
                finally:t.close()
                s.frames(2);s.capture(ident)
    return cases


def live_history(data,variant,plan):
    """Generate native messages in a copy of the user's history state."""
    font=FontZero(ORIGINAL_ROM.read_bytes());folder=OUT/variant/'live-history'
    with Session(data,folder) as s:
        restore_file(s,STATES['history']);s.frames(2)
        c=s.core;root=c.memory.u32[0x0200000C];history=root+0x1979C
        t=FixTrace(c);rows=[];entries=[]
        try:
            ui.native_step(s,t,0x0805D0B4,[0])
            for name,number,message in [('Torneko',6,plan['messages'][0]),('Ines',3,plan['messages'][0]),('Ines',3,plan['messages'][2])]:
                old.write_bytes(c,old.ACTOR,name.encode().ljust(30,b'\0'));c.memory.u32[old.NUMBER]=number
                start=c.memory.u16[0x02007434];hstart=c.memory.u32[0x02007948]
                ui.native_step(s,t,0x0805D3D4,[message['address']],stop=0x0805D488)
                count=(c.memory.u16[0x02007434]-start)%16
                current=[old.cstring(c,0x02007440+80*((start+i)%16),80) for i in range(count)]
                for i,raw in enumerate(current):
                    record=bytes(c.memory[history+64*((hstart+i)%20):history+64*((hstart+i)%20)+64])
                    check(record[3:].split(b'\0')[0]+b'\0'==raw,'History differs from combat line')
                rows.extend(raw.hex() for raw in current);entries.append(dict(name=name,number=number,rows=[r.hex() for r in current]))
        finally:t.close()
        history_bytes=bytes(c.memory[history:history+1280]);history_index=c.memory.u32[0x02007948]
        rendered=queue.render_queue(s,'new-messages',font,rows,True)
        # Restore the original active viewer, carrying across only the records
        # and ring cursor written by the native queue. Reopen it normally.
        restore_file(s,STATES['history'])
        old.write_bytes(c,history,history_bytes);c.memory.u32[0x02007948]=history_index
        s.press('B',60)
        for _ in range(4):s.press('DOWN',20)
        s.press('A',60);s.capture('history-redrawn')
        b.save(folder/'report.json',dict(entries=entries,rendering=rendered,rom_sha256=digest(data),
            state_sha256=digest(STATES['history'].read_bytes()),history_base=history,
            scope='Controlled XP/name slots and native message enqueue/render/history in a disposable user-state copy; no real XP award or level change is claimed.'))
        return entries


def main():
    mgba.log.silence()
    inputs={str(p.relative_to(ROOT)):digest(p.read_bytes()) for p in (ROOT/'saves').iterdir() if p.is_file()}
    plan=load_json(b.OUTPUT/'allocation-plan.json');old_data=b.BASELINE.read_bytes();new_data=b.ROM.read_bytes()
    check(digest(new_data)==load_json(b.OUTPUT/'english-build.json')['rom_sha256'],'Candidate hash differs')
    results={}
    for variant,data in [('baseline',old_data),('english',new_data)]:
        results[variant]=captures(data,variant)
        print(variant,'screens captured',flush=True)
        results[variant]['formatter']=formatter_cases(data,variant,plan)
        results[variant]['live_history']=live_history(data,variant,plan)
    locations=location_cases(new_data,plan)
    changed=0
    for before,after in zip(results['baseline']['formatter'],results['english']['formatter'],strict=True):
        check(before['return_r0']==after['return_r0'],'Formatter source advancement changed')
        a=bytes.fromhex(before['raw_hex']);z=bytes.fromhex(after['raw_hex'])
        if a!=z:
            check(before['id'] in b.MESSAGE_IDS,'Unselected/non-ASCII template changed')
            check(len(a)==len(z) and a.replace(b'\n',b' ')==z.replace(b'\n',b' '),'Change exceeds line-break join')
            # Existing deliberately oversized stress names may overflow old rows;
            # any newly joined row itself must respect both limits.
            index=next(i for i,(x,y) in enumerate(zip(a,z)) if x!=y)
            check(a[index]==10 and z[index]==32,'Unexpected changed byte')
            line=z[:index].split(b'\n')[-1]+z[index:].split(b'\n')[0].rstrip(b'\0')
            check(measure(line.decode(),FontZero(ORIGINAL_ROM.read_bytes()))<=208 and len(line)<=59,'Joined row exceeds limits')
            changed+=1
    check(changed>0,'Numeric joins did not execute')
    check([len(e['rows']) for e in results['english']['live_history']]==[1,1,1],'Reported messages are not single lines')
    for kind in ('records','keyboard','status'):
        report=results['english'][kind]
        if kind=='keyboard':
            hints=[d for d in report['payloads'] if bytes.fromhex(d['raw_hex']).startswith((b'B: Erase\0',b'B: Cancel\0'))]
            check(hints,'Missing B hints')
            for d in hints:
                gs=[g for g in report['glyphs'] if g['draw_serial']==d['serial']]
                if gs:check(d['x']==156 and max(g['x']+g['advance'] for g in gs)<=208,'Keyboard hint clips')
        elif kind=='records':
            gs=[g for g in report['glyphs'] if g['window_origin']==[24,16] and g['window_width']==160]
            check(gs and max(g['x']+g['advance'] for g in gs)<=160,'Category selector clips')
    for path,sha in inputs.items():check(digest((ROOT/path).read_bytes())==sha,'User save/state changed')
    b.save(OUT/'initial-checks.json',dict(source_sha256=digest(ORIGINAL_ROM.read_bytes()),rom_sha256=digest(new_data),
        baseline_sha256=digest(old_data),input_hashes=inputs,formatter_cases=len(results['english']['formatter']),
        compacted_cases=changed,full_message_and_fallback_source_returns_preserved=True,
        queue_history_cases=140,location_cases=len(locations),user_files_unchanged=True))
    b.save(OUT/'locations.json',locations)
    print('Formatter cases passed:',len(results['english']['formatter']),'compacted:',changed,flush=True)


if __name__=='__main__':main()
