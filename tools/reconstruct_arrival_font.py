"""Recover Shiren bitmap letters and mark system-font supplements for auditions."""
import string
from collections import defaultdict
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from tools.build_first_label import ROOT, digest
from tools.extract_arrival_cards import OUTPUT, label_font, save_json
from tools.translation_pipeline import check, load_json

DEST = ROOT / 'assets/fonts/arrival-candidates.json'
PAPYRUS = Path('/System/Library/Fonts/Supplemental/Papyrus.ttc')
ROUNDED = Path('/System/Library/Fonts/Supplemental/Comic Sans MS.ttf')
CHARACTERS = ''.join(chr(n) for n in range(32, 127))
# Reviewed character boundaries in the previously decoded, source-pinned strips.
# Most letters below touch their neighbour's occupied columns. They must not be
# inferred by counting blank columns; these selections isolate their real ink.
CURATED = {
    'D': (19, 101, 110), 'I': (1, 63, 70), 'J': (9, 46, 55),
    'O': (2, 2, 13), 'U': (16, 2, 11), 'V': (1, 2, 11),
    'W': (14, 2, 13), 'k': (12, 41, 49), 'p': (11, 105, 115),
    'y': (1, 42, 51), 'z': (9, 62, 71), '-': (2, 88, 98),
    "'": (25, 29, 33),
}


def isolated_candidates(entries):
    candidates = defaultdict(list)
    for e in entries:
        im = Image.open(ROOT/e['png']).convert('L')
        check(digest((ROOT/e['png']).read_bytes()) == e['png_sha256'], 'Reference PNG changed')
        runs, start = [], None
        for x in range(im.width+1):
            ink = x < im.width and any(im.getpixel((x, y)) for y in range(24))
            if ink and start is None:
                start = x
            if not ink and start is not None:
                runs.append((start, x)); start = None
        words, groups = e['source_comment_label'].split(), [[]]
        for pair in runs:
            if groups[-1] and pair[0]-groups[-1][-1][1] >= 5:
                groups.append([])
            groups[-1].append(pair)
        check(len(words) == len(groups), 'Review reference word segmentation')
        for word, group in zip(words, groups):
            if len(word) == len(group):
                for char, (left, right) in zip(word, group):
                    candidates[char].append((e['row'], left, right))
    return candidates


