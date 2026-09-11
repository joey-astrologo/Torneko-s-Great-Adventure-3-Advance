"""Enter real names with joypad input, persist native saves, and cold-load them."""

import argparse
import json
from pathlib import Path
import string

import mgba.log
from mgba._pylib import ffi, lib
from PIL import Image, ImageDraw

from tools.build_first_label import ORIGINAL_ROM, digest
from tools.build_name_entry import OUTPUT, NAME_RAM, LATIN, DEFAULT_NAME, build_name_rom, compact_name
from tools.translation_pipeline import FontZero
from tools.verify_expansion import Session, create_adventure
from tools.verify_first_label import battery_snapshot, require
from tools.verify_translation import TranslationTrace

EDIT_BUFFER, KEY_SELECTION, KEY_PAGE, NAME_CURSOR = 0x02009DF8, 0x02009DF4, 0x02009DE8, 0x02009DF0


class NameEntryTrace(TranslationTrace):
    def __init__(self, core):
        self.name_events = []
        self.points = (0x08085934, 0x08085942, 0x080027D0, 0x0800230A, 0x08085548, 0x08096654)
        super().__init__(core)
        for address in self.points:
            point = ffi.new("struct mBreakpoint*")
            point.address, point.segment, point.type = address, -1, lib.BREAKPOINT_HARDWARE
            require(self.debugger.platform.setBreakpoint(self.debugger.platform, point) >= 0, "Name breakpoint failed")

    def entered(self, debugger, reason, info):
        try:
            if info != ffi.NULL and reason == lib.DEBUGGER_ENTER_BREAKPOINT and int(info.address) in self.points:
                address = int(info.address)
                regs = [int(r) & 0xFFFFFFFF for r in self.cpu.gprs]
                if address != 0x08096654 or regs[2] in (6, 8, 0x5C, 0x70):
                    event = {"instruction": f"0x{address:08X}", "phase": self.phase,
                             "frame": self.core.frame_counter, "registers": regs,
                             "name_hex": bytes(self.core.memory[NAME_RAM:NAME_RAM + 8]).hex(),
                             "neighbors_hex": bytes(self.core.memory[0x02004F80:0x02004F94]).hex()}
                    if address in (0x080027D0, 0x0800230A):
                        event["record_name_hex"] = bytes(self.core.memory[regs[6] + 16:regs[6] + 24]).hex()
                    if address == 0x08085548:
                        event["slot_name_hex"] = bytes(self.core.memory[regs[2]:regs[2] + 8]).hex()
                    self.name_events.append(event)
                return
            super().entered(debugger, reason, info)
        except Exception as error:
            self.errors.append(str(error))
        finally:
            debugger.state = lib.DEBUGGER_RUNNING

    def report(self):
        return {**super().report(), "name_events": self.name_events}


def select_character(session, character):
    """Navigate the game's existing grid. Memory is read only; input is joypad."""
    target_page = int(character.islower())
    if session.core.memory.u32[KEY_PAGE] != target_page:
        session.press("L", 15)
    require(session.core.memory.u32[KEY_PAGE] == target_page, "Keyboard case toggle failed")
    alphabet = string.ascii_lowercase if target_page else string.ascii_uppercase
    target = 5 + (alphabet + string.digits).index(character)
    for _ in range(30):
        current = session.core.memory.u32[KEY_SELECTION]
        if current == target:
            return
        if current < 5:
            key = "DOWN"
        else:
            row, column = divmod(current - 5, 10)
            target_row, target_column = divmod(target - 5, 10)
            key = ("DOWN" if row < target_row else "UP") if row != target_row else ("RIGHT" if column < target_column else "LEFT")
        session.press(key, 15)
    raise AssertionError("Could not navigate keyboard")


def attach(session):
    trace = NameEntryTrace(session.core)
    frames = session.frames
    session.frames = lambda count, unused=None: trace.frames(count)
    return trace, frames


