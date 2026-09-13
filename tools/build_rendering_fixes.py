"""Apply the four screenshot-reported rendering corrections cumulatively."""
import argparse
import json
from pathlib import Path
import struct
import subprocess
import tempfile

from tools import build_arrival_credits as previous
from tools.build_first_label import ORIGINAL_ROM, ROOT, digest
from tools.translation_pipeline import FontZero, atomic_write, check, load_json
from tools.rom_build import AppendAllocator, RomBuild

OUTPUT = ROOT / 'build/rendering-fixes'
BASELINE = previous.ROM
ROM = OUTPUT / 'torneko3-rendering-fixes-english.gba'
ASM = ROOT / 'tools/rendering_fixes.asm'
OWNER = 'rendering-fixes'
MESSAGE_IDS = ('gameplay.001b4e23', 'gameplay.001b4e38',
               'gameplay.001b4e7b', 'gameplay.001b4e91')
TOWN_DISPLAYS = {
    'Seabed mountain rest stop': 'Seabed Mt. rest stop',
    'Great Baleina castle town': 'Great Baleina town',
    "Madame Gracos's bazaar": "Mme. Gracos's bazaar",
    'Mountain Foothills shrine': 'Foothills shrine',
    'Ruins rest stop - South': 'Ruins rest - South',
    'Ruins rest stop - North': 'Ruins rest - North',
    'Northern Plateau shrine': 'N. Plateau shrine',
}


def save(path, value):
    atomic_write(path, (json.dumps(value, ensure_ascii=False, indent=2)+'\n').encode())


