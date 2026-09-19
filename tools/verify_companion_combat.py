"""Native styled-name combat regression gate: formatter, history, bounds and rendering."""
from collections import Counter
from pathlib import Path
import re
import mgba.log
from PIL import Image
from tools import build_companion_combat as b, verify_rendering_fixes as v, verify_ally_nicknames as nick
from tools.translation_pipeline import FontZero,check,load_json
from tools.verify_expansion import Session
from tools.prose_review import save

STYLE=re.compile(rb'\x03\x05\x05|\x03\x06')
FIXTURES=(nick.STATE,v.old.STATE)


def fits(raw,font):
    visible=STYLE.sub(b'',raw)
    return len(raw)<=59 and all(32<=c<=126 for c in visible) and sum(max(font.glyph(chr(c))[1:]) for c in visible)<=208


def expect(raw,message,font,cap=1000):
    if len(raw)>=cap:return raw
    lines=raw[:-1].split(b'\n')
    if 'span' in message:
        original=bytes.fromhex(message['raw_hex']);start=original.index(message['span'].encode())
        skip=original[:start].count(b'\n');count=message['span'].count('\n')
    else:skip=len(lines)-2;count=1
    if skip<0 or len(lines)<skip+count+1:return raw
    span=b' '.join(lines[skip:skip+count+1]);measure=span
    if 'span' in message and skip==0 and span.startswith(b'!'):measure=span[1:]
    if not fits(measure,font):return raw
    return b'\n'.join(lines[:skip]+[span]+lines[skip+count+1:])+b'\0'


