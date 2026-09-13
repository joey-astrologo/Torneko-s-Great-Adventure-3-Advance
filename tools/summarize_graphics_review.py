"""Publish source-linked detail crops and a bounded graphics-review index."""
from html import escape
from pathlib import Path
import struct

from PIL import Image, ImageDraw

from tools.build_first_label import ROOT, ORIGINAL_ROM, digest
from tools.build_arrival_credits import ROM
from tools.extract_arrival_cards import label_font, save_json
from tools.extract_scene_review import OUT, scene
from tools.translation_pipeline import check, load_json

DETAILS=[
    (97,'Cake plaque',(100,30,142,54),'Lettering-like marks; no reliable Japanese or English transcription from these pixels.'),
    (43,'Gold wall panel',(230,37,255,63),'Decorative or lettering-like pattern; no confidently readable Japanese.'),
    (18,'Hanging paper',(102,115,132,165),'Blank paper below the holder; no visible writing in this source crop.'),
    (34,'Inn sign',(147,51,183,80),'Readable INN, already Latin lettering in the original.'),
    (72,'Outside sign',(188,185,226,219),'Coloured pictorial/decorative marks; no confidently readable Japanese.'),
    (66,'Room notice',(230,102,260,136),'Notice-like horizontal strokes; too small to transcribe reliably.'),
]
ENDING=[(0x91D628,9),(0x91D7C0,56),(0x91D9A8,83),(0x91DD08,31),(0x91DD78,101)]


