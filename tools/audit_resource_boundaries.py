"""Classify five apparent strings through native palette and animated tile readers."""
import json
import struct
from pathlib import Path
import mgba.log
from mgba._pylib import ffi, lib
from tools import audit_scene_resources as scene
from tools import verify_dungeon_interface as ui, verify_tutorial_gameplay as queue
from tools import verify_core_gameplay as old, verify_system_labels as system
from tools.build_first_label import ROOT, ORIGINAL_ROM, digest
from tools.translation_pipeline import check, load_json, atomic_write
from tools.verify_expansion import Session

OUT = ROOT/'build/completion/resource-boundaries'
DESC, ANIM, PALETTES, COLORS, FORMAT = 0x02008C90, 0x02008C70, 0x02008BF8, 0x030032A0, 0x02008CB8
LOCAL = 0x03007800
EXTRA = (0x08060620, 0x08089D0C, 0x08088F44)


class Trace(ui.InterfaceTrace):
    def __init__(self, core):
        self.calls, self.phase = [], ''
        super().__init__(core)

    def entered(self, debugger, reason, info):
        if info != ffi.NULL and reason == lib.DEBUGGER_ENTER_BREAKPOINT and info.address in EXTRA:
            self.calls.append({'phase': self.phase, 'pc': hex(int(info.address)),
                               'args': [int(self.cpu.gprs[i])&0xFFFFFFFF for i in range(4)]})
        super().entered(debugger, reason, info)


def setup(s, t, original, number):
    c = s.core
    check(c.load_raw_state(system.STATE.read_bytes()), 'Resource fixture restore failed')
    cache = original[scene.CACHE[0]:scene.CACHE[1]]
    check(bytes(c.memory[scene.CACHE[2]:scene.CACHE[2]+len(cache)]) == cache, 'Scene cache differs')
    descriptor = struct.unpack_from('<I', original, scene.CACHE[0]+number*4)[0]
    t.phase = f'scene-{number}-descriptor'
    ui.native_step(s, t, 0x08066FE4, [number, 0], stop=0x08067030)
    expected = original[descriptor-0x08000000:descriptor-0x08000000+36]
    check(bytes(c.memory[DESC:DESC+36]) == expected and c.memory.u16[0x02008C88] == number,
          'Native scene selection/copy differs')
    header = c.memory.u32[DESC]
    h = struct.unpack_from('<6H3I', original, header-0x08000000)
    return {'scene': number, 'descriptor': hex(descriptor), 'header': hex(header), 'header_fields': list(h)}


def upload(s, t, original, number, frame):
    c = s.core; ancestry = setup(s, t, original, number)
    header = int(ancestry['header'], 0); h = ancestry['header_fields']
    c.memory.u32[LOCAL] = header
    before = bytes(c.memory[ANIM-8:ANIM+32])
    ui.native_step(s, t, 0x08067588, [], stop=0x080675B6, overrides={0x08067588: {'sp': LOCAL}})
    table = c.memory.u32[ANIM+12]
    check(table == h[8] and c.memory.u32[ANIM+16] == 0x06008000+h[1]*32 and
          c.memory.u32[ANIM+20] == h[2]*32, 'Native animation initializer differs')
    check(bytes(c.memory[ANIM-8:ANIM]) == before[:8] and
          bytes(c.memory[ANIM+24:ANIM+32]) == before[32:], 'Animation initializer changed adjacent fields')
    selected = []
    for i in range(frame):
        queue.select_slice(c, 0x08067FDA, 0x08067FEE, {'r5': ANIM}, 0)
        value = c.memory.u32[ANIM+12]
        check(value == table+(i+1)*12, 'Native frame advance differs')
        selected.append(hex(value))
    record = c.memory.u32[ANIM+12]
    source, dest, size = c.memory.u32[record+4], c.memory.u32[ANIM+16], c.memory.u32[ANIM+20]
    boundary = bytes(c.memory[dest-8:dest])+bytes(c.memory[dest+size:dest+size+8])
    t.phase = f'scene-{number}-frame-{frame}-upload'
    ui.native_step(s, t, 0x08068118, [])
    raw = bytes(c.memory[dest:dest+size])
    check(raw == original[source-0x08000000:source-0x08000000+size], 'Native animated tile upload differs')
    check(boundary == bytes(c.memory[dest-8:dest])+bytes(c.memory[dest+size:dest+size+8]),
          'Native tile upload changed adjacent VRAM')
    call = [e for e in t.calls if e['phase'] == t.phase and e['pc'] == hex(0x08088F44)]
    check(len(call) == 1 and call[0]['args'][:3] == [dest, source, size] and c.memory.u8[ANIM+1] == 0,
          'Native upload source/length or pending flag differs')
    return {**ancestry, 'frame': frame, 'frame_record': hex(record), 'frame_advances': selected,
            'tile_source': hex(source), 'tile_end_exclusive': hex(source+size), 'tile_bytes': size,
            'destination': hex(dest), 'copied_sha256': digest(raw), 'adjacent_vram_unchanged': True,
            'upload': call[0]}


