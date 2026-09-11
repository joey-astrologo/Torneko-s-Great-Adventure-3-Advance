"""Trace and verify the first label patch through the original game's renderer."""

import argparse
import json
from pathlib import Path
import struct
import tempfile

import mgba.core
import mgba.image
import mgba.log
from mgba._pylib import ffi, lib
from PIL import ImageChops

from tools.build_first_label import ORIGINAL_ROM, OUTPUT, digest, load_manifest, patch_rom

BOOT_FRAMES = 600
START_HOLD_FRAMES = 3
MENU_WAIT_FRAMES = 240
LABEL_BOX = (28, 15, 80, 28)


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def battery_snapshot(core):
    pointer = ffi.new("void**")
    size = core._core.savedataClone(core._core, pointer)
    try:
        return bytes(ffi.buffer(pointer[0], size)) if size else b""
    finally:
        if pointer[0] != ffi.NULL:
            lib.free(pointer[0])


class TextTrace:
    """Keep CFFI callback objects alive and report callback failures to Python."""

    def __init__(self, core, watch_addresses=(0x08C78280, 0x08C782D8)):
        self.core = core
        self.cpu = ffi.cast("struct ARMCore*", core._core.cpu)
        self.reads, self.glyphs, self.errors = [], [], []
        self.callback = ffi.callback(
            "void(struct mDebugger*, enum mDebuggerEntryReason, struct mDebuggerEntryInfo*)",
            self.entered,
        )
        self.debugger = ffi.new("struct mDebugger*")
        self.debugger.type = lib.DEBUGGER_CUSTOM
        self.debugger.entered = self.callback
        lib.mDebuggerAttach(self.debugger, core._core)
        try:
            for address in watch_addresses:
                point = ffi.new("struct mWatchpoint*")
                point.address, point.segment, point.type = address, -1, lib.WATCHPOINT_READ
                require(self.debugger.platform.setWatchpoint(self.debugger.platform, point) >= 0,
                        "Could not install text read watchpoint")
            point = ffi.new("struct mBreakpoint*")
            point.address, point.segment, point.type = 0x0808BC78, -1, lib.BREAKPOINT_HARDWARE
            require(self.debugger.platform.setBreakpoint(self.debugger.platform, point) >= 0,
                    "Could not install glyph lookup breakpoint")
        except Exception:
            self.close()
            raise

    def entered(self, debugger, reason, info):
        try:
            if info == ffi.NULL:
                return
            require(len(self.reads) + len(self.glyphs) < 1000, "Unexpectedly large text trace")
            if reason == lib.DEBUGGER_ENTER_WATCHPOINT:
                thumb = bool(self.cpu.cpsr.packed & 0x20)
                self.reads.append({
                    "address": f"0x{info.address:08X}",
                    "instruction": f"0x{(self.cpu.gprs[15] - (4 if thumb else 8)) & 0xFFFFFFFF:08X}",
                    "frame": self.core.frame_counter,
                })
            elif reason == lib.DEBUGGER_ENTER_BREAKPOINT:
                address = self.cpu.gprs[0] & 0xFFFFFFFF
                data = bytes(self.core.memory[address:address + 12])
                bitmap, code, advance = struct.unpack_from("<IHh", data)
                font = self.core.memory.u32[0x020398F8]
                self.glyphs.append({
                    "code": code, "advance": advance,
                    "x": self.cpu.gprs[6], "y": self.cpu.gprs[8],
                    "descriptor": f"0x{address:08X}", "bitmap": f"0x{bitmap:08X}",
                    "font": font,
                    "glyph_table": f"0x{self.core.memory.u32[0x020398EC + 4 * font]:08X}",
                    "frame": self.core.frame_counter,
                })
        except Exception as error:
            self.errors.append(str(error))
        finally:
            debugger.state = lib.DEBUGGER_RUNNING

    def frames(self, count):
        before = self.core.frame_counter
        for _ in range(count):
            lib.mDebuggerRunFrame(self.debugger)
        require(not self.errors, f"Debugger callback failed: {self.errors}")
        require(self.core.frame_counter - before == count, "Unexpected frame count")

    def close(self):
        self.core._core.detachDebugger(self.core._core)