def prepare():
    original = ORIGINAL_ROM.read_bytes(); baseline = BASELINE.read_bytes()
    prior = load_json(BASELINE.parent/'english-build.json')
    check(digest(baseline) == prior['rom_sha256'], 'Baseline changed')
    allocator = AppendAllocator(0x1000000+prior['ledger']['appended_used_with_padding'])
    def allocate(name, raw):
        ident = OWNER+'.'+name; at = allocator.allocate(ident, raw, 4)
        path = OUTPUT/'packed'/f'{name}.bin'; atomic_write(path, raw)
        allocator.allocations[-1].update(owner=OWNER, file=str(path.relative_to(ROOT)))
        return at
    descriptor_at = struct.unpack_from('<I', baseline, 0x76234)[0]-0x8000000
    descriptor = bytearray(baseline[descriptor_at:descriptor_at+64])
    check(struct.unpack_from('<3H', descriptor, 16) == (13,3,15), 'Town window changed')
    struct.pack_into('<3H', descriptor, 16, 14,3,14)
    new_descriptor = allocate('town-window', descriptor)
    font = FontZero(original)
    widths = bytes(max(font.glyph(chr(c))[1:]) if 32<=c<=126 else 0 for c in range(128))
    width_at = allocate('font-zero-widths', widths)
    town_names=[]; pairs=bytearray()
    from tools.build_enemies import measure
    for entry in load_json(ROOT/'translations/early-journey.json')['entries']:
        if entry['group'] != 'place': continue
        full=entry['english']; display=TOWN_DISPLAYS.get(full,full)
        check(measure(display,font)<=112,'Town location still too wide: '+display)
        word=int(entry['place_owners'][0]['pointer_offset'],0)
        pointer=struct.unpack_from('<I',baseline,word)[0]
        off=pointer-0x8000000
        check(baseline[off:baseline.index(b'\0',off)].decode()==full,'Town identity differs')
        row=dict(id=entry['id'],index=entry['place_owners'][0]['index'],source_pointer=pointer,
                 japanese=entry['japanese'],full=full,display=display,width=measure(display,font))
        if display != full:
            at=allocate('town-'+str(row['index']),display.encode()+b'\0')
            pairs.extend(struct.pack('<II',pointer,at+0x8000000)); row['display_pointer']=at+0x8000000
        town_names.append(row)
    pairs.extend(bytes(8)); town_at=allocate('town-display-pointers',pairs)
    sources = []
    for ident in MESSAGE_IDS:
        patches = [p for p in prior['ledger']['patches'] if p['id'].startswith(ident+'.')]
        targets = {struct.unpack('<I', bytes.fromhex(p['after']))[0] for p in patches}
        check(len(targets) == 1, 'Message pointers disagree: '+ident)
        address = targets.pop(); off = address-0x8000000
        raw = baseline[off:baseline.index(b'\0',off)+1]
        last_break=raw.rfind(b'\n')
        line_address=(address+raw.rfind(b'\n',0,last_break)+1) if last_break>=0 else 0
        sources.append(dict(id=ident,address=address,line_address=line_address,raw_hex=raw.hex(),pointer_patches=patches))
    code_at = (allocator.cursor+3)&~3
    with tempfile.TemporaryDirectory(prefix='torneko-rendering-asm-') as directory:
        command = [str(ROOT/'.tools/bin/armips'), str(ASM), '-equ','CODE_ADDRESS',hex(code_at+0x8000000),
                   '-equ','WIDTH_TABLE',hex(width_at+0x8000000),'-equ','TOWN_NAMES',hex(town_at+0x8000000),
                   '-sym2','symbols.txt']
        for i,row in enumerate(sources):
            command += ['-equ',f'MESSAGE_{i}',hex(row['address']),'-equ',f'LINE_{i}',hex(row['line_address'])]
        result = subprocess.run(command,cwd=directory,capture_output=True,text=True)
        check(result.returncode == 0,result.stdout+result.stderr)
        code = (Path(directory)/'rendering-fixes.bin').read_bytes()
        symbols={fields[1]:int(fields[0],16) for line in (Path(directory)/'symbols.txt').read_text().splitlines()
                 if len(fields:=line.split())==2 and fields[1] in ('FormatHook','JoinNumberLine','TownLocation')}
    check(allocate('formatter',code) == code_at,'Code alignment differs')
    # mov ip,r3; ldr r3,[pc,#4]; bx r3; nop; aligned destination literal.
    hook = bytes.fromhex('9c46014b1847c046')+struct.pack('<I',code_at+0x8000001)
    changes = [
        ('keyboard-clear',0x7BD94,bytes.fromhex('aa2165222623'),bytes.fromhex('9c2165223423'),None,
         'Clear the complete moved B-hint region: x156, y101, width52'),
        ('keyboard-update-x',0x7BDA0,bytes.fromhex('aa20'),bytes.fromhex('9c20'),None,
         'Use x156 for hint redraws after every inserted/erased character'),
        ('keyboard-hint-x',0x7BE4A,bytes.fromhex('aa20'),bytes.fromhex('9c20'),None,
         'Place B: Erase/Cancel at x156 inside the 208px keyboard, after the 134px main hint'),
        ('records-width',0x85FCC,bytes.fromhex('1a20'),bytes.fromhex('1420'),'result.categories.width',
         'Use a 160px category selector; all labels including cursor fit, and the right border stays on screen'),
        ('dungeon-location',0xCA28C4,struct.pack('<3H',13,3,15),struct.pack('<3H',14,3,14),None,
         'Move the location content right 8px and narrow it to 112px, accounting for both window borders'),
        ('town-location',0x76234,struct.pack('<I',descriptor_at+0x8000000),struct.pack('<I',new_descriptor+0x8000000),'gameplay.window.00076234',
         'Apply the same location geometry to the separate town descriptor'),
        ('town-display',0x76254,bytes.fromhex('eaf7daf8021c01a8'),bytes.fromhex('004b1847')+struct.pack('<I',symbols['TownLocation']|1),None,
         'Use seven measured status-only town display forms; retain full names in shared place/Zoom tables'),
        ('numeric-line',0x7D8CC,bytes.fromhex('f0b5474680b48fb0041c0d1c'),hook,None,
         'Preserve the native formatter; conditionally join the final numeric line of four XP/level templates after substitution'),
    ]
    patches=[]
    for name,offset,before,after,supersedes,reason in changes:
        check(baseline[offset:offset+len(before)] == before, 'Unexpected baseline bytes: '+name)
        old = next((p for p in prior['ledger']['patches'] if p['id']==supersedes),None) if supersedes else None
        if old:check(bytes.fromhex(old['after']) == before and old['offset']==offset,'Wrong prior owner')
        else:check(original[offset:offset+len(before)] == before,'Unowned original precondition differs')
        patches.append(dict(id=OWNER+'.'+name,offset=offset,before=before.hex(),after=after.hex(),supersedes=old,reason=reason))
    plan = dict(source_rom=str(ORIGINAL_ROM.relative_to(ROOT)),source_sha256=digest(original),
        baseline_rom=str(BASELINE.relative_to(ROOT)),baseline_sha256=digest(baseline),output_rom=None,
        builder_sha256=digest(Path(__file__).read_bytes()),asm_sha256=digest(ASM.read_bytes()),
        start=allocator.start,end_exclusive=allocator.cursor,allocations=allocator.allocations,patches=patches,
        messages=sources,town_names=town_names,symbols=symbols,original_town_descriptor=[0xC3EE90,0xC3EED0],previous_town_descriptor=[descriptor_at,descriptor_at+64],
        new_permanent_ram=[],save_layout_changes=[],formatter_extra_stack_bytes=112,
        joining_rule='ASCII only; replace final LF with space only when the joined line fits 208 pixels and 59 bytes. Otherwise retain original wrapping.')
    save(OUTPUT/'allocation-plan.json',plan)
    print(f"Prepared [{plan['start']:08X},{plan['end_exclusive']:08X}); document before building.",flush=True)


