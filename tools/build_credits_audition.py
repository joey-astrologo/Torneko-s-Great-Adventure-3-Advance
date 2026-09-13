"""Package a standalone ending-credit typography audition; no ROM insertion."""
from pathlib import Path
from PIL import Image

from tools.build_first_label import ROOT, ORIGINAL_ROM, digest
from tools.build_arrival_audition import data_url
from tools.extract_credits import OUT as CREDITS, collect, original_image
from tools.extract_arrival_cards import save_json
from tools.font_metrics import extract_fonts
from tools.reconstruct_arrival_font import bitmap_record
from tools.translation_pipeline import check, load_json
import json

OUT=CREDITS/'audition'
FONT=ROOT/'assets/fonts/arrival-candidates.json'
TEMPLATE=ROOT/'tools/credits_audition/index.html'
SCRIPT=ROOT/'tools/credits_audition/studio.js'
ARRIVAL_TEMPLATE=ROOT/'tools/arrival_audition/index.html'


def bitmap(glyph,origin,baseline=12):
    im=Image.new('L',(12,len(glyph['pixels'])))
    for y,row in enumerate(glyph['pixels']):
        for x,v in enumerate(row):im.putpixel((x,y),round(v*255/7) if glyph['colored'] else 255 if v else 0)
    return bitmap_record(im,-baseline,{'origin':origin},glyph['advance'])


def build():
    rom=ORIGINAL_ROM.read_bytes();manifest=collect(rom);fonts=load_json(FONT)
    check(fonts['harness_sha256']==digest((ROOT/'tools/reconstruct_arrival_font.py').read_bytes()),'Stale arrival font asset')
    native=extract_fonts(rom)
    small={'id':'small','name':'Original small text (font 0)','cap_height':native[0]['glyphs']['H']['ink_bounds'][3]-native[0]['glyphs']['H']['ink_bounds'][1],
           'glyphs':{ch:bitmap(g,'original_font_0') for ch,g in native[0]['glyphs'].items()},
           'source':{'source_rom_sha256':digest(rom),'table':'0x00C93B4C'}}
    fonts['faces'].append(small)
    for face in fonts['faces']:
        # A source glyph, explicitly marked, avoids dropping/changing copyright.
        g=bitmap(native[2]['glyphs']['@'],'original_copyright_supplement')
        # Scale the source 12px symbol into the candidate's source cap height.
        im=Image.new('L',(g['width'],g['height']))
        im.putdata([int(v)*85 for row in g['rows'] for v in row])
        h=face['cap_height'];im=im.resize((h,h),Image.Resampling.NEAREST)
        face['glyphs']['©']=bitmap_record(im,-h,{'origin':'original_copyright_supplement'},h+1)
    font_hash=digest(json.dumps(fonts,sort_keys=True,separators=(',',':')).encode())
    data={'schema':1,'source_sha256':digest(rom),'font_asset_sha256':font_hash,
          'renderer_sha256':digest(SCRIPT.read_bytes()),'pages':manifest['pages'],'fonts':fonts,
          'originals':{p['id']:data_url(original_image(rom,p)) for p in manifest['pages']}}
    encoded=json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')
    style=ARRIVAL_TEMPLATE.read_text().split('<style>',1)[1].split('</style>',1)[0]
    html=TEMPLATE.read_text().replace('__STYLE__',style).replace('__DATA__',encoded).replace('__SCRIPT__',SCRIPT.read_text())
    OUT.mkdir(parents=True,exist_ok=True);(OUT/'index.html').write_text(html)
    save_json(OUT/'build.json',{'source_rom':manifest['source_rom'],'source_sha256':digest(rom),'output_rom':None,
              'cards':31,'references':140,'distinct_sources':139,'font_asset_sha256':font_hash,
              'arrival_font_asset_sha256':digest(FONT.read_bytes()),
              'html_sha256':digest((OUT/'index.html').read_bytes()),
              'source_files':{str(p.relative_to(ROOT)):digest(p.read_bytes()) for p in (Path(__file__),TEMPLATE,SCRIPT,ARRIVAL_TEMPLATE)},
              'scope':'Offline ending-credit text-layer typography audition. Original names, roles and copyright preserved. Rounded starts the audition following the user preference; no final font choice or ROM insertion.'})
    print('Built offline credits audition:',OUT/'index.html')


if __name__=='__main__':build()
