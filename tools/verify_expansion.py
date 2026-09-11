"""Exercise relocated text, cartridge saves, and cold-boot loading on 16/32 MiB ROMs."""

import argparse
import json
from pathlib import Path
import tempfile

import mgba.core
import mgba.image
import mgba.log
from mgba._pylib import ffi
from PIL import ImageChops

from tools.build_first_label import ORIGINAL_ROM, ROOT, digest, load_manifest
from tools.build_expansion_probe import OUTPUT, LABEL_OFFSET, LIMIT_PROBE_OFFSET, PROOF_TEXT, make_expanded_rom
from tools.verify_first_label import TextTrace, battery_snapshot, require


class Session:
    """Use only a temporary ROM and a native, file-backed cartridge save."""

    def __init__(self, rom_data, output, initial_save=None):
        self.rom_data, self.output, self.initial_save = rom_data, output, initial_save
        self.frames_recorded = []
        self.core = None

    def __enter__(self):
        self.output.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(prefix="cartridge-", dir=self.output)
        self.rom_path = Path(self.temporary.name) / "game.gba"
        self.save_path = self.rom_path.with_suffix(".sav")
        try:
            self.rom_path.write_bytes(self.rom_data)
            if self.initial_save is not None:
                self.save_path.write_bytes(self.initial_save)
            self.core = mgba.core.load_path(str(self.rom_path))
            require(self.core is not None, "Could not load cartridge")
            require(self.core.autoload_save(), "Could not open native cartridge save file")
            self.screen = mgba.image.Image(*self.core.desired_video_dimensions())
            self.core.set_video_buffer(self.screen)
            self.core.reset()
            return self
        except Exception:
            self.__exit__(None, None, None)
            raise

    def __exit__(self, *_):
        if self.core is not None:
            ffi.release(self.core._core)
            self.core = None
        self.disk_save = self.save_path.read_bytes() if self.save_path.exists() else b""
        self.temporary.cleanup()

    def frames(self, count, trace=None):
        if trace:
            trace.frames(count)
        else:
            for _ in range(count):
                self.core.run_frame()

    def press(self, key, wait=120, trace=None):
        code = getattr(self.core, "KEY_" + key)
        self.core.set_keys(code)
        self.frames(3, trace)
        self.core.clear_keys(code)
        self.frames(wait, trace)
        self.frames_recorded.append({"key": key, "hold": 3, "released": wait,
                                     "end_frame": self.core.frame_counter})

    def capture(self, name):
        image = self.screen.to_pil().convert("RGB")
        image.save(self.output / (name + ".png"))
        return image


def decoded_codes(text):
    return [int.from_bytes(character.encode("cp932"), "big") for character in text]


