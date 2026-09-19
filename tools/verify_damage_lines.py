"""Compare native received/outgoing damage formatting, queue/history and rendering."""
import mgba.log
from tools import build_damage_lines as b, verify_rendering_fixes as v
from tools.build_enemies import measure
from tools.translation_pipeline import FontZero, load_json, check
from tools.verify_expansion import Session


def run(data=None,output=None):
    mgba.log.silence();plan=load_json(b.PLAN);font=FontZero(b.ORIGINAL_ROM.read_bytes())
    data=b.ROM.read_bytes() if data is None else data
    output=b.OUTPUT if output is None else output
    inputs={str(p):b.digest(p.read_bytes()) for p in (b.ROOT/'saves').iterdir() if p.is_file()}
    results={};state=v.old.STATE.read_bytes()
    prior=load_json(b.BASELINE.parent/'english-build.json')
    unselected=0x08000000+next(a['offset'] for a in prior['ledger']['allocations'] if a['id']=='help.001b5e36')
    for variant,rom_data in [('baseline',b.BASELINE.read_bytes()),('english',data)]:
        rows=[]
        with Session(rom_data,output/'verification'/variant) as s:
            for message in plan['messages']:
                for name in ('Torneko','Ines','WWWWWWW','W'*29,'i'*29,'トルネコ','Slime','Crack-billed platypunk'):
                    for number in (6,9999,2147483647,-2147483648):
                        check(s.core.load_raw_state(state),'Cannot restore fixture')
                        v.old.slots(s.core,font,'normal')
                        for i in range(3):v.old.write_bytes(s.core,v.old.ACTOR+i*30,name.encode('cp932').ljust(30,b'\0'))
                        s.core.memory.u32[v.old.NUMBER]=number&0xffffffff
                        raw,ret=v.formatted(s,message['address'])
                        t=v.FixTrace(s.core)
                        try:
                            v.queue.prepare_queue(s,t,start=15,history_start=19)
                            queued=v.queue.enqueue(s,t,message['address'],raw)
                        finally:t.close()
                        row=dict(id=message['id'],name=name,number=number,raw_hex=raw.hex(),return_r0=ret,queue=queued)
                        if number==6 and ((name=='Torneko' and message['id'] in b.IDS[:3]) or (name=='Slime' and message['id']=='gameplay.001b4d95')):
                            row['rendering']=v.queue.render_queue(s,message['id'],font,queued['rows_hex'],True)
                        rows.append(row)
            # Small destination capacities and unrelated no-damage messages stay safe.
            for source in [r['address'] for r in plan['messages'][4:]]+[unselected]:
                for cap in (1,8,16,64):
                    for mode in (0,1):
                        check(s.core.load_raw_state(state),'Cannot restore short fixture')
                        v.old.slots(s.core,font,'normal')
                        raw,ret=v.formatted(s,source,cap,mode)
                        rows.append(dict(id='capacity',source=source,capacity=cap,mode=mode,raw_hex=raw.hex(),return_r0=ret))
        results[variant]=rows
        b.save(output/'verification'/variant/'cases.json',rows)
        print(variant,len(rows),'native cases passed',flush=True)
    changed=0
    for before,after in zip(results['baseline'],results['english'],strict=True):
        a=bytes.fromhex(before['raw_hex']);z=bytes.fromhex(after['raw_hex'])
        if before['id'] in b.IDS or before['id'].endswith('.continuation'):
            joined=a.replace(b'\n',b' ')
            fits=all(32<=c<=126 for c in joined[:-1]) and len(joined)<=60 and measure(joined[:-1].decode('ascii',errors='replace'),font)<=208
            check(z==(joined if fits else a),'Wrong damage join/fallback: '+repr(after))
            check(before['return_r0']==after['return_r0'],'Full-format source advancement changed')
        elif before['id']!='capacity':
            check(a==z and before['return_r0']==after['return_r0'],'XP/level regression')
        if a!=z:
            changed+=1
            check(a.replace(b'\n',b' ')==z.replace(b'\n',b' ') or after.get('mode')==1,'Unexpected output change')
            check(all(len(line)<=59 for line in z[:-1].split(b'\n')),'History limit exceeded')
        if before['id']=='capacity' and (before['capacity']<16 or before['source']==unselected):
            check(a==z and before['return_r0']==after['return_r0'],'Short buffer behavior changed')
    check(changed>0,'No joins verified')
    check(inputs=={str(p):b.digest(p.read_bytes()) for p in (b.ROOT/'saves').iterdir() if p.is_file()},'User saves changed')
    report=dict(source_sha256=b.digest(b.ORIGINAL_ROM.read_bytes()),
        baseline_sha256=b.digest(b.BASELINE.read_bytes()),rom_sha256=b.digest(data),
        cases_per_rom=len(results['english']),changed_cases=changed,inputs_unchanged=inputs,
        scope='Controlled native formatter, queue/history ring wrap, guard bytes and rendered damage rows; no natural battle replay claimed.')
    b.save(output/'acceptance.json',report)
    print('Accepted',changed,'changed cases',flush=True)
    return report

if __name__=='__main__':run()
