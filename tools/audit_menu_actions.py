"""Read-only menu width audit of the current published ROM.

Run from the project root: .venv/bin/python -m tools.audit_menu_actions
Uses disposable emulator sessions and existing fixtures; does not build a ROM,
change translations, or install a publication gate. Output: build/menu-action-audit/.
Some tests invoke bounded native readers directly, not natural gameplay routes.
"""
import json,struct
from pathlib import Path
import mgba.log
from tools.verify_expansion import Session
from tools import verify_dungeon_interface as ui, verify_ally_services as ally
from tools.build_first_label import ORIGINAL_ROM,digest
from tools.prose_review import effective_catalog,REVIEW
from tools.font_metrics import extract_fonts,measure_line
from tools.build_arena_services import MENU_TABLES as ARENA
from tools.build_ally_services import MENU_TABLES as SERVICES
from tools.build_encounter_ui import MENUS
from tools.translation_pipeline import FontZero
r=Path('build/torneko-3-english.gba').read_bytes();out=Path('build/menu-action-audit');font=FontZero(ORIGINAL_ROM.read_bytes());glyphs=extract_fonts(r)[0];cases=[]
mgba.log.silence()
def capture(s,t,name):
 rows=[]
 for d in t.payloads:
  gs=[g for g in t.positions if g['draw_serial']==d['serial']]
  if not gs:continue
  right=max(g['x']+g['advance'] for g in gs)
  ink=0
  for g in gs:
   bitmap,_=font.descriptors[g['code']];raw=font.original[bitmap-0x08000000:bitmap-0x08000000+72]
   occupied=[x for y in range(12) for x in range(12) if (raw[y*6+x//2]>>(4*(x%2)))&15]
   if occupied:ink=max(ink,g['x']+max(occupied)+1)
  rows.append(dict(raw_hex=d['raw_hex'],text=bytes.fromhex(d['raw_hex']).split(b'\0')[0].decode('ascii',errors='backslashreplace'),x=min(g['x'] for g in gs),right=right,ink_right=ink,width=gs[0]['window_width'],remaining=gs[0]['window_width']-max(right,ink)))
 case=dict(id=name,rows=rows,errors=t.errors);cases.append(case)
 (out/(name+'.json')).write_text(json.dumps(dict(case,payloads=t.payloads,glyphs=t.positions),indent=2))
 s.frames(2);s.capture(name)
 print(name,min((x['remaining'] for x in rows),default=999),flush=True)
with Session(r,out) as s:
 state=ally.STATE.read_bytes()
 for base,count in list(ARENA)+list(SERVICES)+list(MENUS)+[(0x87231C,3)]:
  assert s.core.load_raw_state(state)
  t=ui.InterfaceTrace(s.core)
  try:
   ui.native_step(s,t,0x0807B294,[0x08000000+base,0,0,0],stop=0x0807B3B6)
   capture(s,t,f'table-{base:08x}')
  finally:t.close()
 for group in range(12):
  for mode in (0,1):
   assert s.core.load_raw_state(state);ally.set_values(s.core,font,'stress' if mode else 'normal');t=ui.InterfaceTrace(s.core)
   try:
    ui.native_step(s,t,0x08096654,[0x020090C0,0x08C3DB78+group*56,56]);ui.native_step(s,t,0x0807191C,[mode]);capture(s,t,f'ally-{group:02d}-{mode}')
   finally:t.close()
 for fn,name in [(0x080755C0,'warehouse'),(0x0806FC78,'container')]:
  for item in (1,64,133,190,247,273,304):
   assert s.core.load_raw_state(ui.STATE.read_bytes());ui.install_item(s.core,0x0200A480,item);base=s.core.memory.u32[0x08075760];s.core.memory.u32[0x02009110]=base+10*12
   args=[0,1,0x0200A480,0,16] if name=='warehouse' else [0,1,0x0200A480,0,0,base+9*12,0]
   t=ui.InterfaceTrace(s.core)
   try:ui.native_step(s,t,fn,args);capture(s,t,f'{name}-{item}')
   finally:t.close()
# Execute the real shared trading popup draw block, supplying its caller label.
with Session(r,out) as s:
 for label,word in [('medal-exchange',0x63A3C),('casino-trade',0x77AD8)]:
  assert s.core.load_raw_state(state);t=ui.InterfaceTrace(s.core)
  try:
   s.core.memory.u32[0x03007000+0x6E8]=s.core.memory.u32[0x08000000+word]
   ui.native_step(s,t,0x08076AA2,[],stop=0x08076ADC,overrides={0x08076AA2:{'sp':0x03007000}})
   capture(s,t,label)
  finally:t.close()
# Wider system menus and the actual settings callback.
with Session(r,out) as s:
 for name,fn,args,stop in [('extra-menu',0x0800398C,[],0x08000000),('party-menu',0x08003A40,[6],0x08003ADC),('orders',0x08072A78,[0,0],0x08072B86)]:
  assert s.core.load_raw_state(state);t=ui.InterfaceTrace(s.core)
  try:
   ui.native_step(s,t,fn,args,stop=stop,overrides={0x08072AD2:{'r0':99},0x08072AEE:{'r0':99}} if name=='orders' else None);capture(s,t,name)
  finally:t.close()
 assert s.core.load_raw_state(ui.STATE.read_bytes())
 for key in ('B','RIGHT','DOWN','A'):s.press(key,80)
 from mgba._pylib import ffi
 settings=bytes(ffi.buffer(s.core.save_raw_state()))
 for row,arena in [(i,0) for i in range(35)]+[(0,26),(22,26)]:
  assert s.core.load_raw_state(settings);s.core.memory.u8[0x02004FF0]=arena;s.core.memory.u16[0x020091B0]=0;t=ui.InterfaceTrace(s.core)
  try:
   ui.native_step(s,t,0x0808BBD8,[0]);ui.native_step(s,t,0x0808C758,[0,0,0,152,24]);ui.native_step(s,t,0x080786AC,[0x08C3FBA0+row*20,row,0]);ui.native_step(s,t,0x0808BBF8,[0]);capture(s,t,f'settings-{row:02d}-{arena}')
  finally:t.close()
 entries={e['id']:e for e in effective_catalog('dungeon-interface')['entries']}
 for row in range(41):
  ui.action_case(s,ui.STATE.read_bytes(),row,True,font,entries,out)
  result=json.loads((out/f'action-{row:02d}.json').read_text())
  cases.append(dict(id=f'action-{row:02d}',checks=result['checks']))
  print(f'action-{row:02d} passed',flush=True)
# Check the narrow secondary reader with the longest action and transfer label.
with Session(r,out) as s:
 for name,word,index in [('warehouse-take-out',0x75760,11),('warehouse-withdraw',0x7392C,0)]:
  assert s.core.load_raw_state(ui.STATE.read_bytes());ui.install_item(s.core,0x0200A480,247)
  s.core.memory.u32[0x02009110]=s.core.memory.u32[0x08000000+word]+index*12
  t=ui.InterfaceTrace(s.core)
  try:
   ui.native_step(s,t,0x080755C0,[0,1,0x0200A480,0,16]);capture(s,t,name)
  finally:t.close()
# Inventory all explicitly typed menu/action/choice families, keeping control
# templates distinct from plain labels. These widths alone do not prove fit.
labels=[]
for catalog in json.loads(REVIEW.read_text())['catalogs']:
 for e in effective_catalog(catalog)['entries']:
  family=e.get('family','');text=e.get('display') or e.get('english','')
  if family not in ('action','command','choice','menu','extra_menu','party_menu','order','setting') and not (family in ('label','override') and catalog in ('ally-services','merchants','arena-services','dungeon-interface')) and not (catalog=='catalog' and e['id'].split('.')[0] in ('title','choice','mode','settings')):continue
  measured=None
  plain=text.lstrip('*')
  if all(32<=ord(c)<127 for c in plain) and not any(c in plain for c in '{}$%`'):
   measured=measure_line(glyphs,plain)
  labels.append(dict(catalog=catalog,id=e['id'],family=family,japanese=e['japanese'],review_text=text,metrics=measured,pointer_owners=e.get('pointer_owners',e.get('pointer_offsets',[]))))
(out/'label-inventory.json').write_text(json.dumps(dict(rom_sha256=digest(r),scope='Reviewed catalog labels, not a promise of current inserted wording; native cases resolve current pointers. Casino Exchange is superseded by Trade.',entries=labels),ensure_ascii=False,indent=2))
(out/'native-summary.json').write_text(json.dumps(dict(rom_sha256=digest(r),harness_sha256=digest(Path(__file__).read_bytes()),fixture_hashes={str(p):digest(p.read_bytes()) for p in [ally.STATE,ui.STATE]},cases=cases),indent=2))