def inspect_title(session, offset, text):
    core = session.core
    session.frames(600)
    require(core._native.memory.savedata.type == 2, "Expected FLASH512 save hardware")
    state = core.save_raw_state()
    require(state is not None, "Could not capture pre-menu state")
    save = battery_snapshot(core)
    (session.output / "title.state").write_bytes(bytes(ffi.buffer(state)))
    (session.output / "title.sav").write_bytes(save)
    expected = text.encode("cp932") + b"\0"
    addresses = [base + offset for base in (0x08000000, 0x0A000000, 0x0C000000)]
    for address in addresses:
        require(bytes(core.memory[address:address + len(expected)]) == expected,
                f"Cartridge view did not expose relocated text at 0x{address:08X}")
    trace = TextTrace(core, (0x08C78280, 0x08000000 + offset))
    try:
        session.press("START", 240, trace)
        image = session.capture("menu")
        before = (image.tobytes(), bytes(core.memory[0x02000000:0x02040000]),
                  bytes(core.memory[0x03000000:0x03008000]), core.frame_counter)
        reads, glyphs = list(trace.reads), list(trace.glyphs)
        require([(r["address"], r["instruction"]) for r in reads] ==
                [("0x08C78280", "0x08084CD8"), (f"0x{0x08000000 + offset:08X}", "0x0808C732")],
                "The title renderer did not read the expected relocated pointer and text")
        row = [glyph for glyph in glyphs if glyph["y"] == 0]
        require([glyph["code"] for glyph in row] == decoded_codes(text), "Unexpected title glyphs")
        require(row[-1]["x"] + row[-1]["advance"] <= 86, "Proof text exceeds this menu's text area")
        require(core.load_raw_state(state), "Could not restore pre-menu state")
        require(core._core.savedataRestore(core._core, save, len(save), False), "Could not restore battery snapshot")
        trace.reads.clear()
        trace.glyphs.clear()
        session.press("START", 240, trace)
        after = (session.screen.to_pil().convert("RGB").tobytes(),
                 bytes(core.memory[0x02000000:0x02040000]),
                 bytes(core.memory[0x03000000:0x03008000]), core.frame_counter)
        require(before == after and reads == trace.reads and glyphs == trace.glyphs,
                "Save-state replay changed pixels, RAM, frame counter, or rendering trace")
    finally:
        trace.close()
    report = {"rom_sha256": digest(session.rom_data), "rom_bytes": len(session.rom_data),
              "label": text, "label_file_offset": f"0x{offset:08X}",
              "label_gba_address": f"0x{0x08000000 + offset:08X}",
              "save_type": "FLASH512", "save_bytes": len(save),
              "cartridge_views_checked": [f"0x{address:08X}" for address in addresses],
              "reads": reads, "glyphs": row, "state_replay_identical": True,
              "menu_rgb_sha256": digest(image.tobytes())}
    (session.output / "title-trace.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return image, report


def create_adventure(session, slot=1):
    require(slot in (1, 2), "Adventure slot must be 1 or 2")
    initial_save = battery_snapshot(session.core)
    frames = []
    session.press("A")  # First menu option -> adventure-log slots.
    frames.append(session.capture("slots"))
    if slot == 2:
        session.press("DOWN", 30)
        frames.append(session.capture("slot-two-selected"))
    session.press("A")  # Empty first slot -> explanation.
    frames.append(session.capture("new-log-explanation"))
    session.press("A")  # Explanation -> naming keyboard, default name セーブ1.
    frames.append(session.capture("name-entry"))
    for _ in range(3):
        session.press("RIGHT", 30)  # Move to おわり (finish).
    session.press("A")
    frames.append(session.capture("name-confirmation"))
    session.press("A")  # Accept the default name.
    frames.append(session.capture("mode-menu"))
    session.press("A")  # Scenario mode.
    frames.append(session.capture("mode-confirmation"))
    session.press("UP", 30)  # This confirmation defaults to No; select Yes.
    session.press("A", 720)  # Allow the game to write its FLASH save and finish.
    frames.append(session.capture("save-created"))
    created = battery_snapshot(session.core)
    changed = sum(a != b for a, b in zip(initial_save, created))
    require(len(created) == 65536 and changed > 1024, "Adventure creation did not write a substantial FLASH record")
    (session.output / "created.sav").write_bytes(created)
    return created, frames, changed


def cold_reload(rom_data, save, output):
    with Session(rom_data, output, save) as session:
        session.frames(600)
        session.press("START", 240)
        frames = [session.capture("saved-menu")]
        session.press("A")  # Continue is selected by default after a successful save load.
        frames.append(session.capture("saved-slot"))
        session.press("A")  # Select slot 1; game reads the adventure record.
        frames.append(session.capture("loaded-notice"))
        session.press("A", 1200)  # Acknowledge and enter the opening story.
        frames.append(session.capture("opening-story"))
        fixture = json.loads((ROOT / "tests/fixtures/expansion.json").read_text())
        require(digest(frames[-1].tobytes()) == fixture["opening_story_rgb_sha256"],
                "Cold-loaded game did not reach the visually reviewed opening story")
        report = {"input_save_sha256": digest(save), "rom_sha256": digest(rom_data),
                  "route": session.frames_recorded, "final_frame": session.core.frame_counter,
                  "opening_story_rgb_sha256": digest(frames[-1].tobytes())}
    report["disk_save_bytes_after_close"] = len(session.disk_save)
    (output / "reload.json").write_text(json.dumps(report, indent=2) + "\n")
    return frames, report


def same_outside_label(first, second, box):
    difference = ImageChops.difference(first, second)
    bounds = difference.getbbox()
    if bounds is None:
        return True
    left, top, right, bottom = box
    return left <= bounds[0] and top <= bounds[1] and bounds[2] <= right and bounds[3] <= bottom


def verify(rom=ORIGINAL_ROM, output=OUTPUT):
    mgba.log.silence()
    rom, output = Path(rom).resolve(), Path(output).resolve()
    original = rom.read_bytes()
    japanese = load_manifest()["japanese"]
    primary = (output / "torneko3-expansion-32m.gba").read_bytes()
    require(primary == make_expanded_rom(original), "Expanded build differs from the reproducible builder")
    variants = [("original", original, 0x00C782D8, japanese),
                ("expanded-japanese", make_expanded_rom(original, japanese), LABEL_OFFSET, japanese),
                ("expanded-english", primary, LABEL_OFFSET, PROOF_TEXT),
                ("expanded-limit", make_expanded_rom(original, PROOF_TEXT, LIMIT_PROBE_OFFSET), LIMIT_PROBE_OFFSET, PROOF_TEXT)]
    menus, title_reports, created_saves, created_screens, reload_screens, reload_reports = {}, {}, {}, {}, {}, {}
    for name, data, offset, text in variants:
        with Session(data, output / name) as session:
            menus[name], title_reports[name] = inspect_title(session, offset, text)
            if name in ("original", "expanded-english"):
                created_saves[name], created_screens[name], changed = create_adventure(session)
                (session.output / "creation.json").write_text(json.dumps({
                    "route_after_title": session.frames_recorded[2:],
                    "final_frame": session.core.frame_counter,
                    "save_sha256": digest(created_saves[name]), "changed_save_bytes": changed,
                }, indent=2) + "\n")
        if name in created_saves:
            require(session.disk_save == created_saves[name], "Native save file did not persist the game's FLASH contents")
            reload_screens[name], reload_reports[name] = cold_reload(data, session.disk_save, output / name / "cold-reload")
    require(menus["original"].tobytes() == menus["expanded-japanese"].tobytes(),
            "Relocating unchanged Japanese text changed the menu pixels")
    require(menus["expanded-english"].tobytes() == menus["expanded-limit"].tobytes(),
            "Text at the first and last parts of the appended region rendered differently")
    require(same_outside_label(menus["original"], menus["expanded-english"], (28, 15, 110, 28)),
            "The expanded English menu differs outside the first label")
    require(created_saves["original"] == created_saves["expanded-english"],
            "Identical new-adventure routes generated different cartridge saves")
    for base, expanded in zip(created_screens["original"], created_screens["expanded-english"]):
        require(same_outside_label(base, expanded, (28, 15, 110, 28)), "New-adventure screens differ outside the label")
    for index, (base, expanded) in enumerate(zip(reload_screens["original"], reload_screens["expanded-english"])):
        # The saved title menu has Continue on row 1 and our relocated label on row 2.
        require(same_outside_label(base, expanded, (28, 27, 110, 40)), f"Cold-reload screen {index} differs beyond the relocated label")
    # Check that the original game can load the expanded build's native save as well.
    _, cross_report = cold_reload(original, created_saves["expanded-english"], output / "cross-load-original")
    require(rom.read_bytes() == original, "Original ROM changed during verification")
    result = {"passed": True, "original_sha256": digest(original), "expanded_sha256": digest(primary),
              "tested_text_addresses": [report["label_gba_address"] for report in title_reports.values()],
              "unchanged_japanese_relocation_pixel_identical": True,
              "near_limit_relocation_pixel_identical": True,
              "state_replays_identical": True,
              "native_save_files_persisted": True, "original_and_expanded_saves_identical": True,
              "cold_load_reached_opening_story": True, "expanded_save_loads_in_original": True,
              "save_bytes": len(created_saves["original"]),
              "save_sha256": digest(created_saves["original"]),
              "cross_load": cross_report,
              "scope": "mGBA 0.10.5; title menu, new-adventure creation, cold reload and opening story. Other text systems and full gameplay remain untested."}
    (output / "expansion-verification.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rom", nargs="?", type=Path, default=ORIGINAL_ROM)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    print(json.dumps(verify(args.rom, args.output), indent=2))
