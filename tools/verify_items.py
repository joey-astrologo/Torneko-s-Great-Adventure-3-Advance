"""Verify complete item relocation and controlled inventory UI in native mGBA."""

import argparse
import json
from pathlib import Path
import struct

import mgba.log
from mgba._pylib import ffi, lib
from PIL import Image, ImageChops, ImageDraw

from tools.build_first_label import ORIGINAL_ROM, digest
from tools.build_items import CATALOG, OUTPUT, STARTER_DRAFTS, TABLES, build_item_rom
from tools.build_name_entry import build_name_rom, compact_name
from tools.game_text import GameTextCodec
from tools.translation_pipeline import FontZero, load_json
from tools.verify_expansion import Session, create_adventure
from tools.verify_first_label import require
from tools.verify_name_entry import creation, reload_name
from tools.verify_translation import TranslationTrace


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def distinct_glyph_observations(glyphs):
    """Collapse only adjacent identical placements; retain a repeat count."""
    result, repeats = [], 0
    fields = ("draw_serial", "caller", "code", "advance", "x", "y", "font", "spacing", "window_origin", "window_width", "window_height")
    for glyph in glyphs:
        if result and all(glyph.get(k) == result[-1].get(k) for k in fields):
            repeats += 1
        else:
            result.append(glyph)
    return result, repeats


def coalesce_empty_draw_observations(draws, positions):
    """Require a complete following observation for a repeated empty draw.

    Native breakpoints can report an entry twice across a frame boundary. The
    cause is not assumed. An empty observation is accepted only if the very
    next serial has the exact same text, address and geometry and has glyphs.
    The caller must still validate that complete glyph sequence and placement.
    """
    observed = {g["draw_serial"] for g in positions}
    result, repeats = [], 0
    for draw in draws:
        if draw["serial"] in observed:
            result.append(draw)
            continue
        following = [d for d in draws if d["serial"] == draw["serial"] + 1 and d["serial"] in observed]
        require(len(following) == 1 and all(draw[k] == following[0][k] for k in ("phase", "address", "x", "y"))
                and bytes.fromhex(draw["raw_hex"]).split(b"\0",1)[0] == bytes.fromhex(following[0]["raw_hex"]).split(b"\0",1)[0],
                "Native draw has no glyphs or an exact following observation")
        repeats += 1
    return result, repeats


class ItemTrace(TranslationTrace):
    def __init__(self, core, words):
        self.payloads = []
        super().__init__(core, watch_addresses=words)

    def entered(self, debugger, reason, info):
        super().entered(debugger, reason, info)
        try:
            if info != ffi.NULL and reason == lib.DEBUGGER_ENTER_BREAKPOINT:
                if info.address == 0x0808CBA0:
                    address = int(self.cpu.gprs[2]) & 0xFFFFFFFF
                    self.payloads.append({**self.draw_sources[-1], "serial": len(self.draw_sources) - 1,
                                          "raw_hex": bytes(self.core.memory[address:address + 512]).hex()})
                elif info.address == 0x0808BC78:
                    self.positions[-1]["draw_serial"] = len(self.draw_sources) - 1
        except Exception as error:
            self.errors.append(str(error))
        finally:
            debugger.state = lib.DEBUGGER_RUNNING


def enter_world(session):
    session.frames(600)
    for key, delay in (("START", 240), ("A", 120), ("A", 120), ("A", 1200)):
        session.press(key, delay)
    for _ in range(24):
        session.press("A", 240)
    for _ in range(48):
        session.press("A", 300)
    require(session.core.memory.u32[0x0200C640] == 0x0200A480, "Opening route did not expose expected inventory head")
    require(session.core.memory.u32[0x0200A480] == 0, "Fixture requires an empty first inventory record")
    return bytes(ffi.buffer(session.core.save_raw_state()))


def install_item(core, address, item, enhancement=0):
    # Existing record, not a new allocation. Restore the state after each case.
    for at in range(address, address + 24):
        core.memory.u8[at] = 0
    core.memory.u32[address] = 0x81800000
    core.memory.u16[address + 14] = item
    core.memory.u16[address + 16] = enhancement & 0xFFFF


