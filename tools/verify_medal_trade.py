"""Native trading label and narrow secondary-action publication checks."""
from pathlib import Path
import mgba.log
from tools import build_medal_trade as b
from tools import verify_dungeon_interface as ui, verify_ally_services as ally
from tools.verify_core_gameplay import command_ink_check
from tools.translation_pipeline import FontZero, check
from tools.prose_review import save
from tools.verify_expansion import Session

FIXTURES = (ally.STATE, ui.STATE)


def run(data, output=None):
    mgba.log.silence()
    output = output or b.OUTPUT/'verification'
    font = FontZero(b.ORIGINAL_ROM.read_bytes())
    cases = []
    with Session(data, output) as s:
        for name, word, expected in [('medal', 0x63A3C, 'Trade'), ('casino', 0x77AD8, 'Trade'),
                                     ('take-out', 0x75760, 'Take out'), ('withdraw', 0x7392C, 'Withdraw')]:
            trading = name in ('medal', 'casino')
            check(s.core.load_raw_state((ally.STATE if trading else ui.STATE).read_bytes()), 'Restore fixture')
            source = s.core.memory.u32[0x08000000+word] + (11*12 if name == 'take-out' else 0)
            t = ui.InterfaceTrace(s.core)
            try:
                if trading:
                    check(bytes(s.core.memory[source:source+6]) == b'Trade\0', name+' action is not Trade')
                    s.core.memory.u32[0x030076E8] = source
                    ui.native_step(s,t,0x08076AA2,[],stop=0x08076ADC,overrides={0x08076AA2:{'sp':0x03007000}})
                else:
                    ui.install_item(s.core, 0x0200A480, 247)
                    s.core.memory.u32[0x02009110] = source
                    ui.native_step(s,t,0x080755C0,[0,1,0x0200A480,0,16])
                checks = []
                texts = []
                for d in t.payloads:
                    raw = bytes.fromhex(d['raw_hex']).split(b'\0')[0]
                    if raw.startswith(b'\x03\x05'): raw = raw[3:]
                    text = raw.decode('ascii')
                    texts.append(text)
                    gs = [g for g in t.positions if g['draw_serial'] == d['serial']]
                    checks.append(command_ink_check(gs,text,font))
                check(texts[0] == expected and 'Info' in texts, 'Wrong action sequence')
                if trading: check(texts == ['Trade','Info'], 'Trading actions differ')
                check(not t.errors, str(t.errors))
                s.frames(2); s.capture(name)
                cases.append(dict(id=name,source=hex(source),texts=texts,checks=checks,glyphs=t.positions))
            finally: t.close()
    result = dict(rom_sha256=b.digest(data), harness_sha256=b.digest(Path(__file__).read_bytes()),
        fixture_hashes={str(p):b.digest(p.read_bytes()) for p in FIXTURES}, cases=cases,
        scope='Native bounded popup readers; not natural medal transaction playback')
    save(output/'report.json',result)
    print('Medal/casino Trade and narrow Take out/Withdraw checks passed',flush=True)
    return result


if __name__ == '__main__':
    run(b.ROM.read_bytes())