def creation(data, output, slot, name="Torneko", initial_save=None):
    with Session(data, output, initial_save) as session:
        session.frames(600)
        trace, frames = attach(session)
        try:
            trace.phase = "title"
            session.press("START", 240)
            if initial_save is not None:
                session.press("DOWN", 30)  # New game follows Continue on populated saves.
            session.press("A")
            # With slot 1 occupied, New game automatically selects empty slot 2.
            if slot == 2 and initial_save is None:
                session.press("DOWN", 30)
            session.press("A")
            session.capture("explanation")
            session.press("A")
            require(bytes(session.core.memory[EDIT_BUFFER:EDIT_BUFFER + 8]) == compact_name(DEFAULT_NAME), "Initial name is not Torneko")
            require(any(d["preview_hex"] == DEFAULT_NAME.encode().hex() for d in trace.draws.values()), "Default name did not render")
            session.capture("name-default")
            trace.phase = "edit"
            for _ in DEFAULT_NAME:
                session.press("B", 15)
            require(session.core.memory.u8[EDIT_BUFFER] == 0, "Default name was not erased")
            session.capture("keyboard-upper")
            for index, character in enumerate(name):
                select_character(session, character)
                session.press("A", 15)
                expected = bytes(LATIN[c] for c in name[:index + 1])
                observed = bytes(session.core.memory[EDIT_BUFFER:EDIT_BUFFER + len(expected)])
                require(observed == expected, f"Joypad entry mismatch at {character}")
            session.capture("name-entered")
            require(session.core.memory.u8[EDIT_BUFFER + len(name)] == 0, "Name lacks terminator")
            if len(name) == 7:
                require(session.core.memory.u32[KEY_SELECTION] == 4, "Full name did not select Done")
            else:
                session.press("R", 15)
            trace.phase = "confirmation"
            session.press("A")
            session.capture("confirmation")
            require(any(name.encode().hex() in f.get("output_hex", "") for f in trace.formats
                        if f["phase"] == "confirmation"), "Name substitution was not rendered")
            trace.phase = "commit"
            session.press("A")
            session.capture("mode")
            require(bytes(session.core.memory[NAME_RAM:NAME_RAM + 8]) == compact_name(name).ljust(8, b"\0"), "Name commit truncated")
            before, after = [e for e in trace.name_events if e["instruction"] in ("0x08085934", "0x08085942")][-2:]
            require(before["neighbors_hex"] == after["neighbors_hex"], "Name commit overwrote neighboring globals")
            trace.phase = "save"
            session.press("A")
            session.press("UP", 30)
            session.press("A", 720)
            session.capture("saved")
            save = battery_snapshot(session.core)
            records = [e for e in trace.name_events if e["instruction"] == "0x080027D0"]
            require(records and records[-1]["record_name_hex"] == compact_name(name).ljust(8, b"\0").hex(), "Adventure record truncated name")
            report = trace.report()
            report.update({"slot": slot, "name": name, "inputs": session.frames_recorded})
        finally:
            session.frames = frames
            trace.close()
    require(len(session.disk_save) == 65536 and session.disk_save == save, "Native save was not persisted")
    (output / "created.sav").write_bytes(save)
    report["save_sha256"] = digest(save)
    (output / "trace.json").write_text(json.dumps(report, indent=2) + "\n")
    return save, report


