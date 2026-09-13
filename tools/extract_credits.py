"""Extract the original positioned ending-credit text cards, without ROM writes."""
import struct
from pathlib import Path

from PIL import Image, ImageDraw

from tools.build_first_label import ROOT, ORIGINAL_ROM, digest, load_manifest
from tools.font_metrics import extract_fonts, measure_line
from tools.review_fonts import draw_glyph
from tools.extract_arrival_cards import label_font, save_json
from tools.translation_pipeline import check
from tools.verify_story_provenance import positioned_coordinates

OUT = ROOT/'build/credits'
START, END = 0x91D688, 0x91DD00


def palette(rom):
    def channel(v):
        v = (v >> 3) & 31
        return (v << 3) | (v >> 2)
    return [[channel(v >> shift) for shift in (0, 8, 16)]
            for v, in struct.iter_unpack('<I', rom[0xCA178C:0xCA17CC])]


def collect(rom):
    check(digest(rom) == load_manifest()['base_sha256'], 'Expected pinned Japanese ROM')
    font = extract_fonts(rom)[2]
    pages, pending, commands, sources, glyph_ranges = [], [], [], {}, {}
    for at in range(START, END, 8):
        word, pointer = struct.unpack_from('<II', rom, at)
        opcode = word & 255
        commands.append({'offset': f'0x{at:08X}', 'end_exclusive': f'0x{at+8:08X}',
                         'raw_hex': rom[at:at+8].hex(), 'opcode': opcode})
        if opcode == 0x29:
            source = pointer - 0x08000000
            check(0x91DDB0 <= source < 0x91E6A8, 'Unexpected credit source')
            end = rom.index(0, source)+1
            text = rom[source:end-1].decode('ascii')
            check(text and all(32 <= ord(c) < 127 for c in text), 'Nonliteral credit source')
            x, y = positioned_coordinates(word)
            advance = measure_line(font, text)['advance']
            draw_x = x if x >= 0 else max(0, (208-advance)//2)
            draw_y = y if y >= 0 else (pending[-1]['y'] if pending else 0)-y
            pending.append({'command_offset': f'0x{at:08X}', 'source_offset': f'0x{source:08X}',
                            'encoded_text': text, 'text': text.replace('@', '©'),
                            'kind': 'copyright' if text.startswith('@') else 'name' if text == text.upper() and x >= 0 else 'heading',
                            'command_x': x, 'command_y': y, 'x': draw_x, 'y': draw_y,
                            'advance': advance})
            sources[source] = {'offset': f'0x{source:08X}', 'end_exclusive': f'0x{end:08X}',
                               'raw_hex': rom[source:end].hex(), 'text': text.replace('@', '©')}
            for c in text:
                g = font['glyphs'][c]
                for key, size in (('descriptor', 12), ('bitmap', 72)):
                    start = int(g[key], 0)-0x08000000
                    glyph_ranges[(start, size)] = {'offset': f'0x{start:08X}', 'end_exclusive': f'0x{start+size:08X}',
                                                  'kind': key, 'sha256': digest(rom[start:start+size])}
        elif opcode == 0x2E:
            check(word == 0x00281B2E and pending, 'Unexpected credit presentation command')
            check(len(pending) <= 16, 'Credit queue overflow')
            pages.append({'id': f'credits-{len(pages)+1:02d}', 'label': pending[0]['text'],
                          'present_command': f'0x{at:08X}', 'lines': pending})
            pending = []
        else:
            check(not pending, 'Other commands intervene in a pending text card')
    check(not pending and len(pages) == 31 and sum(len(p['lines']) for p in pages) == 140,
          'Credit command/page inventory changed')
    check(len(sources) == 139, 'Credit source inventory changed')
    return {'schema': 1, 'source_rom': str(ORIGINAL_ROM.relative_to(ROOT)), 'source_sha256': digest(rom),
            'output_rom': None, 'font_id': 2, 'palette': palette(rom), 'window': [16, 16, 208, 136],
            'pages': pages, 'sources': list(sources.values()), 'commands': commands,
            'glyph_ranges': list(glyph_ranges.values()),
            'resource_ranges': [{'offset': f'0x{a:08X}', 'end_exclusive': f'0x{b:08X}', 'purpose': owner,
                                 'sha256': digest(rom[a:b])} for a,b,owner in (
                                     (0xCA178C,0xCA17CC,'original credits palette'),
                                     (0x86F44C,0x86F45C,'original credits window descriptor'))],
            'scope': '31 positioned credit text cards from the Japanese original, including five opening strings absent from the prior 134-source audit. All are already English. Sources, commands, bitmap and descriptor ranges are occupied; gaps are protected. Text-layer reconstruction, not complete ending playback or an inventory of ending illustrations.',
            'copyright_encoding': 'The font-2 glyph at ASCII @ is a copyright symbol. Human-readable text uses ©; source bytes remain @.'}


def original_image(rom, page):
    font, colours = extract_fonts(rom)[2], palette(rom)
    im = Image.new('RGB', (240,160), 'black')
    for line in page['lines']:
        x, y = 16+line['x'], 16+line['y']
        for c in line['encoded_text']:
            glyph = draw_glyph(font, c, colours)
            im.paste(glyph, (x,y), glyph)
            x += font['glyphs'][c]['advance']
    return im


def contact_sheet(images, pages, scale=2):
    cols=4; cellw=240*scale+24; cellh=160*scale+52
    out=Image.new('RGB',(cols*cellw,100+((len(pages)+cols-1)//cols)*cellh),'#172328')
    d=ImageDraw.Draw(out)
    d.text((20,15),'Torneko 3 · Original Japanese-ROM credits',font=label_font(26),fill='#eff2ec')
    d.text((20,53),'31 text cards · original font and colours · isolated text layer',font=label_font(18),fill='#b6c6c8')
    for i,(im,p) in enumerate(zip(images,pages)):
        x=i%cols*cellw+12;y=100+i//cols*cellh
        out.paste(im.resize((240*scale,160*scale),Image.Resampling.NEAREST),(x,y))
        d.text((x,y+160*scale+7),p['id']+' · '+p['label'][:34],font=label_font(15),fill='#d6e1dc')
    return out


def extract():
    rom=ORIGINAL_ROM.read_bytes(); manifest=collect(rom); out=OUT/'original';out.mkdir(parents=True,exist_ok=True)
    images=[]
    for p in manifest['pages']:
        im=original_image(rom,p);im.save(out/(p['id']+'.png'));images.append(im)
    contact_sheet(images,manifest['pages']).save(OUT/'credits-original.png')
    contact_sheet(images,manifest['pages'],1).save(OUT/'credits-original-1x.png')
    manifest['generator_sha256']=digest(Path(__file__).read_bytes())
    save_json(OUT/'manifest.json',manifest)
    print('Extracted 31 original credit cards: 140 references, 139 distinct English sources.')


if __name__=='__main__':
    extract()
