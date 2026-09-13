"""Fresh names, natural dungeon defeat, priest save, cold records and both logs."""
import json
import struct
from pathlib import Path
import mgba.log
from mgba._pylib import ffi, lib
from tools import build_inventory_notice as b
from tools import verify_name_entry as names
from tools import verify_current_text_pass as opening
from tools import trace_story_provenance
from tools.build_first_label import ROOT, ORIGINAL_ROM, digest
from tools.build_name_entry import NAME_RAM, compact_name
from tools.translation_pipeline import check, load_json, atomic_write, FontZero
from tools.verify_expansion import Session
from tools.verify_inventory_notice import NoticeTrace, check_ui
from tools.verify_result_runtime import map_errors, ink_pixels
from tools.verify_first_label import battery_snapshot
from tools.verify_natural_cave import sources
from tools.verify_story_provenance import check_natural
from tools.verify_dungeon_interface import check_glyphs
from tools.verify_core_gameplay import visible
from tools.game_text import GameTextCodec

OUT = ROOT/'build/completion/roundtrip/verification'
PROFILE, PROFILE_SIZE = 0x02002FD4, 0x1FAC
EXPECTED_NAME = compact_name('Torneko').ljust(8, b'\0')


def save(path, value):
    atomic_write(path, (json.dumps(value, ensure_ascii=False, indent=2)+'\n').encode())


class RoundtripTrace(NoticeTrace):
    def __init__(self, *args):
        self.save_events, self.result_events = [], []
        super().__init__(*args)
        for address in (0x080027D0, 0x0800230A, 0x08085548, 0x080011F0, 0x080016DC, 0x0805C6F8):
            point = ffi.new('struct mBreakpoint*')
            point.address, point.segment, point.type = address, -1, lib.BREAKPOINT_HARDWARE
            check(self.debugger.platform.setBreakpoint(self.debugger.platform, point) >= 0, 'Save/result observer failed')

    def entered(self, debugger, reason, info):
        try:
            if info != ffi.NULL and reason == lib.DEBUGGER_ENTER_BREAKPOINT:
                pc = int(info.address); regs = [int(r)&0xFFFFFFFF for r in self.cpu.gprs]
                if pc in (0x080027D0, 0x0800230A, 0x08085548, 0x080011F0, 0x080016DC):
                    e = {'pc': hex(pc), 'phase': self.phase, 'frame': self.core.frame_counter,
                         'name_hex': bytes(self.core.memory[NAME_RAM:NAME_RAM+8]).hex()}
                    if pc in (0x080027D0, 0x0800230A):
                        e['record_name_hex'] = bytes(self.core.memory[regs[6]+16:regs[6]+24]).hex()
                    if pc == 0x08085548:
                        e['slot_name_hex'] = bytes(self.core.memory[regs[2]:regs[2]+8]).hex()
                    if pc in (0x080011F0, 0x080016DC):
                        e['profile_hex'] = bytes(self.core.memory[PROFILE:PROFILE+PROFILE_SIZE]).hex()
                    self.save_events.append(e)
                elif pc == 0x0805C6F8:
                    raw = bytes(self.core.memory[0x02034DDC:0x020355DC])
                    check(not map_errors(raw), 'Natural ending tilemap differs')
                    self.result_events.append({'frame': self.core.frame_counter, 'phase': self.phase,
                        'profile_hex': bytes(self.core.memory[PROFILE:PROFILE+PROFILE_SIZE]).hex(),
                        'name_hex': bytes(self.core.memory[NAME_RAM:NAME_RAM+8]).hex(), 'map_cells_verified': 459})
            super().entered(debugger, reason, info)
        except Exception as error:
            self.errors.append(str(error))
        finally:
            debugger.state = lib.DEBUGGER_RUNNING

    def report(self):
        return {**super().report(), 'save_events': self.save_events, 'result_events': self.result_events,
                'animation': self.animation}


