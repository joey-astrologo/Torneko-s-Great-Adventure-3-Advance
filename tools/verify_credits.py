"""Verify every original credit card using restored, controlled native rendering."""
from pathlib import Path
import struct

import mgba.log
from PIL import Image, ImageChops

from tools.build_first_label import ORIGINAL_ROM, ROOT, digest
from tools import verify_dungeon_interface as ui
from tools.verify_expansion import Session
from tools.verify_companion_dialogue import run_to
from tools.verify_core_gameplay import write_bytes
from tools.verify_items import distinct_glyph_observations
from tools.extract_credits import OUT, collect, original_image, palette
from tools.extract_arrival_cards import save_json
from tools.font_metrics import extract_fonts
from tools.translation_pipeline import check

STATE=ROOT/'build/story-provenance/natural/final.state'
CONTROLLER=0x0203F000
WINDOW=0x02034CD8


def verify(limit=None):
    mgba.log.silence();rom=ORIGINAL_ROM.read_bytes();manifest=collect(rom)
    font=extract_fonts(rom)[2];state=STATE.read_bytes();cases=[]
    with Session(rom,OUT/'native') as s:
        c=s.core
        for page in manifest['pages'][:limit]:
            check(c.load_raw_state(state),'Cannot restore disposable original state')
            root=c.memory.u32[0x03000010]
            write_bytes(c,CONTROLLER,b'\0'*0x80)
            c.memory.u32[root+0x998]=0
            for line in page['lines']:
                c.memory.u32[CONTROLLER+0x24]=0x08000000+int(line['command_offset'],0)
                run_to(c,0x08064E28,0x0806559E,{'r0':CONTROLLER})
            check(c.memory.u32[root+0x998]==len(page['lines']),'Native queue count differs')
            t=ui.InterfaceTrace(c)
            try:
                setup=ui.native_step(s,t,0x08062928,[],stop=0x08062976)
                # Palette writes are queued as packed RGB in IWRAM; the forced
                # slice deliberately does not play the ending's fade/upload.
                palette_at=c.memory.u32[0x08089D38]+0xF0*4
                check(palette_at==0x03003660 and bytes(c.memory[palette_at:palette_at+64])==rom[0xCA178C:0xCA17CC],
                      'Native credit palette staging differs from its original source')
                draw=ui.native_step(s,t,0x080629A2,[],stop=0x08062A6A)
                check(c.memory.u32[root+0x998]==0,'Native queue was not consumed')
                gs,repeats=distinct_glyph_observations(t.positions)
                expected=[]
                for line in page['lines']:
                    x=line['x']
                    for ch in line['encoded_text']:
                        expected.append((ord(ch),x,line['y'],font['glyphs'][ch]['advance']))
                        x+=font['glyphs'][ch]['advance']
                actual=[(g['code'],g['x'],g['y'],g['advance']) for g in gs]
                check(actual==expected,'Credit native glyph/position mismatch '+page['id'])
                check(all(g['font']==2 and g['spacing']==0 and g['window_origin']==[16,16]
                          and g['window_width']==208 and g['window_height']==136 for g in gs),
                      'Credit font/window differs')
                at=c.memory.u32[WINDOW+0x14];w=c.memory.u16[WINDOW+4];h=c.memory.u16[WINDOW+8]
                check(w==26 and h==17 and 0x02000000<=at<0x02040000-w*h*32,'Credit tile buffer bounds differ')
                raw=bytes(c.memory[at:at+w*h*32]);colours=palette(rom)
                im=Image.new('RGB',(240,160),'black')
                for y in range(h*8):
                    for x in range(w*8):
                        v=raw[((y//8)*w+x//8)*32+(y%8)*4+(x%8)//2]
                        index=(v>>(4*(x%2)))&15
                        im.putpixel((x+16,y+16),tuple(colours[index]))
                im.save(s.output/(page['id']+'.png'))
                reference=original_image(rom,page)
                delta=ImageChops.difference(im,reference)
                if delta.getbbox():delta.save(s.output/(page['id']+'-difference.png'))
                check(delta.getbbox() is None,'Native credit pixel buffer differs '+page['id'])
                case={'id':page['id'],'lines':len(page['lines']),'glyphs':len(gs),
                      'duplicate_observations':repeats,'font':2,'window':[16,16,208,136],
                      'buffer_start':f'0x{at:08X}','buffer_end_exclusive':f'0x{at+len(raw):08X}',
                      'native_buffer_sha256':digest(raw),'rgb_sha256':digest(im.tobytes()),
                      'extracted_pixels_match':True,'queue_consumed':True,
                      'setup_steps':setup['steps'],'draw_steps':draw['steps']}
                save_json(s.output/(page['id']+'.json'),dict(case,positions=gs));cases.append(case)
                print(page['id'],'native glyphs and whole text-layer pixels match',flush=True)
            finally:t.close()
    check(ORIGINAL_ROM.read_bytes()==rom,'Original ROM changed during credit verification')
    result={'source_rom':manifest['source_rom'],'source_sha256':digest(rom),'output_rom':None,
            'state':str(STATE.relative_to(ROOT)),'state_sha256':digest(state),
            'harness_sha256':digest(Path(__file__).read_bytes()),
            'extractor_sha256':digest((ROOT/'tools/extract_credits.py').read_bytes()),
            'cases':cases,'cards':len(cases),'references':sum(p['lines'] for p in cases),
            'native_packed_palette_staging_matches':True,'original_rom_unchanged':True,
            'scope':'Controlled original queue/setup/draw instructions, all glyph positions and entire decoded native tile buffer compared to independent extraction. Native packed palette staging matches source; full-bright RGB is reconstructed from the palette, not a captured fade/upload frame. Restored page fixtures, no natural ending playthrough, transition timing or background illustrations. No ROM or persistent save writes.'}
    save_json(OUT/('native-verification.json' if limit is None else 'native-probe.json'),result)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--limit',type=int);args=p.parse_args();verify(args.limit)
