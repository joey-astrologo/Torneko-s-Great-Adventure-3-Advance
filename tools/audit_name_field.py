"""Audit compact name capacity and a temporary seven-slot editor layout probe."""

import argparse
import json
from pathlib import Path
import struct

import mgba.log
from mgba._pylib import ffi, lib
from PIL import Image, ImageDraw

from tools.build_first_label import ORIGINAL_ROM, ROOT, digest, load_manifest
from tools.translation_pipeline import FontZero
from tools.verify_expansion import Session, create_adventure
from tools.verify_first_label import require
from tools.verify_translation import TranslationTrace

OUTPUT = ROOT / "build/name-field"
NAME = 0x02004F82
EDIT_BUFFER = 0x02009DF8


class NameTrace(TranslationTrace):
    def __init__(self, core):
        self.name_calls, self.name_copies = [], []
        super().__init__(core, (NAME,))
        for address in (0x0807BAD4, 0x0807BB74, 0x0808593A, 0x08085940, 0x080969A8, 0x080027D0):
            point = ffi.new("struct mBreakpoint*")
            point.address, point.segment, point.type = address, -1, lib.BREAKPOINT_HARDWARE
            require(self.debugger.platform.setBreakpoint(self.debugger.platform, point) >= 0,
                    "Could not install name breakpoint")

    def entered(self, debugger, reason, info):
        try:
            if info != ffi.NULL and reason == lib.DEBUGGER_ENTER_BREAKPOINT:
                address = int(info.address)
                if address in (0x0807BAD4, 0x0807BB74, 0x0808593A, 0x08085940, 0x080969A8, 0x080027D0):
                    regs = [int(r) & 0xFFFFFFFF for r in self.cpu.gprs]
                    record = {"instruction": f"0x{address:08X}", "phase": self.phase,
                              "frame": self.core.frame_counter, "registers": [f"0x{r:08X}" for r in regs]}
                    if address in (0x0807BAD4, 0x0807BB74):
                        record.update({"limit": regs[3], "buffer": f"0x{regs[2]:08X}",
                                       "input_hex": bytes(self.core.memory[regs[2]:regs[2] + 8]).hex()})
                        self.name_calls.append(record)
                    elif address == 0x0808593A or (address == 0x080969A8 and regs[1] == NAME):
                        record.update({"destination": f"0x{regs[0]:08X}", "source": f"0x{regs[1]:08X}",
                                       "copy_bytes": regs[2], "caller": f"0x{(regs[14] & ~1) - 4:08X}"})
                        self.name_copies.append(record)
                    elif address == 0x08085940:
                        record["terminator_address"] = f"0x{regs[5] + 5:08X}"
                        self.name_copies.append(record)
                    elif address == 0x080027D0:
                        record.update({"record_address": f"0x{regs[6]:08X}", "name_offset": 16,
                                       "bytes_copied": regs[2],
                                       "record_name_hex": bytes(self.core.memory[regs[6] + 16:regs[6] + 22]).hex()})
                        self.name_copies.append(record)
                    return
            super().entered(debugger, reason, info)
        except Exception as error:
            self.errors.append(str(error))
        finally:
            debugger.state = lib.DEBUGGER_RUNNING


