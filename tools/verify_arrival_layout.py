"""Check relocated arrival map cells, exact artwork and a natural transition."""
from pathlib import Path
import struct
import mgba.log
from PIL import Image, ImageChops, ImageDraw

from tools import build_arrival_layout as b
from tools import verify_arrival_credits as old
from tools.build_first_label import ROOT, ORIGINAL_ROM, digest
from tools.prose_review import save
from tools.translation_pipeline import check, load_json
from tools.verify_expansion import Session
from tools.verify_first_label import battery_snapshot
from tools.extract_arrival_cards import paint_cell, label_font

OUT=b.OUTPUT/'verification'


def expected_image(plan,title,number):
    arena=title['selectors'][0]%32==26
    title_image=old.quantized(ROOT/title['file'])
    shift=48 if arena else 32
    check(title_image.getbbox()[3]+shift<=160,'Title falls off screen')
    image=Image.new('RGB',(240,160),'black');image.paste(title_image,(0,shift))
    if not arena:
        check(title_image.getbbox()[3]+shift<=80,'Floor map would erase title pixels')
        floor=plan['floors'][number+(256 if title['selectors'][0]%32 in (25,27) else 0)]
        image.paste(old.quantized(ROOT/floor['file']),(0,80))
    return image


def controlled(data,plan):
    cases=list(dict.fromkeys([(s,n,0) for s in range(64) for n in (0,1,9,10,99,100,255)]+
                            [(s,n,0) for s in (0,25,27) for n in range(256)]+
                            [(s,1,1) for s in range(64)]))
    titles={s:t for t in plan['titles'] for s in t['selectors']}
    colours=[tuple(c) for c in plan['palette_rgb']];records=[];previews=[]
    with Session(data,OUT/'controlled') as session:
        c=session.core;state=old.STATE.read_bytes()
        for selector,number,suppress in cases:
            check(c.load_raw_state(state),'Fixture restore failed')
            dungeon=selector%32;shift=6 if dungeon==26 else 4
            c.memory.u8[0x02004FF0]=dungeon;c.memory.u8[0x02004FF1]=number
            c.memory.u32[0x02004F8C]=selector//32;c.memory.u8[0x02000034]=suppress
            before_map=bytes(c.memory[old.MAP:old.MAP+0x840])
            before_tiles=bytes(c.memory[old.TILES:old.TILES+0x2800])
            guards=[(a,bytes(c.memory[a:z])) for a,z in
                ((old.MAP-16,old.MAP),(old.MAP+0x840,old.MAP+0x850),
                 (old.TILES-16,old.TILES),(old.TILES+0x2800,old.TILES+0x2810),
                 (0x02002FD4,0x02004F80))]
            save_before=battery_snapshot(c);title=titles[selector]
            puzzle=dungeon in (25,27);visible=not suppress and not(puzzle and number==100)
            floor=plan['floors'][number+(256 if puzzle else 0)]
            title_bytes=data[title['offset']+0x800:title['end_exclusive']]
            expected_tiles=title_bytes+before_tiles[len(title_bytes):0x1400]
            expected_tiles+=data[floor['tiles_offset']:floor['tiles_offset']+floor['tile_count']*32].ljust(0x1400,b'\0')
            expected_map=bytearray(before_map)
            for y in range(1,33):expected_map[y*64+2:y*64+64]=bytes(62)
            if visible:
                for y in range(9):
                    at=title['offset']+y*64+2
                    expected_map[(y+1+shift)*64+2:(y+1+shift)*64+60]=data[at:at+58]
                if dungeon!=26:
                    for y in range(4):
                        at=floor['map_offset']+y*60
                        expected_map[(y+10)*64:(y+10)*64+60]=data[at:at+60]
            steps=old.invoke(c)
            check(bytes(c.memory[old.MAP:old.MAP+0x840])==expected_map,f'Arrival map differs: {selector}/{number}/{suppress}')
            check(bytes(c.memory[old.TILES:old.TILES+0x2800])==expected_tiles,'Artwork tile buffers changed')
            check(bytes(c.memory[0x03003620:0x03003660])==struct.pack('<16I',*plan['palette_words']),'Palette changed')
            check(c.memory.u8[0x02005E48]==1,'Native upload not queued')
            check(all(bytes(c.memory[a:a+len(raw)])==raw for a,raw in guards),'Adjacent map/tile/profile bytes changed')
            check(battery_snapshot(c)==save_before,'Arrival modified save')
            if number==1 and not suppress and selector==title['selectors'][0]:
                image=Image.new('RGB',(240,160),'black')
                for y in range(1+shift,10+shift):
                    for x in range(1,30):
                        paint_cell(image,(x*8,y*8),expected_tiles,c.memory.u16[old.MAP+64*y+2*x],colours)
                if dungeon!=26:
                    for y in range(10,14):
                        for x in range(30):
                            paint_cell(image,(x*8,y*8),expected_tiles,c.memory.u16[old.MAP+64*y+2*x],colours)
                check(ImageChops.difference(image,expected_image(plan,title,number)).getbbox() is None,'Original artwork differs at new position')
                image.save(session.output/(title['id']+'.png'));previews.append((title['text'],image))
            records.append(dict(selector=selector,floor=number,suppression_flag=suppress,
                card_visible=visible,floor_visible=visible and dungeon!=26,steps=steps))
            if len(records)%100==0:print('Arrival layout',len(records),'/',len(cases),flush=True)
    sheet=Image.new('RGB',(4*480,((len(previews)+3)//4)*350),'#192225');draw=ImageDraw.Draw(sheet)
    for i,(name,image) in enumerate(previews):
        x=i%4*480;y=i//4*350;sheet.paste(image.resize((480,320),Image.Resampling.NEAREST),(x,y))
        draw.text((x+6,y+325),name,font=label_font(15),fill='white')
    sheet.save(OUT/'all-cards.png')
    return {'count':len(records),'cases':records,'previews':len(previews),
            'entire_maps_tiles_palette_match':True,'abi_guards_profile_and_save_intact':True}


def verify():
    mgba.log.silence();OUT.mkdir(parents=True,exist_ok=True)
    data=b.ROM.read_bytes();before=b.BASELINE.read_bytes();plan=load_json(b.PLAN)
    report=load_json(b.OUTPUT/'english-build.json');prior=load_json(b.BASELINE.parent/'english-build.json')
    check(digest(data)==report['rom_sha256'] and digest(before)==plan['previous_sha256'],'Wrong ROMs')
    check(digest(b.PLAN.read_bytes())==report['allocation_plan_sha256'],'Plan differs from build')
    expected=bytearray(before);at=plan['allocations'][0]['offset'];code=bytes.fromhex(plan['code_hex'])
    expected[at:at+len(code)]=code;expected[0x5298:0x52A0]=bytes.fromhex(plan['replacement_hex'])
    check(bytes(expected)==data,'Unaccounted ROM change')
    check(report['ledger']['allocations']==prior['ledger']['allocations']+plan['allocations'],'Prior owners changed')
    for allocation in prior['ledger']['allocations']:
        at=allocation['offset'];end=at+allocation['bytes']
        check(data[at:end]==before[at:end],'Earlier allocated bytes changed')
    for p,q in zip(prior['ledger']['patches'],report['ledger']['patches'],strict=True):
        check((q.get('supersedes')==p) if p['id']=='arrival-credits.map' else q==p,'Unexpected patch supersession')
    check(report['ledger']['memory_reservations']==prior['ledger']['memory_reservations'],'RAM reservations changed')
    original=ORIGINAL_ROM.read_bytes()
    check(all(data[a:z]==original[a:z] for a,z in old.SOURCE_RANGES),'Original artwork changed')
    user_files={str(p.relative_to(ROOT)):digest(p.read_bytes()) for p in (ROOT/'saves').rglob('*') if p.is_file()}
    assets=load_json(b.art.OUT/'allocation-plan.json')
    native=controlled(data,assets)
    old.expected_image=expected_image;old.VERIFY=OUT;old.BASELINE=b.BASELINE
    natural=old.natural(data,assets)
    check(all(digest((ROOT/p).read_bytes())==sha for p,sha in user_files.items()),'User save/state changed')
    # Native screenshots for both placements, taken at the same route frame.
    old_image=Image.open(b.art.OUT/'verification/cave/native-second-floor.png').convert('RGB')
    new_image=Image.open(OUT/'cave/native-second-floor.png').convert('RGB')
    sheet=Image.new('RGB',(960,354),'#192225');draw=ImageDraw.Draw(sheet)
    for i,(label,image) in enumerate((('Previous spacing',old_image),('Compact centred spacing',new_image))):
        draw.text((i*480+8,8),label,font=label_font(16),fill='white')
        sheet.paste(image.resize((480,320),Image.Resampling.NEAREST),(i*480,30))
    sheet.save(OUT/'before-after.png')
    result={'status':'passed','source_rom':str(ORIGINAL_ROM.relative_to(ROOT)),'source_sha256':digest(original),
        'output_rom':str(b.ROM.relative_to(ROOT)),'rom_sha256':digest(data),'baseline_sha256':digest(before),
        'plan_sha256':digest(b.PLAN.read_bytes()),'harness_sha256':digest(Path(__file__).read_bytes()),
        'controlled':native,'natural':natural,'whole_rom_matches_owned_changes':True,
        'prior_allocations_and_unrelated_patches_unchanged':True,'user_files_unchanged':True,
        'user_file_sha256':user_files,'new_bytes_with_alignment':plan['end_exclusive']-plan['start'],
        'scope':'Complete discovered arrival selectors, defensive floor values and suppression; one natural cave arrival/fade/movement route. Unknown town-card families are not covered.'}
    save(b.OUTPUT/'acceptance.json',result)
    print('PASSED',native['count'],'constructor cases and natural arrival/fade/movement',flush=True)


if __name__=='__main__':verify()
