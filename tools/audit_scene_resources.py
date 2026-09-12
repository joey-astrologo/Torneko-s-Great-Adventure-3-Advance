"""Resolve short extraction candidates through native scene/script ownership."""
import argparse
import json
import struct
from pathlib import Path
import mgba.log
from tools.build_first_label import ORIGINAL_ROM, ROOT, digest
from tools import verify_dungeon_interface as ui, verify_tutorial_gameplay as queue
from tools import verify_core_gameplay as old, verify_system_labels as system
from tools.audit_text_coverage import translated_ids
from tools.translation_pipeline import check, load_json, atomic_write
from tools.verify_expansion import Session

OUTPUT = ROOT / 'build/completion/scene-resource-audit'
BASELINE = ROOT / 'build/completion/text-polish/torneko3-text-polish-english.gba'
CACHE = (0xCB02F4, 0xCB048C, 0x0200046C)
CONTROLLER = 0x0203F000
CONTROLLER_BYTES = 0xA8
READERS = {'actor': (20, 0x080690FC, 0x08069116, 0x08069122),
           'object': (24, 0x0806B598, 0x0806B5B2, 0x0806B5BE)}
SLICES = {'actor': {8: (0x08069786, 0x0806979A), 12: (0x0806979A, 0x080697AE),
                    16: (0x080697AE, 0x080697C2), 20: (0x080697C2, 0x080697D2)},
          'object': {8: (0x0806B95E, 0x0806B982), 12: (0x0806B982, 0x0806B992),
                     16: (0x0806B992, 0x0806B9A2), 20: (0x0806B9A2, 0x0806B9B0)}}


