"""Exercise native indexed graphics, original palette and arena result branches."""
import argparse
import struct
from pathlib import Path
import mgba.log
from mgba._pylib import ffi, lib
from tools import build_arena_graphics as b, verify_arena_final as arena
from tools import verify_dungeon_interface as ui, verify_system_labels as system
from tools.build_first_label import ORIGINAL_ROM, digest
from tools.translation_pipeline import check, load_json
from tools.verify_expansion import Session
from tools.verify_items import write_json

BASELINE = b.previous.OUTPUT / 'torneko3-arena-final-english.gba'
STATE = arena.STATE
WINDOW = 0x02034CD8
ui.BREAKS = (*ui.BREAKS, 0x0805D070, 0x0808C2D8)


class GraphicsTrace(ui.InterfaceTrace):
    def __init__(self, core):
        self.headings, self.blits = [], []
        super().__init__(core)

    def entered(self, debugger, reason, info):
        if info != ffi.NULL and reason == lib.DEBUGGER_ENTER_BREAKPOINT:
            c = self.core; args = [int(self.cpu.gprs[i]) & 0xFFFFFFFF for i in range(4)]
            if info.address == 0x0805D070:
                self.headings.append({'x': args[0], 'y': args[1], 'source': hex(args[2]),
                                      'indexes_hex': arena.old.cstring(c, args[2], 64).hex()})
            elif info.address == 0x0808C2D8:
                sp = int(self.cpu.gprs[13]) & 0xFFFFFFFF
                self.blits.append({'window': args[0], 'x': args[1], 'y': args[2], 'width': args[3],
                                   'height': c.memory.u32[sp], 'source': hex(c.memory.u32[sp + 4]),
                                   'palette': c.memory.u32[sp + 8]})
        super().entered(debugger, reason, info)


def setup(s):
    check(s.core.load_raw_state(STATE.read_bytes()), 'Arena graphics fixture restore')
    t = GraphicsTrace(s.core)
    try:
        ui.native_step(s, t, 0x0805CAFC, [], stop=0x0805CB38, overrides={0x0805CAFC: {'sp': arena.LOCAL}})
    finally:
        t.close()


def tile_buffer(c):
    at = c.memory.u32[WINDOW + 0x14]
    width, height = c.memory.u16[WINDOW + 4], c.memory.u16[WINDOW + 8]
    check(at == 0x02035E1C and width == 26 and height == 17 and
          c.memory.u32[WINDOW + 0x24] == width * height * 32, 'Arena graphics original static buffer differs')
    return at, width, height, bytes(c.memory[at:at + width * height * 32])


