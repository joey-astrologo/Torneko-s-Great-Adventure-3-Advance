"""Accept the complete rendering correction ledger and export comparison sheets."""
from pathlib import Path
from PIL import Image,ImageDraw
from tools import build_rendering_fixes as b
from tools.translation_pipeline import check,load_json
from tools.build_first_label import ROOT,ORIGINAL_ROM,digest


def main():
    root=b.OUTPUT/'verification';plan=load_json(b.OUTPUT/'allocation-plan.json')
    before=b.BASELINE.read_bytes();after=b.ROM.read_bytes()
    report=load_json(b.OUTPUT/'english-build.json');checks=load_json(root/'initial-checks.json')
    check(digest(after)==report['rom_sha256']==checks['rom_sha256'],'Runtime evidence belongs to another build')
    expected=bytearray(before)
    for row in plan['allocations']:
        raw=(ROOT/row['file']).read_bytes();check(digest(raw)==row['sha256'],'Prepared asset changed')
        expected[row['offset']:row['offset']+len(raw)]=raw
    for row in plan['patches']:
        raw=bytes.fromhex(row['after']);expected[row['offset']:row['offset']+len(raw)]=raw
    check(bytes(expected)==after,'Unexpected ROM changes beyond the owned fixes')
    prior=load_json(b.BASELINE.parent/'english-build.json')['ledger'];ledger=report['ledger']
    check(ledger['allocations'][:-len(plan['allocations'])]==prior['allocations'],'Earlier allocations changed')
    superseded={p['supersedes']['id']:p for p in plan['patches'] if p['supersedes']}
    for p in prior['patches']:
        if p['id'] in superseded:
            replacement=next(q for q in ledger['patches'] if q['id']==superseded[p['id']]['id'])
            check(replacement['supersedes']==p,'Superseded owner history lost')
        else:check(p in ledger['patches'],'Unrelated patch owner changed')
    check(ledger['memory_reservations']==prior['memory_reservations'],'Permanent RAM ownership changed')
    rows=[('Name entry','keyboard/erase.png'),('Empty-name hint','keyboard/cancel.png'),
          ('Records menu','records/corrected.png'),('Dungeon status','status/corrected.png'),
          ('Message history: new entries','live-history/history-redrawn.png')]
    sheet=Image.new('RGB',(480,len(rows)*182),(24,24,28));draw=ImageDraw.Draw(sheet)
    for i,(label,file) in enumerate(rows):
        for j,variant in enumerate(('baseline','english')):
            draw.text((240*j+4,182*i+3),('Before: ' if not j else 'After: ')+label,fill='white')
            sheet.paste(Image.open(root/variant/file).convert('RGB'),(240*j,182*i+22))
    sheet.save(root/'before-after.png')
    sheet.resize((960,len(rows)*364),Image.Resampling.NEAREST).save(root/'before-after-2x.png')
    town=Image.new('RGB',(720,182*3),(24,24,28));draw=ImageDraw.Draw(town)
    for i,row in enumerate(p for p in plan['town_names'] if p['full']!=p['display']):
        x=i%3*240;y=i//3*182
        draw.text((x+3,y+3),row['display'],fill='white')
        town.paste(Image.open(root/'english/locations'/f'town-{row["index"]:02d}.png').convert('RGB'),(x,y+22))
    town.save(root/'town-displays.png')
    files=['initial-checks.json','locations.json','baseline/formatter.json','english/formatter.json','before-after.png','town-displays.png']
    acceptance=dict(status='passed',source_rom=str(ORIGINAL_ROM.relative_to(ROOT)),source_sha256=digest(ORIGINAL_ROM.read_bytes()),
        output_rom=str(b.ROM.relative_to(ROOT)),rom_sha256=digest(after),baseline_sha256=digest(before),
        new_allocations=len(plan['allocations']),new_bytes_with_alignment=plan['end_exclusive']-plan['start'],
        checked_patch_ranges=len(plan['patches']),superseded_patches=len(superseded),prior_allocations_preserved=True,
        whole_image_matches_owned_changes=True,permanent_ram_and_save_layout_unchanged=True,validation=checks,
        artifacts={str((root/f).relative_to(ROOT)):digest((root/f).read_bytes()) for f in files},
        harness_sha256=digest((ROOT/'tools/verify_rendering_fixes.py').read_bytes()),
        scope='Native menu navigation from supplied states, cold keyboard input, 94 controlled location cases, and paired formatter/queue/history fixtures. XP examples are generated with controlled slots; natural combat awards are not claimed. Existing saved history retains its old line breaks.')
    b.save(b.OUTPUT/'acceptance.json',acceptance)
    print('Accepted rendering fixes:',acceptance['rom_sha256'],flush=True)


if __name__=='__main__':main()
