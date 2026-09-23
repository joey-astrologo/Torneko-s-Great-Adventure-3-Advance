"""Verify the dungeon save selector and its compact native three-line page."""
from pathlib import Path
import struct
import mgba.log
from tools import build_dungeon_save_prompt as b, verify_church_services as church
from tools import verify_ally_services as service, verify_dungeon_interface as ui
from tools.translation_pipeline import FontZero, check, load_json
from tools.verify_expansion import Session
from tools.prose_review import save

FIXTURES=(church.STATE,)


def run(data=None,output=None):
    mgba.log.silence();data=b.ROM.read_bytes() if data is None else data
    output=b.OUTPUT/'verification' if output is None else Path(output)
    baseline=b.BASELINE.read_bytes();plan=load_json(b.PLAN)
    source=struct.unpack_from('<I',data,b.POINTER)[0]
    check(data[source-0x08000000:source-0x08000000+len(b.PAYLOAD)]==b.PAYLOAD,'Save prompt payload differs')
    check(data[:b.POINTER]==baseline[:b.POINTER] and data[b.POINTER+4:plan['start']]==baseline[b.POINTER+4:plan['start']] and data[plan['end_exclusive']:]==baseline[plan['end_exclusive']:],'Unowned bytes changed')
    font=FontZero(b.ORIGINAL_ROM.read_bytes())
    with Session(data,output) as s:
        check(s.core.load_raw_state(church.STATE.read_bytes()),'Save prompt fixture restore')
        t=ui.InterfaceTrace(s.core)
        try:
            r=ui.native_step(s,t,0x0807ABF8,[0,0x08000000+church.b.TABLE+3*church.b.STRIDE,0],stop=0x0807AC14)
            check(r['return_r0']==source,'Dungeon voice selector differs')
        finally:t.close()
        result=service.pages(s,source,'dungeon-save-prompt',font,b.TEXT)
        check(len(result['pages'])==1,'Save prompt still spans multiple pages')
        gs=result['pages'][0]['glyphs'];lines=b.TEXT.split('\n');index=0;ys=[]
        for line in lines:
            group=gs[index:index+len(line)];index+=len(line)
            check(len({g['y'] for g in group})==1,'Save prompt line wrapped')
            ys.append(group[0]['y'])
        check(ys==[ys[0],ys[0]+12,ys[0]+24],'Save prompt has a blank row')
    report=dict(rom_sha256=b.digest(data),source=hex(source),rows=ys,rendering=result,
        scope='Actual church type-3 save selector and native paged renderer; no save transaction')
    save(output/'report.json',report);print('Dungeon save prompt: one page, three consecutive rows',flush=True);return report

if __name__=='__main__':run()
