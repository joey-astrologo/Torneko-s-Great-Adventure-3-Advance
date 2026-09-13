"""Adapt original credits capitals into a coherent arrival-card display face."""
from pathlib import Path
import string

from PIL import Image, ImageDraw

from tools.build_first_label import ROOT, ORIGINAL_ROM, digest, load_manifest
from tools.extract_arrival_cards import OUTPUT, label_font, save_json
from tools.extract_credits import palette
from tools.font_metrics import extract_fonts
from tools.reconstruct_arrival_font import bitmap_record
from tools.review_fonts import draw_glyph
from tools.translation_pipeline import check

DEST=ROOT/'assets/fonts/credits-arrival-candidate.json'
# These punctuation shapes were inspected in the original atlas. In particular,
# @ draws copyright and _ draws a box; do not pretend they are ASCII equivalents.
CHARACTERS=string.ascii_uppercase+string.ascii_lowercase+string.digits+" '-.,:!?()/&+#%"+'©'
LEVELS=(0,0,85,85,170,170,255,255)


def build():
    rom=ORIGINAL_ROM.read_bytes();check(digest(rom)==load_manifest()['base_sha256'],'Wrong original ROM')
    native=extract_fonts(rom)[2];glyphs={};sources={}
    for ch in CHARACTERS:
        source='@' if ch=='©' else ch.upper()
        g=native['glyphs'][source]
        check(not g['colored'] or all(v<8 for row in g['pixels'] for v in row),'Unexpected credits capital palette index')
        a=int(g['descriptor'],0)-0x08000000;b=int(g['bitmap'],0)-0x08000000
        source_record={'character':source,'code':ord(source),'descriptor_offset':f'0x{a:08X}',
                       'descriptor_end_exclusive':f'0x{a+12:08X}','descriptor_hex':rom[a:a+12].hex(),
                       'bitmap_offset':f'0x{b:08X}','bitmap_end_exclusive':f'0x{b+72:08X}',
                       'bitmap_hex':rom[b:b+72].hex(),'single_byte_map_offset':f'0x{0xCA2674+ord(source)*2:08X}'}
        sources[source]=source_record
        im=Image.new('L',(12,12));im.putdata([LEVELS[v] if g['colored'] else 255 if v else 0 for row in g['pixels'] for v in row])
        bbox=im.getbbox()
        origin={'origin':'credits_derived','source_character':source,'source_bitmap_offset':source_record['bitmap_offset'],
                'variant':'small_cap' if ch.islower() else 'capital_or_symbol'}
        if bbox is None:
            check(ch==' ','Unexpected empty source glyph '+repr(ch))
            glyphs[ch]=bitmap_record(im,0,origin,5);continue
        # Both cases use the same large italic source design. The original
        # lowercase slots instead contain a separate upright small-cap design.
        height=13 if ch.islower() else 17;scale=height/12
        im=im.crop(bbox)
        im=im.resize((max(1,round(im.width*scale*.82)),max(1,round(im.height*scale))),Image.Resampling.LANCZOS)
        # Quantize before cropping so invisible low-alpha fringes cannot enlarge
        # the exported metrics. The browser receives only four alpha levels.
        im=im.point(lambda v:((v*3+127)//255)*85)
        glyphs[ch]=bitmap_record(im,round((bbox[1]-12)*scale),origin)
        check(glyphs[ch]['width']<glyphs[ch]['advance'],'Arrival glyph can overwrite its next cell')
    face={'id':'credits','name':'Credits adapted · small capitals','cap_height':17,'glyphs':glyphs,
          'source':{'source_rom_sha256':digest(rom),'font_id':2,'font_table':'0x00CA1300'},
          'scope':'Modified original-Japanese credits capitals: blue/dark fringe removed, four alpha levels, 82% width, capitals/digits 17px and derived small capitals 13px. New spacing. No external or fan-patch glyphs; no conventional lowercase design claimed.'}
    report={'schema':1,'source_rom':str(ORIGINAL_ROM.relative_to(ROOT)),'source_sha256':digest(rom),'output_rom':None,
            'harness_sha256':digest(Path(__file__).read_bytes()),'alphabet':CHARACTERS,'face':face,
            'source_glyphs':list(sources.values()),'parameters':{'palette_index_to_alpha':LEVELS,
            'horizontal_scale':.82,'cap_height':17,'small_cap_height':13,'space_advance':5,'gap':1},
            'scope':'Offline font audition only. Occupied source ranges; no ROM allocation or insertion.'}
    save_json(DEST,report)
    # Original and modified forms side by side, with a shared baseline per row.
    chars=string.ascii_uppercase+string.ascii_lowercase+string.digits+"'-.,:!?";sheet=Image.new('RGB',(1120,96+((len(chars)+9)//10)*128),'#192225');d=ImageDraw.Draw(sheet)
    d.text((16,16),'Credits alphabet · original glyph / adapted arrival glyph',font=label_font(20),fill='#e9eee8')
    d.text((16,49),'3x view · lowercase inputs use newly derived small capitals · original ROM only',font=label_font(15),fill='#a4b1b0')
    for i,ch in enumerate(chars):
        x=i%10*112+12;y=96+i//10*128
        src=draw_glyph(native,ch,palette(rom)).resize((36,36),Image.Resampling.NEAREST);sheet.paste(src,(x,y+30),src)
        g=glyphs[ch]
        for yy,row in enumerate(g['rows']):
            for xx,v in enumerate(row):
                if v!='0':
                    at=(x+48+xx*3,y+66+(g['top']+yy)*3)
                    d.rectangle((*at,at[0]+2,at[1]+2),fill=tuple(c*int(v)//3 for c in (255,247,229)))
        d.text((x,y+86),ch+' · '+('small cap' if ch.islower() else 'capital' if ch.isupper() else 'symbol'),font=label_font(12),fill='#b9c9c7')
    out=OUTPUT/'audition';out.mkdir(parents=True,exist_ok=True);sheet.save(out/'credits-alphabet-review.png')
    print(f'Built credits-derived arrival face: {len(glyphs)} characters from {len(sources)} original glyphs.')


if __name__=='__main__':build()