def language_checks(report, data, index, ledger):
    proof = check_natural(report, data, index)
    font, codec = FontZero(ORIGINAL_ROM.read_bytes()), GameTextCodec(ORIGINAL_ROM.read_bytes())
    story = []
    for v in report['versions']:
        text = visible(bytes.fromhex(v['output_hex']), codec)
        glyphs = [g for g in report['positions'] if g['version'] == v['serial']]
        story.append({'version': v['serial'], 'source': v['source']['master_id'],
                      **check_glyphs(glyphs, text, font)})
    allocations = {a['offset']+0x08000000: a for a in ledger['allocations']}
    pages = []
    for serial, f in enumerate(report['formats']):
        if f['caller'] != '0x0807AE04':
            continue
        source = int(f['source'], 0)
        check(source in allocations and f['payload_limit'] == 999 and f['written_bytes'] <= 999,
              'Unowned or oversized paged message')
        text = visible(bytes.fromhex(f['output_hex']), codec)
        glyphs = [g for g in report['paged_positions'] if g['draw_serial'] == serial]
        pages.append({'format_serial': serial, 'allocation': allocations[source]['id'],
                      **check_glyphs(glyphs, text, font)})
    ui, repeats = check_ui(report)
    return {'story_provenance': proof, 'story': story, 'paged_messages': pages,
            'whole_string_draws': ui, 'duplicate_draws': repeats}


def create_start(data):
    first, _ = names.creation(data, OUT/'setup/create-1', 1)
    initial, _ = names.creation(data, OUT/'setup/create-2', 2, initial_save=first)
    path = OUT/'setup/both-logs.sav'; path.write_bytes(initial)
    old_save, old_output = trace_story_provenance.SAVE, opening.OUT
    try:
        trace_story_provenance.SAVE = path; opening.OUT = OUT/'setup/opening'
        report = opening.natural(data)
        state = (opening.OUT/'natural/final.state').read_bytes()
    finally:
        trace_story_provenance.SAVE, opening.OUT = old_save, old_output
    print('Fresh logs and 46-message opening passed', flush=True)
    return initial, state, report


