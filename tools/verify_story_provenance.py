"""Check original event operands, formatted RAM provenance and omitted resources."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import struct

from tools.audit_text_coverage import SourceIndex, cartridge_offset
from tools.build_first_label import ORIGINAL_ROM, ROOT, digest, load_manifest
from tools.game_text import GameTextCodec, DecodeError, rebuild
from tools.translation_pipeline import atomic_write, check, load_json

OUTPUT = ROOT / 'build/story-provenance'
CONTROLLER, SCRIPT = 0x0203F000, 0x0203F100
# Opcode -> (dispatch branch, receiving function, source register).
ROUTES = {
    0x23: (0x0806639C, 0x08061244, 0),
    0x24: (0x0806552C, 0x0806128C, 0),
    0x25: (0x08065536, 0x080612D4, 0),
    0x26: (0x08065540, 0x08061320, 0),
    0x27: (0x0806554A, 0x08061200, 0),
    0x28: (0x08065560, 0x08061200, 0),
    0x29: (0x08065584, 0x0806136C, 1),
    0x2A: (0x080655A0, 0x08061244, 0),
    0x2B: (0x080655A0, 0x0806128C, 0),
    0x2C: (0x080655A0, 0x080612D4, 0),
    0x2D: (0x080655A0, 0x08061320, 0),
    0x96: (0x08066306, 0x08061244, 0),
    0x97: (0x08066306, 0x080612D4, 0),
}


def write(name, value):
    atomic_write(OUTPUT / name, (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode())


def hx(value):
    return f'0x{value:08X}'


def positioned_coordinates(word):
    x = (word >> 16) & 0xFFFF
    return (x - 0x10000 if x & 0x8000 else x, ((word >> 8) & 255) - 0x80)


def check_natural(trace, original, master):
    """Recheck the complete chain, not a match on the displayed Japanese text."""
    index = SourceIndex(master)
    # The capture harness rejects callback errors before writing this report.
    check(not trace['unattributed_story_reads'], 'Unattributed native story trace')
    check(trace['versions'] and trace['story_ram_reads'], 'Empty story provenance trace')
    ids, opcodes, destinations = set(), Counter(), Counter()
    for serial, version in enumerate(trace['versions']):
        check(version['serial'] == serial, 'Bad buffer version serial')
        prepare = trace['preparations'][version['preparation_serial']]
        check(prepare['wrapper_serial'] is not None, 'Preparation lacks originating wrapper')
        wrapper = trace['wrappers'][prepare['wrapper_serial']]
        check(wrapper['event_serial'] is not None, 'Wrapper lacks originating event')
        event = trace['commands'][wrapper['event_serial']]
        at = cartridge_offset(int(event['cursor'], 0), len(original))
        check(at is not None and event['command_in_original_rom'], 'Event cursor is not original ROM')
        raw = bytes.fromhex(event['raw_hex'])
        check(len(raw) == 8 and original[at:at+8] == raw, 'Event bytes differ from original')
        word, operand = struct.unpack('<II', raw)
        check(word == int(event['command_word'], 0) and operand == int(event['operand'], 0), 'Event fields differ from bytes')
        check(int(event['operand_word'], 0) == int(event['cursor'], 0)+4, 'Wrong event operand word')
        opcode = word & 255
        check(opcode == event['opcode'] and opcode in ROUTES and opcode != 0x29, 'Wrong story opcode')
        check(int(wrapper['entry'], 0) == ROUTES[opcode][1], 'Event selected wrong wrapper')
        for source in (wrapper['source'], prepare['source'], version['source']):
            check(int(source['address'], 0) == operand, 'Source changed between producer stages')
            offset = cartridge_offset(operand, len(original))
            check(offset is not None and source['offset'] == hx(offset), 'Invalid ROM source')
            location = index.locate(offset)
            check(location['kind'] == 'source_start' and source['master_id'] == location['master_id'], 'Source is not a master start')
            payload = bytes.fromhex(source['source_hex'])
            check(original[offset:offset+len(payload)] == payload, 'Source bytes changed')
        formatted = trace['formats'][version['format_serial']]
        check(formatted['caller'] == '0x08061726' and int(formatted['source'], 0) == operand, 'Formatter has wrong caller/source')
        destination, limit = int(version['destination'], 0), int(version['limit'], 0)
        check(destination == int(prepare['structure'], 0)+12 and limit-destination == 1023, 'Story buffer bounds differ')
        check(formatted['destination'] == version['destination'] and int(formatted['payload_end'], 0) == limit, 'Formatter has wrong destination')
        check(formatted['output_hex'] == version['output_hex'], 'Version lost formatter output')
        output = bytes.fromhex(version['output_hex'])
        check(output and output[-1] == 0 and len(output) <= 1024, 'Unterminated or oversized story output')
        check(len(output) == version['written_bytes']+1 == formatted['written_bytes']+1, 'Output byte count differs')
        ids.add(version['source']['master_id']); opcodes[opcode] += 1; destinations[version['destination']] += 1
    read_versions = set()
    for row in trace['story_ram_reads']:
        serial, delta = row['version_serial'], row['byte_delta']
        check(0 <= serial < len(trace['versions']) and delta >= 0, 'Invalid RAM read version/offset')
        version = trace['versions'][serial]
        output, raw = bytes.fromhex(version['output_hex']), bytes.fromhex(row['raw_hex'])
        check(raw and output[delta:delta+len(raw)] == raw, 'RAM read differs from originating version')
        check(row['caller'] in ('0x080618F4', '0x08061A9C', '0x08061AD2') and row['count'] > 0, 'Invalid story consumer')
        read_versions.add(serial)
    check(read_versions == set(range(len(trace['versions']))), 'A formatted version was never read')
    return {'buffer_versions': len(trace['versions']), 'distinct_master_sources': len(ids), 'master_ids': sorted(ids),
            'command_fetches': len(trace['commands']), 'aggregated_ram_reads': len(trace['story_ram_reads']),
            'executed_ram_reads': sum(r['count'] for r in trace['story_ram_reads']), 'unattributed_ram_reads': 0,
            'opcodes': {hx(k): v for k, v in sorted(opcodes.items())}, 'buffer_destinations': dict(destinations),
            'largest_formatted_payload_bytes': max(v['written_bytes'] for v in trace['versions'])}


def resources(original, master):
    codec, index, rows = GameTextCodec(original), SourceIndex(master), {}
    commands = []
    for at in range(0x91D6C8, 0x91DD00, 8):
        word, pointer = struct.unpack_from('<II', original, at)
        if word & 255 == 0x29: commands.append((at, 'original_English_credit'))
    commands.append((0xAB94AC, 'punctuation_only_dialogue'))
    for at, role in commands:
        word, pointer = struct.unpack_from('<II', original, at)
        offset = cartridge_offset(pointer, len(original))
        check(offset is not None, 'Resource source outside ROM')
        parsed = codec.parse(original, offset)
        check(index.locate(offset)['kind'] == 'uncovered', 'Reviewed resource already in master')
        check(rebuild(parsed['tokens']) == bytes.fromhex(parsed['raw_hex']), 'Resource round trip failed')
        row = rows.setdefault(offset, {'offset': hx(offset), 'end_exclusive': hx(offset+len(bytes.fromhex(parsed['raw_hex']))),
            'role': role, 'display': parsed['display'], 'source_hex': parsed['raw_hex'], 'source_tokens': parsed['tokens'],
            'command_references': [], 'insertion_ownership': 'none; native source/reader evidence only'})
        row['command_references'].append({'offset': hx(at), 'end_exclusive': hx(at+8), 'word': hx(word),
            'operand_word': hx(at+4), 'source': hx(pointer), 'raw_hex': original[at:at+8].hex()})
    result = {'source_sha256': digest(original), 'entries': list(rows.values()),
        'credit_command_count': len(commands)-1, 'credit_distinct_sources': len(rows)-1,
        'scope': 'One reviewed credits command span plus one punctuation-only dialogue. Sources are original-ROM text, not fan-patch English. Natural ending/event reachability and relocation remain untested.'}
    write('reviewed-resources.json', result)
    return result


def plain_header_scan(original, master):
    """A deliberately narrow sweep; headers with parameters are NOT covered."""
    index, codec = SourceIndex(master), GameTextCodec(original)
    counts, known, outside = Counter(), set(), []
    for at in range(0, len(original)-7, 4):
        word, pointer = struct.unpack_from('<II', original, at)
        if word not in ROUTES: continue
        offset = cartridge_offset(pointer, len(original))
        if offset is None: continue
        location = index.locate(offset); counts[(word, location['kind'])] += 1
        if location.get('master_id'): known.add(location['master_id'])
        else:
            try: parsed = codec.parse(original, offset); preview = parsed['display']
            except DecodeError as error: preview = str(error)
            outside.append({'command_offset': hx(at), 'word': hx(word), 'source': hx(pointer),
                'preview': preview, 'classification': 'reviewed_punctuation_source' if offset == 0xAB94E8 else 'unverified_pair_shape'})
    result = {'source_sha256': digest(original), 'counts': [{'opcode': hx(o), 'location': k, 'pairs': n} for (o,k),n in sorted(counts.items())],
        'matching_master_ids': sorted(known), 'outside_master': outside,
        'scope': 'All aligned pairs whose entire first word is exactly a checked opcode and second word is a physical-ROM pointer. This intentionally misses nonzero command parameters, RAM operands, unaligned commands and other families. Coincidental code/data pairs remain possible; matching pairs never grant event reachability or insertion ownership.'}
    write('plain-header-scan.json', result)
    return result


def native_probes(original, reviewed):
    import mgba.log
    from mgba._pylib import ffi
    from tools.verify_ally_services import context
    from tools.verify_dungeon_interface import registers
    from tools.verify_companion_dialogue import run_to
    from tools.verify_core_gameplay import write_bytes
    from tools.verify_expansion import Session
    mgba.log.silence()
    state = (OUTPUT/'natural/final.state').read_bytes()
    cases, credits = [], []
    with Session(original, OUTPUT/'controlled') as session:
        core = session.core
        def restore():
            check(core.load_raw_state(state), 'Original route state failed to restore')
            write_bytes(core, CONTROLLER, b'\0'*0x80)
            write_bytes(core, SCRIPT, b'\0'*0x20)
            return core.memory.u32[0x03000010]
        # Execute the entire fetch/dispatch, stopping at the native recipient.
        # Synthetic headers deliberately exercise branches without pretending to
        # establish normal event reachability or identify original pointer owners.
        source = 0x0891BBB4
        for opcode, (branch, recipient, argument) in ROUTES.items():
            root = restore()
            word = 0x00108029 if opcode == 0x29 else opcode
            write_bytes(core, SCRIPT, struct.pack('<IIII', word, source, 0x98, 0x08919134))
            core.memory.u32[CONTROLLER+0x24] = SCRIPT
            result = run_to(core, 0x08064E28, recipient, {'r0': CONTROLLER})
            check(result['registers'][argument] == source, 'Native command lost source operand')
            check(core.memory.u32[CONTROLLER+0x34] == SCRIPT and core.memory.u8[CONTROLLER+0x38] == opcode, 'Wrong native fetched command')
            check(core.memory.u32[CONTROLLER+0x24] == SCRIPT+(16 if opcode in (0x96,0x97) else 8), 'Unexpected command consumption')
            check(struct.unpack_from('<I', original, 0x64E68+(opcode-1)*4)[0] == branch, 'Dispatch table disagrees with native route')
            if opcode in (0x96,0x97):
                check(core.memory.u32[0x02000430] == 1 and core.memory.u32[0x02008B80] == 0x08919134, 'Choice-prefix list was not consumed')
            cases.append({'opcode': hx(opcode), 'synthetic_word': hx(word), 'source': hx(source), 'recipient': hx(recipient),
                'source_register': argument, 'steps': result['steps'], 'cursor_after': hx(core.memory.u32[CONTROLLER+0x24])})
        for row in reviewed['entries']:
            if row['role'] != 'original_English_credit': continue
            for ref in row['command_references']:
                root = restore(); slot = len(credits) % 16
                before = bytearray(b'\xA5' * 0xC4)
                struct.pack_into('<I', before, 0xC0, slot)
                write_bytes(core, root+0x8D8, before)
                core.memory.u32[CONTROLLER+0x24] = 0x08000000+int(ref['offset'],0)
                queued = run_to(core, 0x08064E28, 0x0806559E, {'r0': CONTROLLER})
                word, source = int(ref['word'],0), int(ref['source'],0)
                x, y = positioned_coordinates(word)
                expected = before[:]
                struct.pack_into('<ii', expected, slot*8, x, y)
                struct.pack_into('<I', expected, 0x80+slot*4, source)
                struct.pack_into('<I', expected, 0xC0, slot+1)
                check(bytes(core.memory[root+0x8D8:root+0x99C]) == expected, 'Positioned queue changed adjacent slots')
                # Native pointer/position loads through the draw-call boundary.
                # Negative x follows the native glyph-width centering loop;
                # negative y is relative to the controlled previous-y value.
                core.memory.u32[0x03007C20] = 0  # reader local previous-y at sp+20
                drawn = run_to(core, 0x080629C4, 0x08062A54, {'r4': slot, 'sp': 0x03007C00})
                draw_x, draw_y, draw_source = drawn['registers'][:3]
                check(draw_y == abs(y) and draw_source == source, 'Positioned reader did not supply original credit to draw')
                check(draw_x == x if x >= 0 else 0 <= draw_x <= 104, 'Positioned reader x differs')
                credits.append({'command_offset': ref['offset'], 'source_offset': row['offset'], 'slot': slot,
                    'x': x, 'draw_x': draw_x, 'relative_y': y, 'draw_y': draw_y, 'queue_steps': queued['steps'], 'read_steps': drawn['steps'], 'other_slots_intact': True})
        row = next(e for e in reviewed['entries'] if e['role'] == 'punctuation_only_dialogue')
        root = restore(); core.memory.u32[CONTROLLER+0x24] = 0x08AB94AC
        # This wrapper also initializes a window. Its native clearing loops
        # exceed the short selector helper's 10,000-instruction allowance.
        saved = context(core); cpu = ffi.cast('struct ARMCore*', core._core.cpu)
        try:
            registers(core, {'cpsr': 255, 'sp': 0x03007E00, 'lr': 0x08000001, 'r0': CONTROLLER, 'pc': 0x08064E28})
            for steps in range(500000):
                pc = (int(cpu.gprs[15]) & 0xFFFFFFFF) - (2 if cpu.cpsr.packed & 32 else 4)
                if pc == 0x0806172A: break
                core.step()
            else: raise ValueError(f'Punctuation formatter stalled at {pc:08X}')
        finally: registers(core, saved)
        raw = bytes.fromhex(row['source_hex']); destination = root+0x5C
        check(bytes(core.memory[destination:destination+len(raw)]) == raw, 'Punctuation line did not reach native story buffer')
        punctuation = {'command_offset': '0x00AB94AC', 'source_offset': row['offset'], 'destination': hx(destination),
                       'output_hex': raw.hex(), 'steps': steps}
    result = {'source_sha256': digest(original), 'state_sha256': digest(state), 'opcode_cases': cases,
        'credit_queue_and_draw_input_cases': credits, 'punctuation_formatter': punctuation,
        'scope': 'Controlled original-code slices. 13 synthetic command headers test operand routing; credits and punctuation use untouched original command bytes. Restored CPU/queue state and chosen entries do not prove natural event/ending reachability, full credit playback, glyph pixels, or relocated pointer compatibility.'}
    write('native-probes.json', result)
    return result


def verify():
    original = ORIGINAL_ROM.read_bytes()
    check(digest(original) == load_manifest()['base_sha256'], 'Wrong original ROM')
    hashes = load_json(OUTPUT/'before/hashes.json')
    for name, value in hashes.items(): check(digest((ROOT/name).read_bytes()) == value, f'Input changed: {name}')
    master = load_json(ROOT/'translations/master.json')['entries']
    trace = load_json(OUTPUT/'natural/trace.json')
    for key, path in (('harness_sha256', ROOT/'tools/trace_story_provenance.py'),
                      ('reader_helper_sha256', ROOT/'tools/trace_text_systems.py'),
                      ('master_sha256', ROOT/'translations/master.json'),
                      ('initial_save_sha256', ROOT/'build/text-coverage/runtime/creation/created.sav')):
        check(trace[key] == digest(path.read_bytes()), f'Stale natural trace input: {key}')
    check(trace['source_sha256'] == digest(original) and trace['inputs'], 'Wrong/empty natural route')
    natural = check_natural(trace, original, master); write('natural-coverage.json', natural)
    reviewed = resources(original, master); scan = plain_header_scan(original, master)
    native = native_probes(original, reviewed)
    log = (OUTPUT/'unit-tests.log').read_text(); match = re.search(r'Ran (\d+) tests', log)
    check(match and int(match[1]) >= 162 and log.rstrip().endswith('OK'), 'Unit tests incomplete or failed')
    for name, value in hashes.items(): check(digest((ROOT/name).read_bytes()) == value, f'Input changed during verification: {name}')
    artifacts = ('natural/trace.json', 'natural/final.state', 'natural-coverage.json', 'native-probes.json',
        'reviewed-resources.json', 'plain-header-scan.json', 'story-wrappers.txt', 'dispatch-text.txt',
        'positioned-text.txt', 'positioned-reader.txt', 'positioned-draw.txt', 'unit-tests.log')
    report = {'status': 'passed', 'source_sha256': digest(original), 'preserved_input_files': len(hashes), 'input_hashes': hashes,
        'natural': natural, 'native_opcode_cases': len(native['opcode_cases']),
        'native_credit_cases': len(native['credit_queue_and_draw_input_cases']), 'reviewed_extra_sources': len(reviewed['entries']),
        'unit_tests': int(match[1]), 'harness_sha256': digest(Path(__file__).read_bytes()),
        'native_step_helper_sha256': digest((ROOT/'tools/verify_companion_dialogue.py').read_bytes()),
        'artifact_sha256': {name: digest((OUTPUT/name).read_bytes()) for name in artifacts},
        'limits': 'Opening story provenance and documented controlled readers only. No full-game discovery claim, insertion, master edit, font/save change, translation count increase, or fan-patch reuse.'}
    write('acceptance.json', report)
    print(json.dumps({k:v for k,v in report.items() if k not in ('input_hashes','artifact_sha256')}, indent=2))
    return report


if __name__ == '__main__':
    argparse.ArgumentParser(description=__doc__).parse_args(); verify()
