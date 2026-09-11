"""Guard native species-copy buffers and disguised-monster item formatters."""

import json
from pathlib import Path

import mgba.log
from mgba._pylib import ffi
from tools.build_first_label import ORIGINAL_ROM, ROOT, digest
from tools.verify_expansion import Session
from tools.verify_first_label import require
from tools.verify_items import install_item, write_json

OUTPUT = ROOT / "build/enemy-items/verification"


def native_call(session, state, function, row, disguised_item=False):
    core = session.core
    require(core.load_raw_state(state), "Cannot restore guarded-call fixture")
    cpu = ffi.cast("struct ARMCore*", core._core.cpu)
    record, stack = 0x0203F000, 0x03007E00
    if disguised_item:
        destination, capacity = 0x0203F100, 100
        install_item(core, record, row)
        # This specific reveal mask selects Cannibox, species row 66. Other
        # reveal states are not inferred from the generic 'Mimic' category.
        core.memory.u32[record] |= 0x50000
    else:
        destination, capacity = 0x0203F200, 30
        for address in range(record, record + 0x150):
            core.memory.u8[address] = 0
        core.memory.u16[record + 8] = row
        core.memory.u8[record + 0x137] = 1
    for address in range(destination - 8, destination + capacity + 8):
        core.memory.u8[address] = 0xA5
    core.memory.u32[stack] = 0
    registers = {"cpsr": 0xFF, "sp": stack, "r0": row if function == 0x08032D6C else record,
                 "r1": destination, "r2": 0, "r3": 0, "lr": 0x08000001, "pc": function}
    for name, value in registers.items():
        require(core._core.writeRegister(core._core, name.encode(), ffi.new("uint32_t*", value)), "Register setup failed")
    reads = []
    for steps in range(100000):
        thumb = bool(cpu.cpsr.packed & 0x20)
        pc = (int(cpu.gprs[15]) & 0xFFFFFFFF) - (2 if thumb else 4)
        if pc == 0x08000000:
            break
        if thumb:
            instruction = core.memory.u16[pc]
            # Thumb LDR (word, immediate): observe only actual monster-table
            # loads; this does not alter or skip any original instruction.
            if instruction & 0xF800 == 0x6800:
                address = (int(cpu.gprs[(instruction >> 3) & 7]) & 0xFFFFFFFF) + ((instruction >> 6) & 31) * 4
                if 0x08192568 <= address < 0x08192888:
                    reads.append({"pc": hex(pc), "word": hex(address), "target": hex(core.memory.u32[address])})
        core.step()
    else:
        raise RuntimeError(f"Native helper did not return: {function:08X}/{row}")
    raw = bytes(core.memory[destination:destination + capacity])
    require(b"\0" in raw, "Native helper did not terminate within its buffer")
    raw = raw.split(b"\0", 1)[0] + b"\0"
    require(bytes(core.memory[destination - 8:destination]) == b"\xA5" * 8 and
            bytes(core.memory[destination + capacity:destination + capacity + 8]) == b"\xA5" * 8,
            "Native helper overwrote its destination guards")
    if reads:
        source = core.memory.u32[int(reads[-1]["word"], 16)]
        expected = bytes(core.memory[source:source + 100]).split(b"\0", 1)[0]
        require(expected in raw if disguised_item else raw == expected + b"\0", "Native helper truncated or replaced the selected name")
    require(reads or function == 0x08032D6C and row == 0, "Unexpected helper path without a species-table read")
    return {"function": hex(function), "row": row, "raw_hex": raw.hex(), "reads": reads,
            "guards_intact": True, "bytes": len(raw), "capacity": capacity, "steps": steps}


def verify():
    mgba.log.silence()
    state_path = OUTPUT / "save/world.state"
    state = state_path.read_bytes()
    for language in ("english", "japanese", "baseline"):
        rom = OUTPUT / "baseline.gba" if language == "baseline" else OUTPUT.parent / f"torneko3-enemies-items-{language}.gba"
        output, data = OUTPUT / f"{language}-enemy-guards", rom.read_bytes()
        with Session(data, output) as session:
            cases = [native_call(session, state, function, row)
                     for function in (0x08032D6C, 0x08032CA4) for row in range(200)]
            disguised = [native_call(session, state, 0x08080A5C, item, True)
                         for item in (1, 58, 64, 115, 128, 133, 190, 247, 273, 304, 341)]
        write_json(output / "verification.json", {"rom_sha256": digest(data),
            "source_sha256": digest(ORIGINAL_ROM.read_bytes()), "fixture_state_sha256": digest(state),
            "cases": cases, "mimics": disguised,
            "scope": "Controlled 30-byte name-copy calls and 100-byte revealed-Cannibox item formatting. Other live actor/reveal conditions remain gameplay coverage."})
        print(f"{language}: {len(cases)} name copies and {len(disguised)} disguised-item calls passed", flush=True)


if __name__ == "__main__":
    verify()
