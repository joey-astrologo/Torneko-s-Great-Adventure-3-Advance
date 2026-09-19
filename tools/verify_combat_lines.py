"""Native approved-span regression gate: formatter, queue/history, continuations."""
import argparse
from collections import Counter
import json
from pathlib import Path
import mgba.log
from tools import build_combat_lines as b, verify_rendering_fixes as v
from tools.translation_pipeline import FontZero,load_json,check
from tools.verify_expansion import Session


def fits(raw,font):
    return len(raw)<=59 and all(32<=c<=126 for c in raw) and sum(max(font.glyph(chr(c))[1:]) for c in raw)<=208


def expect(raw,message,font,capacity=1000):
    # Independent reference model from the original formatted row boundaries.
    original=bytes.fromhex(message['raw_hex']);start=original.index(message['span'].encode())
    skip=original[:start].count(b'\n');count=message['span'].count('\n')
    lines=raw[:-1].split(b'\n')
    if len(raw)>=capacity or len(lines)<skip+count+1:return raw
    span=b' '.join(lines[skip:skip+count+1]);measured=span[1:] if skip==0 and span.startswith(b'!') else span
    if not fits(measured,font):return raw
    return b'\n'.join(lines[:skip]+[span]+lines[skip+count+1:])+b'\0'


def set_values(core,font,profile):
    v.old.slots(core,font,'normal')
    if profile=='normal':actors=['Torneko','Slime','Slime'];items=['Medicinal herb','Bread','Magic shield','Magic shield'];num=6
    elif profile=='wide':actors=['W'*17]*3;items=['W'*20]*4;num=2147483647
    elif profile=='narrow':actors=['i'*29]*3;items=['i'*48]*4;num=-2147483648
    elif profile=='non-ascii':actors=['トルネコ']*3;items=['薬草']*4;num=9999
    elif profile=='suffix':actors=['Crack-billed platypunk']*3;items=['Steel broadsword+99','Steel shield+99','Magic shield','Magic shield'];num=9999
    elif profile=='slot-capacity':actors=['W'*29]*3;items=['i'*99]*4;num=-2147483648
    else:raise ValueError(profile)
    for i,name in enumerate(actors):v.old.write_bytes(core,v.old.ACTOR+i*30,name.encode('cp932').ljust(30,b'\0'))
    for i,name in enumerate(items):v.old.write_bytes(core,v.old.ITEM+i*100,name.encode('cp932').ljust(100,b'\0'))
    for i in range(4):core.memory.u32[v.old.NUMBER+4*i]=num&0xffffffff


