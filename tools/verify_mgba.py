"""Check the installed mGBA bindings using a temporary copy of a supplied ROM."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tempfile

import mgba.core
import mgba.image
import mgba.log
from mgba._pylib import ffi, lib


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def run_frames(core, count):
    before = core.frame_counter
    for _ in range(count):
        core.run_frame()
    require(core.frame_counter - before == count, "Frame advancement mismatch")


def verify_breakpoint(core, rom_bytes):
    """Use the release's native API; its high-level breakpoint helper is stale."""
    instruction = int.from_bytes(rom_bytes[:4], "little")
    require(instruction >> 24 == 0xEA, "Expected a GBA entry-point ARM branch")
    offset = instruction & 0xFFFFFF
    if offset & 0x800000:
        offset -= 0x1000000
    target = 0x08000008 + offset * 4
    hits = []

    @ffi.callback("void(struct mDebugger*, enum mDebuggerEntryReason, struct mDebuggerEntryInfo*)")
    def entered(debugger, reason, info):
        if reason == lib.DEBUGGER_ENTER_BREAKPOINT and info != ffi.NULL:
            hits.append(int(info.address))
        debugger.state = lib.DEBUGGER_RUNNING

    debugger = ffi.new("struct mDebugger*")
    debugger.type = lib.DEBUGGER_CUSTOM
    debugger.entered = entered
    lib.mDebuggerAttach(debugger, core._core)
    try:
        point = ffi.new("struct mBreakpoint*")
        point.address = target
        point.segment = -1
        point.type = lib.BREAKPOINT_HARDWARE
        point_id = debugger.platform.setBreakpoint(debugger.platform, point)
        require(point_id >= 0, "Could not install execution breakpoint")
        for _ in range(100000):
            lib.mDebuggerRun(debugger)
            if hits:
                break
        require(hits == [target], f"Execution breakpoint did not fire: {hits}")
        require(debugger.platform.clearBreakpoint(debugger.platform, point_id), "Could not clear breakpoint")
    finally:
        core._core.detachDebugger(core._core)
    return f"0x{target:08X}"


def verify(rom_path, output):
    mgba.log.silence()
    original = rom_path.read_bytes()
    rom_hash = hashlib.sha256(original).hexdigest()
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="mgba-check-", dir=output) as scratch:
        copied_rom = Path(scratch) / "base.gba"
        shutil.copyfile(rom_path, copied_rom)
        core = mgba.core.load_path(str(copied_rom))
        require(core is not None, "Could not load ROM")
        screen = mgba.image.Image(*core.desired_video_dimensions())
        core.set_video_buffer(screen)
        core.reset()
        breakpoint = verify_breakpoint(core, original)
        core.reset()

        # Exercise RAM access widths before executing any more game instructions.
        address = 0x02000000
        saved_word = core.memory.u32[address]
        for width, value in ((8, 0xA5), (16, 0xBEEF), (32, 0x12345678)):
            view = getattr(core.memory, f"u{width}")
            view[address] = value
            require(view[address] == value, f"{width}-bit memory access mismatch")
        core.memory.u32[address] = saved_word
        run_frames(core, 600)
        image = screen.to_pil().convert("RGB")
        require(image.size == (240, 160), "Unexpected screen dimensions")
        require(len(image.getcolors(240 * 160)) > 1, "Framebuffer is blank")
        image.save(output / "mgba-boot.png")

        snapshot = core.save_raw_state()
        require(snapshot is not None, "Could not save raw state")
        (output / "mgba-core.state").write_bytes(bytes(ffi.buffer(snapshot)))
        # Battery-save data is a separate part of the fixture.
        save_pointer = ffi.new("void**")
        save_size = core._core.savedataClone(core._core, save_pointer)
        save_data = bytes(ffi.buffer(save_pointer[0], save_size)) if save_size else b""
        if save_pointer[0] != ffi.NULL:
            lib.free(save_pointer[0])
        (output / "mgba-battery.sav").write_bytes(save_data)

        def replay():
            core.set_keys(core.KEY_A)
            require(core._core.getKeys(core._core) == 1 << core.KEY_A, "Button press failed")
            run_frames(core, 3)
            core.clear_keys(core.KEY_A)
            require(core._core.getKeys(core._core) == 0, "Button release failed")
            run_frames(core, 60)
            return (
                screen.to_pil().convert("RGB").tobytes(),
                bytes(core.memory[0x02000000:0x02040000]),
                bytes(core.memory[0x03000000:0x03008000]),
                core.frame_counter,
            )

        first = replay()
        require(core.load_raw_state(snapshot), "Could not restore raw state")
        if save_data:
            require(core._core.savedataRestore(core._core, save_data, len(save_data), False),
                    "Could not restore battery-save data")
        second = replay()
        require(first == second, "State replay changed pixels, RAM, or frame count")
        screen.to_pil().convert("RGB").save(output / "mgba-replay.png")
        report = {
            "rom_sha256": rom_hash,
            "rom_size": len(original),
            "binding_path": mgba.core.__file__,
            "screen_size": list(image.size),
            "boot_frames": 600,
            "replay_frames": 63,
            "execution_breakpoint": breakpoint,
            "memory_access_widths": [8, 16, 32],
            "raw_state_bytes": len(snapshot),
            "battery_save_bytes": len(save_data),
            "repeatable_pixels_and_ram": True,
            "bios": "mGBA built-in BIOS; no external BIOS loaded",
        }
        # Release the native core while its temporary cartridge file still exists.
        ffi.release(core._core)
    require(hashlib.sha256(rom_path.read_bytes()).hexdigest() == rom_hash, "Original ROM changed")
    (output / "mgba-report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rom", type=Path)
    parser.add_argument("--output", type=Path, default=Path(".tools/validation"))
    args = parser.parse_args()
    verify(args.rom.resolve(), args.output.resolve())
