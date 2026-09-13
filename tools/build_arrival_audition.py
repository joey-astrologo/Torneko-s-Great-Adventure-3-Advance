"""Package a portable, offline arrival-card lettering audition."""
import base64
import io
import json
from pathlib import Path

from PIL import Image

from tools.build_first_label import ORIGINAL_ROM, ROOT, digest
from tools.extract_arrival_cards import OUTPUT, collect, name_image, floor_glyph, save_json
from tools.translation_pipeline import check, load_json

OUT = OUTPUT/'audition'
FONT = ROOT/'assets/fonts/arrival-candidates.json'
CREDITS_FONT = ROOT/'assets/fonts/credits-arrival-candidate.json'
COMPATIBLE = ROOT/'tools/arrival_audition/compatible-revisions.json'
TEMPLATE = ROOT/'tools/arrival_audition/index.html'
SCRIPT = ROOT/'tools/arrival_audition/studio.js'


def data_url(image, transparent=False):
    if transparent:
        image = image.convert('RGBA')
        image.putdata([(r, g, b, 255 if r or g or b else 0)
                       for r, g, b, _ in image.get_flattened_data()])
    buffer = io.BytesIO(); image.save(buffer, format='PNG')
    return 'data:image/png;base64,'+base64.b64encode(buffer.getvalue()).decode()


def build():
    original = ORIGINAL_ROM.read_bytes(); manifest = collect(original)
    fonts = load_json(FONT)
    check(fonts['harness_sha256'] == digest((ROOT/'tools/reconstruct_arrival_font.py').read_bytes()),
          'Regenerate the font after changing its reconstruction')
    credits = load_json(CREDITS_FONT)
    check(credits['source_sha256'] == digest(original) and credits['harness_sha256'] ==
          digest((ROOT/'tools/reconstruct_credits_arrival_font.py').read_bytes()), 'Regenerate the credits arrival font')
    fonts['faces'].append(credits['face'])
    font_hash = digest(json.dumps(fonts, sort_keys=True, separators=(',', ':')).encode())
    images = {e['id']: data_url(name_image(original, e), True) for e in manifest['entries']}
    images.update({'glyph'+str(i): data_url(floor_glyph(original, i), True) for i in range(12)})
    backgrounds = {
        'cave': OUTPUT/'research/stairs/transition-120.png',
        'village': OUTPUT/'verification/village/frame-0120.png',
    }
    sources = []
    for key, path in backgrounds.items():
        im = Image.open(path).convert('RGB')
        check(im.size == (240, 160), 'Expected native-size background capture')
        images[key] = data_url(im)
        sources.append({'id': key, 'png': str(path.relative_to(ROOT)), 'sha256': digest(path.read_bytes()),
                        'scope': 'Captured gameplay used as an audition backdrop, not a claim of native card placement.'})
    cards = []
    for e in manifest['entries']:
        dungeon = e['selectors'][0] % 32
        cards.append({k: e[k] for k in ('id','selectors','english_name_reference','japanese_name_reference')}
                     | {'sample_suffix': 'none' if dungeon == 26 else 'puzzle' if dungeon in (25,27) else 'F'})
    data = {'schema': 1, 'cards': cards, 'fonts': fonts, 'images': images,
            'source_sha256': manifest['source_sha256'], 'font_asset_sha256': font_hash,
            'compatible_revisions': load_json(COMPATIBLE), 'renderer_sha256': digest(SCRIPT.read_bytes())}
    encoded = json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c')
    html = TEMPLATE.read_text().replace('__AUDITION_DATA__', encoded).replace('__AUDITION_SCRIPT__', SCRIPT.read_text())
    OUT.mkdir(parents=True, exist_ok=True)
    output = OUT/'index.html'; output.write_text(html)
    save_json(OUT/'build.json', {
        'source_rom': manifest['source_rom'], 'source_sha256': manifest['source_sha256'], 'output_rom': None,
        'html': str(output.relative_to(ROOT)), 'html_sha256': digest(output.read_bytes()),
        'font_asset': str(FONT.relative_to(ROOT)), 'font_asset_sha256': font_hash,
        'font_sources': {str(p.relative_to(ROOT)): digest(p.read_bytes()) for p in (FONT, CREDITS_FONT)},
        'source_files': {str(p.relative_to(ROOT)): digest(p.read_bytes()) for p in (Path(__file__), TEMPLATE, SCRIPT, COMPATIBLE)},
        'backgrounds': sources, 'cards': len(cards), 'selectors': sum(len(c['selectors']) for c in cards),
        'scope': 'Offline artwork audition for location-title-only and arrival cards. Main Japanese logo retained. No ROM patch, new memory allocation, save edit or final font approval.',
    })
    print('Built standalone audition:', output.relative_to(ROOT))


if __name__ == '__main__':
    build()