def tile_sources(rom,row,box):
    side=row['metatile_side'];cellsize=side*8;_,_,definitions=scene(rom,row['scene'])
    sources={}
    for layer,plane in enumerate(row['planes']):
        for my in range(box[1]//cellsize,(box[3]-1)//cellsize+1):
            for mx in range(box[0]//cellsize,(box[2]-1)//cellsize+1):
                meta=plane[my][mx]
                check(meta<1024,'Detail needs whole-metatile flip provenance')
                if not meta:continue
                for k,entry in enumerate(definitions[meta]):
                    x,y=mx*cellsize+k%side*8,my*cellsize+k//side*8
                    if x+8<=box[0] or x>=box[2] or y+8<=box[1] or y>=box[3]:continue
                    index=entry&1023
                    if not index:continue
                    check(index<row['static_tile_count'],'Detail reaches animated tile; add frame provenance')
                    at=row['tiles']+(index-1)*32
                    key=(at,layer,x,y)
                    sources[key]=dict(start=at,end_exclusive=at+32,sha256=digest(rom[at:at+32]),
                        layer=layer,screen_xy=[x,y],metatile=meta,
                        metatile_word=row['metatiles']+((meta-1)*side*side+k)*2,
                        tile_index=index,tilemap_entry=f'0x{entry:04X}',palette_bank=entry>>12)
    return list(sources.values())


def summarize():
    rom=ORIGINAL_ROM.read_bytes();english=ROM.read_bytes()
    manifest=load_json(OUT/'scene-manifest.json');native=load_json(OUT/'native-verification.json')
    check(native['scene_manifest_sha256']==digest((OUT/'scene-manifest.json').read_bytes()),'Native report predates scene export')
    check(native['count']==102 and len(native['animation_cases'])==194,'Incomplete native verification')
    rows=[];sheet=Image.new('RGB',(3*360,80+2*350),'#192225');d=ImageDraw.Draw(sheet)
    d.text((16,15),'Small source-art details / 6x pixels',font=label_font(23),fill='white')
    d.text((16,47),'Review leads, not confirmed missing translations',font=label_font(16),fill='#b6c6c8')
    (OUT/'details').mkdir(exist_ok=True)
    for i,(number,label,box,note) in enumerate(DETAILS):
        source=manifest['entries'][number];im=Image.open(ROOT/source['png']).crop(box)
        path=OUT/'details'/f'scene-{number:03d}.png';im.save(path)
        x,y=i%3*360,80+i//3*350
        d.text((x+8,y+5),f'Scene {number:03d}: {label}',font=label_font(15),fill='white')
        sheet.paste(im.resize((im.width*6,im.height*6),Image.Resampling.NEAREST),(x+8,y+35))
        rows.append(dict(scene=number,label=label,pixel_crop=list(box),png=str(path.relative_to(ROOT)),
            png_sha256=digest(path.read_bytes()),assessment=note,source_tiles=tile_sources(rom,source,box)))
    sheet.save(OUT/'small-details.png')
    ending=[]
    for at,number in ENDING:
        word,operand=struct.unpack_from('<II',rom,at)
        check(word==3 and operand==number,'Ending scene command changed')
        ending.append(dict(start=at,end_exclusive=at+8,raw_hex=rom[at:at+8].hex(),scene=number,
            evidence='Opcode 03 loads scene ID through native dispatch 08065152, calling background loader 08066FE4 at 080651A8. Static script association; no full ending playback.'))
    unique={}
    for row in manifest['entries']:
        for span in row['source_ranges']:
            key=(span['start'],span['end_exclusive'],span['purpose'])
            record=unique.setdefault(key,dict(span,scenes=[]))
            record['scenes'].append(row['scene'])
    spans=sorted(unique.values(),key=lambda x:(x['start'],x['end_exclusive'],x['purpose']))
    for span in spans:
        a,b=span['start'],span['end_exclusive']
        check(english[a:b]==rom[a:b],f'Accepted English build changed reviewed art {a:08X}')
    report=dict(source_rom=str(ORIGINAL_ROM.relative_to(ROOT)),source_sha256=digest(rom),output_rom=None,
        compared_english_rom=str(ROM.relative_to(ROOT)),compared_english_sha256=digest(english),
        source_ranges=spans,range_convention='ROM file offsets, start inclusive, end exclusive',
        shared_sources='Repeated or nested source ranges describe existing shared readers, not independent writable allocations.',
        ending_scene_commands=ending,details=rows,confirmed_additional_japanese_text=[],
        source_bytes_unchanged_in_current_english=True,
        visual_review='All five scene overview sheets and seven animation sheets inspected; selected small signs/panels inspected at native size and enlarged. END and INN are readable original English. Some decorative/lettering-like marks remain untranscribed, not asserted Japanese.',
        limits=['Not a complete inventory of sprite/object overlays or every ROM graphics loader.',
                'Base palette and first-frame scene composites; palette/time-of-day effects and camera motion are separate.',
                'No separate town-name card is confirmed in this background family; absence elsewhere is not proved.',
                'Native credit playback, ending transitions and new-English full regression were not part of this step.'],
        summarizer_sha256=digest(Path(__file__).read_bytes()))
    save_json(OUT/'resource-ranges.json',report)
    cards=''.join(f'<a href="scenes/scene-{s["scene"]:03d}.png"><img loading="lazy" src="scenes/scene-{s["scene"]:03d}.png" alt="Scene {s["scene"]:03d}"><span>Scene {s["scene"]:03d} · {s["image_size"][0]}×{s["image_size"][1]}</span></a>' for s in manifest['entries'])
    html='''<!doctype html><html lang="en"><meta charset="utf-8"><title>Torneko 3 original graphics review</title>
<style>body{background:#192225;color:#eaf0eb;font:16px system-ui;margin:32px}a{color:#cde3bb}p{max-width:900px;line-height:1.5}.gallery{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:20px}.gallery a{display:flex;flex-direction:column;background:#101819;padding:10px;text-decoration:none}.gallery img{width:100%;height:220px;object-fit:contain;image-rendering:pixelated}.gallery span{margin-top:8px}nav a{display:inline-block;margin:8px 20px 8px 0}</style>
<h1>Torneko 3 · Original graphics review</h1><p>102 scene-table backgrounds, 73 graphics sets and all 194 tile-animation frames. Source maps and native loader output agree. No additional readable Japanese title card was identified in this family. Small ambiguous details are preserved for review.</p>
<nav><a href="ending-backgrounds.png">Ending backgrounds / END graphic</a><a href="small-details.png">Small signs and lettering-like details</a><a href="../../docs/GRAPHICS_REVIEW.md">Findings and coverage</a></nav>
<p>Click an image for its full-resolution PNG. These are decoded background layers, including offscreen layouts; actors, objects, camera, fades and palette animation are separate. Some tiny decorative marks cannot be reliably transcribed. The current English ROM is unchanged.</p><div class="gallery">'''+cards+'</div></html>'
    (OUT/'index.html').write_text(html)
    save_json(OUT/'acceptance.json',dict(source_sha256=digest(rom),output_rom=None,english_rom_sha256=digest(english),
        native_scenes=102,native_animation_frames=194,new_confirmed_japanese_artwork=0,
        review_details=len(rows),source_range_records=len(spans),
        artifacts={str(p.relative_to(ROOT)):digest(p.read_bytes()) for p in
                   [OUT/'scene-manifest.json',OUT/'native-verification.json',OUT/'resource-ranges.json',OUT/'index.html',OUT/'small-details.png',OUT/'ending-backgrounds.png']}))
    print('Review index and six source-linked details published;',len(spans),'existing range records protected; English ROM unchanged.')


if __name__=='__main__':summarize()