def run(data=None,output=None):
    mgba.log.silence();data=b.ROM.read_bytes() if data is None else data
    output=b.OUTPUT/'verification' if output is None else Path(output)
    font=FontZero(b.ORIGINAL_ROM.read_bytes());state=v.old.STATE.read_bytes()
    inputs={str(p):b.digest(p.read_bytes()) for p in (b.ROOT/'saves').iterdir() if p.is_file()}
    damage=load_json(b.ROOT/'build/damage-lines/allocation-plan.json')['messages']
    combat=load_json(b.ROOT/'translations/combat-line-joins.json')['messages']
    messages=damage+combat;cases=[];counts=Counter();screens=[]
    with Session(b.BASELINE.read_bytes(),output/'baseline') as old,Session(data,output/'english') as new:
        tables=nick.cold_tables(new);nick.restore(new,nick.STATE.read_bytes(),tables)
        slime=next(e for e in load_json(nick.CATALOG)['entries'] if e['species_english']=='Slime')
        generated=nick.generate(new.core,slime['row'],1)
        decoded=nick.decode(new.core,bytes.fromhex(generated['compact_hex']))
        native=nick.format_names(new.core,slime['row'],decoded)
        names=list(dict.fromkeys(bytes.fromhex(n['raw_hex'])[:-1] for n in native))
        check(set(names)=={b'\x03\x05\x05Goot1\x03\x06',b'\x03\x05\x05Goot1Lv99\x03\x06'},'Native names changed')
        profiles=[('native-'+str(i),[name]*3,6) for i,name in enumerate(names)]
        profiles += [('mixed',[names[-1],names[0],b'Slime'],9999),('styled-wide',[b'\x03\x05\x05'+b'W'*23+b'\x03\x06']*3,2147483647),
            ('unknown-control',[b'\x03\x05\x04Goot1\x03\x06']*3,6),('incomplete-control',[b'Goot1\x03\x05']*3,6)]
        def setup(s,actors,num):
            check(s.core.load_raw_state(state),'Restore failed');v.old.slots(s.core,font,'normal')
            for i,name in enumerate(actors):
                check(len(name)<=29,'Actor fixture too long')
                v.old.write_bytes(s.core,v.old.ACTOR+i*30,name.ljust(30,b'\0'))
            for i in range(4):s.core.memory.u32[v.old.NUMBER+i*4]=num&0xffffffff
        def compare(m,label,actors,num,cap=1000,queue=True):
            for s in (old,new):setup(s,actors,num)
            before,ret=v.formatted(old,m['address'],cap);after,newret=v.formatted(new,m['address'],cap)
            wanted=expect(before,m,font,cap)
            check(after==wanted,f'Wrong styled join {m["id"]}/{label}/{cap}: {before!r} -> {after!r}; wanted {wanted!r}')
            check(ret==newret,'Source advancement differs')
            check(before.replace(b'\n',b' ')==after.replace(b'\n',b' '),'Non-break bytes changed')
            counts['formatter']+=1;counts['joined' if after!=before else 'fallback']+=1
            row=dict(id=m['id'],profile=label,capacity=cap,before_hex=before.hex(),after_hex=after.hex())
            valid=all(len(line)<=59 for line in before[:-1].lstrip(b'!').split(b'\n'))
            if queue and valid:
                t=v.FixTrace(new.core)
                try:v.queue.prepare_queue(new,t,start=15,history_start=19);row['queue']=v.queue.enqueue(new,t,m['address'],after)
                finally:t.close()
                counts['queue_history']+=1
                if label=='native-1' and m['id'] in ('gameplay.001b4e23','gameplay.001b4dac','gameplay.001b4e7b','tutorial.001b5038','tutorial.001b505b','gameplay.001b5913'):
                    rendered=v.queue.render_queue(new,m['id'],font,row['queue']['rows_hex'],False)
                    text=b''.join(bytes.fromhex(x)[:-1] for x in row['queue']['rows_hex'])
                    visible=STYLE.sub(b'',text).decode('ascii')
                    gs=rendered['glyphs'];check([g['code'] for g in gs]==[font.glyph(c)[0] for c in visible],'Styled rendering glyphs differ')
                    for g in gs:check(g['x']+g['advance']<=208,'Styled rendering clipped')
                    if m['id'].startswith('gameplay.'):
                        # These representative lines begin with Goot1, then a
                        # space and ordinary prose. Inspect native foreground
                        # pixels, not just the presence of control bytes.
                        with Image.open(new.output/rendered['screens'][-1]) as image:
                            for index,wanted_colour in ((0,(0,255,255)),(6,(255,255,255))):
                                g=gs[index];bitmap,_=font.descriptors[g['code']]
                                raw=font.original[bitmap-0x08000000:bitmap-0x08000000+72]
                                colours={image.getpixel((g['window_origin'][0]+g['x']+x,g['window_origin'][1]+g['y']+y))
                                    for y in range(12) for x in range(12) if (raw[y*6+x//2]>>(4*(x%2)))&15}
                                check(colours=={wanted_colour},'Companion colour/reset pixels differ')
                                counts['colour_pixel_checks']+=1
                    screens.append(dict(id=m['id'],rendering=rendered))
            elif queue:counts['oversized_stock_rows_formatter_only']+=1
            cases.append(row)
            return before,after
        for index,m in enumerate(messages):
            for label,actors,num in profiles:compare(m,label,actors,num)
            if (index+1)%40==0:print('Companion sources checked',index+1,'/',len(messages),flush=True)
        # Exact byte limits with two decorated names (10 invisible bytes).
        byte=next(m for m in combat if m['id']=='tutorial.001b6cd6')
        literal=byte['span'].replace('\n',' ').replace('$m0','').replace('$m1','')
        for n in (59,60):
            total=n-len(literal)-10;left=total//2
            actors=[b'\x03\x05\x05'+b'i'*size+b'\x03\x06' for size in (left,total-left,1)]
            a,z=compare(byte,str(n)+'-bytes',actors,6)
            check((a!=z)==(n==59),'Byte threshold not exercised');counts['exact_boundaries']+=1
        # Exact pixel limits while below the byte limit.
        pixel=next(m for m in combat if m['id']=='gameplay.001b40c2')
        literal=pixel['span'].replace('\n',' ').replace('$m2','');width=sum(max(font.glyph(c)[1:]) for c in literal)
        for n in (208,209):
            choices=[b'W'*w+b'i'*i+b'a'*a for w in range(25) for i in range(25-w) for a in range(25-w-i)]
            text=next(x for x in choices if sum(max(font.glyph(chr(c))[1:]) for c in x)==n-width)
            name=b'\x03\x05\x05'+text+b'\x03\x06'
            a,z=compare(pixel,str(n)+'-pixels',[name]*3,6)
            check((a!=z)==(n==208),'Pixel threshold not exercised');counts['exact_boundaries']+=1
        # Truncation through controls and output capacity for every affected source.
        for m in messages:
            if not any(x in bytes.fromhex(m['raw_hex']) for x in (b'$m0',b'$m1',b'$m2')):continue
            for cap in (1,3,6,16,30,60,80):
                compare(m,'capacity',[names[-1]]*3,6,cap,False)
                for s in (old,new):setup(s,[names[-1]]*3,6)
                a,ar=v.formatted(old,m['address'],cap,1);z,zr=v.formatted(new,m['address'],cap,1)
                if (a,ar)!=(z,zr):check(len(z)<=cap and b'\n' not in z and fits(z[:-1].lstrip(b'!'),font),'Unsafe styled line-mode result')
                counts['line_mode_capacity']+=1
        # Preserve attacker/continuation history flags and ring-wrap records.
        allocations={a['id']:a['offset']+0x08000000 for a in load_json(b.BASELINE.parent/'english-build.json')['ledger']['allocations']}
        for ident in ('tutorial.001b5038','tutorial.001b505b','prose-review.tutorial.001b507e'):
            m=next(m for m in messages if m['id']==ident)
            for prefix in ('tutorial.001b5021','tutorial.001b5032'):
                setup(new,[names[-1]]*3,6);t=v.FixTrace(new.core)
                try:
                    v.queue.prepare_queue(new,t,start=14,history_start=19)
                    raw=v.old.guarded_format(new,t,allocations[prefix]);q1=v.queue.enqueue(new,t,allocations[prefix],raw)
                    new.core.memory.u8[0x02007942]=1
                    raw=v.old.guarded_format(new,t,m['address']);q2=v.queue.enqueue(new,t,m['address'],raw)
                    check(bytes.fromhex(q1['history_hex'][0])[2]==1 and bytes.fromhex(q2['history_hex'][0])[2]==0,'Continuation flag differs')
                    check(bytes(new.core.memory[v.queue.HISTORY+19*64:v.queue.HISTORY+20*64]).hex()==q1['history_hex'][0],'Attacker record overwritten')
                finally:t.close()
                counts['continuations']+=1
    check(inputs=={str(p):b.digest(p.read_bytes()) for p in (b.ROOT/'saves').iterdir() if p.is_file()},'User saves changed')
    report=dict(rom_sha256=b.digest(data),baseline_sha256=b.digest(b.BASELINE.read_bytes()),harness_sha256=b.digest(Path(__file__).read_bytes()),
        counts=dict(counts),native_names=native,cases=cases,rendering=screens,inputs_unchanged=inputs,
        scope='Controlled native names, formatter, queue/history, rendering and continuation flags; not natural battle replay')
    save(output/'report.json',report);print('Companion combat checks passed',dict(counts),flush=True);return report


if __name__=='__main__':run()