def check_graphics(c, before, headings, blits, data, catalog, variant, report):
    at, width, height, initial = before
    expected = bytearray(initial); selected = []; expected_blits = []
    atlas = c.memory.u32[0x0805D0B0]
    by_source = {0x08000000 + (int(e['offset'], 0) if variant == 'baseline' else report['arena_graphics']['relocated'][e['id']]['offset']): e for e in catalog['entries']}
    for h in headings:
        e = by_source[int(h['source'], 0)]; selected.append(e['id'])
        indexes = bytes.fromhex(h['indexes_hex'])
        check(len(indexes) == e['cells'] + 1 and indexes[-1] == 0, 'Arena heading index count differs')
        check(h['x'] % 8 == h['y'] % 8 == 0 and h['x'] + e['cells'] * 16 <= width * 8 and
              h['y'] + 16 <= c.memory.u16[WINDOW + 6] * 8, 'Arena graphic field leaves window')
        for i, code in enumerate(indexes[:-1]):
            source = atlas + (code - 1) * 128
            check(0 <= source - 0x08000000 < len(data) - 128, 'Arena graphic index outside cartridge')
            expected_blits.append({'window': 0, 'x': h['x'] + i * 16, 'y': h['y'], 'width': 16,
                                   'height': 16, 'source': hex(source), 'palette': 14})
            raw = data[source - 0x08000000:source - 0x08000000 + 128]
            for ty in range(2):
                for tx in range(2):
                    dest = ((h['y'] // 8 + ty) * width + h['x'] // 8 + i * 2 + tx) * 32
                    start = (ty * 2 + tx) * 32
                    expected[dest:dest + 32] = raw[start:start + 32]
                    tilemap = 0x02034DDC + (c.memory.u16[WINDOW + 2] + h['y'] // 8 + ty) * 64 + (c.memory.u16[WINDOW] + h['x'] // 8 + i * 2 + tx) * 2
                    check(c.memory.u16[tilemap] >> 12 == 14, 'Arena graphic native palette bank differs')
    check(blits == expected_blits, 'Arena native indexed blit sequence differs')
    check(bytes(c.memory[at:at + len(expected)]) == expected, 'Arena graphic buffer differs or unrelated tiles changed')
    return {'sources': selected, 'native_blits': len(blits), 'whole_buffer_exact': True,
            'buffer': hex(at), 'tile_dimensions': [width, height], 'palette_bank': 14}


def verify(variant):
    mgba.log.silence()
    rom = BASELINE if variant == 'baseline' else b.OUTPUT / f'torneko3-arena-graphics-{variant}.gba'
    data = rom.read_bytes(); catalog = load_json(b.OUTPUT / 'catalog.json')
    report = {} if variant == 'baseline' else load_json(b.OUTPUT / f'{variant}-build.json')
    cases, words = [], []
    with Session(data, b.OUTPUT / 'verification' / variant) as s:
        c = s.core
        for e in catalog['entries']:
            for p in e['pointer_owners']:
                at = int(p['offset'], 0); target = 0x08000000 + (int(e['offset'], 0) if variant == 'baseline' else report['arena_graphics']['relocated'][e['id']]['offset'])
                check(c.memory.u32[at + 0x08000000] == target, 'Arena graphic pointer differs')
                words.append({'word': hex(at), 'source': hex(target)})
        target = 0x08000000 + (b.ATLAS[0] if variant == 'baseline' else report['arena_graphics']['atlas_offset'])
        check(c.memory.u32[0x0805D0B0] == target, 'Arena atlas pointer differs')
        words.append({'word': '0x5d0b0', 'source': hex(target)})
        for kind in ('winners', 'empty', 'draw', 'defeat', 'victory'):
            setup(s); t = GraphicsTrace(c)
            fonts = bytes(c.memory[0x020398EC:0x020398F8])
            try:
                if kind in ('winners', 'empty'):
                    # Snapshot before only the native graphic heading call;
                    # the horizontal rule and text rows are separate writes.
                    before = tile_buffer(c)
                    ui.native_step(s, t, 0x0805CB38, [], stop=0x0805CB42, overrides={0x0805CB38: {'sp': arena.LOCAL}})
                    proof = check_graphics(c, before, t.headings, t.blits, data, catalog, variant, report)
                    ui.native_step(s, t, 0x0805CB42, [], stop=0x0805CB52, overrides={0x0805CB42: {'sp': arena.LOCAL}})
                    if kind == 'winners':
                        for row in range(8): arena.row(s, t, b'WWWWWWW', row, 9999, 7, row, 20)
                        ui.native_step(s, t, 0x0805CB80, [], stop=0x0805CB92, overrides={0x0805CB80: {'r7': 8, 'r4': 13, 'r9': 20, 'r5': 0}})
                    else:
                        ui.native_step(s, t, 0x0805CB58, [], stop=0x0805CB92, overrides={0x0805CB58: {'r0': 0}})
                    status = None
                else:
                    # Original initialization up to the first heading.
                    ui.native_step(s, t, 0x0805CEB8, [], stop=0x0805CED2)
                    before = tile_buffer(c)
                    ui.native_step(s, t, 0x0805CED2, [], stop=0x0805CEDC)
                    header = check_graphics(c, before, t.headings, t.blits, data, catalog, variant, report)
                    ui.native_step(s, t, 0x0805CEDC, [], stop=0x0805CEEC)
                    before = tile_buffer(c); nh, nb = len(t.headings), len(t.blits)
                    mode = ('draw', 'defeat', 'victory').index(kind)
                    c.memory.u32[arena.LOCAL + 0x1C] = mode
                    ui.native_step(s, t, 0x0805CEEC, [], stop=0x0805CF78, overrides={0x0805CEEC: {'sp': arena.LOCAL}})
                    body = check_graphics(c, before, t.headings[nh:], t.blits[nb:], data, catalog, variant, report)
                    status_at = c.memory.u32[0x0805CF2C]
                    status = c.memory.u8[status_at]
                    check(status == (2, 0, 1)[mode], 'Arena native outcome status changed')
                    proof = {'header': header, 'body': body}
                check(bytes(c.memory[0x020398EC:0x020398F8]) == fonts, 'Arena graphics changed font state')
                ui.native_step(s, t, 0x0808BBF8, [0]); ui.native_step(s, t, 0x0808BB14, [0])
                r = system.record(s, t, kind, 'english', kind=kind, graphics=proof, headings=t.headings, blits=t.blits,
                                  status=status, font_state_intact=True)
                cases.append(r)
            finally:
                t.close()
        result = {'variant': variant, 'rom_sha256': digest(data), 'source_sha256': digest(ORIGINAL_ROM.read_bytes()),
                  'catalog_sha256': digest((b.OUTPUT / 'catalog.json').read_bytes()), 'harness_sha256': digest(Path(__file__).read_bytes()),
                  'helper_sha256': {**system.helper_hashes(), 'verify_system_labels.py': digest(Path(system.__file__).read_bytes()), 'verify_arena_final.py': digest(Path(arena.__file__).read_bytes())},
                  'fixture_sha256': digest(STATE.read_bytes()), 'pointer_words': words, 'cases': cases,
                  'screens': [p for row in cases for p in row['screens']]}
        write_json(s.output / 'verification.json', result)
        print(variant, len(cases), 'arena graphics cases passed', flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('variant', choices=('english', 'japanese', 'baseline'))
    verify(p.parse_args().variant)
