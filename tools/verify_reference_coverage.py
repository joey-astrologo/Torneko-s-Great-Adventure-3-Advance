"""Check expected English in duplicate menus, startup-cache readers and post-game replay."""
from pathlib import Path
import struct
import mgba.log
from tools import build_reference_coverage as b
from tools import verify_dungeon_interface as ui, verify_ally_services as service
from tools import verify_core_gameplay as old, verify_tutorial_gameplay as queue
from tools.verify_rendering_fixes import FixTrace
from tools.game_text import GameTextCodec
from tools.translation_pipeline import FontZero, check
from tools.verify_expansion import Session
from tools.prose_review import save

POSTGAME = b.ROOT/'saves/torneko-3-english-post-game.sav'
SAVE_HASH = '98489ca7e1286b83a189ec430f25e2f8b1008560ae52fd5241a2fe01fff5d7e8'
FIXTURES = (service.STATE, old.STATE, POSTGAME)
# Expectations independent of the ROM output being examined.
MENUS = {
    0xD9340: ['Talk', 'Kaclang', 'Cancel'],
    0xD93C8: ['Talk', 'Call allies', 'Cancel'],
    0xD9580: ['Talk', 'Warp somewhere', 'Cancel'],
    0xD9638: ['Spells', 'Talk', 'Cancel'],
    0xD9680: ['Heal', 'Bang', 'Squelch', 'Cancel'],
    0x87231C: ['Buy', 'Sell', 'Cancel'],
    0xC3E498: ['Withdraw', 'Deposit', 'Instructions', 'Cancel'],
    0xC3F158: ['Deposit', 'Withdraw', 'Cancel'],
    0xC40260: ['Pray', 'Hear guidance', 'Lift curse', 'Cancel'],
    0xC402F4: ['Entrants', 'Place a bet', 'Instructions', 'Cancel'],
    0xC40358: ['Arena monsters', 'Registered monsters', 'Monster lodge', 'Cancel'],
    0xC403E0: ['View next opponents', 'Battle', 'Arena instructions', 'Cancel'],
    0xC4044C: ['Yes', 'No'],
    0xC414B8: ['Registered battles', 'Enter password', 'About battles', 'Cancel'],
    0xC41530: ['Battle', 'View opponents', 'Erase all', 'Cancel'],
    0xC4158C: ["Tipper's allies", 'Registered monsters', 'Cancel battle'],
    0xC4CD0C: ['Yes', 'No'],
    0xC4CD40: ['Story mode', 'Extra mode', 'Barinabo Challenge mode', 'Help', 'Cancel'],
    0xC4CDD8: ['Story mode', 'Extra mode', '???', 'Help', 'Cancel'],
}
INPUTS = [('START',120),('DOWN',20),('A',120),('A',120),('R',30),('A',180),('R',30),('A',180)]


def pointer_errors(data):
    errors = []
    for word, alias, source, english in b.REFERENCES:
        target = struct.unpack_from('<I', data, word)[0]-0x08000000
        expected = english.encode()+b'\0'
        if data[target:target+len(expected)] != expected:
            errors.append(f'{word:08X}: expected {english!r}')
        if data[word:word+4] != data[alias:alias+4]:
            errors.append(f'{word:08X}: alias differs')
    return errors