def capture(data, output, slots, save_route=False):
    with Session(data, output) as session:
        session.frames(600)
        trace = NameTrace(session.core)
        frames, screenshot = session.frames, session.capture
        session.frames = lambda count, unused=None: trace.frames(count)
        captures = {}

        def capture_screen(name):
            result = screenshot(name)
            captures[name] = {"frame": session.core.frame_counter,
                              "edit_buffer_hex": bytes(session.core.memory[EDIT_BUFFER:EDIT_BUFFER + 32]).hex(),
                              "name_ram_hex": bytes(session.core.memory[NAME:NAME + 8]).hex()}
            trace.phase = "after-" + name
            return result

        session.capture = capture_screen
        try:
            trace.phase = "title"
            session.press("START", 240)
            session.capture("title")
            if save_route:
                created, _, _ = create_adventure(session)
            else:
                session.press("A")
                session.press("A")
                session.press("A")
                session.capture("name-entry")
            calls = [c for c in trace.name_calls if c["instruction"] == "0x0807BB74"]
            require(calls and all(c["limit"] == slots for c in calls), "Unexpected native character limit")
            glyphs = [g for g in trace.positions if g["caller"] == "0x0808CD38" and g["window_origin"][1] == 16]
            widths = sorted({g["window_width"] for g in glyphs})
            require(widths == ([48] if slots == 4 else [80]), "Unexpected name editor window width")
            result = {"rom_sha256": digest(data), "slots": slots, "calls": trace.name_calls,
                      "copies": trace.name_copies, "name_reads": trace.source_reads,
                      "name_glyphs": glyphs, "window_widths": widths,
                      "captures": captures, "inputs": session.frames_recorded}
        finally:
            session.frames = frames
            trace.close()
    if save_route:
        require(created == session.disk_save, "Native save was not persisted")
        result["save_sha256"] = digest(created)
    (output / "trace.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    return result


def audit(rom=ORIGINAL_ROM, output=OUTPUT):
    rom, output = Path(rom).resolve(), Path(output).resolve()
    original = rom.read_bytes()
    require(digest(original) == load_manifest()["base_sha256"], "Expected Japanese original")
    require(original[0x858E6:0x858E8] == b"\x04\x23", "Unexpected editor-limit instruction")
    mgba.log.silence()
    normal = capture(original, output / "original", 4, save_route=True)
    # This experiment changes only the caller's limit in a temporary cartridge copy.
    # It stops at the editor and never commits a name to the six-byte destination.
    probe = bytearray(original)
    probe[0x858E6:0x858E8] = b"\x07\x23"
    expanded = capture(bytes(probe), output / "seven-slot-layout-only", 7)
    require(any(c.get("destination") == f"0x{NAME:08X}" and c.get("copy_bytes") == 6
                for c in normal["copies"]), "Did not observe the six-byte name commit")
    require(any(c.get("terminator_address") == "0x02004F87" for c in normal["copies"]),
            "Did not observe the committed-name terminator")
    require(any(c.get("name_offset") == 16 and c.get("bytes_copied") == 6 for c in normal["copies"]),
            "Did not observe the six-byte copy into the adventure record")
    font = FontZero(original)
    mapping_table = struct.unpack_from("<I", original, 0xC467E4)[0] - 0x08000000
    codes = [int.from_bytes(original[mapping_table + i * 2:mapping_table + i * 2 + 2], "big") for i in range(256)]
    report = {"source_sha256": digest(original), "requested_name": "Torneko", "required_characters": 7,
              "current_editor_characters": 4, "current_commit_bytes": 6, "commit_terminator_index": 5,
              "compact_storage_needed_for_seven_characters": 8,
              "adventure_record_name_offset": 16, "adventure_record_name_copy_bytes": 6,
              "ordinary_latin_font_advance": sum(font.glyph(c)[1] for c in "Torneko"),
              "editor_cell_pixels": 11, "current_editor_window_pixels": 48,
              "seven_slot_probe_window_pixels": 80,
              "compact_mapping_table_offset": f"0x{mapping_table:08X}",
              "ascii_characters_present_in_compact_mapping": {c: [i for i, code in enumerate(codes) if code == ord(c)] for c in dict.fromkeys("Torneko")},
              "seven_slot_probe": "Only the temporary caller limit changed; no longer name was saved and no production ROM was modified",
              "normal_route_save_sha256": normal["save_sha256"],
              "scope": "Adventure Log name editor, compact encoding, immediate commit, and window sizing. Persistent record expansion and a Latin keyboard are not implemented."}
    sheet = Image.new("RGB", (480, 180), "#18202b")
    draw = ImageDraw.Draw(sheet)
    for index, (label, path) in enumerate((("Original: four slots", output / "original/name-entry.png"),
                                         ("Layout probe: seven slots", output / "seven-slot-layout-only/name-entry.png"))):
        draw.text((index * 240 + 4, 2), label, fill="white")
        with Image.open(path) as screenshot:
            sheet.paste(screenshot, (index * 240, 20))
    sheet.save(output / "name-field-comparison.png")
    require(rom.read_bytes() == original, "Source ROM changed")
    (output / "audit.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rom", nargs="?", type=Path, default=ORIGINAL_ROM)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    print(json.dumps(audit(args.rom, args.output), ensure_ascii=False, indent=2))