def adventure(data, build, initial, state):
    replay_path = ROOT/'build/completion/roundtrip/exploration/readers.json'
    replay = load_json(replay_path)['inputs']
    index, _, _ = sources(data, build['ledger'])
    watch = [0x08000000+int(e['offset'], 0) for e in load_json(ROOT/'translations/unowned-text-review.json')['entries']]
    folder = OUT/'adventure'
    with Session(data, folder, initial) as s:
        check(s.core.load_raw_state(state) and s.core.frame_counter == 27606, 'New opening checkpoint differs')
        check(battery_snapshot(s.core) == initial and bytes(s.core.memory[NAME_RAM:NAME_RAM+8]) == EXPECTED_NAME,
              'Checkpoint/save name differs')
        t = RoundtripTrace(s.core, data, index, watch)
        try:
            for i, row in enumerate(replay):
                t.phase = f'input-{i:03d}'
                if row['key'] is not None:
                    k = getattr(s.core, 'KEY_'+row['key']); s.core.set_keys(k); t.frames(row['hold']); s.core.clear_keys(k)
                t.frames(row['released'])
                check(s.core.frame_counter == row['end_frame'], 'Adventure replay timing differs')
                if i in (88, 156, 176) or i >= 177:
                    s.capture(t.phase)
                if i % 40 == 39:
                    print('Adventure replay', i+1, '/', len(replay), flush=True)
            s.capture('saved-title')
            result = t.report(); save(folder/'raw-trace.json', result)
            check(not t.errors and not result['source_reads'], 'Trace error or unresolved Japanese source read')
            check(len(t.result_events) == 1 and len(t.animation) == 17 and
                  all(a['mismatches'] == 0 and a['outside_window_unchanged'] for a in t.animation), 'Natural result animation incomplete')
            check(all(e['name_hex'] == EXPECTED_NAME.hex() for e in t.result_events), 'Result transition changed current name')
            check(any(e['pc'] == '0x80016dc' for e in t.save_events), 'Native records write not reached')
            writes = [e for e in t.save_events if e['pc'] == '0x80027d0']
            check(writes and all(e['name_hex'] == e['record_name_hex'] == EXPECTED_NAME.hex() for e in writes),
                  'Native adventure save truncated the name')
            checks = language_checks(result, data, index, build['ledger'])
            saved = battery_snapshot(s.core)
            profile = bytes(s.core.memory[PROFILE:PROFILE+PROFILE_SIZE])
            check(len(saved) == 65536 and saved != initial and saved[0xE000:0xFFAC] == profile,
                  'Natural save did not write its profile')
            earned = bytes.fromhex(t.result_events[0]['profile_hex'])[20:68]
            check(profile[20:68] == earned and struct.unpack_from('<2H', earned) == (5, 22)
                  and earned[25] == 1 and int.from_bytes(earned[10:13], 'little') == 1,
                  'Saved record differs from the natural She-slime defeat')
            check(saved == (ROOT/'build/completion/roundtrip/exploration/latest.sav').read_bytes(),
                  'Popup wording correction changed the native saved result')
            (folder/'saved.state').write_bytes(bytes(ffi.buffer(s.core.save_raw_state())))
            result.update(rom_sha256=digest(data), initial_save_sha256=digest(initial), initial_state_sha256=digest(state),
                replay_sha256=digest(replay_path.read_bytes()), inputs=replay, checks=checks,
                output_save_sha256=digest(saved), saved_profile_sha256=digest(profile), earned_record_hex=earned.hex(),
                scope='Normal buttons from the fresh native two-Log/opening checkpoint through first-floor defeat, return to the village priest, Pray/save, stop playing and title. No injected inventory, HP, position, event flags or records. This is a completed defeat route, not a dungeon clear.')
            save(folder/'trace.json', result)
        finally:
            t.close()
    check(s.disk_save == saved, 'Closed cartridge file differs from native FLASH')
    (OUT/'earned.sav').write_bytes(s.disk_save)
    print('Native priest save and earned score persisted', flush=True)
    return saved, result