def run(data=None, output=None):
    mgba.log.silence()
    data = b.ROM.read_bytes() if data is None else data
    output = b.OUTPUT/'verification' if output is None else Path(output)
    original = b.ORIGINAL_ROM.read_bytes();font = FontZero(original);codec = GameTextCodec(original)
    check(not pointer_errors(data), str(pointer_errors(data)))
    # Known-bad baseline must fail independent English expectations.
    rejected = pointer_errors(b.BASELINE.read_bytes())
    check(len(rejected) == 30, 'Regression did not reject all 15 old references')
    menus = [];cases = []
    with Session(data, output/'native') as s:
        s.frames(5)
        caches = []
        for a,z in ((0xCAFEC0,0xCAFEE8),(0xCB0094,0xCB0098)):
            ram = 0x02000000+a-0xCAFE88
            raw = bytes(s.core.memory[ram:ram+z-a])
            check(raw == data[a:z], 'Cold-start cache differs from ROM')
            caches.append((ram,raw))
        for base,expected in MENUS.items():
            for enabled in ((0,1) if base in (0xC4CD40,0xC4CDD8) else (0,)):
                check(s.core.load_raw_state(service.STATE.read_bytes()), 'Menu state restore')
                s.core.memory.u32[0x02002FE4] = enabled
                for row in range(len(expected)+1):
                    at = base+row*12
                    check(data[at+4:at+12] == original[at+4:at+12], 'Menu metadata changed')
                check(data[base+len(expected)*12:base+len(expected)*12+4] == b'\0'*4, 'Menu terminator changed')
                trace = FixTrace(s.core)
                try:
                    ui.native_step(s,trace,0x0807B294,[base+0x08000000,0,0,0],stop=0x0807B3B6)
                    rows = [old.visible(bytes.fromhex(d['raw_hex']),codec) for d in trace.payloads]
                    check(rows == expected, f'Menu {base:08X} language differs: {rows!r}')
                    menus.append(dict(table=hex(base),enabled=enabled,rows=rows))
                finally:trace.close()
        for n,(word,alias,source,english) in enumerate(b.REFERENCES[4:]):
            check(s.core.load_raw_state(old.STATE.read_bytes()), 'Cache-reader state restore')
            for ram,raw in caches:old.write_bytes(s.core,ram,raw)
            values = old.slots(s.core,font,'normal')
            index = n%5 if n<10 else 0
            s.core.memory.u16[0x02005F32] = index
            entry,stop = (0x0800AC50,0x0800AC5E) if n<5 else (0x0800AC7C,0x0800AC8A) if n<10 else (0x08047898,0x080478A2)
            trace = FixTrace(s.core)
            try:
                result = ui.native_step(s,trace,entry,[],stop=stop,overrides={entry:{'r10':0}} if n==10 else None)
                target = struct.unpack_from('<I',data,word)[0]
                check(result['return_r0'] == target, 'Native cache selector returned wrong source')
                raw = old.guarded_format(s,trace,target)
                expected = (english.replace('$i0',values['$i0'])).encode()+b'\0'
                # Existing fit-aware wrappers may join an approved line break.
                check(raw in (expected, expected.replace(b'\n', b' ')),
                      f'Cache reader {word:08X} language differs: {raw!r}')
                queue.prepare_queue(s,trace)
                queued = queue.enqueue(s,trace,target,raw)
                cases.append(dict(word=hex(word),index=index,source=hex(target),formatted_hex=raw.hex(),queue=queued))
            finally:trace.close()
    save_bytes = POSTGAME.read_bytes();check(b.digest(save_bytes) == SAVE_HASH, 'Post-game fixture changed')
    with Session(data, output/'postgame', initial_save=save_bytes) as s:
        s.frames(600)
        for key,frames in INPUTS:s.press(key,frames)
        trace = FixTrace(s.core)
        try:
            s.press('A',180,trace)
            rows = [old.visible(bytes.fromhex(d['raw_hex']),codec) for d in trace.payloads]
            check(rows == MENUS[0xC4CD40], f'Natural post-game menu language differs: {rows!r}')
            s.capture('postgame-mode-menu')
        finally:trace.close()
    check(POSTGAME.read_bytes() == save_bytes, 'User save changed')
    report = dict(rom_sha256=b.digest(data), source_sha256=b.digest(original),
        fixtures={str(p.resolve().relative_to(b.ROOT)):b.digest(p.read_bytes()) for p in FIXTURES},
        menus=menus, cache_cases=cases, cold_cache_hex=[dict(ram=hex(ram),raw_hex=raw.hex()) for ram,raw in caches],
        postgame=dict(save_sha256=SAVE_HASH,initial_frames=600,inputs=INPUTS+[('A',180)],rows=rows,source_save_unchanged=True),
        baseline_rejected=rejected,
        scope='19 enumerated menu tables, both mode flags, 11 native cache selectors/queue paths, and one natural post-game mode-menu replay; not full-game reachability')
    save(output/'report.json',report)
    print(f'Reference coverage: {len(menus)} menu cases, {len(cases)} cache readers, post-game replay passed',flush=True)
    return report

if __name__ == '__main__':run()
