"""Freeze the approved browser raster output; no ROM writes."""
import base64
import json

from PIL import Image

from tools.build_first_label import ROOT, digest
from tools.extract_arrival_cards import save_json
from tools.translation_pipeline import check, load_json
from tools import verify_arrival_audition as browser

OUT = ROOT/'build/completion/arrival-credits'
APPROVAL = ROOT/'assets/arrival-cards/approved.json'
AUDITION = ROOT/'build/arrival-cards/audition'

EXPORT = r'''
<script>
async function exportApproved() {
  if (!window.Audition) {setTimeout(exportApproved,50);return;}
  let report;
  try {
    const A=window.Audition, approved=__APPROVAL__, s=approved.settings;
    if(A.DATA.font_asset_sha256!==approved.font_asset_sha256 ||
       A.DATA.renderer_sha256!==approved.renderer_sha256) throw Error('Approved renderer changed');
    const titles=approved.cards.map(c=>{
      const source=A.DATA.cards.find(x=>x.id===c.id),r=A.render(source,{...s,presentation:'title'},c.text);
      if(!r.fit||r.supplements.length||JSON.stringify(source.selectors)!==JSON.stringify(c.selectors)) throw Error('Title differs: '+c.id);
      return {id:c.id,selectors:c.selectors,text:c.text,bounds:r.bounds,png:r.canvas.toDataURL()};
    });
    const floors=[];
    for(const kind of ['F','puzzle'])for(let number=0;number<256;number++) {
      const card=A.DATA.cards.find(c=>c.sample_suffix===kind), r=A.render(card,{...s,floor:number});
      const b=r.floorBounds;
      if(!r.fit||r.supplements.length||b[0]<0||b[2]>240||b[1]<96||b[3]>128) throw Error('Floor exceeds reserved rows');
      const crop=document.createElement('canvas');crop.width=240;crop.height=32;
      crop.getContext('2d').drawImage(r.canvas,0,96,240,32,0,0,240,32);
      floors.push({kind,number,bounds:b,png:crop.toDataURL()});
    }
    report={status:'passed',titles,floors};
  } catch(e) {report={status:'failed',error:String(e)};}
  document.body.replaceChildren();const p=document.createElement('pre');p.id='verification-result';
  p.textContent=JSON.stringify(report);document.body.appendChild(p);
}
exportApproved();
</script>
'''


def export():
    approved = load_json(APPROVAL)
    build = load_json(AUDITION/'build.json')
    html = (AUDITION/'index.html').read_bytes()
    check(digest(html) == build['html_sha256'] == approved['audition_html_sha256'], 'Approved HTML changed')
    OUT.mkdir(parents=True, exist_ok=True)
    script = EXPORT.replace('__APPROVAL__', json.dumps(approved, ensure_ascii=True))
    page = OUT/'export.html'
    page.write_text(html.decode().replace('</html>', script+'</html>'))
    browser.OUT = OUT
    dom = OUT/'export-dom.html'
    browser.chrome(['--virtual-time-budget=20000', '--dump-dom', page.as_uri()+'?preset=credits'], dom)
    parser = browser.ResultParser(); parser.feed(dom.read_text())
    check(bool(parser.result), 'Raster export did not finish')
    report = json.loads(parser.result)
    check(report['status'] == 'passed', report.get('error', 'Raster export failed'))
    colours = set()
    for group in ('titles', 'floors'):
        for row in report[group]:
            ident = row['id'] if group == 'titles' else f"{row['kind']}-{row['number']:03d}"
            path = OUT/'raster'/f'{ident}.png'; path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(base64.b64decode(row.pop('png').split(',', 1)[1]))
            im = Image.open(path).convert('RGB')
            check(im.size == ((240,160) if group == 'titles' else (240,32)), 'Raster dimensions changed')
            colours.update(tuple(c >> 3 for c in rgb) for rgb in im.get_flattened_data())
            row.update(file=str(path.relative_to(ROOT)), sha256=digest(path.read_bytes()))
    report.update(source_sha256=approved['source_rom_sha256'], output_rom=None,
                  approval_sha256=digest(APPROVAL.read_bytes()), exporter_sha256=digest(__file_bytes()),
                  rgb555_colours=sorted(colours), colour_count=len(colours))
    save_json(OUT/'rasters.json', report)
    print('Exported', len(report['titles']), 'titles and', len(report['floors']), 'floor lines;', len(colours), 'RGB555 colours')


def __file_bytes():
    from pathlib import Path
    return Path(__file__).read_bytes()


if __name__ == '__main__':
    export()