def save(path, value):
    atomic_write(path, (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode())


def collect(original):
    u32 = lambda at: struct.unpack_from('<I', original, at)[0]
    check(u32(0x6C604) == CACHE[2] and u32(CACHE[1]) == 0, 'Scene cache ownership differs')
    roots, groups, stops = {}, [], []
    for scene in range((CACHE[1] - CACHE[0]) // 4):
        descriptor = u32(CACHE[0] + scene * 4) - 0x08000000
        check(0 <= descriptor <= len(original) - 36, 'Scene descriptor leaves cartridge')
        fields = struct.unpack_from('<9I', original, descriptor)
        for kind, (offset, _, _, _) in READERS.items():
            base = fields[offset // 4] - 0x08000000
            check(0 <= base < len(original), 'Scene group base leaves cartridge')
            # This is a bounded structural lead. Native field/registration/fetch
            # verification is required separately for each promoted source.
            later = [v - 0x08000000 for v in fields if base + 0x08000000 < v < 0x09000000]
            boundary = min(later + [descriptor])
            for group in range(min(256, max(0, (boundary - base) // 8))):
                word = base + 8 * group
                count, pointer = struct.unpack_from('<II', original, word)
                if count > 64 or bool(count) != bool(pointer) or (count and not 0x08000000 <= pointer <= 0x09000000 - count * 24):
                    stops.append({'scene': scene, 'kind': kind, 'group': group, 'word': hex(word), 'reason': 'invalid count/pointer pair'}); break
                records = [pointer - 0x08000000 + i * 24 for i in range(count)]
                if any(any((v := u32(rec + field)) and (not 0x08000000 <= v < 0x09000000 or v % 4) for field in (8, 12, 16, 20)) for rec in records):
                    stops.append({'scene': scene, 'kind': kind, 'group': group, 'word': hex(word), 'reason': 'invalid record script pointer'}); break
                groups.append({'scene': scene, 'kind': kind, 'group': group, 'word': hex(word), 'count': count, 'records': hex(pointer), 'end_exclusive': hex(word + 8)})
                for row, rec in enumerate(records):
                    for field in (8, 12, 16, 20):
                        source = u32(rec + field)
                        if source:
                            roots.setdefault(source - 0x08000000, []).append({'scene': scene, 'kind': kind, 'group': group,
                                'row': row, 'descriptor': hex(descriptor), 'group_word': hex(word), 'count': count,
                                'record': hex(rec), 'field': field, 'pointer_word': hex(rec + field)})
    master = load_json(ROOT / 'translations/master.json')['entries']; done, _ = translated_ids(master)
    retained = {e['master_id'] for e in load_json(ROOT / 'build/completion/retained-resources.json')['entries']
                if e['kind'] != 'scene_script_command'}
    entries = []
    for e in master:
        at = int(e['offset'], 0)
        if e['id'] in done | retained or at not in roots: continue
        raw = bytes.fromhex(e['source_hex'])
        check(len(raw) <= 8 and original[at:at + len(raw)] == raw and 1 <= original[at] <= 0xAB, 'Scene-root candidate requires separate text review')
        entries.append({'master_id': e['id'], 'offset': e['offset'], 'end_exclusive': hex(at + len(raw)),
                        'source_hex': e['source_hex'], 'japanese': e['japanese'], 'command_hex': original[at:at + 8].hex(),
                        'opcode': original[at], 'owners': roots[at]})
    return {'schema': 1, 'source_sha256': digest(original), 'cache': {'rom_start': hex(CACHE[0]), 'rom_end_exclusive': hex(CACHE[1]), 'ram_start': hex(CACHE[2])},
            'groups': groups, 'structural_stops': stops, 'entries': entries,
            'scope': 'Candidate ancestry only until native verification. No complete script grammar, natural reachability or insertion ownership is granted.'}


def prepare():
    report = collect(ORIGINAL_ROM.read_bytes())
    save(OUTPUT / 'source-candidates.json', report)
    print(len(report['entries']), 'scene program candidates; exact ancestry recorded', flush=True)


def verify():
    mgba.log.silence(); original = ORIGINAL_ROM.read_bytes(); data = BASELINE.read_bytes()
    candidates = load_json(OUTPUT / 'source-candidates.json')
    check(candidates == collect(original), 'Scene ancestry changed before proof')
    cases = []
    with Session(data, OUTPUT / 'native') as s:
        c = s.core
        s.frames(600)
        check(bytes(c.memory[CACHE[2]:CACHE[2] + CACHE[1] - CACHE[0]]) == original[CACHE[0]:CACHE[1]], 'Cold scene cache differs')
        for e in candidates['entries']:
            check(c.load_raw_state(system.STATE.read_bytes()), 'Scene audit fixture restore')
            check(bytes(c.memory[CACHE[2]:CACHE[2] + CACHE[1] - CACHE[0]]) == original[CACHE[0]:CACHE[1]], 'Restored scene cache differs')
            at = int(e['offset'], 0); owner = e['owners'][0]
            _, entry, stop, advance = READERS[owner['kind']]
            selected = queue.select_slice(c, entry, stop, {'r0': owner['scene'], 'r1': owner['group']}, 4)
            record_base = int(selected['source'], 0)
            check(record_base == c.memory.u32[int(owner['group_word'], 0) + 0x08000004], 'Native scene/group base differs')
            record = record_base
            for index in range(owner['row']):
                selected = queue.select_slice(c, advance, stop, {'r4': record, 'r5': index,
                    'r6': int(owner['group_word'], 0) + 0x08000000, 'r7': owner['group']}, 4)
                record = int(selected['source'], 0)
            check(record == int(owner['record'], 0) + 0x08000000, 'Native scene record stride differs')
            system.guard(c, CONTROLLER, CONTROLLER_BYTES)
            old.write_bytes(c, CONTROLLER, b'\0' * CONTROLLER_BYTES)
            begin, end = SLICES[owner['kind']][owner['field']]
            t = ui.InterfaceTrace(c)
            try:
                ui.native_step(s, t, begin, [], stop=end, overrides={begin: {'r4': CONTROLLER,
                    'r6': CONTROLLER, 'r7': record, 'r9': record}})
                slot = (owner['field'] - 8) // 4
                check(c.memory.u32[CONTROLLER + 16 + slot * 4] == at + 0x08000000, 'Native script registration differs')
                ui.native_step(s, t, 0x0806452C, [CONTROLLER, 0, slot])
                check(c.memory.u32[CONTROLLER + 0x24] == at + 0x08000000, 'Native script activation differs')
            finally:
                t.close()
            dispatched = queue.select_slice(c, 0x08064E28, 0x08064E60, {'r0': CONTROLLER}, 0)
            check(c.memory.u32[CONTROLLER + 0x24] == at + 0x08000008 and c.memory.u32[CONTROLLER + 0x34] == at + 0x08000000 and
                  c.memory.u8[CONTROLLER + 0x38] == e['opcode'], 'Native event fetch/cursor differs')
            table = struct.unpack_from('<I', original, 0x64E64)[0]
            expected = c.memory.u32[table + (e['opcode'] - 1) * 4]
            check(int(dispatched['source'], 0) == expected, 'Native event dispatch differs')
            system.guards(c, CONTROLLER, CONTROLLER_BYTES)
            check(data[at:at + 8] == bytes.fromhex(e['command_hex']) == original[at:at + 8], 'Scene command was modified')
            cases.append({**e, 'selected_owner': owner, 'native_record': hex(record), 'registered_slot': slot,
                          'dispatch_target': hex(expected), 'guards_intact': True, 'command_bytes_unchanged': True})
        result = {'status': 'scene_program_candidates_native_verified', 'source_sha256': digest(original),
                  'verified_rom': str(BASELINE.relative_to(ROOT)), 'verified_rom_sha256': digest(data),
                  'candidates_sha256': digest((OUTPUT / 'source-candidates.json').read_bytes()),
                  'harness_sha256': digest(Path(__file__).read_bytes()), 'fixture_sha256': digest(system.STATE.read_bytes()),
                  'helper_sha256': {Path(m.__file__).name: digest(Path(m.__file__).read_bytes()) for m in (ui, queue, old, system)},
                  'entries': cases, 'scope': 'Native scene/group/record selection, script-field registration and activation, original eight-byte command fetch and opcode dispatch. The candidate prefix is program data, not a displayed string. Execution stops before event actions; natural scene/branch reachability and complete group/script inventories are not established. No ROM writes or insertion space.'}
        save(OUTPUT / 'native-verification.json', result)
    print(len(cases), 'scene program candidates verified through native dispatch', flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('mode', choices=('prepare', 'verify'))
    prepare() if p.parse_args().mode == 'prepare' else verify()
