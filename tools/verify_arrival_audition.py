"""Exercise the offline audition in Chrome and save its review PNG exports."""
import base64
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time

from PIL import Image

from tools.build_first_label import ROOT, digest
from tools.build_arrival_audition import OUT
from tools.extract_arrival_cards import save_json
from tools.translation_pipeline import check, load_json

CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'


class ResultParser(HTMLParser):
    def __init__(self):
        super().__init__(); self.active = False; self.result = ''

    def handle_starttag(self, tag, attrs):
        if tag == 'pre' and ('id', 'verification-result') in attrs:
            self.active = True

    def handle_endtag(self, tag):
        if tag == 'pre':
            self.active = False

    def handle_data(self, data):
        if self.active:
            self.result += data


def chrome(args, stdout):
    with tempfile.TemporaryDirectory(prefix='arrival-browser-') as profile:
        command = [CHROME, '--headless', '--disable-gpu', '--no-first-run',
                   '--no-default-browser-check', '--disable-background-networking',
                   '--disable-component-update', '--disable-sync', '--hide-scrollbars',
                   '--user-data-dir='+profile, *args]
        with stdout.open('wb') as out, (OUT/'browser.log').open('ab') as log:
            process = subprocess.Popen(command, stdout=out, stderr=log, start_new_session=True)
            deadline = time.monotonic()+45
            while process.poll() is None and time.monotonic() < deadline:
                # Some macOS Chrome helpers linger after completing the output.
                # Wait for a complete DOM/PNG, then close only this process group.
                complete = stdout.stat().st_size > 0 and stdout.read_bytes().rstrip().endswith(b'</html>')
                for arg in args:
                    if arg.startswith('--screenshot='):
                        target = Path(arg.split('=', 1)[1])
                        if target.exists():
                            try:
                                with Image.open(target) as im:
                                    im.verify()
                                complete = True
                            except (OSError, SyntaxError):
                                pass
                if complete:
                    break
                time.sleep(.25)
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
                process.wait(timeout=10)
        check(stdout.stat().st_size > 0 or any(a.startswith('--screenshot=') for a in args),
              'Chrome produced no output; review browser.log')


def verify():
    build = load_json(OUT/'build.json'); html = OUT/'index.html'
    check(build['html_sha256'] == digest(html.read_bytes()), 'Audition page changed since build')
    dom = OUT/'browser-verification.html'
    chrome(['--virtual-time-budget=15000', '--dump-dom', html.as_uri()+'?verify=1'], dom)
    parser = ResultParser(); parser.feed(dom.read_text())
    check(bool(parser.result), 'Browser verification did not finish')
    report = json.loads(parser.result)
    check(report['status'] == 'passed', report.get('error', 'Browser verification failed'))
    exports = report.pop('pngs')
    outputs = []
    for name, url in exports.items():
        check(url.startswith('data:image/png;base64,'), 'Unexpected export format')
        path = OUT/name; path.write_bytes(base64.b64decode(url.split(',', 1)[1]))
        with Image.open(path) as im:
            outputs.append({'png': str(path.relative_to(ROOT)), 'size': list(im.size),
                            'sha256': digest(path.read_bytes())})
    save_json(OUT/'default-settings.json', report.pop('settings'))
    report.update(source_sha256=build['source_sha256'], output_rom=None,
                  html_sha256=build['html_sha256'], font_asset_sha256=build['font_asset_sha256'],
                  harness_sha256=digest(Path(__file__).read_bytes()), png_exports=outputs,
                  scope='Browser artwork, fit, preset/floor combinations, settings validation and exports. No GBA insertion/runtime proof or font approval.')
    save_json(OUT/'verification.json', report)
    # Native-sized pixels remain inspectable alongside the enlarged comparison.
    (OUT/'studio-preview.png').unlink(missing_ok=True)
    chrome(['--virtual-time-budget=5000', '--window-size=1440,1300',
            '--screenshot='+str(OUT/'studio-preview.png'), html.as_uri()], OUT/'screenshot-log.txt')
    print(f"Passed {len(report['checks'])} browser checks; three review PNGs and default settings exported.")


if __name__ == '__main__':
    verify()
