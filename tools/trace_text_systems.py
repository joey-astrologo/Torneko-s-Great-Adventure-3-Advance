"""Record text-reader evidence on reproducible Japanese-ROM routes."""

import argparse
from collections import Counter
import json
from pathlib import Path
import struct

import mgba.log
from mgba._pylib import ffi, lib

from tools.build_first_label import ORIGINAL_ROM, ROOT, digest, load_manifest
from tools.verify_expansion import Session, create_adventure
from tools.verify_first_label import require

OUTPUT = ROOT / "build/text-inventory"


def hex_address(value):
    return f"0x{value & 0xFFFFFFFF:08X}"


class ReaderTrace:
    """Aggregate native calls; retain all callbacks until debugger detachment."""

    def __init__(self, core, watch_addresses=()):
        self.core = core
        self.cpu = ffi.cast("struct ARMCore*", core._core.cpu)
        self.reads, self.draws, self.glyphs = {}, {}, Counter()
        self.errors = []
        self.source_reads = []
        self.formats, self.format_stack = [], []
        self.phase = "boot"
        self.callback = ffi.callback(
            "void(struct mDebugger*, enum mDebuggerEntryReason, struct mDebuggerEntryInfo*)",
            self.entered)
        self.debugger = ffi.new("struct mDebugger*")
        self.debugger.type = lib.DEBUGGER_CUSTOM
        self.debugger.entered = self.callback
        lib.mDebuggerAttach(self.debugger, core._core)
        try:
            for address in watch_addresses:
                point = ffi.new("struct mWatchpoint*")
                point.address, point.segment, point.type = address, -1, lib.WATCHPOINT_READ
                require(self.debugger.platform.setWatchpoint(self.debugger.platform, point) >= 0,
                        "Could not install source watchpoint")
            for address in (0x0808C72C, 0x0808CBA0, 0x0808BC4C, 0x0807D8CC, 0x0807DBDE):
                point = ffi.new("struct mBreakpoint*")
                point.address, point.segment, point.type = address, -1, lib.BREAKPOINT_HARDWARE
                require(self.debugger.platform.setBreakpoint(self.debugger.platform, point) >= 0,
                        "Could not install reader breakpoint")
        except Exception:
            self.close()
            raise

    def entered(self, debugger, reason, info):
        try:
            if info == ffi.NULL:
                return
            regs = [int(r) & 0xFFFFFFFF for r in self.cpu.gprs]
            if reason == lib.DEBUGGER_ENTER_WATCHPOINT:
                thumb = bool(self.cpu.cpsr.packed & 0x20)
                self.source_reads.append({"phase": self.phase, "address": hex_address(info.address),
                                          "instruction": hex_address(regs[15] - (4 if thumb else 8)),
                                          "frame": self.core.frame_counter,
                                          "registers": [hex_address(r) for r in regs]})
                return
            if reason != lib.DEBUGGER_ENTER_BREAKPOINT:
                return
            caller = (regs[14] & ~1) - 4  # Observed callers are Thumb BL instructions.
            if info.address == 0x0807D8CC:
                row = {"phase": self.phase, "caller": hex_address(caller),
                       "source": hex_address(regs[0]), "destination": hex_address(regs[1]),
                       "payload_end": hex_address(regs[2]), "payload_limit": regs[2] - regs[1],
                       "line_mode": regs[3] & 0xFF, "frame": self.core.frame_counter}
                self.formats.append(row)
                self.format_stack.append(row)
            elif info.address == 0x0807DBDE:
                require(self.format_stack, "Formatter return without traced entry")
                row = self.format_stack.pop()
                start = int(row["destination"], 16)
                require(start <= regs[5] <= int(row["payload_end"], 16), "Formatter exceeded output limit")
                row["written_bytes"] = regs[5] - start
                row["output_hex"] = bytes(self.core.memory[start:regs[5] + 1]).hex()
                require(self.core.memory.u8[regs[5]] == 0, "Formatter output lacks terminator")
            elif info.address == 0x0808C72C:
                address = regs[0]
                raw = bytes(self.core.memory[address:address + 2])
                width = 2 if 0x80 <= raw[0] <= 0x9F or 0xE0 <= raw[0] <= 0xFE else 1
                raw = raw[:width]
                key = (self.phase, caller, address, raw.hex())
                if key not in self.reads:
                    self.reads[key] = {"phase": self.phase, "caller": hex_address(caller),
                                       "address": hex_address(address), "raw_hex": raw.hex(),
                                       "first_frame": self.core.frame_counter, "count": 0}
                self.reads[key]["count"] += 1
            elif info.address == 0x0808CBA0:
                address = regs[2]
                raw = bytes(self.core.memory[address:address + 512])
                # A preview only: binary control arguments can themselves be zero.
                preview = raw.split(b"\0", 1)[0]
                key = (self.phase, caller, address, preview.hex())
                if key not in self.draws:
                    self.draws[key] = {"phase": self.phase, "caller": hex_address(caller),
                                      "address": hex_address(address), "x": regs[0], "y": regs[1],
                                      "window": regs[3], "preview_hex": preview.hex(),
                                      "preview": preview.decode("cp932", errors="backslashreplace"),
                                      "first_frame": self.core.frame_counter, "count": 0}
                self.draws[key]["count"] += 1
            else:
                font = int(self.core.memory.u32[0x020398F8])
                self.glyphs[(self.phase, caller, regs[2], font)] += 1
            require(len(self.reads) + len(self.draws) < 100000, "Unexpectedly large reader trace")
        except Exception as error:
            self.errors.append(str(error))
        finally:
            debugger.state = lib.DEBUGGER_RUNNING

    def frames(self, count):
        before = self.core.frame_counter
        for _ in range(count):
            lib.mDebuggerRunFrame(self.debugger)
        require(not self.errors, f"Reader callback failed: {self.errors[:5]}")
        require(self.core.frame_counter - before == count, "Unexpected frame count")

    def close(self):
        self.core._core.detachDebugger(self.core._core)

    def report(self):
        return {"reads": list(self.reads.values()), "draws": list(self.draws.values()),
                "source_reads": self.source_reads,
                "formats": self.formats,
                "glyphs": [{"phase": p, "caller": hex_address(c), "code": code,
                            "font": font, "count": n}
                           for (p, c, code, font), n in self.glyphs.items()]}


