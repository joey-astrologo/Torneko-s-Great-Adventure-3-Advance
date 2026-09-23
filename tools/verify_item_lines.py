"""Native item names, combat/history and acquisition-path regression gate."""
from pathlib import Path
from collections import Counter
import re
import mgba.log
from tools import build_item_lines as b, verify_rendering_fixes as v, verify_merchants as world
from tools import verify_items as items, verify_item_contexts as contexts
from tools.game_text import GameTextCodec
from tools.translation_pipeline import FontZero, check, load_json
from tools.verify_expansion import Session
from tools.prose_review import save

FIXTURES=(v.old.STATE,world.STATE)


def glyphs(raw,font):
    result=[];i=0
    while i<len(raw):
        if raw[i:i+2]==b'\x03\x05' and i+2<len(raw) and 2<=raw[i+2]<=7:i+=3;continue
        if raw[i:i+2]==b'\x03\x06':i+=2;continue
        if raw[i]==0x87 and i+1<len(raw) and 0x40<=raw[i+1]<=0x4f:
            code=int.from_bytes(raw[i:i+2],'big');ptr,advance=font.descriptors[code]
            bitmap=font.original[ptr-0x08000000:ptr-0x08000000+72]
            xs=[x for y in range(12) for x in range(12) if (bitmap[y*6+x//2]>>(4*(x%2)))&15]
            result.append((code,max(advance,max(xs)+1 if xs else 0)));i+=2;continue
        if not 32<=raw[i]<=126:return None
        code,advance,ink=font.glyph(chr(raw[i]));result.append((code,max(advance,ink)));i+=1
    return result


def fits(raw,font):
    gs=glyphs(raw,font)
    return len(raw)<=59 and gs is not None and sum(w for _,w in gs)<=208


def expected(raw,message,font,cap=1000):
    if len(raw)>=cap:return raw
    source=bytes.fromhex(message['raw_hex']);start=source.index(message['span'].encode())
    skip=source[:start].count(b'\n');count=message['span'].count('\n')
    lines=raw[:-1].split(b'\n')
    if len(lines)<skip+count+1:return raw
    span=b' '.join(lines[skip:skip+count+1]);measure=span[1:] if skip==0 and span.startswith(b'!') else span
    if not fits(measure,font):return raw
    return b'\n'.join(lines[:skip]+[span]+lines[skip+count+1:])+b'\0'


def run(data=None,output=None):
    mgba.log.silence();data=b.ROM.read_bytes() if data is None else data
    output=b.OUTPUT/'verification' if output is None else Path(output);output.mkdir(parents=True,exist_ok=True)
    font=FontZero(b.ORIGINAL_ROM.read_bytes());state=v.old.STATE.read_bytes();counts=Counter();cases=[];screens=[]
    baseline=b.BASELINE.read_bytes();plan=load_json(b.PLAN)
    allowed=((0x62294,0x6229C),(0x7D8CC,0x7D8D8),(plan['start'],plan['end_exclusive']))
    check(len(data)==len(baseline),'Unexpected ROM size')
    # Later cumulative components own additional ranges; their combined ledger
    # validates those writes. Keep the exact byte-diff check for this checkpoint.
    if b.digest(data)==load_json(b.OUTPUT/'english-build.json')['rom_sha256']:
        cursor=0
        for lo,hi in sorted(allowed):
            check(data[cursor:lo]==baseline[cursor:lo],'Unowned ROM bytes changed');cursor=hi
        check(data[cursor:]==baseline[cursor:],'Trailing ROM bytes changed')
    inputs={str(p):b.digest(p.read_bytes()) for p in (b.ROOT/'saves').iterdir() if p.is_file()}
    messages=[m for m in load_json(b.ROOT/'translations/combat-line-joins.json')['messages'] if '$i' in m['span']]
    with Session(b.BASELINE.read_bytes(),output/'baseline') as old,Session(data,output/'english') as new:
        native=items.native_names(new,state,GameTextCodec(b.ORIGINAL_ROM.read_bytes()),output,
            [(i,0) for i in range(370)]+[(i,n) for i in (1,3,4,5,58) for n in (-99,99)]+[(341,9999),(116,1)])
        context_dir=output/'contexts';context_dir.mkdir(exist_ok=True)
        context_names=contexts.guarded_names(new,state,b.ORIGINAL_ROM.read_bytes(),context_dir)
        names={r['item']:bytes.fromhex(r['output_hex'])[:-1] for r in native if r['enhancement']==0}
        for r in native[-2:]:names[r['item']]=bytes.fromhex(r['output_hex'])[:-1]
        def compare(m,name,label,actor=b'Slime',cap=1000,mode=0,render=False):
            payloads=[]
            for s in (old,new):
                check(s.core.load_raw_state(state),'Restore item fixture');v.old.slots(s.core,font,'normal')
                for i in range(4):v.old.write_bytes(s.core,v.old.ITEM+i*100,(name+b'\0').ljust(100,b'\0'))
                for i in range(3):v.old.write_bytes(s.core,v.old.ACTOR+i*30,(actor+b'\0').ljust(30,b'\0'))
                payloads.append(v.formatted(s,m['address'],cap,mode))
            before,after=payloads
            if mode==0:wanted=expected(before[0],m,font,cap)
            else:
                # Re-expand without line mode to obtain the independently measured full span.
                full=v.formatted(old,m['address'])[0];joined=expected(full,m,font)
                wanted=joined if joined!=full and len(joined)<=cap else before[0]
            check(after[0]==wanted,f'Item join differs: {m["id"]}/{label}/{mode}/{cap}: {after[0]!r} != {wanted!r}')
            counts['formatter']+=1;counts['joined' if before!=after else 'fallback']+=1
            row=dict(id=m['id'],profile=label,mode=mode,capacity=cap,before_hex=before[0].hex(),after_hex=after[0].hex())
            if mode==0 and cap==1000 and all(len(x)<=59 for x in after[0][:-1].split(b'\n')):
                t=v.FixTrace(new.core)
                try:v.queue.prepare_queue(new,t,start=15,history_start=19);q=v.queue.enqueue(new,t,m['address'],after[0])
                finally:t.close()
                counts['queue_history']+=1
                if render:
                    result=v.queue.render_queue(new,m['id']+'-'+label,font,q['rows_hex'],False)
                    raw=b''.join(bytes.fromhex(x)[:-1] for x in q['rows_hex']);gs=glyphs(raw,font)
                    check(gs is not None,'Unsupported render fixture')
                    check([g['code'] for g in result['glyphs']]==[g[0] for g in gs],'Item glyph/icon mismatch')
                    check(all(g['x']+g['advance']<=208 for g in result['glyphs']),'Item rendering clipped')
                    screens.append(dict(id=m['id'],profile=label,rendering=result));counts['rendered']+=1
            cases.append(row)
        targets=[next(m for m in messages if m['id']==key) for key in ('gameplay.001b57ca','gameplay.001b566f','gameplay.001b5686')]
        for m in targets:
            for r in native:compare(m,bytes.fromhex(r['output_hex'])[:-1],f'native-{r["item"]}-{r["enhancement"]}')
        for r in context_names:
            compare(targets[0],bytes.fromhex(r['output_hex'])[:-1],f'context-{r["row"]}-{r["mode"]}')
        # Cursed/unknown identification flag combinations use native item colour 2/6.
        flag_names=[]
        for flags in (0x81800400,0x81000000):
            check(new.core.load_raw_state(state),'Restore flag fixture')
            items.install_item(new.core,0x0203F000,304);new.core.memory.u32[0x0203F000]=flags
            t=v.FixTrace(new.core)
            try:v.ui.native_step(new,t,0x08080A5C,[0x0203F000,0x0203F100,0,0])
            finally:t.close()
            name=v.old.cstring(new.core,0x0203F100,100)[:-1];flag_names.append(dict(flags=hex(flags),output_hex=name.hex()))
            for m in targets:compare(m,name,'flags-'+hex(flags),render=m is targets[0])
        for m in messages:
            for item in (304,116,1):compare(m,names[item],f'item-{item}',b'\x03\x05\x05Goot1\x03\x06')
        for m,item in zip(targets,(304,116,116)):
            compare(m,names[item],'render',render=True)
            for name in (names[item],b'\x87K\x03\x05\x07'+b'W'*40+b'\x03\x06',b'\x87',b'\x87\x50Bread',b'\x03\x05\x7fBread',b'Bread\x03\x05'):
                for cap in (12,24,30,60,80,1000):compare(m,name,'capacity-'+name.hex(),cap=cap)
            for cap in (12,24,30,60,80,1000):compare(m,names[item],'line-mode',cap=cap,mode=1)
        # Exact thresholds with an icon and style bytes included.
        for bound in (208,209):
            prefix=b'Torneko ate '+bytes.fromhex('874b030507');suffix=bytes.fromhex('0306')+b'.'
            overhead=sum(w for _,w in glyphs(prefix+suffix,font));wanted=bound-overhead
            # Find printable glyphs whose widths sum to the precise remainder.
            solutions={0:b''}
            for n in range(1,wanted+1):
                for c in b'Wi.':
                    width=max(font.glyph(chr(c))[1:])
                    if n-width in solutions:solutions[n]=solutions[n-width]+bytes([c]);break
            name=bytes.fromhex('874b030507')+solutions[wanted]+bytes.fromhex('0306')
            check(len(prefix+solutions[wanted]+suffix)<=59,'Pixel boundary confounded by byte bound')
            compare(targets[0],name,f'pixels-{bound}');counts['exact_boundaries']+=1
        for bound in (59,60):
            overhead=len(b'Torneko ate .')+7
            name=bytes.fromhex('874b030507')+b'i'*(bound-overhead)+bytes.fromhex('0306')
            check(sum(w for _,w in glyphs(b'Torneko ate '+name+b'.',font))<=208,'Byte boundary confounded by pixel bound')
            compare(targets[0],name,f'bytes-{bound}');counts['exact_boundaries']+=1
        # Execute the actual acquisition printf + world call, rather than a
        # synthetic direct invocation that would bypass the caller restriction.
        acquisition=load_json(b.PLAN)['constants']['ACQUISITION_SOURCE']
        world_cases=[]
        for label,name in [('gold-1',b'1 gold'),('gold-max',b'9999999 gold'),('native-gold',names[341]),('bread',names[304]),('arrow',names[116]),
                           ('wide',b'W'*27),('long',b'i'*99),('unknown',b'\x03\x05\x7fBread')]:
            values=[]
            for s in (old,new):
                check(s.core.load_raw_state(world.STATE.read_bytes()),'Restore world fixture');v.old.slots(s.core,font,'normal')
                # Native caller's stack printf destination and item name, with adjacent guards.
                v.old.write_bytes(s.core,0x03007E00,b'\xA5'*256)
                v.old.write_bytes(s.core,0x03007F00,name+b'\0'+b'GUARD123')
                t=v.FixTrace(s.core)
                try:
                    call=v.ui.native_step(s,t,0x08062D4A,[],stop=0x080622C8,overrides={0x08062D4A:{'r8':acquisition}})
                    root=s.core.memory.u32[0x03000010];raw=v.old.cstring(s.core,root+0x50+12,1024)
                    check(bytes(s.core.memory[0x03007F00:0x03007F00+len(name)+9])==name+b'\0GUARD123','Acquisition overwrote adjacent item name')
                    values.append(raw)
                    if s is new and label in ('gold-1','gold-max','native-gold','bread','wide'):
                        # Render the verified result in a fresh world fixture; opening
                        # the same native window twice hides its presentation.
                        check(s.core.load_raw_state(world.STATE.read_bytes()),'Restore world rendering fixture')
                        source=world.PRINTF_DEST
                        v.old.write_bytes(s.core,source,raw)
                        result=world.world_pages(s,{'family':'observation'},source,raw,label,font,False,t)
                        gs=[g for page in result['pages'] for g in page['glyphs']]
                        expected_glyphs=glyphs(raw[:-1].replace(b'\n',b''),font)
                        check([g['code'] for g in gs]==[g[0] for g in expected_glyphs],'Acquisition glyph mismatch')
                        if label!='wide':check(len({g['y'] for g in gs})==1,'Acquisition still has two lines')
                        check(all(g['x']+g['advance']<=208 for g in gs),'Acquisition clipped')
                        screens.append(dict(id=label,rendering=result));counts['world_rendered']+=1
                finally:t.close()
            joined=values[0].replace(b'\n',b' ')
            check(values[1]==(joined if fits(joined[:-1],font) else values[0]),'Acquisition join differs '+label)
            world_cases.append(dict(label=label,before_hex=values[0].hex(),after_hex=values[1].hex()));counts['world']+=1
        # Same raw payload called from elsewhere must retain its original lines.
        check(new.core.load_raw_state(world.STATE.read_bytes()),'Restore caller-negative fixture')
        v.old.slots(new.core,font,'normal');v.old.write_bytes(new.core,world.PRINTF_DEST,b'$t obtained\n123 gold!\0')
        t=v.FixTrace(new.core)
        try:
            v.ui.native_step(new,t,0x08062294,[world.PRINTF_DEST],stop=0x080622C8)
            root=new.core.memory.u32[0x03000010];check(v.old.cstring(new.core,root+0x50+12)==b'Torneko obtained\n123 gold!\0','Unrelated caller changed')
        finally:t.close()
        counts['unrelated_world_caller']=1
    check(inputs=={str(p):b.digest(p.read_bytes()) for p in (b.ROOT/'saves').iterdir() if p.is_file()},'User saves changed')
    report=dict(rom_sha256=b.digest(data),baseline_sha256=b.digest(b.BASELINE.read_bytes()),counts=dict(counts),cases=cases,
        world_cases=world_cases,native_flag_names=flag_names,rendering=screens,scope='Controlled native item formatters, combat queue/history, actual acquisition printf/call instructions and native world rendering; not natural gameplay replays.')
    save(output/'report.json',report);print('Item line checks passed',dict(counts),flush=True);return report

if __name__=='__main__':run()