def bitmap_record(im, top, origin, advance=None):
    bbox = im.getbbox()
    if bbox is None:
        return {'width': 0, 'height': 0, 'top': 0, 'advance': advance or 6, 'rows': [], **origin}
    im = im.crop(bbox)
    # Four alpha levels form a reproducible small-palette bitmap, not a font file.
    rows = [''.join(str((im.getpixel((x, y))*3+127)//255) for x in range(im.width))
            for y in range(im.height)]
    return {'width': im.width, 'height': im.height, 'top': top+bbox[1],
            'advance': advance or im.width+1, 'rows': rows, **origin}


def outline_face(path, index, face_id, name):
    # Match a 17-pixel H; all glyphs share the same baseline and font size.
    size = min(range(8, 55), key=lambda n: abs(
        ImageFont.truetype(str(path), n, index=index).getbbox('H', anchor='ls')[3]
        - ImageFont.truetype(str(path), n, index=index).getbbox('H', anchor='ls')[1]-17))
    font = ImageFont.truetype(str(path), size, index=index)
    glyphs = {}
    for ch in CHARACTERS:
        box = font.getbbox(ch, anchor='ls')
        im = Image.new('L', (max(1, box[2]-box[0]), max(1, box[3]-box[1])))
        ImageDraw.Draw(im).text((-box[0], -box[1]), ch, font=font, anchor='ls', fill=255)
        glyphs[ch] = bitmap_record(im, box[1], {'origin': 'system_font'},
                                   advance=6 if ch == ' ' else None)
    return {'id': face_id, 'name': name, 'cap_height': 17, 'glyphs': glyphs,
            'source': {'file': str(path), 'sha256': digest(path.read_bytes()),
                       'collection_index': index, 'font_name': font.getname(), 'size': size},
            'scope': 'Rasterized audition glyphs from the installed font; no outline font redistributed.'}


def export():
    reference = load_json(OUTPUT/'references/shiren-source.json')
    source_root = ROOT.parent/'Shiren/shiren-revamp-fixes'
    for f in reference['source_files']:
        check(digest((source_root/f['path']).read_bytes()) == f['sha256'], 'External reference source changed')
    candidates = isolated_candidates(reference['entries'])
    selections = {ch: values[0] for ch, values in candidates.items()}
    selections.update(CURATED)
    source_chars = set(''.join(e['source_comment_label'] for e in reference['entries']))-{' '}
    check(set(selections) == source_chars, 'A source letter has not been recovered')
    condensed = outline_face(PAPYRUS, 0, 'papyrus-condensed', 'Papyrus Condensed')
    regular = outline_face(PAPYRUS, 1, 'papyrus', 'Papyrus Regular')
    rounded = outline_face(ROUNDED, 0, 'rounded', 'Rounded comparison (Comic Sans MS)')
    glyphs = {}
    by_row = {e['row']: e for e in reference['entries']}
    for ch in CHARACTERS:
        if ch == ' ':
            glyphs[ch] = bitmap_record(Image.new('L', (1, 1)), 0, {'origin': 'spacing'}, 6)
        elif ch in selections:
            row, left, right = selections[ch]
            source = Image.open(ROOT/by_row[row]['png']).convert('L')
            glyphs[ch] = bitmap_record(source.crop((left, 0, right, 24)), -19, {
                'origin': 'shiren_crop', 'source_row': row,
                'source_png': by_row[row]['png'], 'crop': [left, 0, right, 24],
                'source_png_sha256': by_row[row]['png_sha256'],
                'selection': 'reviewed_boundary' if ch in CURATED else 'isolated_word_character',
                'source_candidates': candidates.get(ch, []),
            })
        else:
            source = condensed['glyphs'][ch]
            # The source bitmap strokes are heavier than small-size Papyrus.
            # A one-pixel rightward weight plus binary threshold makes a draft
            # supplement legible beside them; provenance retains the adjustment.
            im = Image.new('L', (max(1, source['width']+1), max(1, source['height'])))
            for y, line in enumerate(source['rows']):
                for x, value in enumerate(line):
                    if int(value) >= 1:
                        im.putpixel((x, y), 255); im.putpixel((x+1, y), 255)
            glyphs[ch] = bitmap_record(im, source['top'], {
                'origin': 'papyrus_supplement',
                'transformation': 'one-pixel horizontal weight; binary alpha threshold 85',
                'review_status': 'draft supplement; absent from Shiren source names',
            })
    recovered = {'id': 'shiren', 'name': 'Shiren recovered + marked supplements',
                 'cap_height': 17, 'glyphs': glyphs,
                 'source': {'reference_manifest_sha256': digest((OUTPUT/'references/shiren-source.json').read_bytes()),
                            'supplement_font': condensed['source']},
                 'scope': 'Exact cropped Shiren source pixels with new spacing; absent characters use explicitly marked Papyrus Condensed raster supplements. Typeface identity is not established. Audition draft.'}
    report = {'schema': 1, 'source_rom': None, 'output_rom': None,
              'harness_sha256': digest(Path(__file__).read_bytes()),
              'alphabet': CHARACTERS, 'recovered_characters': ''.join(sorted(selections)),
              'supplement_characters': ''.join(ch for ch in CHARACTERS if ch not in selections and ch != ' '),
              'faces': [recovered, regular, condensed, rounded]}
    save_json(DEST, report)
    # Proof sheet retains a shared baseline and identifies every supplement.
    chars = string.ascii_uppercase+string.ascii_lowercase+string.digits+"'-.,:!?()/&+"
    sheet = Image.new('RGB', (1120, 70+((len(chars)+9)//10)*106), '#20232a')
    draw = ImageDraw.Draw(sheet); font = label_font(13)
    draw.text((16, 12), 'Recovered Shiren alphabet | white: source crop | amber: Papyrus supplement', font=font, fill='white')
    draw.text((16, 34), '3x view; shared baseline; supplements and new spacing remain audition drafts', font=font, fill='#b7c1cf')
    for i, ch in enumerate(chars):
        g = glyphs[ch]; x, y = (i%10)*112+16, 70+i//10*106
        colour = (255, 255, 255) if g['origin'] == 'shiren_crop' else (242, 184, 98)
        for yy, line in enumerate(g['rows']):
            for xx, v in enumerate(line):
                if v != '0':
                    draw.rectangle((x+xx*3, y+48+(g['top']+yy)*3, x+xx*3+2, y+48+(g['top']+yy)*3+2),
                                   fill=tuple(c*int(v)//3 for c in colour))
        draw.text((x, y+82), ch+'  '+('source' if g['origin'] == 'shiren_crop' else 'draft'), font=font, fill=colour)
    sheet.save(OUTPUT/'audition/alphabet-review.png')
    print(f'Recovered {len(selections)} source characters; {len(report["supplement_characters"])} marked supplements; four audition faces.')


if __name__ == '__main__':
    export()
