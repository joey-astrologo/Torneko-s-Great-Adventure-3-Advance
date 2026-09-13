"""Check the offline credits controls and export reviewable PNGs with Chrome."""
import base64
import json
from pathlib import Path

from PIL import Image

from tools.build_credits_audition import OUT
from tools.build_first_label import ROOT, ORIGINAL_ROM, digest
from tools.extract_arrival_cards import save_json
from tools.translation_pipeline import check, load_json
from tools import verify_arrival_audition as browser


def verify():
    build=load_json(OUT/'build.json');html=OUT/'index.html'
    check(build['html_sha256']==digest(html.read_bytes()),'Credits HTML changed after build')
    for name,sha in build['source_files'].items():check(digest((ROOT/name).read_bytes())==sha,'Stale credits source: '+name)
    # Reuse the isolated-process browser runner, directing only this process's
    # output/logs to credits. The existing arrival files/tool are not modified.
    browser.OUT=OUT
    dom=OUT/'browser-verification.html'
    browser.chrome(['--virtual-time-budget=15000','--dump-dom',html.as_uri()+'?verify=1'],dom)
    parser=browser.ResultParser();parser.feed(dom.read_text());check(bool(parser.result),'Credits browser checks did not finish')
    report=json.loads(parser.result);check(report['status']=='passed',report.get('error','Credits browser check failed'))
    pngs=report.pop('pngs');exports=[]
    for name,url in pngs.items():
        check(url.startswith('data:image/png;base64,'),'Unexpected credits export')
        path=OUT/name;path.write_bytes(base64.b64decode(url.split(',',1)[1]))
        with Image.open(path) as im:exports.append({'png':str(path.relative_to(ROOT)),'size':list(im.size),'sha256':digest(path.read_bytes())})
    save_json(OUT/'default-settings.json',report.pop('settings'))
    report.update(source_sha256=build['source_sha256'],output_rom=None,html_sha256=build['html_sha256'],
                  font_asset_sha256=build['font_asset_sha256'],harness_sha256=digest(Path(__file__).read_bytes()),
                  png_exports=exports,scope='Browser controls, layout bounds/collisions, source text retention, presets, settings and PNG exports. Offline artwork, no ROM insertion.')
    check(digest(ORIGINAL_ROM.read_bytes())==build['source_sha256'],'Original ROM changed')
    save_json(OUT/'verification.json',report)
    (OUT/'studio-preview.png').unlink(missing_ok=True)
    browser.chrome(['--virtual-time-budget=5000','--window-size=1500,1200','--screenshot='+str(OUT/'studio-preview.png'),html.as_uri()],OUT/'screenshot-log.txt')
    print(f"Passed {len(report['checks'])} browser checks; exported credits sheet, comparisons and native PNG.")


if __name__=='__main__':verify()
