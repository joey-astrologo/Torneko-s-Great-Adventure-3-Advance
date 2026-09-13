"""Verify approved arrivals in native ARM execution and a normal cave transition."""
from pathlib import Path
import struct

import mgba.log
from mgba._pylib import ffi
from PIL import Image, ImageChops, ImageDraw

from tools.build_first_label import ROOT, ORIGINAL_ROM, digest
from tools.build_arrival_credits import OUT, ROM, BASELINE, SOURCE_RANGES
from tools.extract_arrival_cards import save_json, paint_cell, label_font
from tools.translation_pipeline import check, load_json
from tools.verify_expansion import Session
from tools.verify_dungeon_interface import registers
from tools.verify_first_label import battery_snapshot
from tools.trace_text_systems import ReaderTrace

VERIFY = OUT/'verification'
CAVE = ROOT/'build/completion/cave-clear'
STATE = CAVE/'continued/stair-approach.state'
TILES = 0x02035DDC
MAP = 0x02034DDC


def quantized(path):
    im = Image.open(path).convert('RGB')
    im.putdata([tuple(((c>>3)<<3)|((c>>3)>>2) for c in rgb) for rgb in im.get_flattened_data()])
    return im


def expected_image(plan, title, number):
    im = quantized(ROOT/title['file'])
    dungeon = title['selectors'][0]%32
    if dungeon != 26:
        floor = plan['floors'][number+(256 if dungeon in (25,27) else 0)]
        im.paste(quantized(ROOT/floor['file']),(0,96))
    return im