def capture_route(data, output, route, initial_save=None, watch_addresses=()):
    with Session(data, output, initial_save) as session:
        session.frames(600)
        trace = ReaderTrace(session.core, watch_addresses)
        original_frames, original_capture = session.frames, session.capture
        session.frames = lambda count, unused=None: trace.frames(count)

        def capture(name):
            result = original_capture(name)
            trace.phase = "after-" + name
            return result

        session.capture = capture
        try:
            trace.phase = "title-menu"
            session.press("START", 240)
            session.capture("title-menu")
            if route == "creation":
                create_adventure(session)
            elif route == "settings":
                session.press("DOWN", 30)
                session.press("A")
                session.capture("settings")
                session.press("A")
                session.capture("settings-first-option")
                session.press("B")
                session.capture("settings-back")
            elif route == "story":
                session.press("A")
                session.capture("slots")
                session.press("A")
                session.capture("loaded")
                session.press("A", 1200)
                session.capture("story-page-1")
                session.press("A", 600)
                session.capture("story-page-2")
            report = trace.report()
            report.update({"rom_sha256": digest(data), "route": route,
                           "initial_save_sha256": digest(initial_save) if initial_save else None,
                           "emulator": "mGBA 0.10.5; built-in BIOS", "boot_frames": 600,
                           "inputs": session.frames_recorded})
            (output / "readers.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        finally:
            session.frames = original_frames
            trace.close()
    return report, session.disk_save


def trace_routes(rom=ORIGINAL_ROM, output=OUTPUT):
    rom, output = Path(rom).resolve(), Path(output).resolve()
    data = rom.read_bytes()
    require(digest(data) == load_manifest()["base_sha256"], "Expected verified Japanese original")
    mgba.log.silence()
    summaries = []
    for route in ("settings", "creation", "story"):
        report, save = capture_route(data, output / route, route, save if route == "story" else None)
        callers = Counter((r["caller"], "ROM" if 0x08000000 <= int(r["address"], 16) < 0x0E000000 else "RAM")
                          for r in report["reads"])
        summary = {"route": route, "unique_reads": len(report["reads"]),
                   "draw_calls": len(report["draws"]),
                   "decoder_callers": [{"instruction": c, "source": region, "unique_reads": n}
                                       for (c, region), n in callers.items()]}
        summaries.append(summary)
        print(json.dumps(summary), flush=True)
    (output / "runtime-summary.json").write_text(json.dumps(summaries, indent=2) + "\n")
    require(rom.read_bytes() == data, "Source ROM changed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rom", nargs="?", type=Path, default=ORIGINAL_ROM)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    trace_routes(args.rom, args.output)