def reload_name(data, save, output, expected, slot=1, select_slot=False):
    with Session(data, output, save) as session:
        session.frames(600)
        trace, frames = attach(session)
        try:
            trace.phase = "slots"
            session.press("START", 240)
            session.press("A")
            if select_slot:
                session.press("DOWN", 30)
            session.capture("slots")
            rows = [e for e in trace.name_events if e["instruction"] == "0x08085548"]
            require(rows and rows[-1]["slot_name_hex"].startswith(expected.hex()), "Saved-slot name truncated")
            reverse = {value: ord(key) for key, value in LATIN.items()}
            if all(code in reverse for code in expected[:-1]):
                visible_name = bytes(reverse[code] for code in expected[:-1])
                require(any(visible_name.hex() in d["preview_hex"] for d in trace.draws.values()
                            if d["phase"] == "slots"), "Saved-slot renderer did not receive the full Latin name")
            trace.phase = "load"
            session.press("A")
            session.capture("loaded")
            require(bytes(session.core.memory[NAME_RAM:NAME_RAM + len(expected)]) == expected, "Cold load truncated name")
            trace.phase = "story"
            session.press("A", 1200)
            session.capture("story")
            require(bytes(session.core.memory[NAME_RAM:NAME_RAM + len(expected)]) == expected, "Story transition lost name")
            require(any(g["phase"] == "story" and g["caller"] == "0x08061B4E" for g in trace.positions),
                    "Cold load did not reach the opening-story renderer")
            report = trace.report()
            report.update({"slot": slot, "save_sha256": digest(save), "inputs": session.frames_recorded})
        finally:
            session.frames = frames
            trace.close()
    (output / "trace.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def keyboard_checks(data, original, build, output):
    """Exercise all 62 added IDs and the seven-position limit using real input."""
    with Session(data, output) as session:
        session.frames(600)
        trace, frames = attach(session)
        try:
            session.press("START", 240)
            for _ in range(3):
                session.press("A")
            for _ in DEFAULT_NAME:
                session.press("B", 15)
            characters = string.ascii_uppercase + string.ascii_lowercase + string.digits
            cases = []
            for start in range(0, len(characters), 7):
                name = characters[start:start + 7]
                trace.phase = "alphabet-" + name
                for character in name:
                    select_character(session, character)
                    session.press("A", 15)
                require(bytes(session.core.memory[EDIT_BUFFER:EDIT_BUFFER + len(name) + 1]) == compact_name(name), "Alphabet entry failed")
                require(any(d["preview_hex"] == (name.encode() + ("＊" * (7 - len(name))).encode("cp932")).hex()
                            for d in trace.draws.values() if d["phase"] == trace.phase), "Alphabet did not render correctly")
                cases.append(name)
                for _ in name:
                    session.press("B", 15)
                require(session.core.memory.u8[EDIT_BUFFER] == 0, "Erase failed")
            # At capacity, Next cannot create an eighth slot; typing replaces
            # the seventh letter using the game's existing editing behavior.
            trace.phase = "capacity"
            for character in "Torneko":
                select_character(session, character)
                session.press("A", 15)
            session.press("LEFT", 15)  # Done -> Back
            session.press("LEFT", 15)  # Back -> Next (history is disabled here)
            require(session.core.memory.u32[KEY_SELECTION] == 1, "Next button navigation failed")
            session.press("A", 15)
            require(session.core.memory.u32[NAME_CURSOR] == 6, "Next exceeded seven-character limit")
            select_character(session, "X")
            session.press("A", 15)
            require(bytes(session.core.memory[EDIT_BUFFER:EDIT_BUFFER + 8]) == compact_name("TornekX"), "Full field did not replace last character safely")
            require(bytes(session.core.memory[EDIT_BUFFER + 8:EDIT_BUFFER + 32]) == b"\0" * 24, "Editor wrote past name capacity")
            session.press("START", 15)  # Original kana-variation shortcut ignores Latin IDs.
            require(bytes(session.core.memory[EDIT_BUFFER:EDIT_BUFFER + 8]) == compact_name("TornekX"), "Kana shortcut changed a Latin name")
            session.capture("capacity")
            font = FontZero(original)
            page_checks = []
            for page in (0, 1):
                address = next(a["address"] for a in build["allocations"] if a["id"] == f"name.keyboard-page-{page}")
                glyphs = {(g["x"], g["y"], g["code"]): g for g in trace.positions if g["source"] == address}
                pixels = set()
                for g in glyphs.values():
                    require(g["font"] == 0, "Keyboard did not use the selected font")
                    bitmap = font.descriptors[g["code"]][0] - 0x08000000
                    for y in range(12):
                        for x in range(12):
                            if (original[bitmap + y * 6 + x // 2] >> (4 * (x % 2))) & 15:
                                point = (g["x"] + x, g["y"] + y)
                                require(point not in pixels, "Keyboard glyph ink overlaps")
                                require(0 <= point[0] < 208 and 14 <= point[1] < 98, "Keyboard ink exceeds its area")
                                pixels.add(point)
                require(len(glyphs) == 47, "Incomplete keyboard glyph coverage")
                page_checks.append({"page": page, "glyphs": len(glyphs), "font": 0, "no_ink_overlap": True})
            report = {"alphabet_cases": cases, "added_ids_tested": len(characters),
                      "capacity": 7, "next_clamped": True, "replacement": "TornekX", "pages": page_checks,
                      "inputs": session.frames_recorded}
        finally:
            session.frames = frames
            trace.close()
    (output / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def legacy_checks(data, original, output, slot):
    # Fresh native original saves are the compatibility fixtures; no save-byte
    # edits or emulator memory injection are used to prepare them.
    saves = []
    for label, cartridge in (("original", original), ("new-default", data)):
        with Session(cartridge, output / label) as session:
            session.frames(600)
            session.press("START", 240)
            save, _, _ = create_adventure(session, slot)
        require(save == session.disk_save, "Legacy fixture was not persisted")
        saves.append(save)
    expected = bytes.fromhex("4579ad") + bytes((0x6F + slot, 0))
    reload_name(data, saves[0], output / "reload", expected, slot)
    # Accept the prefilled Torneko without typing, then cold-load it. The only
    # save differences from the original default may be the name and checksum.
    reload_name(data, saves[1], output / "default-reload", compact_name(DEFAULT_NAME), slot)
    base = (slot - 1) * 0x7000
    differences = [i for i, (a, b) in enumerate(zip(*saves)) if a != b]
    allowed = set(range(base, base + 4)) | set(range(base + 0x10, base + 0x18))
    require(set(differences) <= allowed, "Default-name save changed other fields")
    require(saves[1][base + 0x10:base + 0x18] == compact_name(DEFAULT_NAME), "Default-name save did not contain Torneko")
    return {"slot": slot, "original_save_sha256": digest(saves[0]), "japanese_name_preserved": True,
            "default_name": DEFAULT_NAME, "default_accepted_and_cold_loaded": True,
            "default_save_sha256": digest(saves[1]),
            "default_save_changed_offsets": [f"0x{i:04X}" for i in differences]}


def verify(rom=ORIGINAL_ROM, output=OUTPUT):
    original = Path(rom).read_bytes()
    output = Path(output).resolve()
    data, build = build_name_rom(original)
    require((output / "torneko3-name-entry.gba").read_bytes() == data, "Proof build is stale")
    mgba.log.silence()
    checks, legacy = [], []
    alphabet = keyboard_checks(data, original, build, output / "keyboard-tests")
    print("All 62 new letter/digit IDs and the seven-character limit passed", flush=True)
    first_save = None
    for slot in (1, 2):
        save, _ = creation(data, output / f"slot-{slot}/create", slot)
        reload_name(data, save, output / f"slot-{slot}/reload", compact_name("Torneko"), slot)
        checks.append({"slot": slot, "save_sha256": digest(save), "cold_load": True})
        if slot == 1:
            first_save = save
        print(f"Slot {slot}: Torneko entered, persisted, and cold-loaded", flush=True)
        legacy.append(legacy_checks(data, original, output / f"legacy-{slot}", slot))
        print(f"Slot {slot}: Japanese save preserved; prefilled Torneko accepted and cold-loaded", flush=True)
    combined, _ = creation(data, output / "two-slots/create", 2, "gyjpqQ9", first_save)
    require(combined[:0x7000] == first_save[:0x7000], "Creating slot 2 changed slot 1's save record")
    reload_name(data, combined, output / "two-slots/reload-one", compact_name("Torneko"), 1)
    reload_name(data, combined, output / "two-slots/reload-two", compact_name("gyjpqQ9"), 2, select_slot=True)
    print("Both occupied slots cold-loaded; creating slot 2 preserved slot 1", flush=True)
    # One-letter names exercise the opposite boundary and zero-padding rules.
    short, _ = creation(data, output / "short/create", 1, "A")
    reload_name(data, short, output / "short/reload", compact_name("A"), 1)
    sheet = Image.new("RGB", (720, 360), "#18202b")
    draw = ImageDraw.Draw(sheet)
    screens = (("Default name: Torneko", "slot-1/create/name-default.png"),
               ("Confirm the name", "slot-1/create/confirmation.png"),
               ("Slot 1 after fresh start", "slot-1/reload/slots.png"),
               ("Slot 2 after fresh start", "slot-2/reload/slots.png"),
               ("Both slots: second name", "two-slots/reload-two/slots.png"),
               ("Existing Japanese save", "legacy-1/reload/slots.png"))
    for i, (label, path) in enumerate(screens):
        x, y = i % 3 * 240, i // 3 * 180
        draw.text((x + 4, y + 2), label, fill="white")
        with Image.open(output / path) as screenshot:
            sheet.paste(screenshot, (x, y + 20))
    sheet.save(output / "name-entry-proof.png")
    report = {"rom_sha256": digest(data), "source_sha256": digest(original), "default_name": DEFAULT_NAME, "checks": checks,
              "keyboard": alphabet, "legacy": legacy, "both_slots_save_sha256": digest(combined),
              "slot_one_record_preserved": True, "short_name_cold_load": True,
              "save_bytes": 65536, "emulator": "mGBA 0.10.5; built-in BIOS; native file-backed saves"}
    (output / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
    require(Path(rom).read_bytes() == original, "Source ROM changed")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rom", nargs="?", type=Path, default=ORIGINAL_ROM)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    print(json.dumps(verify(args.rom, args.output), indent=2))