def check_english_ui(trace, item, entries, rom, font):
    checks = []
    for family in TABLES:
        entry = next(e for e in entries if e["family"] == family and item in e["item_indices"])
        if family == "name" and item == 127:
            # Reserved row 127 is a projectile bundle record: its byte +0x15
            # selects another item-name row, zero in this disposable fixture.
            entry = next(e for e in entries if e["family"] == "name" and 0 in e["item_indices"])
        text = entry["english"]
        require(text is not None, "UI fixture needs an English draft")
        pointer_word = TABLES[family][0] + (0 if family == "name" and item == 127 else item) * 4
        source = struct.unpack_from("<I", rom, pointer_word)[0]
        reads = [r for r in trace.source_reads if int(r["address"], 16) == 0x08000000 + pointer_word]
        require(reads, f"No native item pointer read: {entry['id']}")
        if family == "description":
            draws = [d for d in trace.payloads if d["phase"] == "information" and int(d["address"], 16) == source]
            draws, repeated_draws = coalesce_empty_draw_observations(draws, trace.positions)
            require(len(draws) == 1 and (draws[0]["x"], draws[0]["y"]) == (0, 26), "Description did not reach its native panel")
        else:
            draws = [d for d in trace.payloads if d["phase"] in ("inventory", "information")
                     and (d["phase"] != "information" or d["y"] == 3)
                     and text.encode() in bytes.fromhex(d["raw_hex"]).split(b"\0", 1)[0]]
            draws, repeated_draws = coalesce_empty_draw_observations(draws, trace.positions)
            require({d["phase"] for d in draws} == {"inventory", "information"}, "Name missing from inventory or information header")
        for draw in draws:
            glyphs, repeats = distinct_glyph_observations([g for g in trace.positions if g["draw_serial"] == draw["serial"]])
            require(glyphs and all(g["font"] == 0 and g["spacing"] == 0 for g in glyphs), "Item text did not use unspaced font 0")
            expected = [font.glyph(c)[0] for c in text if c != "\n"]
            codes = [g["code"] for g in glyphs]
            if family == "description":
                require(codes == expected, "Description glyphs differ from English draft")
                index = 0
                for line_index, line in enumerate(text.split("\n")):
                    x = 0
                    for character in line:
                        glyph = glyphs[index]
                        _, advance, ink = font.glyph(character)
                        require((glyph["x"], glyph["y"]) == (x, 26 + 13 * line_index), "Unexpected description wrapping/position")
                        require(x + max(advance, ink) <= 192 and glyph["y"] + 12 <= 100,
                                "Description collides with window edge or footer")
                        x += advance
                        index += 1
            else:
                require(any(codes[i:i + len(expected)] == expected for i in range(len(codes))), "Native item-name glyph sequence differs")
                limit = 144 if draw["phase"] == "information" else glyphs[0]["window_width"]
                require(all(g["x"] + g["advance"] <= limit for g in glyphs), "Formatted name exceeds its native row")
            checks.append({"id": entry["id"], "phase": draw["phase"], "source": f"0x{source:08X}",
                           "pointer_read_instructions": sorted({r["instruction"] for r in reads}),
                           "glyphs": len(glyphs), "identical_glyph_reobservations": repeats,
                           "empty_duplicate_draw_observations": repeated_draws, "window_width": glyphs[0]["window_width"],
                           "max_advance_right": max(g["x"] + g["advance"] for g in glyphs)})
    return checks


def inventory_checks(session, state, catalog, language, output, item_ids=None):
    images, checks = {}, []
    font = FontZero(ORIGINAL_ROM.read_bytes())
    codec = GameTextCodec(ORIGINAL_ROM.read_bytes())
    for item in (STARTER_DRAFTS if item_ids is None else item_ids):
        require(session.core.load_raw_state(state), "Could not restore the empty inventory state")
        install_item(session.core, 0x0200A480, item)
        words = [0x08000000 + base + item * 4 for base, _ in TABLES.values()]
        if item == 127:
            words.append(0x0818F16C)
        trace = ItemTrace(session.core, words)
        folder = output / f"item-{item:03d}"
        folder.mkdir(parents=True, exist_ok=True)
        try:
            for phase, key in (("world-menu", "B"), ("inventory", "A"), ("actions", "A"), ("information", "A")):
                trace.phase = phase
                if phase == "information":
                    # Pots expose contents/use/name actions before Description.
                    # Select the actual Japanese command observed in the native
                    # menu, rather than assuming that every item shares row 0.
                    menu = [d for d in trace.report()["draws"] if d["phase"] == "actions" and d["window"] == 1]
                    description = [d for d in menu if "".join(t["text"] for t in
                        codec.parse(bytes.fromhex(d["preview_hex"]) + b"\0", 0)["tokens"] if t["kind"] == "text")
                        in ("説明", "Info")]
                    require(len(description) == 1, f"Cannot find native Description command for item {item}")
                    ys = sorted({d["y"] for d in menu})
                    for _ in range(ys.index(description[0]["y"])):
                        session.press("DOWN", 15, trace)
                session.press(key, 120, trace)
                if phase in ("inventory", "information"):
                    shot = session.screen.to_pil().convert("RGB")
                    shot.save(folder / f"{phase}.png")
                    images[item, phase] = shot
            # Assert the actual table source reached the normal information UI.
            desc = struct.unpack_from("<I", session.rom_data, TABLES["description"][0] + 4 * item)[0]
            require(any(d["phase"] == "information" and int(d["address"], 16) == desc for d in trace.payloads),
                    f"Controller route did not open item {item}'s description")
            if language == "english":
                checks.extend(check_english_ui(trace, item, catalog["entries"], session.rom_data, font))
            write_json(folder / "trace.json", {**trace.report(), "rom_sha256": digest(session.rom_data),
                       "fixture_item": item, "fixture_flags": "0x81800000", "enhancement": 0,
                       "inputs": session.frames_recorded[-4:]})
        finally:
            trace.close()
    return images, checks


