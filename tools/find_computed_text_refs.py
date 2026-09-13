"""Conservative straight-line Thumb constant leads, not verified text ownership.

Scan halfword positions in the main code envelope, seed cartridge-valued
PC-relative loads, and follow a limited set of constant operations. A hit must
be independently disassembled and checked through its consumer before use.
No branch following, call-return inference, variable indexing or RAM analysis.
"""
import json
import struct
from tools.build_first_label import ROOT, ORIGINAL_ROM, digest
from tools.translation_pipeline import load_json, atomic_write

OUTPUT = ROOT/'build/completion/computed-text-review.json'


def scan():
    data = ORIGINAL_ROM.read_bytes()
    queue = load_json(ROOT/'build/completion/current-text-review.json')
    # Keep the input schema explicit; these are unresolved extraction starts.
    targets = {0x08000000+int(e['offset'], 0): e for e in queue['entries']}
    hits, seeds = [], 0
    def word(at):
        return struct.unpack_from('<I', data, at)[0]
    for start in range(0xC0, 0x9A800, 2):
        instruction = struct.unpack_from('<H', data, start)[0]
        if instruction & 0xF800 != 0x4800:
            continue
        literal = ((start+4)&~3)+(instruction&255)*4
        value = word(literal)
        if not any(abs(value-target) <= 0x10000 for target in targets):
            continue
        seeds += 1
        regs = [None]*16
        trail = []
        for pc in range(start, min(start+96, 0x9A800), 2):
            op = struct.unpack_from('<H', data, pc)[0]
            action = ''
            if op & 0xF800 == 0x4800:
                dst = (op>>8)&7; at = ((pc+4)&~3)+(op&255)*4
                regs[dst] = word(at); action = f'ldr r{dst},[0x{at+0x08000000:08x}]'
            elif op & 0xF800 == 0x2000:
                dst = (op>>8)&7; regs[dst] = op&255; action = f'mov r{dst},#{op&255}'
            elif op & 0xF800 in (0x3000, 0x3800):
                dst = (op>>8)&7; delta = (op&255)*(1 if op&0xF800 == 0x3000 else -1)
                if regs[dst] is not None: regs[dst] = (regs[dst]+delta)&0xFFFFFFFF
                action = f'add r{dst},#{delta}'
            elif op & 0xF800 == 0x1800:
                dst, src = op&7, (op>>3)&7
                rhs = (op>>6)&7 if op&0x400 else regs[(op>>6)&7]
                regs[dst] = None if regs[src] is None or rhs is None else (regs[src]+(-rhs if op&0x200 else rhs))&0xFFFFFFFF
                action = f'add/sub r{dst},r{src},operand'
            elif op & 0xFF00 == 0x4600:
                dst, src = (op&7)|((op>>4)&8), (op>>3)&15
                if dst == 15 or src == 15: break
                regs[dst] = regs[src]; action = f'mov r{dst},r{src}'
            elif op & 0xFF00 == 0x4400:
                dst, src = (op&7)|((op>>4)&8), (op>>3)&15
                if dst == 15 or src == 15: break
                regs[dst] = None if regs[dst] is None or regs[src] is None else (regs[dst]+regs[src])&0xFFFFFFFF
                action = f'add r{dst},r{src}'
            elif op & 0xE000 == 0 and op & 0x1800 != 0x1800:
                dst, src, amount, kind = op&7, (op>>3)&7, (op>>6)&31, (op>>11)&3
                v = regs[src]
                if v is None: regs[dst] = None
                elif kind == 0: regs[dst] = (v<<amount)&0xFFFFFFFF
                elif kind == 1: regs[dst] = v>>(amount or 32)
                else: regs[dst] = ((v if v < 0x80000000 else v-0x100000000)>>(amount or 32))&0xFFFFFFFF
                action = f'shift r{dst},r{src}'
            elif op & 0xF800 == 0x2800 or op & 0xFFC0 == 0x4280 or op & 0xFF00 == 0x4500:
                continue  # Compare does not change the tracked registers.
            elif op & 0xFE00 == 0xB400:
                continue  # PUSH does not change r0-r14; stack values are not tracked.
            elif op & 0xF800 in (0x6000, 0x7000, 0x8000, 0x9000):
                continue  # Store; no writable-memory loads are propagated.
            elif op & 0xF800 in (0x6800, 0x7800, 0x8800, 0x9800):
                dst = (op>>8)&7 if op&0xF800 == 0x9800 else op&7
                regs[dst] = None; action = f'unknown memory load r{dst}'
            else:
                break  # Includes branches, calls, POP and unsupported ALU forms.
            trail.append({'pc': hex(pc+0x08000000), 'halfword': hex(op), 'operation': action})
            if pc != start and regs[dst] in targets:
                target = regs[dst]
                hits.append({'source_id': targets[target]['master_id'], 'target': hex(target),
                    'seed_pc': hex(start+0x08000000), 'seed_literal': hex(literal+0x08000000),
                    'seed_value': hex(value), 'register': dst, 'path': list(trail)})
    report = {'source_sha256': digest(data), 'harness_sha256': digest(__import__('pathlib').Path(__file__).read_bytes()),
        'input_sha256': digest((ROOT/'build/completion/current-text-review.json').read_bytes()),
        'code_envelope': ['0x080000c0', '0x0809a800'], 'targets': len(targets), 'literal_seeds': seeds,
        'hits': hits, 'scope': 'Static leads only. Halfword positions are not established instruction boundaries. At most 48 straight-line instructions after each nearby cartridge-valued literal; unsupported instructions and all control transfers stop analysis. A negative result does not prove unused text.'}
    atomic_write(OUTPUT, (json.dumps(report, ensure_ascii=False, indent=2)+'\n').encode())
    print(len(hits), 'static computed-address leads from', seeds, 'literal seeds', flush=True)


if __name__ == '__main__':
    scan()
