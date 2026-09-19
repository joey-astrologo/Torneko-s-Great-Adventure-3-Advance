"""Replay supplied menu bugs and reject regressions before ROM publication."""
import argparse
from pathlib import Path
import struct
import mgba.log
from tools import build_menu_fixes as b
from tools.verify_expansion import Session
from tools.verify_rendering_fixes import restore_file,FixTrace
from tools.verify_first_label import battery_snapshot
from tools.translation_pipeline import check,load_json

FIXTURES=b.ROOT/'tools/menu_fixtures.json'
WINDOW=0x02034CD8


def windows(c):
    rows=[]
    for n in range(4):
        at=WINDOW+n*64;w=c.memory.u16[at+4];h=c.memory.u16[at+6]
        start=c.memory.u32[at+0x18];size=c.memory.u32[at+0x24]
        rows.append(dict(id=n,x=c.memory.u16[at],y=c.memory.u16[at+2],width=w,height=h,
            buffer=start,bytes=size,bitmap_hex=bytes(c.memory[start:start+size]).hex() if w else ''))
    return rows


def masks(c):
    at=c.memory.u32[0x02039938]
    check(0x02039948<=at<=0x02039BCC,'Unexpected active clipping buffer')
    return [[c.memory.u16[at+y*4],c.memory.u16[at+y*4+2]] for y in range(160)]


def shade_check(c):
    profile=c.memory.u32[0x02034DD8];values=masks(c)
    # Interior command-only rows are independent of a location panel's coverage.
    for y in range(17,55):
        right=102 if profile==4 and y in (17,54) else 103
        check(any((v>>8)<=10 and (v&255)>=right for v in values[y]),f'Missing command shading at y{y}, profile{profile}: {values[y]}')
    return dict(profile=profile,scanlines=values)


def visible(draws):
    return [bytes.fromhex(d['raw_hex']).split(b'\0')[0] for d in draws]


def run(data,output=None,*,assert_fixed=True):
    mgba.log.silence();output=output or b.OUTPUT/'verification/english'
    manifest=load_json(FIXTURES);reports=[]
    inputs={p:b.digest(p.read_bytes()) for p in (b.ROOT/'saves').iterdir() if p.is_file()}
    for fixture in manifest['fixtures']:
        ident=fixture['id'];path=b.ROOT/fixture['path']
        check(path.is_file() and b.digest(path.read_bytes())==fixture['sha256'],'Missing/changed regression state: '+str(path))
        with Session(data,output/ident) as s:
            restore_file(s,path);s.frames(2);battery=battery_snapshot(s.core)
            s.capture('restored');s.press('B',20)
            if ident=='casino':
                # Its action pointer was cached before the supplied state. Exit
                # and re-enter the conversation so the ROM literal is reread.
                for key in ('B','B','A','A','A','A'):s.press(key,60)
            # Closing the old, possibly corrupt menu makes the game rebuild its
            # parent normally. No RAM edits or forced program counters are used.
            parent=windows(s.core)
            t=FixTrace(s.core)
            try:
                if ident=='idle':
                    s.frames(1900,t)
                    check(s.core.memory.u32[0x02034DD8]==4,'Real idle timeout did not open compact menu')
                elif ident=='status':s.press('B',30,t)
                else:s.press('A',30,t)
                check(not t.errors,str(t.errors))
                after=windows(s.core);texts=visible(t.payloads)
                s.capture('opened')
                row=dict(id=ident,windows=after,texts_hex=[x.hex() for x in texts],glyphs=t.positions,
                    state_sha256=fixture['sha256'],rom_sha256=b.digest(data))
                if ident in ('idle','status','ground','stairs','trap'):
                    if assert_fixed:
                        check(after[0]['width']==10,'Command width reverted')
                        row['shading']=shade_check(s.core)
                    else:row['shading']=dict(profile=s.core.memory.u32[0x02034DD8],scanlines=masks(s.core))
                if ident in ('ground','stairs','trap'):
                    if assert_fixed:
                        for n in range(3):
                            check(all(after[n][k]==parent[n][k] for k in ('x','y','width','height','buffer','bytes','bitmap_hex')),f'{ident}: background panel{n} changed when popup opened')
                    row['cached_panels_unchanged']=[after[n]==parent[n] for n in range(3)]
                if ident=='ground' and assert_fixed:
                    check(any(x.rstrip()==b'Nothing at your feet.' for x in texts),'Ground popup wording differs')
                if ident=='casino' and assert_fixed:
                    check(b'Trade' in texts and b'Exchange' not in texts,'Casino label not Trade')
                if ident=='warehouse':
                    if assert_fixed:
                        check(after[1]==parent[1],'Warehouse counter bitmap/layout changed on action open')
                        check(after[1]['width']==5 and after[2]['width']==6,'Warehouse panel widths differ')
                    row['counter_preserved']=after[1]==parent[1]
                # Check real glyph ink extents, excluding the popup's deliberate
                # blank fill spaces (which native clipping safely discards).
                if assert_fixed:
                    for g in t.positions:
                        if g['code']==32:continue
                        check(g['x']>=0 and g['x']+g['advance']<=g['window_width'],f'{ident}: glyph clips {g}')
                if ident in ('ground','stairs','trap','casino','warehouse'):
                    s.press('B',20,t);s.capture('closed')
                    closed=windows(s.core)
                    if assert_fixed and ident in ('ground','stairs','trap','warehouse'):
                        n=1 if ident=='warehouse' else 0
                        check(closed[n]['width']==parent[n]['width'],'Parent layout changed after cancelling')
                    s.press('A',20,t);s.capture('reopened')
                    repeated=windows(s.core)
                    if assert_fixed:
                        ids=range(3) if ident in ('ground','stairs','trap') else (1,)
                        for n in ids:
                            # Status time can advance when the parent redraws.
                            expected=closed[n] if ident in ('ground','stairs','trap','warehouse') else after[n]
                            check(repeated[n]==expected,f'{ident}: repeated open changes cached panel{n}')
                check(battery_snapshot(s.core)==battery,'Menu navigation changed cartridge save')
                row['save_unchanged']=True;reports.append(row)
            finally:t.close()
    check(all(b.digest(p.read_bytes())==h for p,h in inputs.items()),'User save files changed')
    report=dict(rom_sha256=b.digest(data),fixture_manifest_sha256=b.digest(FIXTURES.read_bytes()),
        verifier_sha256=b.digest(Path(__file__).read_bytes()),assert_fixed=assert_fixed,cases=reports,trap=manifest['trap'])
    b.save(output/'report.json',report)
    print('Menu checks passed:',len(reports),'states; fixed assertions:',assert_fixed,flush=True)
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--baseline',action='store_true');args=p.parse_args()
    run((b.BASELINE if args.baseline else b.ROM).read_bytes(),b.OUTPUT/'verification'/('baseline' if args.baseline else 'english'),assert_fixed=not args.baseline)