def native_names(session, state, codec, output, cases=None):
    """Bounded calls of the real formatter, with guarded 100-byte destinations."""
    core = session.core
    cpu = ffi.cast("struct ARMCore*", core._core.cpu)
    record, dest, stack = 0x0203F000, 0x0203F100, 0x03007E00
    rows = []
    cases = ([(i, 0) for i in range(370)] + [(i, n) for i in (1, 3, 4, 5, 58) for n in (-99, 99)]) if cases is None else cases
    for item, enhancement in cases:
        require(core.load_raw_state(state), "Could not restore formatter fixture")
        install_item(core, record, item, enhancement)
        for at in range(dest - 8, dest + 108):
            core.memory.u8[at] = 0xA5
        core.memory.u32[stack] = 0
        for register, value in {"cpsr": 0xFF, "sp": stack, "r0": record, "r1": dest,
                                "r2": 0, "r3": 0, "lr": 0x08000001, "pc": 0x08080A5C}.items():
            require(core._core.writeRegister(core._core, register.encode(), ffi.new("uint32_t*", value)), "Register setup failed")
        loaded_words = []
        for steps in range(100000):
            pc = (int(cpu.gprs[15]) & 0xFFFFFFFF) - (2 if cpu.cpsr.packed & 0x20 else 4)
            if pc == 0x08000000:
                break
            if pc == 0x08080B62:
                word = int(cpu.gprs[0]) & 0xFFFFFFFF
                loaded_words.append({"word": f"0x{word:08X}", "target": f"0x{core.memory.u32[word]:08X}"})
            core.step()
        else:
            raise AssertionError(f"Item formatter did not return: {item}/{enhancement}")
        require(bytes(core.memory[dest - 8:dest]) == b"\xA5" * 8 and bytes(core.memory[dest + 100:dest + 108]) == b"\xA5" * 8,
                "Item formatter overwrote the 100-byte destination guards")
        parsed = codec.parse(bytes(core.memory[dest:dest + 100]), 0, maximum=100)
        require(parsed["end"] < 100, "Formatted name leaves no truncation reserve")
        rows.append({"item": item, "enhancement": enhancement, "bytes_including_nul": parsed["end"],
                     "output_hex": parsed["raw_hex"], "display": parsed["display"], "steps": steps,
                     "pointer_loads_at_08080B62": loaded_words, "guards_intact": True})
    write_json(output / "native-names.json", {"rom_sha256": digest(session.rom_data), "cases": rows})
    return rows


