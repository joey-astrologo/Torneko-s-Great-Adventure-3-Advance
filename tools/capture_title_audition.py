"""Capture the original title naturally for an offline artwork audition."""
from pathlib import Path
import struct
import mgba.log
from tools.audit_boot_graphics import Trace
from tools.build_first_label import ROOT, ORIGINAL_ROM, digest
from tools.extract_arrival_cards import save_json
from tools.translation_pipeline import check, load_json
from tools.verify_expansion import Session
from tools.build_rendering_fixes import ROM as BASELINE

OUT = ROOT / 'build/title-audition'


def capture():
    mgba.log.silence()
    original = ORIGINAL_ROM.read_bytes()
    # Keep the Japanese-title comparison reproducible after latest English
    # starts displaying the approved localized artwork.
    current = BASELINE.read_bytes()
    source_hash = digest(original)
    current_hash = digest(current)
    check(current_hash == load_json(BASELINE.parent/'english-build.json')['rom_sha256'],
          'Pre-title baseline report differs')
    resources = load_json(ROOT/'build/completion/boot-graphics/research/resource-ranges.json')
    check(resources['source_sha256'] == source_hash, 'Wrong resource source')
    title = next(r for r in resources['records'] if r['id'] == 2)
    for lo, hi, expected in ((title['source'], title['tiles_end_exclusive'], title['source_sha256']),
                             (title['palette'], title['palette_end_exclusive'], title['palette_sha256'])):
        start, end = int(lo, 0), int(hi, 0)
        check(digest(original[start:end]) == expected, 'Title source changed')
        check(original[start:end] == current[start:end], 'Current title resource differs')
    saves = {str(p.relative_to(ROOT)): digest(p.read_bytes())
             for p in (ROOT/'saves').rglob('*') if p.is_file()}
    cases = []
    frames = []
    for variant, data in (('japanese', original), ('current', current)):
        with Session(data, OUT/'reference'/variant) as session:
            trace = Trace(session.core, data)
            try:
                trace.frames(600)
                frame = session.capture('title')
                frames.append(frame.tobytes())
                check([r['index'] for r in trace.rows] == [1, 0, 9, 2], 'Boot route differs')
                if variant == 'japanese':
                    palette = bytes(session.core.memory[0x05000000:0x05000200])
                    colors = [list(((v & 31) << 3, ((v >> 5) & 31) << 3,
                                    ((v >> 10) & 31) << 3))
                              for v in struct.unpack('<256H', palette)]
                    save_json(OUT/'reference/palette.json', colors)
                cases.append({'variant': variant, 'rom_sha256': digest(data),
                              'frame': 600, 'inputs': [], 'native_graphics': trace.rows,
                              'png_sha256': digest((session.output/'title.png').read_bytes())})
            finally:
                trace.close()
    check(frames[0] == frames[1], 'Japanese/current title pixels differ')
    check(digest(ORIGINAL_ROM.read_bytes()) == source_hash and digest(BASELINE.read_bytes()) == current_hash,
          'A ROM changed during capture')
    check(all(digest((ROOT/p).read_bytes()) == h for p, h in saves.items()), 'User save changed')
    save_json(OUT/'reference/provenance.json', {
        'source_rom': str(ORIGINAL_ROM.relative_to(ROOT)), 'source_sha256': source_hash,
        'baseline_rom': str(BASELINE.relative_to(ROOT)), 'baseline_sha256': current_hash,
        'output_rom': None, 'cases': cases, 'title_resource': title,
        'japanese_current_pixels_equal': True, 'user_save_hashes': saves,
        'user_files_unchanged': True, 'harness_sha256': digest(Path(__file__).read_bytes()),
        'scope': 'Natural cold boot, no buttons or RAM edits, native source/map/tile checks. '
                 'This verifies only the retained Japanese reference; no English title is inserted.'})
    print('Captured identical Japanese/current title screens with native provenance.')


if __name__ == '__main__':
    capture()
