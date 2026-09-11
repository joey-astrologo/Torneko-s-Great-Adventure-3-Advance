"""Insert the complete default-nickname table with bounded recruitment encoding."""
import argparse
import csv
import json
from pathlib import Path
import struct
import subprocess
import tempfile

from tools import build_companion_dialogue as previous
from tools.build_first_label import ORIGINAL_ROM, ROOT, digest
from tools.build_name_entry import LATIN
from tools.game_text import GameTextCodec, rebuild
from tools.rom_build import RomBuild
from tools.translation_pipeline import FontZero, atomic_write, check, load_json

OUTPUT = ROOT/'build/ally-nicknames'
CATALOG = ROOT/'translations/ally-nicknames.json'
TABLE, ROWS, CAPACITY = 0x1A9F30, 200, 6


def extract_catalog(original):
    codec = GameTextCodec(original); entries = []
    species = {e['row']: e for e in load_json(ROOT/'translations/enemies.json')['entries'] if e['family']=='name'}
    for row in range(ROWS):
        word = TABLE+row*4; offset = struct.unpack_from('<I', original, word)[0]-0x08000000
        source = codec.parse(original, offset)
        check(rebuild(source['tokens']) == original[offset:source['end']], 'Nickname source round trip failed')
        entries.append({'id': f'ally.nickname.{row:03d}', 'family': 'nickname', 'row': row,
            'offset': f'0x{offset:08X}', 'pointer_offset': f'0x{word:08X}', 'master_id': f'jp_{offset:08x}',
            'japanese': source['display'], 'source_hex': source['raw_hex'], 'source_tokens': source['tokens'],
            'species_id': species[row]['id'], 'species_japanese': species[row]['japanese'],
            'species_english': species[row]['english'], 'english': None, 'display': None, 'notes': '', 'references': []})
    return {'schema': 1, 'base_sha256': digest(original), 'font': 0,
        'scope': 'All 200 default ally nickname pointers; 198 distinct original strings. Existing five-character compact storage retained.', 'entries': entries}


def validate_catalog(original, catalog):
    fresh = extract_catalog(original); entries = {e['id']: e for e in catalog['entries']}
    check(len(entries) == len(catalog['entries']) == ROWS, 'Incomplete/duplicate nickname table')
    for key in ('schema','base_sha256','font','scope'): check(catalog[key] == fresh[key], 'Nickname header changed')
    for source in fresh['entries']:
        e = entries[source['id']]
        for key in source.keys()-{'english','display','notes','references'}:
            check(e[key] == source[key], f'Nickname source/owner changed: {e["id"]}/{key}')
        check(isinstance(e['english'],str) and e['english'] and isinstance(e['notes'],str) and e['notes'], 'Missing nickname language/review')
        encode(e, original)
    by_source = {}
    for e in entries.values():
        value = (e['english'], e['display'])
        check(e['offset'] not in by_source or by_source[e['offset']] == value, 'Shared nickname source has inconsistent wording')
        by_source[e['offset']] = value
    return entries


def encode(entry, original):
    text = entry['display'] or entry['english']
    check(1 <= len(text) < CAPACITY and all(c in LATIN for c in text), 'Nickname needs one to five alphanumeric characters')
    font = FontZero(original); width = sum(font.glyph(c)[1] for c in text)
    check(width <= 60, 'Nickname exceeds five original cells')
    return text.encode()+b'\0', {'full_english': entry['english'], 'display': text, 'characters': len(text),
        'width': width, 'compact_capacity': CAPACITY, 'compact_hex': (bytes(LATIN[c] for c in text)+b'\0').hex(),
        'duplicate_rule': 'Keep first four base letters and final numeric suffix if combined length exceeds five.'}


def expected_compact(text, suffix=0):
    check(0 <= suffix <= 9, 'Invalid duplicate suffix')
    value = text+str(suffix)
    if len(value)>5: value = value[:4]+value[-1]
    check(1 <= len(value) <= 5 and all(c in LATIN for c in value), 'Invalid bounded nickname')
    return bytes(LATIN[c] for c in value)+b'\0', value


def add_nicknames(build, catalog, language):
    entries = validate_catalog(build.original, catalog); relocated = {}; targets = {}
    for e in entries.values():
        offset = int(e['offset'],0); source = bytes.fromhex(e['source_hex']); english, metrics = encode(e, build.original)
        build.protect_source(e['id'], offset, offset+len(source), 'ally-nicknames')
        if offset not in targets:
            targets[offset] = build.allocate(e['id'], english if language=='english' else source, 'ally-nicknames')
        target = targets[offset]
        build.patch(e['id'], int(e['pointer_offset'],0), struct.pack('<I', offset+0x08000000),
            struct.pack('<I',target+0x08000000), 'ally-nicknames', 'Recruitment species*4 pointer load at 08029278')
        relocated[e['id']] = {'offset': target, 'metrics': metrics}
    ascii_ids = bytes(LATIN.get(chr(i),0) for i in range(128))
    ids = build.allocate('ally.nickname.ascii-ids', ascii_ids, 'ally-nicknames')+0x08000000
    code_address = 0x08000000+((build.allocator.cursor+3)&~3)
    with tempfile.TemporaryDirectory(prefix='nickname-asm-') as folder:
        run = subprocess.run([str(ROOT/'.tools/bin/armips'), str(ROOT/'tools/ally_nicknames.asm'),
            '-equ','CODE_ADDRESS',hex(code_address),'-equ','ASCII_IDS',hex(ids)],cwd=folder,text=True,capture_output=True)
        check(run.returncode==0,'Nickname assembly failed: '+run.stdout+run.stderr)
        code = (Path(folder)/'nickname-code.bin').read_bytes()
    target = build.allocate('ally.nickname.encoder',code,'ally-nicknames')+0x08000000
    check(target==code_address,'Nickname encoder moved')
    build.patch('ally.nickname.encoder-entry',0x7D29C,build.original[0x7D29C:0x7D2A4],
        bytes.fromhex('004b1847')+struct.pack('<I',target|1),'ally-nicknames',
        'Bound ASCII recruitment defaults to five compact IDs, preserving duplicate suffix; Japanese/other callers retain original encoder')
    return {'language':language,'rows':ROWS,'unique_sources':len(targets),'relocated':relocated,
            'encoder':{'address':hex(target),'bytes':len(code),'ascii_ids':hex(ids)}}


def build_rom(original, language='english', catalog=None):
    check(language in ('english','japanese'),'Invalid nickname build language')
    build = RomBuild(original)
    _, prior = previous.previous.build_rom(original,build=build)
    dialogue = previous.add_dialogue(build,load_json(previous.CATALOG),'english')
    report = add_nicknames(build,load_json(CATALOG) if catalog is None else catalog,language)
    data, ledger = build.finish()
    return data, {'source_sha256':digest(original),'rom_sha256':digest(data),'nicknames':report,
        'dialogue':dialogue,'prior_dialogue':prior['dialogue'],'history':prior['history'],'ledger':ledger}


def build():
    for language in ('japanese','english'):
        data, report = build_rom(ORIGINAL_ROM.read_bytes(),language)
        atomic_write(OUTPUT/f'torneko3-ally-nicknames-{language}.gba',data)
        atomic_write(OUTPUT/f'{language}-build.json',(json.dumps(report,indent=2)+'\n').encode())
        print(language,report['rom_sha256'],report['ledger']['appended_used_with_padding'],flush=True)


if __name__=='__main__':
    argparse.ArgumentParser(description=__doc__).parse_args(); build()