def build_rom(original, *, build=None):
    plan=load_json(OUTPUT/'allocation-plan.json')
    check(plan['source_sha256']==digest(original),'Wrong Japanese source')
    check(plan['builder_sha256']==digest(Path(__file__).read_bytes()) and plan['asm_sha256']==digest(ASM.read_bytes()),'Regenerate changed plan')
    check(f"`[{plan['start']:08X},{plan['end_exclusive']:08X})`" in (ROOT/'docs/MEMORY_MAP.md').read_text(),'Document allocation span first')
    b=RomBuild(original) if build is None else build
    baseline,prior=previous.build_rom(original,build=b)
    check(baseline==BASELINE.read_bytes() and digest(baseline)==plan['baseline_sha256'],'Earlier cumulative build changed')
    check(b.allocator.cursor==plan['start'],'Allocation plan no longer follows previous components')
    for row in plan['allocations']:
        raw=(ROOT/row['file']).read_bytes();check(digest(raw)==row['sha256'],'Prepared resource changed')
        check(b.allocate(row['id'],raw,OWNER)==row['offset'],'Allocation differs')
    for p in plan['patches']:
        if p['supersedes']:
            old=p['supersedes']
            b.supersede_patch(p['id'],old['id'],old['owner'],bytes.fromhex(p['before']),bytes.fromhex(p['after']),OWNER,p['reason'])
        else:b.patch(p['id'],p['offset'],bytes.fromhex(p['before']),bytes.fromhex(p['after']),OWNER,p['reason'])
    data,ledger=b.finish()
    return data,dict(source_rom=str(ORIGINAL_ROM.relative_to(ROOT)),source_sha256=digest(original),
        output_rom=str(ROM.relative_to(ROOT)),rom_sha256=digest(data),previous_rom_sha256=digest(baseline),
        allocation_plan_sha256=digest((OUTPUT/'allocation-plan.json').read_bytes()),ledger=ledger)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--prepare',action='store_true')
    if p.parse_args().prepare:prepare()
    else:
        data,report=build_rom(ORIGINAL_ROM.read_bytes());atomic_write(ROM,data);save(OUTPUT/'english-build.json',report)
        print('Built',report['rom_sha256'])