def run(data=None,output=None):
    mgba.log.silence();data=b.ROM.read_bytes() if data is None else data
    output=b.OUTPUT/'verification' if output is None else Path(output)
    selection=load_json(b.SELECTION);messages=selection['messages'];font=FontZero(b.ORIGINAL_ROM.read_bytes())
    baseline=b.BASELINE.read_bytes();check(b.digest(baseline)==selection['baseline_sha256'],'Wrong comparison ROM')
    state=v.old.STATE.read_bytes();inputs={str(p):b.digest(p.read_bytes()) for p in (b.ROOT/'saves').iterdir() if p.is_file()}
    results=[];counts=Counter();screens=[]
    profiles=('normal','wide','narrow','non-ascii','suffix','slot-capacity')
    with Session(baseline,output/'baseline') as old,Session(data,output/'english') as new:
        # Exact thresholds, with two independent constraints: a width rejection
        # below 59 bytes, and a 60-byte rejection still below 208 pixels.
        def name_at_width(width):
            for nw in range(30):
                for ni in range(30-nw):
                    for na in range(30-nw-ni):
                        value='W'*nw+'i'*ni+'a'*na
                        if value and sum(max(font.glyph(c)[1:]) for c in value)==width:return value
            raise ValueError('Cannot construct boundary fixture')
        boundary_message=next(m for m in messages if m['id']=='gameplay.001b40c2')
        literal=boundary_message['span'].replace('\n',' ').replace('$m2','')
        literal_width=sum(max(font.glyph(c)[1:]) for c in literal)
        byte_message=next(m for m in messages if m['id']=='gameplay.001b45d0')
        byte_literal=byte_message['span'].replace('\n',' ').replace('$i0','')
        boundaries=[(boundary_message,v.old.ACTOR+60,name_at_width(n-literal_width),f'{n}px') for n in (208,209)]
        boundaries += [(byte_message,v.old.ITEM,'i'*(n-len(byte_literal)),f'{n}bytes') for n in (59,60)]
        for m,slot,value,label in boundaries:
            for s in (old,new):
                check(s.core.load_raw_state(state),'Boundary restore failed');set_values(s.core,font,'normal')
                v.old.write_bytes(s.core,slot,value.encode()+b'\0')
            before,ret=v.formatted(old,m['address']);after,newret=v.formatted(new,m['address'])
            check(after==expect(before,m,font) and ret==newret,'Boundary mismatch '+label)
            check((before!=after)==(label in ('208px','59bytes')),'Boundary did not exercise intended threshold')
            for s,raw in ((old,before),(new,after)):
                t=v.FixTrace(s.core)
                try:
                    v.queue.prepare_queue(s,t,start=15,history_start=19)
                    v.queue.enqueue(s,t,m['address'],raw)
                finally:t.close()
            counts['exact_boundaries']+=1
            results.append(dict(id=m['id'],profile=label,before_hex=before.hex(),after_hex=after.hex()))
        for index,m in enumerate(messages):
            for profile in profiles:
                for s in (old,new):
                    check(s.core.load_raw_state(state),'Cannot restore fixture');set_values(s.core,font,profile)
                before,ret=v.formatted(old,m['address'])
                after,newret=v.formatted(new,m['address'])
                expected=expect(before,m,font)
                check(after==expected,f'Wrong span {m["id"]}/{profile}: {before!r} -> {after!r}, wanted {expected!r}')
                check(newret==ret,'Full formatter advancement changed')
                counts['formatter']+=1;counts['joined' if before!=after else 'fallback']+=1
                result=dict(id=m['id'],profile=profile,before_hex=before.hex(),after_hex=after.hex(),return_r0=newret)
                # Oversized artificial substitutions can already exceed the stock
                # history limit. Test their formatting fallback, not a false claim
                # that the old engine accepts those histories without truncation.
                valid=all(len(line)<=59 for line in before[:-1].lstrip(b'!').split(b'\n'))
                if valid:
                    for s,raw,label in ((old,before,'baseline'),(new,after,'english')):
                        t=v.FixTrace(s.core)
                        try:
                            v.queue.prepare_queue(s,t,start=15,history_start=19)
                            q=v.queue.enqueue(s,t,m['address'],raw)
                            result[label+'_queue']=q
                        finally:t.close()
                    counts['queue_history_pairs']+=1
                    if profile=='normal' and (m['id'] in ('help.001b5b1d','gameplay.001b5913','gameplay.001b468f','tutorial.001b601c') or m['id'].endswith(('5038','505b'))):
                        for s,label in ((old,'baseline'),(new,'english')):
                            rendered=v.queue.render_queue(s,m['id'],font,result[label+'_queue']['rows_hex'],True)
                            screens.append(dict(id=m['id'],variant=label,rendering=rendered))
                else:counts['oversized_original_rows_formatter_only']+=1
                results.append(result)
            if (index+1)%30==0:print('Combat sources checked',index+1,'/',len(messages),flush=True)
        # Short destinations and mode-1 return pointers for every approved span,
        # including sources whose preceding sentence must remain separate.
        for m in messages:
            for cap in (1,8,16,60,64,80):
                for s in (old,new):
                    check(s.core.load_raw_state(state),'Restore failed');set_values(s.core,font,'normal')
                before,ret=v.formatted(old,m['address'],cap,0);after,newret=v.formatted(new,m['address'],cap,0)
                check(after==expect(before,m,font,cap) and ret==newret,'Capacity/full-mode mismatch '+m['id'])
                for record in (r for r in load_json(b.PLAN)['records'] if r['id']==m['id']):
                    before,ret=v.formatted(old,record['key'],cap,1);after,newret=v.formatted(new,record['key'],cap,1)
                    if after!=before or newret!=ret:
                        check(record['skip']==0 and newret==record['end'],'Wrong line-mode source continuation')
                        check(b'\n' not in after and fits(after[:-1].lstrip(b'!'),font),'Unsafe mode-1 line')
                    counts['capacity_line_mode']+=1
                counts['capacity_full_mode']+=1
        # Existing XP/damage messages and all deferred/control/multisentence rows
        # must preserve baseline full formatting and queue/history output.
        untouched=selection['unchanged_messages']
        for r in untouched:
            address=r['address']
            raw=bytes.fromhex(r['raw_hex'])
            check(baseline[address-0x08000000:address-0x08000000+len(raw)]==raw,'Unselected source changed')
            for s in (old,new):
                check(s.core.load_raw_state(state),'Restore failed');set_values(s.core,font,'normal')
            a,ar=v.formatted(old,address);z,zr=v.formatted(new,address)
            check((a,ar)==(z,zr),'Unselected/legacy message changed '+r['id'])
            counts['unselected_legacy']+=1
        # Native continuation flags and preceding attacker records, including ring wrap.
        allocations={a['id']:a['offset']+0x08000000 for a in load_json(b.BASELINE.parent/'english-build.json')['ledger']['allocations']}
        for ident in ('tutorial.001b5038','tutorial.001b505b'):
            m=next(m for m in messages if m['id']==ident)
            for prefix in ('tutorial.001b5021','tutorial.001b5032'):
                for profile in ('normal','wide'):
                    for s,label in ((old,'baseline'),(new,'english')):
                        check(s.core.load_raw_state(state),'Restore failed');set_values(s.core,font,profile)
                        t=v.FixTrace(s.core)
                        try:
                            v.queue.prepare_queue(s,t,start=14,history_start=19)
                            a=v.old.guarded_format(s,t,allocations[prefix]);q1=v.queue.enqueue(s,t,allocations[prefix],a)
                            s.core.memory.u8[0x02007942]=1
                            z=v.old.guarded_format(s,t,m['address']);q2=v.queue.enqueue(s,t,m['address'],z)
                            check(bytes.fromhex(q1['history_hex'][0])[2]==1 and bytes.fromhex(q2['history_hex'][0])[2]==0,'Continuation flag changed')
                            check(bytes(s.core.memory[v.queue.HISTORY+19*64:v.queue.HISTORY+20*64]).hex()==q1['history_hex'][0],'Attacker history overwritten')
                        finally:t.close()
                        if profile=='normal':screens.append(dict(id=ident,variant=label,prefix=prefix,rendering=v.queue.render_queue(s,ident+'-'+prefix,font,q1['rows_hex']+q2['rows_hex'],True)))
                        counts['continuation_sequences']+=1
    check(inputs=={str(p):b.digest(p.read_bytes()) for p in (b.ROOT/'saves').iterdir() if p.is_file()},'User saves changed')
    report=dict(rom_sha256=b.digest(data),baseline_sha256=b.digest(baseline),selection_sha256=b.digest(b.SELECTION.read_bytes()),
                counts=dict(counts),cases=results,rendering=screens,inputs_unchanged=inputs,
                scope='Native controlled formatter, live queue/history, rendering and continuation sequences; not natural battle replay')
    b.save(output/'report.json',report);print('Combat checks passed',dict(counts),flush=True)
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
    run(a.rom.read_bytes() if a.rom else None,a.output)
