"""Compare arrival exports with a native cave transition; record two town routes."""
from pathlib import Path

import mgba.log
from PIL import Image, ImageDraw

from tools.audit_scene_resources import BASELINE
from tools.build_first_label import ORIGINAL_ROM, ROOT, digest
from tools.extract_arrival_cards import (
    OUTPUT, POINTER_TABLE, PALETTE, FLOOR_TILES, collect, name_image,
    add_floor, save_json, label_font,
)
from tools.trace_text_systems import ReaderTrace
from tools.translation_pipeline import check, load_json
from tools.verify_expansion import Session

CAVE = ROOT / 'build/completion/cave-clear'


def transition(s, trace, keys, hold, released, folder):
    """Use only buttons; capture each tenth frame through the transition."""
    codes = [getattr(s.core, 'KEY_' + k) for k in keys]
    start = s.core.frame_counter
    images = []
    s.core.set_keys(*codes)
    for n in range(1, hold + released + 1):
        if n == hold + 1:
            s.core.clear_keys(*codes)
        trace.frames(1)
        if n % 10 == 0:
            im = s.screen.to_pil().convert('RGB')
            path = folder / f'frame-{n:04d}.png'
            im.save(path)
            images.append((n, im))
    sheet = Image.new('RGB', (6*240, ((len(images)+5)//6)*180), '#20232a')
    d = ImageDraw.Draw(sheet)
    for i, (n, im) in enumerate(images):
        x, y = i % 6 * 240, i // 6 * 180
        sheet.paste(im, (x, y))
        d.text((x+4, y+161), f'+{n} / frame {start+n}', fill='white', font=label_font(11))
    sheet.save(folder / 'transition-sheet.png')
    return {'start_frame': start, 'end_frame': s.core.frame_counter,
            'keys': keys, 'hold': hold, 'released': released,
            'capture_interval_frames': 10, 'capture_count': len(images)}


def verify():
    mgba.log.silence()
    original, data = ORIGINAL_ROM.read_bytes(), BASELINE.read_bytes()
    manifest = collect(original)
    ledger = load_json(OUTPUT / 'resource-ranges.json')
    for row in ledger['ranges']:
        start, end = int(row['start'], 0), int(row['end_exclusive'], 0)
        check(original[start:end] == data[start:end], 'English build changed original card source')
    replay = load_json(CAVE / 'replay.json')
    check(digest(data) == replay['rom_sha256'], 'Native route ROM changed')
    root = OUTPUT / 'verification'
    root.mkdir(parents=True, exist_ok=True)
    watch = [0x08000000+POINTER_TABLE+4*i for i in range(64)] + [0x08000000+PALETTE]
    fixture = CAVE / 'continued/stair-approach.state'
    with Session(data, root / 'cave') as s:
        check(s.core.load_raw_state(fixture.read_bytes()), 'Cannot restore native stairs fixture')
        check(s.core.frame_counter == 56313, 'Stair fixture frame changed')
        for row in replay['inputs'][102:109]:
            codes = [getattr(s.core, 'KEY_'+k) for k in row['keys']]
            s.core.set_keys(*codes); s.frames(row['hold']); s.core.clear_keys(*codes)
            s.frames(row['released'])
            check(s.core.frame_counter == row['end_frame'], 'Native route timing differs')
        t = ReaderTrace(s.core, watch)
        try:
            s.core.set_keys(s.core.KEY_A); t.frames(3); s.core.clear_keys(s.core.KEY_A)
            t.frames(7)
            actual = s.capture('native-second-floor')
            expected = add_floor(name_image(original, manifest['entries'][0]), original, 2)
            expected.save(root / 'cave/reconstructed-second-floor.png')
            coords = [(x, y) for y in range(160) for x in range(240)
                      if expected.getpixel((x, y)) != (0, 0, 0)]
            check(all(expected.getpixel(p) == actual.getpixel(p) for p in coords),
                  'Decoded card pixels disagree with native display')
            title = manifest['entries'][0]; at = int(title['offset'], 0); size = title['tile_count']*32
            vram = bytes(s.core.memory[0x06000000:0x06002800])
            check(vram[:size] == original[at+0x800:at+0x800+size], 'Native title tile bytes differ')
            check(vram[0x1400:0x2800] == original[FLOOR_TILES:FLOOR_TILES+0x1400], 'Native floor atlas differs')
            reads = t.source_reads
            check(any(int(r['address'], 0) == 0x08000000+POINTER_TABLE for r in reads), 'Missing native card pointer read')
            check(any(int(r['address'], 0) == 0x08000000+PALETTE for r in reads), 'Missing native arrival palette read')
            native = {'frame': s.core.frame_counter, 'fixture': str(fixture.relative_to(ROOT)),
                      'fixture_sha256': digest(fixture.read_bytes()), 'replay_input_indexes': [102, 108],
                      'matching_artwork_pixels': len(coords), 'pixel_mismatches': 0,
                      'title_and_floor_vram_exact': True, 'source_reads': reads}
        finally:
            t.close()

    routes = []
    cases = [('shrine', 'after-clear-north', ('A', 500), ['UP'], 45, 500),
             ('village', 'inn-exit', ('LEFT', 120), ['DOWN'], 40, 500)]
    for name, state_name, setup, keys, hold, released in cases:
        folder = root / name
        state = CAVE / f'clear-route/{state_name}.state'
        with Session(data, folder) as s:
            check(s.core.load_raw_state(state.read_bytes()), 'Cannot restore town route fixture')
            # The inn alignment uses six held frames in the accepted replay.
            code = getattr(s.core, 'KEY_'+setup[0]); s.core.set_keys(code)
            setup_hold = 6 if name == 'village' else 3
            s.frames(setup_hold); s.core.clear_keys(code); s.frames(setup[1])
            t = ReaderTrace(s.core, watch)
            try:
                route = transition(s, t, keys, hold, released, folder)
                route.update(name=name, fixture=str(state.relative_to(ROOT)),
                             fixture_sha256=digest(state.read_bytes()),
                             setup={'key': setup[0], 'hold': setup_hold, 'released': setup[1]},
                             dungeon_arrival_source_reads=t.source_reads,
                             scope='Normal shrine entry / inn-to-village transition only. Visual review and no reads of the known dungeon-card table do not prove universal absence of town cards.')
                check(not t.source_reads, 'Review unexpected dungeon card use on the town route')
                routes.append(route)
            finally:
                t.close()
    report = {'source_rom': str(ORIGINAL_ROM.relative_to(ROOT)), 'source_sha256': digest(original),
              'verified_rom': str(BASELINE.relative_to(ROOT)), 'verified_rom_sha256': digest(data),
              'output_rom': None, 'harness_sha256': digest(Path(__file__).read_bytes()),
              'extractor_sha256': digest((ROOT / 'tools/extract_arrival_cards.py').read_bytes()),
              'manifest_sha256': digest((OUTPUT / 'manifest.json').read_bytes()),
              'replay_sha256': digest((CAVE / 'replay.json').read_bytes()),
              'original_card_ranges_unchanged': len(ledger['ranges']), 'cave': native, 'town_routes': routes,
              'scope': 'All table resources structurally exported; native pixel/VRAM/source-reader proof for one natural cave card. Town routes are bounded observations. No ROM or save edits.'}
    save_json(OUTPUT / 'verification.json', report)
    print(f"Arrival proof: {len(coords)} exact artwork pixels; original title/floor VRAM exact; two town transitions recorded.")


if __name__ == '__main__':
    verify()
