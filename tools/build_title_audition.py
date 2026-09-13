"""Build a self-contained title-art comparison studio, without ROM insertion."""
import base64
from pathlib import Path
from PIL import Image
from tools.build_first_label import ROOT, ORIGINAL_ROM, digest
from tools.extract_arrival_cards import save_json
from tools.translation_pipeline import check, load_json
from tools.capture_title_audition import OUT, BASELINE

ASSET = ROOT/'assets/title-screen/stone-gold-v1.png'
PROMPT = ASSET.with_name('stone-gold-v1-prompt.txt')
TEMPLATE = ROOT/'tools/title_audition/index.html'
SCRIPT = ROOT/'tools/title_audition/studio.js'


def uri(path):
    return 'data:image/png;base64,' + base64.b64encode(path.read_bytes()).decode()


def build():
    import json
    provenance = load_json(OUT/'reference/provenance.json')
    check(provenance['source_sha256'] == digest(ORIGINAL_ROM.read_bytes()), 'Wrong Japanese original')
    check(provenance['baseline_sha256'] == digest(BASELINE.read_bytes()), 'Recapture pre-title baseline')
    original = OUT/'reference/japanese/title.png'
    check(digest(original.read_bytes()) == provenance['cases'][0]['png_sha256'], 'Reference image changed')
    with Image.open(ASSET) as im:
        size = list(im.size)
        check(size[0] * 2 == size[1] * 3, 'Artwork must have the screen aspect ratio')
    data = {
        'schema': 1, 'source_sha256': provenance['source_sha256'],
        'reference_sha256': digest(original.read_bytes()), 'renderer_sha256': digest(SCRIPT.read_bytes()),
        'original': uri(original), 'palette': load_json(OUT/'reference/palette.json'),
        'candidate': {'id': 'stone-gold-v1', 'name': 'Stone & gold — draft 01',
                      'sha256': digest(ASSET.read_bytes()), 'image': uri(ASSET), 'size': size},
        'wording': {'japanese': 'ドラゴンクエスト キャラクターズ / トルネコの大冒険3 / アドバンス / 不思議のダンジョン',
                    'english': "Dragon Quest Characters / Torneko’s Great Adventure 3 / Advance / Mystery Dungeon"},
    }
    encoded = json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c')
    html = TEMPLATE.read_text().replace('__DATA__', encoded).replace('__SCRIPT__', SCRIPT.read_text())
    (OUT/'index.html').write_text(html)
    save_json(OUT/'build.json', {
        'schema': 1, 'source_rom': provenance['source_rom'], 'source_sha256': provenance['source_sha256'],
        'baseline_rom': provenance['baseline_rom'], 'baseline_sha256': provenance['baseline_sha256'],
        'output_rom': None, 'html_sha256': digest((OUT/'index.html').read_bytes()),
        'reference_sha256': data['reference_sha256'], 'candidate_sha256': data['candidate']['sha256'],
        'renderer_sha256': data['renderer_sha256'], 'candidate_dimensions': size,
        'generation': {'mode': 'built-in image_gen', 'asset': str(ASSET.relative_to(ROOT)),
                       'prompt': str(PROMPT.relative_to(ROOT)), 'prompt_sha256': digest(PROMPT.read_bytes()),
                       'edit_reference': 'build/completion/boot-graphics/research/english/boot-0600.png',
                       'status': 'Unapproved artwork proposal; model redraws the illustrated title and ocean.'},
        'source_files': {str(p.relative_to(ROOT)): digest(p.read_bytes())
                         for p in (Path(__file__), TEMPLATE, SCRIPT)},
        'scope': 'Offline title artwork audition; native-size resampling, colour previews and original '
                 'start-prompt strip composition happen in browser canvas. No ROM patches or allocator reservations.'})
    print('Built title audition:', OUT/'index.html')


if __name__ == '__main__':
    build()