def verify(output=OUTPUT / "verification"):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    mgba.log.silence()
    original, catalog = ORIGINAL_ROM.read_bytes(), load_json(CATALOG)
    base, _ = build_name_rom(original)
    variants = {"baseline": base}
    builds = {}
    for language in ("japanese", "english"):
        variants[language], builds[language] = build_item_rom(original, catalog, language)
        require(variants[language] == (OUTPUT / f"torneko3-items-{language}.gba").read_bytes(), "Rebuild differs from delivered item ROM")
    with Session(original, output / "fresh-japanese-save") as session:
        session.frames(600)
        session.press("START", 240)
        initial_save, _, _ = create_adventure(session)
    require(session.disk_save == initial_save, "Initial native fixture save did not persist")
    images, formatted, native_checks = {}, {}, []
    for language, data in variants.items():
        folder = output / language
        with Session(data, folder, initial_save) as session:
            state = enter_world(session)
            session.capture("world")
            (folder / "world.state").write_bytes(state)
            write_json(folder / "route.json", {"rom_sha256": digest(data), "initial_save_sha256": digest(initial_save),
                       "emulator": "mGBA 0.10.5; built-in BIOS", "inputs": session.frames_recorded})
            images[language], checks = inventory_checks(session, state, catalog, language, folder)
            native_checks.extend(checks)
            formatted[language] = native_names(session, state, GameTextCodec(original), folder)
        print(f"{language}: 8 inventory/information fixtures and {len(formatted[language])} guarded native formatter calls passed", flush=True)
    for key in images["baseline"]:
        require(ImageChops.difference(images["baseline"][key], images["japanese"][key]).getbbox() is None,
                f"Japanese relocation changed native pixels: {key}")
        diff = ImageChops.difference(images["japanese"][key], images["english"][key]).getbbox()
        require(diff is not None, "English item did not change pixels")
        box = (8, 20, 232, 144) if key[1] == "information" else (8, 16, 184, 152)
        require(box[0] <= diff[0] and box[1] <= diff[1] and diff[2] <= box[2] and diff[3] <= box[3],
                "English item changed pixels outside its UI window")
    name_width_checks = []
    codec, font = GameTextCodec(original), FontZero(original)
    for before, after, english in zip(formatted["baseline"], formatted["japanese"], formatted["english"]):
        require(before["output_hex"] == after["output_hex"], "Japanese item relocation changed native name formatting")
        if before["item"] in STARTER_DRAFTS:
            entry = next(e for e in catalog["entries"] if e["family"] == "name" and before["item"] in e["item_indices"])
            require(entry["english"].encode() in bytes.fromhex(english["output_hex"]), "Native formatter lost English name")
            parsed = codec.parse(bytes.fromhex(english["output_hex"]), 0)
            x = right = 0
            for token in parsed["tokens"]:
                if token["kind"] == "text":
                    for character in token["text"]:
                        _, advance, ink = font.glyph(character)
                        if ink:
                            right = max(right, x + ink)
                        x += advance
            require(max(x, right) <= 144, "Decorated English name would overlap the information header's stats")
            name_width_checks.append({"item": before["item"], "enhancement": before["enhancement"],
                                      "formatted_bytes_including_nul": english["bytes_including_nul"],
                                      "formatted_width_from_font_metrics": max(x, right), "limit": 144})
        else:
            require(before["output_hex"] == english["output_hex"], "Undrafted item changed native name formatting")
    expected_ids = {e["id"] for e in catalog["entries"] if e["english"] is not None}
    require({c["id"] for c in native_checks} == expected_ids, "An English item draft lacks native UI coverage")
    save, _ = creation(variants["english"], output / "combined-save/create", 1)
    reload_name(variants["english"], save, output / "combined-save/reload", compact_name("Torneko"))
    montage = Image.new("RGB", (480, len(STARTER_DRAFTS) * 180), "#1c2025")
    drawing = ImageDraw.Draw(montage)
    for row, item in enumerate(STARTER_DRAFTS):
        drawing.text((4, row * 180 + 3), f"{item}: relocated Japanese", fill="white")
        drawing.text((244, row * 180 + 3), STARTER_DRAFTS[item][0], fill="white")
        for column, language in enumerate(("japanese", "english")):
            montage.paste(images[language][item, "information"], (column * 240, row * 180 + 20))
    montage.save(output / "item-comparison.png")
    report = {"source_sha256": digest(original), "rom_sha256": {k: digest(v) for k, v in variants.items()},
              "item_entries": 719, "pointer_words": 740, "japanese_pixel_pairs_identical": 16,
              "formatter_cases_per_variant": len(formatted["baseline"]), "formatter_guards_intact": True,
              "japanese_formatter_outputs_identical": True, "native_english_checks": native_checks,
              "formatted_english_width_checks": name_width_checks,
              "combined_torneko_save_cold_load": True, "save_bytes": len(save),
              "limits": "Controlled identified-item fixtures in the opening village; not a dungeon playthrough or all item states."}
    write_json(output / "report.json", report)
    require(ORIGINAL_ROM.read_bytes() == original, "Original ROM changed during verification")
    print(json.dumps({k: v for k, v in report.items() if k != "native_english_checks"}, indent=2))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT / "verification")
    args = parser.parse_args()
    verify(args.output)
