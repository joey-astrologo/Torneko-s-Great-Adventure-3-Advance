"""Exercise title audition controls and export native-size review images."""
import base64
import json
from pathlib import Path
from PIL import Image
from tools.build_first_label import ROOT, ORIGINAL_ROM, digest
from tools.capture_title_audition import OUT, BASELINE
from tools.extract_arrival_cards import save_json
from tools.translation_pipeline import check, load_json
from tools import verify_arrival_audition as browser


def verify():
    build = load_json(OUT/'build.json')
    html = OUT/'index.html'
    check(digest(html.read_bytes()) == build['html_sha256'], 'Rebuild changed title HTML')
    for path, sha in build['source_files'].items():
        check(digest((ROOT/path).read_bytes()) == sha, 'Rebuild changed title source: '+path)
    browser.OUT = OUT
    dom = OUT/'browser-verification.html'
    browser.chrome(['--virtual-time-budget=20000', '--dump-dom', html.as_uri()+'?verify=1'], dom)
    parser = browser.ResultParser()
    parser.feed(dom.read_text())
    check(bool(parser.result), 'Title browser checks did not finish; inspect browser.log')
    report = json.loads(parser.result)
    check(report['status'] == 'passed', report.get('error', 'Title checks failed'))
    exports = []
    for name, url in report.pop('pngs').items():
        check(Path(name).name == name and name.endswith('.png'), 'Unexpected export name')
        check(url.startswith('data:image/png;base64,'), 'Unexpected export format')
        path = OUT/name
        path.write_bytes(base64.b64decode(url.split(',', 1)[1]))
        with Image.open(path) as im:
            exports.append({'path': str(path.relative_to(ROOT)), 'size': list(im.size),
                            'sha256': digest(path.read_bytes())})
    save_json(OUT/'default-settings.json', report.pop('settings'))
    check(digest(ORIGINAL_ROM.read_bytes()) == build['source_sha256'], 'Original changed')
    check(digest(BASELINE.read_bytes()) == build['baseline_sha256'], 'Pre-title baseline changed')
    refs = load_json(OUT/'reference/provenance.json')
    check(all(digest((ROOT/p).read_bytes()) == h for p, h in refs['user_save_hashes'].items()),
          'A user save changed')
    report.update(source_rom=build['source_rom'], source_sha256=build['source_sha256'],
                  baseline_rom=build['baseline_rom'], baseline_sha256=build['baseline_sha256'],
                  output_rom=None, html_sha256=build['html_sha256'],
                  candidate_sha256=build['candidate_sha256'], renderer_sha256=build['renderer_sha256'],
                  harness_sha256=digest(Path(__file__).read_bytes()), png_exports=exports,
                  roms_and_user_saves_unchanged=True,
                  scope='Offline browser comparison, native-size reduction, colour controls, PNG/settings '
                        'roundtrip, imported art and invalid-input rejection. No English title insertion proof.')
    save_json(OUT/'verification.json', report)
    screenshot = OUT/'studio-preview.png'
    screenshot.unlink(missing_ok=True)
    browser.chrome(['--virtual-time-budget=5000', '--window-size=1440,1320',
                    '--screenshot='+str(screenshot), html.as_uri()], OUT/'screenshot-log.txt')
    print(f"Passed {len(report['checks'])} title audition checks; exported comparison and native/4x PNGs.")


if __name__ == '__main__':
    verify()