def floor_pixels(data,plan):
    colours = [tuple(c) for c in plan['palette_rgb']]
    for row in plan['floors']:
        # Decode native 4bpp cells independently of the packer's tile indexing.
        tiles = bytes(0x1400)+data[row['tiles_offset']:row['tiles_offset']+row['tile_count']*32]
        im=Image.new('RGB',(240,32),'black')
        for i,entry in enumerate(struct.unpack_from('<120H',data,row['map_offset'])):
            paint_cell(im,(i%30*8,i//30*8),tiles,entry,colours)
        check(ImageChops.difference(im,quantized(ROOT/row['file'])).getbbox() is None,
              f"Packed floor pixels differ from approved raster: {row['kind']}/{row['number']}")
    return len(plan['floors'])


def position(core):
    root=core.memory.u32[0x0200000C];actor=core.memory.u32[root+0x19EE4]
    return [core.memory.u16[actor+0x2C],core.memory.u16[actor+0x2E]]


def invoke(core):
    cpu = ffi.cast('struct ARMCore*',core._core.cpu)
    preserved = {f'r{i}':0xA5100000+i for i in range(4,12)}
    registers(core,{'cpsr':0xFF,'sp':0x03007E00,**preserved,'lr':0x08000001,'pc':0x0800518C})
    for steps in range(100000):
        pc = (int(cpu.gprs[15])&0xFFFFFFFF)-(2 if cpu.cpsr.packed&32 else 4)
        if pc == 0x08000000:
            break
        core.step()
    else:
        raise ValueError(f'Constructor did not return: {pc:08X}')
    check(all(int(cpu.gprs[i])&0xFFFFFFFF == preserved[f'r{i}'] for i in range(4,12)), 'Callee-saved register corrupted')
    check(cpu.gprs[13] == 0x03007E00, 'Stack not balanced')
    return steps


def controlled(data,plan,limit=None):
    cases = [(s,n,0) for s in range(64) for n in (0,1,9,10,99,100,255)]
    cases += [(s,n,0) for s in (0,25,27) for n in range(256)]
    cases += [(s,1,1) for s in range(64)]
    cases = list(dict.fromkeys(cases))
    if limit: cases = cases[:limit]
    results = []; title_lookup = {s:t for t in plan['titles'] for s in t['selectors']}
    state = STATE.read_bytes(); previews = []; colours = [tuple(c) for c in plan['palette_rgb']]
    with Session(data,VERIFY/'controlled') as session:
        core = session.core
        for selector,number,suppress in cases:
            check(core.load_raw_state(state),'Could not restore disposable native fixture')
            core.memory.u8[0x02004FF0] = selector%32
            core.memory.u8[0x02004FF1] = number
            core.memory.u32[0x02004F8C] = selector//32
            core.memory.u8[0x02000034] = suppress
            before_map = bytes(core.memory[MAP:MAP+0x840])
            before_tiles = bytes(core.memory[TILES:TILES+0x2800])
            guards = [(a,bytes(core.memory[a:b])) for a,b in
                      [(MAP-16,MAP),(MAP+0x840,MAP+0x850),(TILES-16,TILES),(TILES+0x2800,TILES+0x2810),
                       (0x02002FD4,0x02004F80)]]
            save = battery_snapshot(core)
            title = title_lookup[selector]
            puzzle = selector%32 in (25,27)
            visible = not suppress and not(puzzle and number == 100)
            floor = plan['floors'][number+(256 if puzzle else 0)]
            tile_bytes = data[title['offset']+0x800:title['end_exclusive']]
            expected_tiles = tile_bytes+before_tiles[len(tile_bytes):0x1400]
            expected_tiles += data[floor['tiles_offset']:floor['tiles_offset']+floor['tile_count']*32].ljust(0x1400,b'\0')
            expected_map = bytearray(before_map)
            for y in range(1,33):
                expected_map[y*64+2:y*64+64] = bytes(62)
            if visible:
                for y in range(9):
                    at = title['offset']+y*64+2
                    expected_map[(y+1)*64+2:(y+1)*64+60] = data[at:at+58]
                if selector%32 != 26:
                    for y in range(4):
                        at = floor['map_offset']+y*60
                        expected_map[(y+12)*64:(y+12)*64+60] = data[at:at+60]
            steps = invoke(core)
            check(bytes(core.memory[TILES:TILES+0x2800]) == expected_tiles,f'Tile buffer mismatch: {selector}/{number}/{suppress}')
            check(bytes(core.memory[MAP:MAP+0x840]) == expected_map,f'Map mismatch: {selector}/{number}/{suppress}')
            # 080844B8 queues the upload. The natural frame route below checks
            # actual VRAM after the engine consumes that queue at VBlank.
            palette = bytes(core.memory[0x03003620:0x03003660])
            check(palette == struct.pack('<16I',*plan['palette_words']),'Palette staging differs')
            check(core.memory.u8[0x02005E48] == 1,'Native upload flag not set')
            check(all(bytes(core.memory[a:a+len(b)]) == b for a,b in guards),'Neighbour or profile bytes changed')
            check(battery_snapshot(core) == save,'Constructor changed native save')
            if number == 1 and not suppress and selector == title['selectors'][0]:
                im = Image.new('RGB',(240,160),'black')
                for y in range(1,10):
                    for x in range(1,30):
                        entry = core.memory.u16[MAP+(y*32+x)*2]
                        paint_cell(im,(x*8,y*8),expected_tiles,entry,colours)
                if selector%32 != 26:
                    for y in range(12,16):
                        for x in range(30):
                            paint_cell(im,(x*8,y*8),expected_tiles,core.memory.u16[MAP+(y*32+x)*2],colours)
                check(ImageChops.difference(im,expected_image(plan,title,number)).getbbox() is None,'Native decoded pixels differ from approved artwork')
                im.save(session.output/(title['id']+'.png')); previews.append((title['text'],im))
            results.append(dict(selector=selector,floor=number,suppression_flag=suppress,card_visible=visible,
                                floor_visible=visible and selector%32!=26,steps=steps))
            if len(results)%100 == 0: print('Controlled arrivals:',len(results),'/',len(cases),flush=True)
    if previews:
        sheet = Image.new('RGB',(4*480,((len(previews)+3)//4)*350),'#192225')
        d = ImageDraw.Draw(sheet)
        for i,(name,im) in enumerate(previews):
            x,y=i%4*480,i//4*350;sheet.paste(im.resize((480,320),Image.Resampling.NEAREST),(x,y))
            d.text((x+6,y+325),name,font=label_font(15),fill='white')
        sheet.save(VERIFY/'native-buffer-cards.png')
    return dict(cases=results,count=len(results),full_maps_tiles_palette_match=True,
                callee_saved_registers_and_stack_preserved=True,neighbours_and_save_unchanged=True,
                reconstructed_native_card_previews=len(previews),
                scope='Restored fixtures execute actual constructor and extension instructions. Full tile buffer/map and palette staging checked; upload is queued. Preview PNGs decode native buffers at full palette brightness, not natural screenshots. Actual VRAM is checked in the natural route.')


def natural(data,plan):
    replay = load_json(CAVE/'replay.json'); title = plan['titles'][0]
    with Session(data,VERIFY/'cave') as s:
        check(s.core.load_raw_state(STATE.read_bytes()),'Cannot restore native stairs fixture')
        for row in replay['inputs'][102:109]:
            codes = [getattr(s.core,'KEY_'+k) for k in row['keys']]
            s.core.set_keys(*codes);s.frames(row['hold']);s.core.clear_keys(*codes);s.frames(row['released'])
            check(s.core.frame_counter == row['end_frame'],'Native route frame changed')
        before_save = battery_snapshot(s.core)
        watch = [0x8000000+plan['pointers_at'],0x8000000+plan['palette_at'],0x8000000+plan['records_at']+2*12]
        trace = ReaderTrace(s.core,watch)
        try:
            s.core.set_keys(s.core.KEY_A);trace.frames(3);s.core.clear_keys(s.core.KEY_A);trace.frames(7)
            actual = s.capture('native-second-floor');expected = expected_image(plan,title,2)
            expected.save(s.output/'approved-second-floor-rgb555.png')
            coords = [(x,y) for y in range(160) for x in range(240) if expected.getpixel((x,y)) != (0,0,0)]
            mismatches = [p for p in coords if actual.getpixel(p) != expected.getpixel(p)]
            check(not mismatches,f'Natural artwork mismatch: {len(mismatches)} pixels; first {mismatches[:4]}')
            check(bytes(s.core.memory[0x06000000:0x06002800]) == bytes(s.core.memory[TILES:TILES+0x2800]),'Natural queued VRAM upload differs from complete tile buffer')
            check(all(any(int(r['address'],0)==a for r in trace.source_reads) for a in watch),'Missing native appended resource read')
            captures = [(0,actual)]
            for n in range(1,30):
                trace.frames(10);im=s.capture(f'after-{n*10:03d}')
                captures.append((n*10,im))
            trace.frames(3)
            check(s.core.frame_counter == replay['inputs'][109]['end_frame'],'Stair confirmation timing changed')
            check(s.core.memory.u8[0x02004FF1] == 2,'Natural transition did not enter floor 2')
            check(battery_snapshot(s.core)==before_save,'Arrival changed native save')
            before_position=position(s.core)
            for row in replay['inputs'][110:116]:
                codes=[getattr(s.core,'KEY_'+k) for k in row['keys']]
                s.core.set_keys(*codes);trace.frames(row['hold']);s.core.clear_keys(*codes);trace.frames(row['released'])
                check(s.core.frame_counter == row['end_frame'],'Resumed route timing changed')
            after=s.capture('gameplay-resumed');after_position=position(s.core)
            check(before_position != after_position,'Player did not move after tutorial dismissal')
            with Session(BASELINE.read_bytes(),VERIFY/'baseline-cave') as old:
                check(old.core.load_raw_state(STATE.read_bytes()),'Cannot restore paired baseline')
                for row in replay['inputs'][102:116]:
                    codes=[getattr(old.core,'KEY_'+k) for k in row['keys']]
                    old.core.set_keys(*codes);old.frames(row['hold']);old.core.clear_keys(*codes);old.frames(row['released'])
                before_image=old.capture('gameplay-resumed')
                check(ImageChops.difference(before_image,after).getbbox() is None,'Gameplay screen differs after the card clears')
                check(position(old.core)==after_position and old.core.frame_counter==s.core.frame_counter,'Paired player position/frame differs')
                check(battery_snapshot(old.core)==battery_snapshot(s.core),'Paired route saves differ')
            check(not trace.errors,'Native reader trace errors')
            sheet=Image.new('RGB',(6*240,((len(captures)+5)//6)*180),'#192225');d=ImageDraw.Draw(sheet)
            for i,(n,im) in enumerate(captures):
                x,y=i%6*240,i//6*180;sheet.paste(im,(x,y));d.text((x+4,y+162),f'+{n} frames',fill='white',font=label_font(11))
            sheet.save(s.output/'transition-sheet.png')
            return dict(fixture=str(STATE.relative_to(ROOT)),fixture_sha256=digest(STATE.read_bytes()),
                replay_input_indexes=[102,115],replay_sha256=digest((CAVE/'replay.json').read_bytes()),
                matching_artwork_pixels=len(coords),pixel_mismatches=0,full_vram_upload_matches=True,source_reads=trace.source_reads,
                arrival_frame=57384,final_frame=s.core.frame_counter,save_unchanged=True,
                player_before=before_position,player_after=after_position,
                baseline_after_fade_pixels_frame_position_save_match=True,
                scope='Normal buttons from a restored pre-stair fixture through the natural floor-2 arrival, fade and resumed movement. No dungeon/floor/renderer state injection in this route.')
        finally: trace.close()


def verify(limit=None):
    mgba.log.silence();data=ROM.read_bytes();original=ORIGINAL_ROM.read_bytes()
    build=load_json(OUT/'english-build.json');plan=load_json(OUT/'allocation-plan.json')
    check(digest(data)==build['rom_sha256'] and digest((OUT/'allocation-plan.json').read_bytes())==build['allocation_plan_sha256'],'Build/plan changed')
    check(all(data[a:b]==original[a:b] for a,b in SOURCE_RANGES),'Original arrival source modified')
    VERIFY.mkdir(parents=True,exist_ok=True)
    report=dict(source_rom=str(ORIGINAL_ROM.relative_to(ROOT)),source_sha256=digest(original),
        verified_rom=str(ROM.relative_to(ROOT)),rom_sha256=digest(data),
        harness_sha256=digest(Path(__file__).read_bytes()),floor_raster_roundtrips=floor_pixels(data,plan),controlled=controlled(data,plan,limit),
        natural=natural(data,plan),original_arrival_sources_unchanged=True)
    save_json(VERIFY/('probe.json' if limit else 'verification.json'),report)
    print('Passed',report['controlled']['count'],'controlled cases and natural floor-2 artwork/fade route',flush=True)


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--limit',type=int);args=parser.parse_args()
    verify(args.limit)
