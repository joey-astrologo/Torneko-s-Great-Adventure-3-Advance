"""Check all decoded scene maps against the original native loader."""
from pathlib import Path
import struct

import mgba.log

from tools.build_first_label import ORIGINAL_ROM, ROOT, digest
from tools.extract_arrival_cards import save_json
from tools.extract_scene_review import OUT, scene
from tools import verify_dungeon_interface as ui
from tools import verify_tutorial_gameplay as queue
from tools.verify_system_labels import STATE
from tools.verify_expansion import Session
from tools.verify_first_label import battery_snapshot
from tools.translation_pipeline import check, load_json


def verify(limit=None):
    mgba.log.silence();rom=ORIGINAL_ROM.read_bytes();manifest=load_json(OUT/'scene-manifest.json')
    check(digest(Path('tools/extract_scene_review.py').read_bytes())==manifest['generator_sha256'],'Extractor changed')
    rows=[];animations=[];seen_headers=set()
    with Session(rom,OUT/'native') as s:
        for n in range(limit or 102):
            c=s.core;check(c.load_raw_state(STATE.read_bytes()),'Fixture restore failed')
            source,_,definitions=scene(rom,n)
            map_at=c.memory.u32[0x03000020];meta_at=c.memory.u32[0x0300001C]
            check((map_at,meta_at)==(0x02023160,0x0202ED60),'Native map buffers changed')
            guards=[(a,bytes(c.memory[a:b])) for a,b in [(map_at-8,map_at),(meta_at+920*18,meta_at+920*18+8),
                    (0x02002FD4,0x02004F80)]]
            save=battery_snapshot(c)
            t=ui.InterfaceTrace(c)
            try:
                call=ui.native_step(s,t,0x08066FE4,[n,0],stop=0x0806752C)
                expected_map=bytearray(128*94*4)
                for layer,plane in enumerate(source['planes']):
                    for y,row in enumerate(plane):
                        for x,entry in enumerate(row):struct.pack_into('<H',expected_map,(y*128+x)*4+layer*2,entry)
                actual_map=bytes(c.memory[map_at:map_at+len(expected_map)])
                check(actual_map==expected_map,f'Native compressed-map decode differs for scene {n}')
                expected_meta=b''.join(struct.pack('<9H',*(list(mt)+[0]*(9-len(mt)))) for mt in definitions)
                expected_meta=expected_meta.ljust(920*18,b'\0')
                check(bytes(c.memory[meta_at:meta_at+len(expected_meta)])==expected_meta,f'Native metatiles differ for scene {n}')
                expected_tiles=bytes(32)+rom[source['tiles']:source['tiles']+(source['static_tile_count']-1)*32]
                expected_tiles=expected_tiles.ljust(1024*32,b'\xFF')
                check(bytes(c.memory[0x06008000:0x06010000])==expected_tiles,f'Native static tile upload differs for scene {n}')
                palettes=list(source['palette_words'][:source['palette_banks']*16]);mode=c.memory.u8[0x02008CBC]
                if mode:
                    palettes=[(v if i%16==0 else (v&0x00FF00FF)|((((v>>8)&255)*3//4)<<8)|0xFF000000) for i,v in enumerate(palettes)]
                expected_pal=struct.pack('<'+str(len(palettes))+'I',*palettes)
                check(bytes(c.memory[0x030032A0:0x030032A0+len(expected_pal)])==expected_pal,f'Native palette staging differs for scene {n}')
                check(all(bytes(c.memory[a:a+len(raw)])==raw for a,raw in guards),'Native loader changed neighbours/profile')
                check(battery_snapshot(c)==save and not t.errors,'Native save or trace failure')
                rows.append(dict(scene=n,steps=call['steps'],map_start=map_at,map_end_exclusive=map_at+len(actual_map),
                    map_sha256=digest(actual_map),metatile_start=meta_at,metatile_end_exclusive=meta_at+len(expected_meta),
                    whole_decoded_map_matches=True,all_metatiles_and_padding_match=True,
                    static_vram_and_padding_match=True,palette_mode=mode,base_palette_staging_matches=True,
                    neighbours_profile_and_save_unchanged=True))
                if source['animation_frames'] and source['header'] not in seen_headers:
                    local,anim=0x03007800,0x02008C70
                    c.memory.u32[local]=source['header']+0x8000000
                    ui.native_step(s,t,0x08067588,[],stop=0x08067640,overrides={0x08067588:{'sp':local}})
                    for frame in source['animation_frames']:
                        if frame['frame']:
                            queue.select_slice(c,0x08067FDA,0x08067FEE,{'r5':anim},0)
                        check(c.memory.u32[anim+12]==frame['record']+0x8000000,'Native animation record differs')
                        ui.native_step(s,t,0x08067FEE,[],stop=0x08068048,overrides={0x08067FEE:{'r5':anim}})
                        nt=source['static_tile_count'];attributes=struct.unpack_from('<'+str(source['animated_tile_count'])+'H',rom,frame['attributes'])
                        frame_meta=[]
                        for mt in definitions:
                            frame_meta.extend((entry if (entry&1023)<nt else (entry&4095)|attributes[(entry&1023)-nt]) for entry in mt)
                            frame_meta.extend([0]*(9-len(mt)))
                        packed=struct.pack('<'+str(len(frame_meta))+'H',*frame_meta).ljust(920*18,b'\0')
                        check(bytes(c.memory[meta_at:meta_at+len(packed)])==packed,'Native animated metatile attributes differ')
                        dest=0x06008000+nt*32;size=source['animated_tile_count']*32
                        boundary=bytes(c.memory[dest-8:dest])+bytes(c.memory[dest+size:dest+size+8])
                        ui.native_step(s,t,0x08068118,[])
                        check(bytes(c.memory[dest:dest+size])==rom[frame['tiles']:frame['tiles_end_exclusive']],'Native animated tiles differ')
                        check(boundary==bytes(c.memory[dest-8:dest])+bytes(c.memory[dest+size:dest+size+8]),'Animation changed adjacent VRAM')
                        animations.append(dict(scene=n,frame=frame['frame'],source=frame['tiles'],source_end_exclusive=frame['tiles_end_exclusive'],
                            record=frame['record'],whole_vram_and_metatile_attributes_match=True,adjacent_vram_unchanged=True))
                    check(battery_snapshot(c)==save,'Animation changed save')
                seen_headers.add(source['header'])
            finally:t.close()
            if (n+1)%10==0:print('Native scenes:',n+1,flush=True)
    report=dict(source_rom=str(ORIGINAL_ROM.relative_to(ROOT)),source_sha256=digest(rom),output_rom=None,
        scene_manifest_sha256=digest((OUT/'scene-manifest.json').read_bytes()),harness_sha256=digest(Path(__file__).read_bytes()),
        fixture=str(STATE),fixture_sha256=digest(STATE.read_bytes()),cases=rows,count=len(rows),animation_cases=animations,
        scope='Restored controlled scene IDs through native selection, descriptor copy, base palette staging, static VRAM tiles, padded metatiles and both full RLE/XOR map planes. Additional animation initialization/selection/attribute/upload slices cover every tile-animation frame; timer pacing, palette animation, camera and actors are separate. No natural visits or ending playback. No ROM or persistent save writes.')
    save_json(OUT/('native-probe.json' if limit else 'native-verification.json'),report)
    print('Passed',len(rows),'complete native background decodes',flush=True)


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--limit',type=int);args=parser.parse_args();verify(args.limit)