def capture(rom_data, output):
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="emulator-", dir=output) as temporary:
        rom = Path(temporary) / "game.gba"
        rom.write_bytes(rom_data)
        core = mgba.core.load_path(str(rom))
        require(core is not None, "Could not load ROM")
        try:
            screen = mgba.image.Image(*core.desired_video_dimensions())
            core.set_video_buffer(screen)
            core.reset()
            for _ in range(BOOT_FRAMES):
                core.run_frame()
            title_state = core.save_raw_state()
            require(title_state is not None, "Could not save title state")
            title_battery = battery_snapshot(core)
            (output / "title.state").write_bytes(bytes(ffi.buffer(title_state)))
            (output / "title.sav").write_bytes(title_battery)
            screen.to_pil().convert("RGB").save(output / "title.png")
            trace = TextTrace(core)
            try:
                def route():
                    trace.reads.clear()
                    trace.glyphs.clear()
                    core.set_keys(core.KEY_START)
                    trace.frames(START_HOLD_FRAMES)
                    core.clear_keys(core.KEY_START)
                    trace.frames(MENU_WAIT_FRAMES)
                    return (
                        screen.to_pil().convert("RGB").tobytes(),
                        bytes(core.memory[0x02000000:0x02040000]),
                        bytes(core.memory[0x03000000:0x03008000]),
                        core.frame_counter,
                    )

                first = route()
                first_trace = (list(trace.reads), list(trace.glyphs))
                image = screen.to_pil().convert("RGB")
                image.save(output / "menu.png")
                state = core.save_raw_state()
                require(state is not None, "Could not save menu state")
                (output / "menu.state").write_bytes(bytes(ffi.buffer(state)))
                (output / "menu.sav").write_bytes(battery_snapshot(core))
                require(core.load_raw_state(title_state), "Could not restore title state")
                if title_battery:
                    require(core._core.savedataRestore(core._core, title_battery, len(title_battery), False),
                            "Could not restore title battery save")
                require(first == route(), "Restoring the title state changed the menu pixels, RAM, or frame count")
                require(first_trace == (trace.reads, trace.glyphs), "Restored route changed the rendering trace")
                reads, glyphs = first_trace
            finally:
                trace.close()
            core.set_keys(core.KEY_A)
            for _ in range(3):
                core.run_frame()
            core.clear_keys(core.KEY_A)
            for _ in range(120):
                core.run_frame()
            selected = screen.to_pil().convert("RGB")
            selected.save(output / "selected.png")
            report = {
                "rom_sha256": digest(rom_data),
                "emulator": "mGBA 0.10.5 upstream bindings; see docs/TOOLING.md for source pin and build patch",
                "bios": "mGBA built-in BIOS",
                "initial_save": "Fresh temporary cartridge; no existing save loaded",
                "route": [{"frames": BOOT_FRAMES, "keys": []},
                          {"frames": START_HOLD_FRAMES, "keys": ["START"]},
                          {"frames": MENU_WAIT_FRAMES, "keys": []}],
                "menu_frame": first[3],
                "menu_rgb_sha256": digest(image.tobytes()),
                "label_rgb_sha256": digest(image.crop(LABEL_BOX).tobytes()),
                "state_replay_identical": True,
                "reads": reads, "glyphs": glyphs,
            }
            (output / "capture.json").write_text(json.dumps(report, indent=2) + "\n")
            return image, selected, report
        finally:
            ffi.release(core._core)


def verify(rom=ORIGINAL_ROM, output=OUTPUT):
    mgba.log.silence()
    rom, output = Path(rom).resolve(), Path(output).resolve()
    original = rom.read_bytes()
    manifest = load_manifest()
    expected, _ = patch_rom(original, manifest)
    patched_path = output / "torneko3-title-begin.gba"
    patched = patched_path.read_bytes()
    require(patched == expected, "Built ROM does not match the current proof manifest")
    base_image, base_selected, base_report = capture(original, output / "japanese")
    image, selected, report = capture(patched, output / "patched")
    difference = ImageChops.difference(base_image, image)
    bounds = difference.getbbox()
    require(bounds is not None, "The patched label did not change any pixels")
    left, top, right, bottom = LABEL_BOX
    require(left <= bounds[0] < bounds[2] <= right and top <= bounds[1] < bounds[3] <= bottom,
            f"Pixels changed outside the first menu label: {bounds}")
    require(base_selected.tobytes() != base_image.tobytes(), "Selecting the label did not open a submenu")
    # The game keeps the original menu visible beside the save-slot submenu.
    require(ImageChops.difference(base_selected, selected).tobytes() == difference.tobytes(),
            "The save-slot submenu differs beyond the retained first menu label")
    expected_reads = [("0x08C78280", "0x08084CD8"), ("0x08C782D8", "0x0808C732")]
    for captured in (base_report, report):
        require([(r["address"], r["instruction"]) for r in captured["reads"]] == expected_reads,
                "The expected menu pointer and character decoder were not observed")
    first_line = [glyph for glyph in report["glyphs"] if glyph["y"] == 0]
    require([glyph["code"] for glyph in first_line] == list(manifest["english"].encode("ascii")),
            "The glyph renderer did not receive the expected English label")
    golden = json.loads((Path(__file__).resolve().parents[1] / "tests/fixtures/title_begin.json").read_text())
    require(tuple(golden["crop"]) == LABEL_BOX, "Golden image crop configuration differs")
    require(report["label_rgb_sha256"] == golden["label_rgb_sha256"],
            "Rendered label differs from the visually reviewed proof image")
    require(rom.read_bytes() == original, "Source ROM changed during verification")
    result = {
        "passed": True, "source_sha256": digest(original), "patched_sha256": digest(patched),
        "changed_pixel_bounds": bounds, "unchanged_pixels_outside_label": True,
        "state_replay_identical": True, "submenu_matches_outside_retained_label": True,
        "glyph_codes": [glyph["code"] for glyph in first_line],
        "glyph_advances": [glyph["advance"] for glyph in first_line],
    }
    (output / "verification.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rom", nargs="?", type=Path, default=ORIGINAL_ROM)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    print(json.dumps(verify(args.rom, args.output), indent=2))
