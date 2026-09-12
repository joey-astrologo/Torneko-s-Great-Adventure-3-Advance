"""Native keyboard layouts, original kana grids, history rows and guarded codecs."""
import argparse
import struct
from pathlib import Path
import mgba.log
from tools import build_keyboard_completion as b
from tools import verify_core_gameplay as old, verify_dungeon_interface as ui
from tools import verify_tutorial_gameplay as queue
from tools.build_first_label import ORIGINAL_ROM,digest
from tools.build_name_entry import LATIN
from tools.font_metrics import FONT_LAYOUTS
from tools.game_text import GameTextCodec
from tools.translation_pipeline import check,load_json,FontZero
from tools.verify_expansion import Session
from tools.verify_opening_story import STATE
from tools.verify_items import write_json

BASELINE=b.previous.OUTPUT/'torneko3-merchants-english.gba'
INPUT=0x0203F300
CALLBACK=0x0203F100
HISTORY=0x02009E80
COUNT=0x0200A1A8
DECODE=0x0203F400
PRINTF=0x0203F500


def ink_check(gs,original,*,grid=False,vertical=True):
    occupied=set();overlaps=0;right=bottom=0;outside=0
    for g in gs:
        layout=FONT_LAYOUTS[g['font']];bitmap=None
        for i in range(layout['count']):
            row=struct.unpack_from('<IHhHBB',original,layout['table']-0x08000000+i*12)
            if row[1]==g['code']:bitmap=row[0]-0x08000000;break
        check(bitmap is not None,'Native glyph missing descriptor')
        for y in range(layout['rows']):
            for x in range(12):
                value=(original[bitmap+y*6+x//2]>>(4*(x%2)))&15
                if not value:continue
                point=(g['x']+x,g['y']+y)
                check(0<=point[0]<g['window_width'],'Keyboard ink crosses horizontal window');outside+=not 0<=point[1]<g['window_height']
                if vertical:check(0<=point[1]<g['window_height'],'Keyboard ink crosses vertical window')
                if grid:check(0<=point[0]<208 and 14<=point[1]<98,'Grid ink crosses grid field')
                overlaps+=point in occupied;occupied.add(point);right=max(right,point[0]+1);bottom=max(bottom,point[1]+1)
    return {'glyphs':len(gs),'overlapping_ink_pixels':overlaps,'ink_right':right,'ink_bottom':bottom,'pixels_outside_nominal_height':outside}


def layout(s,caches,variant,codec,page,history,original):
    queue.restore(s,STATE.read_bytes(),caches);c=s.core;t=ui.InterfaceTrace(c);name=f'keyboard-c{codec}-p{page}-h{int(history)}'
    try:
        old.write_bytes(c,INPUT-8,old.GUARD+b'\0'*32+old.GUARD);old.write_bytes(c,CALLBACK,b'\x70\x47')
        call=ui.native_step(s,t,0x0807BB74,[5,codec,INPUT,18 if codec else 7,CALLBACK+1,0 if history else 0xffffffff],stop=0x0807BE70,
            overrides={0x0807BBCA:{'r2':page},0x0807BBDA:{'r2':0}})
        grid=[d for d in t.payloads if d['x']==0 and d['y']==14];check(len(grid)==1,'Keyboard grid count differs')
        gs=[g for g in t.positions if g['draw_serial']==grid[0]['serial']]
        expected_font=codec if variant=='english' else 1 if variant=='original' else 0
        check(gs and all(g['font']==expected_font and g['spacing']==0 for g in gs),'Keyboard grid font differs')
        ink=ink_check(gs,original,grid=True)
        if variant in ('english','original'):check(ink['overlapping_ink_pixels']==0,'Keyboard grid ink overlaps')
        headers=[d for d in t.payloads if d['x']==0 and d['y']==0];check(len(headers)==1,'Keyboard header count differs')
        h=headers[0];hraw=old.cstring(c,int(h['source'],0),256);header_glyphs=[g for g in t.positions if g['draw_serial']==h['serial']]
        if variant=='english':
            e=load_json(b.CATALOG)['entries'][page+(0 if history else 2)]
            check(hraw==b.encode(e,original)[0],'Wrong keyboard header selection')
            ui.check_glyphs(header_glyphs,old.visible(hraw,GameTextCodec(original)),FontZero(original));check(ink_check(header_glyphs,original)['overlapping_ink_pixels']==0,'Header ink overlaps')
            hint=load_json(b.CATALOG)['entries'][4];wanted=b.encode(hint,original)[0]
            draws=[d for d in t.payloads if bytes.fromhex(d['raw_hex']).startswith(wanted)];check(len(draws)==1,'Keyboard shared hint missing')
            hintgs=[g for g in t.positions if g['draw_serial']==draws[0]['serial']];check([g['code'] for g in hintgs]==[FontZero(original).glyph(ch)[0] for ch in hint['english']], 'Keyboard hint glyphs differ');check(all(g['font']==0 and g['spacing']==0 for g in hintgs),'Keyboard hint font differs');ink_check(hintgs,original)
        check(bytes(c.memory[INPUT-8:INPUT])==old.GUARD and bytes(c.memory[INPUT:INPUT+32])==b'\0'*32 and bytes(c.memory[INPUT+32:INPUT+40])==old.GUARD,'Keyboard input source/guard changed')
        check(c.memory.u32[0x02009DE8]==page and c.memory.u32[0x02009DF0]==0,'Keyboard page override changed input cursor')
        s.frames(2);s.capture(name)
        result={'id':name,'codec':codec,'page':page,'history':history,'call':call,'header_hex':hraw.hex(),'grid_hex':old.cstring(c,int(grid[0]['source'],0),1024).hex(),'grid_glyphs':gs,'ink':ink,'guards_intact':True,'screen':name+'.png'}
        write_json(s.output/(name+'.json'),dict(result,payloads=t.payloads,glyphs=t.positions));return result
    finally:t.close()


def history_rows(s,caches,variant,codec,original):
    queue.restore(s,STATE.read_bytes(),caches);c=s.core;t=ui.InterfaceTrace(c);name=f'history-c{codec}'
    try:
        old.write_bytes(c,CALLBACK,b'\x70\x47');ui.native_step(s,t,0x0807D02C,[1,0]);ui.native_step(s,t,0x0808CD70,[0,0])
        names=[bytes(LATIN[ch] for ch in ('W'*7 if i==0 else 'Torneko' if i==1 else 'i'*7)) if codec==0 and variant!='original' else bytes(range(1+i,8+i)) for i in range(8)]
        raw=b''.join(n+b'\0' for n in names);old.write_bytes(c,HISTORY,raw);c.memory.u32[COUNT]=8;checks=[]
        for i,n in enumerate(names):
            old.write_bytes(c,DECODE-8,old.GUARD+b'\xa5'*16+old.GUARD);old.write_bytes(c,PRINTF-8,old.GUARD+b'\xa5'*32+old.GUARD)
            ui.native_step(s,t,0x0807D228,[codec,DECODE,HISTORY+i*8]);decoded=old.cstring(c,DECODE,16)
            ui.native_step(s,t,0x08096744,[PRINTF,0x08C46748,i+1,DECODE]);formatted=old.cstring(c,PRINTF,32)
            check(formatted==b'%2d\x03\x09\x14: %s\0'%(i+1,decoded[:-1]),'History printf content differs')
            for at,size in ((DECODE,16),(PRINTF,32)):check(bytes(c.memory[at-8:at])==old.GUARD and bytes(c.memory[at+size:at+size+8])==old.GUARD,'History buffer guard overwrite')
            checks.append({'row':i,'decoded_hex':decoded.hex(),'formatted_hex':formatted.hex(),'guards_intact':True})
        t.positions.clear();t.payloads.clear();ui.native_step(s,t,0x0807CD14,[0,8,0,codec]);check(len(t.payloads)==8,'Missing native history rows')
        for d,r in zip(t.payloads,checks,strict=True):
            # Native stack reused after each draw: trace owns the bytes at call time.
            check(bytes.fromhex(d['raw_hex']).startswith(bytes.fromhex(r['formatted_hex'])),'Native history row changed');gs=[g for g in t.positions if g['draw_serial']==d['serial']];r['ink']=ink_check(gs,original,vertical=False)
            if variant=='english' and codec==0:check([g['code'] for g in gs]==[FontZero(original).glyph(ch)[0] for ch in old.visible(bytes.fromhex(r['formatted_hex']),GameTextCodec(original))],'Latin history glyphs differ')
        check(bytes(c.memory[HISTORY:HISTORY+64])==raw and c.memory.u32[COUNT]==8,'History rendering changed records')
        s.frames(2);s.capture(name);result={'id':name,'rows':checks,'screen':name+'.png','records_intact':True};write_json(s.output/(name+'.json'),dict(result,payloads=t.payloads,glyphs=t.positions));return result
    finally:t.close()


def popup(s,caches,variant,original):
    queue.restore(s,STATE.read_bytes(),caches);c=s.core;t=ui.InterfaceTrace(c)
    try:
        ui.native_step(s,t,0x0807D02C,[1,0]);ui.native_step(s,t,0x0808CD70,[0,0]);old.write_bytes(c,CALLBACK,b'\x70\x47')
        ui.native_step(s,t,0x0807CDD8,[CALLBACK+1,0,0],stop=0x0807CE0E);check(len(t.payloads)==1,'History popup draws differ');ink=ink_check(t.positions,original)
        if variant=='english':
            check([g['code'] for g in t.positions]==[FontZero(original).glyph(ch)[0] for ch in 'SelectErase'],'Popup glyphs differ');check(all(g['font']==0 and g['spacing']==0 for g in t.positions),'Popup font differs')
        s.frames(2);s.capture('history-popup');result={'id':'history-popup','ink':ink,'screen':'history-popup.png'};write_json(s.output/'history-popup.json',dict(result,payloads=t.payloads,glyphs=t.positions));return result
    finally:t.close()


def verify(variant):
    mgba.log.silence();rom=ORIGINAL_ROM if variant=='original' else BASELINE if variant=='baseline' else b.OUTPUT/f'torneko3-keyboard-completion-{variant}.gba';data=rom.read_bytes();original=ORIGINAL_ROM.read_bytes();cases=[]
    with Session(data,b.OUTPUT/'verification'/variant) as s:
        caches=queue.cold_tables(s)
        # The keyboard's original startup tables are outside tutorial table caches.
        start,end=0xCB0620,0xCB0650;ram=0x02000798
        raw=bytes(s.core.memory[ram:ram+end-start]);check(raw==data[start:end],'Keyboard cold tables differ');caches.append({'rom_start':start,'rom_end':end,'ram_start':ram,'raw_hex':raw.hex()})
        for codec in (0,1):
            for page in (0,1):
                for history in (False,True):cases.append(layout(s,caches,variant,codec,page,history,original));print(variant,cases[-1]['id'],'passed',flush=True)
        histories=[history_rows(s,caches,variant,codec,original) for codec in (0,1)];pop=popup(s,caches,variant,original)
        result={'variant':variant,'rom_sha256':digest(data),'source_sha256':digest(original),'catalog_sha256':digest(b.CATALOG.read_bytes()),'harness_sha256':digest(Path(__file__).read_bytes()),'fixture_sha256':digest(STATE.read_bytes()),'cases':cases,'histories':histories,'popup':pop,'screens':[e['screen'] for e in cases+histories+[pop]],'scope':'Controlled native keyboard entry for both codecs, both pages and History states; original kana grid glyph/font comparison; native history decode/printf/display and popup. Frame callback and initial page are fixtures. Natural password exchange, learned-scroll inscription and save consequences remain separate.'}
        write_json(s.output/'verification.json',result);print(variant,'keyboard checks passed',flush=True)
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('variant',choices=('english','japanese','baseline','original'));verify(p.parse_args().variant)
