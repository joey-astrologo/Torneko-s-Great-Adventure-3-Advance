"""Confirm extraction candidates inside native background graphics assets."""
import json
import struct
from pathlib import Path
import mgba.log
from tools import audit_scene_resources as scene
from tools import verify_dungeon_interface as ui, verify_tutorial_gameplay as queue
from tools import verify_system_labels as system, verify_core_gameplay as old
from tools.build_first_label import ORIGINAL_ROM, ROOT, digest
from tools.translation_pipeline import check, load_json, atomic_write
from tools.verify_expansion import Session

OUTPUT = ROOT / 'build/completion/scene-graphics-audit'
BASELINE = scene.BASELINE
FORMAT = 0x02008CB8
LOCAL = 0x03007800


def save(path, data):
    atomic_write(path, (json.dumps(data, ensure_ascii=False, indent=2) + '\n').encode())


def audit():
    mgba.log.silence(); original = ORIGINAL_ROM.read_bytes(); data = BASELINE.read_bytes()
    ancestry_path = ROOT / 'build/completion/remaining-ui/research/scene-graphics-candidates.json'
    ancestry = load_json(ancestry_path)['assets']
    master = {e['id']: e for e in load_json(ROOT / 'translations/master.json')['entries']}
    selected = {}
    for asset in ancestry:
        for ident in asset['matches']: selected.setdefault(ident, asset)
    cases = []
    with Session(data, OUTPUT / 'native') as s:
        c = s.core
        for ident, asset in selected.items():
            check(c.load_raw_state(system.STATE.read_bytes()), 'Scene graphics state restore')
            expected_cache = original[scene.CACHE[0]:scene.CACHE[1]]
            check(bytes(c.memory[scene.CACHE[2]:scene.CACHE[2]+len(expected_cache)]) == expected_cache, 'Scene graphics cache differs')
            e = master[ident]; start = int(e['offset'], 0); end = start + len(bytes.fromhex(e['source_hex']))
            descriptor = queue.select_slice(c, 0x0806C5F0, 0x0806C60A, {'r0': asset['scene']}, 0)
            desc = int(descriptor['source'], 0)
            check(desc == int(asset['descriptor'], 0) + 0x08000000, 'Native graphics scene selection differs')
            t = ui.InterfaceTrace(c)
            try:
                system.guard(c, old.DEST, 36)
                ui.native_step(s, t, 0x08067022, [], stop=0x08067030,
                               overrides={0x08067022: {'r0': desc, 'r7': old.DEST}})
                system.guards(c, old.DEST, 36)
                check(bytes(c.memory[old.DEST:old.DEST+36]) == original[desc-0x08000000:desc-0x08000000+36], 'Native scene descriptor copy differs')
                header = c.memory.u32[old.DEST]
                check(header == int(asset['header'], 0) + 0x08000000, 'Native graphics header differs')
                h = struct.unpack_from('<6H', original, header - 0x08000000)
                check(h[0] in (0x0202, 0x0303), 'Unexpected scene graphic format')
                c.memory.u32[LOCAL] = header
                adjacent = bytes(c.memory[FORMAT-4:FORMAT+8])
                ui.native_step(s, t, 0x080671CC, [], stop=0x08067230,
                               overrides={0x080671CC: {'sp': LOCAL, 'r6': FORMAT}})
                count = c.memory.u16[FORMAT+2]
                check((c.memory.u16[FORMAT], count) == ((1, 4) if h[0] == 0x0202 else (2, 9)), 'Native metatile dimensions differ')
                check(bytes(c.memory[FORMAT-4:FORMAT]) == adjacent[:4] and bytes(c.memory[FORMAT+4:FORMAT+8]) == adjacent[8:], 'Native format selector changed adjacent fields')
                if asset['kind'] == 'tiles':
                    ptr = queue.select_slice(c, 0x08067162, 0x08067166, {'sp': LOCAL}, 2)
                    unit, total = 32, h[1] - 1
                else:
                    ptr = queue.select_slice(c, 0x0806716A, 0x0806716C, {'r3': header}, 3)
                    unit, total = count * 2, h[3] - 1
                base = int(ptr['source'], 0) - 0x08000000
                check(base == int(asset['start'], 0) and base + unit * total == int(asset['end_exclusive'], 0), 'Native graphics asset span differs')
                check(base <= start < end <= base + unit * total, 'Candidate leaves its graphics asset')
                copies = []
                for index in range((start-base)//unit, (end-base+unit-1)//unit):
                    at = base + index * unit
                    system.guard(c, old.DEST, unit)
                    if asset['kind'] == 'tiles':
                        begin, stop = 0x08067196, 0x080671A6
                    else:
                        begin, stop = 0x0806724E, 0x0806726E
                    # Enter before native counter initialization; injecting
                    # registers at a loop head would reset every iteration.
                    ui.native_step(s, t, begin, [0, old.DEST, at + 0x08000000, FORMAT], stop=stop)
                    system.guards(c, old.DEST, unit)
                    copied = bytes(c.memory[old.DEST:old.DEST+unit])
                    check(copied == original[at:at+unit] == data[at:at+unit], 'Native graphics unit copy differs')
                    copies.append({'start': hex(at), 'end_exclusive': hex(at+unit), 'raw_hex': copied.hex(), 'guards_intact': True})
                check(not t.positions and not t.formats, 'Graphics proof unexpectedly used the text renderer')
                cases.append({'master_id': ident, 'offset': e['offset'], 'end_exclusive': hex(end), 'source_hex': e['source_hex'],
                              'japanese': e['japanese'], 'asset': asset, 'native_format': hex(h[0]), 'copies': copies,
                              'descriptor_and_format_checks': True, 'guards_intact': True})
            finally:
                t.close()
        check(len(cases) == 71, 'Scene graphics candidate coverage changed')
        result = {'status': 'scene_graphics_candidates_native_verified', 'source_sha256': digest(original),
                  'verified_rom': str(BASELINE.relative_to(ROOT)), 'verified_rom_sha256': digest(data),
                  'harness_sha256': digest(Path(__file__).read_bytes()), 'fixture_sha256': digest(system.STATE.read_bytes()),
                  'candidate_manifest_sha256': digest(ancestry_path.read_bytes()),
                  'helper_sha256': {Path(m.__file__).name: digest(Path(m.__file__).read_bytes()) for m in (ui, queue, system, old)},
                  'entries': cases, 'scope': 'Native scene/header copy, format selection, asset-pointer selection and exact guarded copies of all tiles/metatiles covering each candidate. These bytes are 4-bpp image data or metatile indexes, not prose. Original assets unchanged. No complete graphics discovery, natural scene reachability or insertion space is claimed.'}
        save(OUTPUT / 'native-verification.json', result)
    print(len(cases), 'background graphic/index candidates verified', flush=True)


if __name__ == '__main__':
    audit()