def audit():
    mgba.log.silence(); original = ORIGINAL_ROM.read_bytes(); data = scene.BASELINE.read_bytes()
    master = {int(e['offset'], 0): e for e in load_json(ROOT/'translations/master.json')['entries']}
    cases, entries = [], []
    def add(at, kind, case, reason):
        e = master[at]; raw = bytes.fromhex(e['source_hex'])
        check(data[at:at+len(raw)] == original[at:at+len(raw)] == raw, 'Candidate source changed')
        entries.append({'master_id': e['id'], 'offset': hex(at), 'end_exclusive': hex(at+len(raw)),
                        'source_hex': e['source_hex'], 'kind': kind, 'case': case, 'reason': reason})
    breaks = ui.BREAKS
    try:
        ui.BREAKS = breaks+EXTRA
        with Session(data, OUT/'native') as s:
            t = Trace(s.core); c = s.core
            try:
                first = upload(s, t, original, 0, 0)
                check(first['tile_source'] == '0x892c630' and first['tile_bytes'] == 2336,
                      'First scene tile boundary differs')
                h = first['header_fields']; header = int(first['header'], 0)
                c.memory.u32[LOCAL] = header
                ui.native_step(s, t, 0x080671CC, [], stop=0x08067230,
                               overrides={0x080671CC: {'sp': LOCAL, 'r6': FORMAT}})
                check(c.memory.u16[FORMAT] == 1 and c.memory.u16[FORMAT+2] == 4,
                      'Native metatile format differs')
                chosen = queue.select_slice(c, 0x0806716A, 0x0806716C, {'r3': header}, 3)
                check(int(chosen['source'], 0) == h[7] and h[7]+(h[3]-1)*8 == 0x0892C630,
                      'Metatile source/end differs')
                chunks = []
                for at in range(0x92C610, 0x92C630, 8):
                    system.guard(c, old.DEST, 8)
                    ui.native_step(s, t, 0x0806724E, [0, old.DEST, at+0x08000000, FORMAT], stop=0x0806726E)
                    system.guards(c, old.DEST, 8)
                    raw = bytes(c.memory[old.DEST:old.DEST+8])
                    check(raw == original[at:at+8], 'Native final metatile copy differs')
                    chunks.append({'start': hex(at), 'end_exclusive': hex(at+8), 'hex': raw.hex()})
                cases.append({'id': 'cross_asset_decode', 'animation': first, 'metatile_copies': chunks,
                              'metatile_guards_intact': True, 'apparent_terminator': 'First byte of independently uploaded tile asset at 0092C630.'})
                add(0x92C610, 'cross_asset_metatile_tile_decode', 'cross_asset_decode',
                    'The 32 apparent character bytes are four native metatiles; the apparent NUL is the next animated tile asset. This decode crosses a typed asset boundary.')

                animated = upload(s, t, original, 54, 62)
                check(animated['tile_source'] == '0x8aa6640' and animated['tile_bytes'] == 1536,
                      'Scene 54 frame 62 differs')
                cases.append({'id': 'animated_tile_frame', **animated})
                add(0xAA6678, 'animated_tile_pixels', 'animated_tile_frame',
                    'Candidate lies inside scene 54 animated frame 62, selected through native frame advances and copied exactly to VRAM as tile pixels.')

                ancestry = setup(s, t, original, 30)
                before = bytes(c.memory[PALETTES-8:ANIM+8])
                ui.native_step(s, t, 0x0806752C, [], stop=0x08067588)
                check(bytes(c.memory[PALETTES-8:PALETTES]) == before[:8] and
                      bytes(c.memory[ANIM:ANIM+8]) == before[-8:], 'Palette initializer changed adjacent fields')
                row = PALETTES+2*8
                check((c.memory.u16[row], c.memory.u16[row+2], c.memory.u32[row+4]) == (17, 4, 0x08A00A70),
                      'Native palette row differs')
                mode = c.memory.u8[FORMAT+4]
                for tick in range(28):
                    t.phase = f'palette-tick-{tick+1}'
                    ui.native_step(s, t, 0x08067F20, [], stop=0x08067FC4)
                source = 0xA00A70+6*60
                raw = original[source:source+60]; expected = bytearray(raw)
                if mode:
                    for i in range(15):expected[i*4+1] = expected[i*4+1]*3//4; expected[i*4+3] = 255
                actual = bytes(c.memory[COLORS+33*4:COLORS+48*4])
                check(actual == expected and c.memory.u32[row+4] == source+0x08000000+60,
                      'Native seventh palette frame differs')
                calls = [e for e in t.calls if e['pc'] == hex(0x08060620) and e['args'][1] == source+0x08000000]
                check(len(calls) == 1 and calls[0]['args'] == [33, source+0x08000000, 15, mode],
                      'Native palette source/count differs')
                writes = [e for e in t.calls if e['phase'] == calls[0]['phase'] and
                          e['pc'] == hex(0x08089D0C) and 33 <= e['args'][0] <= 47]
                check([e['args'][:2] for e in writes] == [[33+i, struct.unpack_from('<I', expected, i*4)[0]] for i in range(15)],
                      'Native color writes differ')
                cases.append({'id': 'animated_palette_values', **ancestry, 'timer_ticks': 28,
                    'palette_row': 2, 'frame': 6, 'source': hex(source), 'source_hex': raw.hex(),
                    'output_hex': actual.hex(), 'palette_mode': mode, 'native_calls': calls,
                    'native_color_writes': writes, 'initialization_adjacent_fields_unchanged': True})
                for at in (0xA00BF8, 0xA00BFC, 0xA00C00):
                    add(at, 'animated_palette_rgb_value', 'animated_palette_values',
                        'One four-byte RGB value in scene 30 palette-animation row 2, frame 6, copied by the native palette consumer. The zero byte is a color component, not a text terminator.')
                check(not t.errors and not t.positions and not t.formats, 'Resource audit unexpectedly rendered text')
            finally:
                t.close()
    finally:
        ui.BREAKS = breaks
    report = {'status': 'resource_boundaries_native_verified', 'source_sha256': digest(original),
        'verified_rom': str(scene.BASELINE.relative_to(ROOT)), 'verified_rom_sha256': digest(data),
        'harness_sha256': digest(Path(__file__).read_bytes()), 'fixture_sha256': digest(system.STATE.read_bytes()),
        'helper_sha256': {Path(m.__file__).name: digest(Path(m.__file__).read_bytes()) for m in (ui, queue, system)},
        'listing_sha256': {str(p.relative_to(ROOT)): digest(p.read_bytes()) for p in (
            ROOT/'build/completion/remaining-ui/research/scene-readers.txt',
            OUT/'research/animation-readers.txt', OUT/'research/animation-tick.txt', OUT/'research/animation-upload.txt')},
        'entries': entries, 'cases': cases,
        'scope': 'Five extraction candidates classified through bounded native descriptor initialization, metatile copies, animation frame selection/upload and palette timer/color writes. No ROM modifications, free space, artwork work or natural scene reachability claim. Tile frame advance bypasses timer pacing; palette ticks execute native countdowns.'}
    atomic_write(OUT/'native-verification.json', (json.dumps(report, ensure_ascii=False, indent=2)+'\n').encode())
    print(len(entries), 'resource-boundary candidates verified', flush=True)


if __name__ == '__main__':
    audit()