def cold(data, build, saved, earned):
    index, _, _ = sources(data, build['ledger']); folder = OUT/'cold'
    inputs = [('title', 'START', 240), ('down-1', 'DOWN', 30), ('down-2', 'DOWN', 30),
        ('categories', 'A', 240), ('list', 'A', 240), ('detail', 'A', 240),
        ('back-list', 'B', 120), ('back-categories', 'B', 120), ('history-selected', 'DOWN', 30),
        ('history', 'A', 240), ('history-back', 'B', 120), ('title-back', 'B', 120),
        ('slots', 'A', 240), ('load', 'A', 240), ('village', 'A', 600), ('welcome-dismissed', 'A', 300)]
    with Session(data, folder, saved) as s:
        t = RoundtripTrace(s.core, data, index, [])
        try:
            t.frames(600); detail = None
            for phase, key, wait in inputs:
                t.phase = phase; s.press(key, wait, t); screen = s.capture(phase)
                if phase == 'detail':
                    c = s.core
                    check(bytes(c.memory[PROFILE:PROFILE+PROFILE_SIZE]) == saved[0xE000:0xFFAC], 'Cold native profile differs')
                    check(bytes(c.memory[PROFILE+20:PROFILE+68]) == bytes.fromhex(earned), 'Cold score record differs')
                    rawmap = bytes(c.memory[0x02034DDC:0x020355DC])
                    check(not map_errors(rawmap) and rawmap == bytes(c.memory[0x06006000:0x06006800]), 'Cold score map differs')
                    check(bytes(c.memory[0x02035E1C:0x0203977C]) == bytes(c.memory[0x06000040:0x060039A0]), 'Cold score bitmap differs')
                    detail = ink_pixels(c, screen)
                    check(detail['white_ink_pixels'] > 500 and detail['mismatched_white_ink_pixels'] == 0, 'Cold score ink differs')
            result = t.report(); save(folder/'raw-trace.json', result)
            check(not t.errors and detail is not None, 'Cold trace failed')
            check(bytes(s.core.memory[NAME_RAM:NAME_RAM+8]) == EXPECTED_NAME and s.core.memory.u32[0x0200000C] == 0,
                  'Cold load did not preserve Torneko in town')
            loads = [e for e in t.save_events if e['pc'] == '0x800230a']
            check(loads and all(e['record_name_hex'] == EXPECTED_NAME.hex() for e in loads), 'Native saved-name read differs')
            checks = language_checks(result, data, index, build['ledger'])
            strings = [c['text'] for c in checks['whole_string_draws']]
            for expected in ('Records', 'Torneko: High scores', 'Adventure history',
                'Torneko/Mysterious cave 1F', 'Defeated by She-slime', '[Torneko] Barinabo Village', 'HP 15/15 Lv1 Trip 1'):
                check(expected in strings, 'Cold menu/summary did not display: '+expected)
            (folder/'village.state').write_bytes(bytes(ffi.buffer(s.core.save_raw_state())))
            result.update(rom_sha256=digest(data), input_save_sha256=digest(saved), checks=checks, detail_pixels=detail,
                inputs=s.frames_recorded, scope='Fresh core and naturally written save: records/categories/list/detail/history, then native Log 1 load back to the saved village. No save or state edits.')
            save(folder/'trace.json', result)
        finally:
            t.close()
    check(s.disk_save == saved, 'Cold records/load route changed the save file')
    names.reload_name(data, saved, OUT/'cold-log-2', EXPECTED_NAME, slot=2, select_slot=True)
    print('Cold earned record, saved village and untouched Log 2 passed', flush=True)
    return result


def verify():
    mgba.log.silence(); path = b.OUTPUT/'torneko3-inventory-notice-english.gba'; data = path.read_bytes()
    build = load_json(b.OUTPUT/'english-build.json'); check(digest(data) == build['rom_sha256'], 'Combined ROM changed')
    initial, state, intro = create_start(data)
    saved, play = adventure(data, build, initial, state)
    loaded = cold(data, build, saved, play['earned_record_hex'])
    report = {'status': 'native_dungeon_save_roundtrip_passed', 'rom': str(path.relative_to(ROOT)),
        'rom_sha256': digest(data), 'source_sha256': digest(ORIGINAL_ROM.read_bytes()),
        'harness_sha256': digest(Path(__file__).read_bytes()), 'initial_save_sha256': digest(initial),
        'output_save_sha256': digest(saved), 'save_bytes': len(saved), 'name': 'Torneko', 'logs_checked': [1, 2],
        'opening_messages': intro['proof']['buffer_versions'], 'adventure_messages': len(play['checks']['story']),
        'adventure_paged_messages': len(play['checks']['paged_messages']),
        'adventure_whole_draws': len(play['checks']['whole_string_draws']),
        'cold_whole_draws': len(loaded['checks']['whole_string_draws']), 'cold_result_pixels': loaded['detail_pixels'],
        'earned_record_hex': play['earned_record_hex'], 'unowned_japanese_reads': 0,
        'reports': {str(p.relative_to(OUT)): digest(p.read_bytes()) for p in (OUT/'adventure/trace.json', OUT/'cold/trace.json', OUT/'cold-log-2/trace.json')},
        'scope': 'Fresh native keyboard creation of two seven-letter logs, normal opening and first-floor defeat, priest save, fresh-core earned ranking/history display and Log 1 town reload, then independent cold Log 2 opening. No injected game state after the native opening checkpoint. Dungeon clearing, later outcomes and graphics remain separate.'}
    save(OUT.parent/'component-checkpoint.json', report)
    print(report['status'], flush=True)


if __name__ == '__main__':
    verify()
