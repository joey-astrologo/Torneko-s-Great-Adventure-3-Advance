"""Native verification of unidentified names and synthesis descriptions."""

import argparse
import json
from pathlib import Path
import struct

import mgba.log
from mgba._pylib import ffi, lib
from PIL import Image, ImageChops, ImageDraw

from tools.build_first_label import ORIGINAL_ROM, digest
from tools.build_item_contexts import CATALOG, OUTPUT, TABLES, build_context_rom, encode_english
from tools.build_items import CATALOG as ITEMS, build_item_rom
from tools.build_name_entry import compact_name
from tools.game_text import GameTextCodec
from tools.translation_pipeline import FontZero, load_json
from tools.verify_expansion import Session, create_adventure
from tools.verify_first_label import require
from tools.verify_items import ItemTrace, enter_world, install_item, inventory_checks, write_json, distinct_glyph_observations, coalesce_empty_draw_observations
from tools.verify_name_entry import creation, reload_name

CATEGORY_ITEMS = {3: 64, 7: 133, 8: 190, 9: 247, 10: 273, 11: 304}
UNKNOWN_ROWS = (0, 52, 112, 172, 201, 234)
SYNTHESIS_ROWS = (1, 2, 33, 38)


def unidentified_state(core, original, item, row, mode="unknown"):
    core.memory.u32[0x02000000] = 1
    core.memory.u32[0x0200C71C] = 0
    core.memory.u16[0x0200C722 + 2 * item] = 0xFFF if mode == "identified" else row
    slot = max(0, struct.unpack_from("<h", original, 0xC4C4FC + 2 * item)[0])
    name = compact_name("Test") if mode == "custom" else b"\0"
    for i, value in enumerate(name.ljust(8, b"\0")):
        core.memory.u8[0x0200CA06 + 8 * slot + i] = value


class SynthesisTrace(ItemTrace):
    def __init__(self, core, words):
        self.wrappers, self.pending = [], None
        super().__init__(core, words)
        try:
            for address in (0x0806DFE0, 0x0806DFE4):
                point = ffi.new("struct mBreakpoint*")
                point.address, point.segment, point.type = address, -1, lib.BREAKPOINT_HARDWARE
                require(self.debugger.platform.setBreakpoint(self.debugger.platform, point) >= 0, "Could not trace synthesis wrapper")
        except Exception:
            self.close()
            raise

    def entered(self, debugger, reason, info):
        super().entered(debugger, reason, info)
        try:
            if info != ffi.NULL and reason == lib.DEBUGGER_ENTER_BREAKPOINT:
                if info.address == 0x0806DFE0:
                    regs = [int(r) & 0xFFFFFFFF for r in self.cpu.gprs]
                    dest = regs[0]
                    self.pending = {"destination": dest, "source": regs[3], "style": regs[2],
                                    "before_guard": bytes(self.core.memory[dest - 8:dest]).hex(),
                                    "after_guard": bytes(self.core.memory[dest + 1024:dest + 1032]).hex()}
                elif info.address == 0x0806DFE4:
                    require(self.pending is not None, "Wrapper returned without entry")
                    row, self.pending = self.pending, None
                    dest = row["destination"]
                    require(bytes(self.core.memory[dest - 8:dest]).hex() == row["before_guard"] and
                            bytes(self.core.memory[dest + 1024:dest + 1032]).hex() == row["after_guard"], "Synthesis wrapper changed buffer neighbors")
                    # Source strings contain only text/CR/1D; the style byte is nonzero.
                    raw = bytes(self.core.memory[dest:dest + 1024]).split(b"\0", 1)[0] + b"\0"
                    source = bytes(self.core.memory[row["source"]:row["source"] + 1024]).split(b"\0", 1)[0] + b"\0"
                    require(len(raw) <= 1024 and raw == b"\x03\x05" + bytes([row["style"]]) + source,
                            "Synthesis wrapper changed source bytes or exceeded capacity")
                    row.update(output_hex=raw.hex(), bytes_including_nul=len(raw), neighbors_preserved=True)
                    self.wrappers.append(row)
        except Exception as error:
            self.errors.append(str(error))
        finally:
            debugger.state = lib.DEBUGGER_RUNNING


def guarded_names(session, state, original, output):
    core, codec = session.core, GameTextCodec(original)
    cpu = ffi.cast("struct ARMCore*", core._core.cpu)
    record, dest, stack = 0x0203F000, 0x0203F100, 0x03007E00
    cases = [(row, "unknown") for row in range(246)] + [(row, mode) for row in UNKNOWN_ROWS for mode in ("identified", "custom")]
    results = []
    for row, mode in cases:
        require(core.load_raw_state(state), "Cannot restore name fixture")
        category = struct.unpack_from("<I", original, 0x190808 + 8 * row)[0]
        item = CATEGORY_ITEMS[category]
        install_item(core, record, item)
        unidentified_state(core, original, item, row, mode)
        for address in range(dest - 8, dest + 108):
            core.memory.u8[address] = 0xA5
        core.memory.u32[stack] = 0
        for register, value in {"cpsr": 0xFF, "sp": stack, "r0": record, "r1": dest, "r2": 0,
                                "r3": 0, "lr": 0x08000001, "pc": 0x08080A5C}.items():
            require(core._core.writeRegister(core._core, register.encode(), ffi.new("uint32_t*", value)), "Cannot set native-call registers")
        reads = []
        for steps in range(100000):
            pc = (int(cpu.gprs[15]) & 0xFFFFFFFF) - (2 if cpu.cpsr.packed & 0x20 else 4)
            if pc == 0x08000000:
                break
            if pc in (0x0808109A, 0x0808113E):
                word = int(cpu.gprs[0]) & 0xFFFFFFFF
                reads.append({"instruction": pc, "word": word, "target": core.memory.u32[word]})
            core.step()
        else:
            raise AssertionError(f"Name formatter did not return: {row}/{mode}")
        require(bytes(core.memory[dest - 8:dest]) == b"\xA5" * 8 and bytes(core.memory[dest + 100:dest + 108]) == b"\xA5" * 8,
                "Name formatter changed buffer guards")
        parsed = codec.parse(bytes(core.memory[dest:dest + 100]), 0, maximum=100)
        require(parsed["end"] < 100, "Name formatter left no truncation reserve")
        expected = 0x0819080C + row * 8
        require([r["word"] for r in reads] == ([expected] if mode == "unknown" else []), "Unexpected unidentified-name reader selection")
        if mode == "custom":
            require(b"Test" in bytes.fromhex(parsed["raw_hex"]), "Custom name path lost its Latin text")
        results.append({"row": row, "item": item, "mode": mode, "reads": reads, "output_hex": parsed["raw_hex"],
                        "display": parsed["display"], "bytes_including_nul": parsed["end"], "steps": steps, "guards_intact": True})
    write_json(output / "native-names.json", {"rom_sha256": digest(session.rom_data), "cases": results})
    return results


def english_glyphs(trace, entry, family, font):
    if family == "synthesis":
        draws = [d for d in trace.payloads if d["phase"] == "synthesis" and d["y"] == 48]
    else:
        needle = entry["english"].encode()
        draws = [d for d in trace.payloads if needle in bytes.fromhex(d["raw_hex"]).split(b"\0", 1)[0]]
    require(draws, "English draft did not reach a native draw")
    draws, repeated_draws = coalesce_empty_draw_observations(draws, trace.positions)
    checks = []
    for draw in draws:
        glyphs, repeats = distinct_glyph_observations([g for g in trace.positions if g["draw_serial"] == draw["serial"]])
        require(glyphs and all(g["font"] == 0 and g["spacing"] == 0 for g in glyphs), "Unexpected font or spacing")
        codes = [g["code"] for g in glyphs]
        expected = [font.glyph(c)[0] for c in entry["english"] if c != "\n"]
        if family == "synthesis":
            require(codes == expected, "Synthesis English glyph sequence differs")
            _, metrics = encode_english(entry, font)
            index = 0
            for line, y in zip(entry["english"].split("\n"), metrics["line_y"]):
                x = 0
                for c in line:
                    glyph = glyphs[index]
                    _, advance, ink = font.glyph(c)
                    require((glyph["x"], glyph["y"]) == (x, y), "Synthesis CR/1D placement changed")
                    require(x + max(advance, ink) <= 192 and y + 12 <= 100, "Synthesis text collides with edge/footer")
                    x += advance
                    index += 1
        else:
            require(any(codes[i:i + len(expected)] == expected for i in range(len(codes))), "Unidentified English glyphs differ")
            require(all(g["x"] + g["advance"] <= g["window_width"] for g in glyphs), "Unidentified name exceeds native row")
        checks.append({"id": entry["id"], "glyphs": len(glyphs), "identical_glyph_reobservations": repeats,
                       "empty_duplicate_draw_observations": repeated_draws, "window_width": glyphs[0]["window_width"],
                       "line_y": sorted({g["y"] for g in glyphs}), "max_advance_right": max(g["x"] + g["advance"] for g in glyphs)})
    return checks


def capture_contexts(session, state, original, catalog, language, output, cases=None):
    require(session.core.load_raw_state(state), "Cannot restore world fixture")
    session.press("B", 120)
    menu = bytes(ffi.buffer(session.core.save_raw_state()))
    font, images, checks, wrappers, diagnostics = FontZero(original), {}, [], [], {}
    cases = ([("unidentified", row, False) for row in UNKNOWN_ROWS] + [("synthesis", row, False) for row in range(100)] + [("synthesis", 1, True)]) if cases is None else cases
    for family, row, high_bit in cases:
        require(session.core.load_raw_state(menu), "Cannot restore menu fixture")
        entry = next(e for e in catalog["entries"] if e["family"] == family and row in e["rows"])
        base, _, stride, field = TABLES[family]
        word = 0x08000000 + base + row * stride + field
        if family == "unidentified":
            item = CATEGORY_ITEMS[entry["category_fields"][0]["value"]]
            install_item(session.core, 0x0200A480, item)
            unidentified_state(session.core, original, item, row)
        else:
            item = 58 if 33 <= row <= 37 or row == 86 else 133 if 38 <= row <= 85 else 1
            install_item(session.core, 0x0200A480, item)
            session.core.memory.u32[0x0200A480] |= 0x08000000
            session.core.memory.u8[0x0200A484] = row | (0x80 if high_bit else 0)
            session.core.memory.u8[0x0200A492] = 1
        trace = SynthesisTrace(session.core, [word]) if family == "synthesis" else ItemTrace(session.core, [word])
        key = f"{family}-{row:03d}" + ("-high-bit" if high_bit else "")
        folder = output / key
        folder.mkdir(parents=True, exist_ok=True)
        try:
            trace.phase = "inventory"
            session.press("A", 120, trace)
            if family == "synthesis":
                trace.phase = "actions"
                session.press("A", 120, trace)
                trace.phase = "synthesis"
                session.press("A", 120, trace)
            require(any(int(r["address"], 16) == word for r in trace.source_reads), f"No native table read: {key}")
            if family == "synthesis":
                require(len(trace.wrappers) == 1, "Expected one native synthesis wrapper")
                require(trace.wrappers[0]["source"] == session.core.memory.u32[word], "Wrapper read a different synthesis source")
                wrappers.append({"case": key, **trace.wrappers[0]})
            if language == "english" and entry["english"] is not None:
                checks.extend(english_glyphs(trace, entry, family, font))
            shot = session.screen.to_pil().convert("RGB")
            images[key] = shot
            shot.save(folder / "screen.png")
            write_json(folder / "trace.json", {**trace.report(), "rom_sha256": digest(session.rom_data), "row": row,
                       "item": item, "high_bit": high_bit, "controlled_mode": family == "unidentified"})
            if family == "synthesis" and entry["english"] is not None:
                # Keep normal captures as the acceptance images. A separate
                # diagnostic distinguishes animated sprites under translucent
                # windows from changes to the native background/text layers.
                session.core._native.video.renderer.disableOBJ = True
                try:
                    session.frames(1, trace)
                    diagnostic = session.screen.to_pil().convert("RGB")
                    diagnostic.save(folder / "diagnostic-objects-disabled.png")
                    diagnostics[key] = diagnostic
                finally:
                    session.core._native.video.renderer.disableOBJ = False
        except Exception:
            write_json(folder / "failure.json", {"case": key, "rom_sha256": digest(session.rom_data),
                "trace": trace.report(), "payloads": trace.payloads, "positions": trace.positions})
            session.capture("failure-" + key)
            raise
        finally:
            trace.close()
    write_json(output / "synthesis-wrappers.json", {"rom_sha256": digest(session.rom_data), "calls": wrappers})
    return images, checks, wrappers, diagnostics


def verify(output=OUTPUT / "verification"):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    mgba.log.silence()
    original, catalog, items = ORIGINAL_ROM.read_bytes(), load_json(CATALOG), load_json(ITEMS)
    variants = {"baseline": build_item_rom(original, items)[0]}
    for language in ("japanese", "english"):
        variants[language], _ = build_context_rom(original, catalog, language)
        require(variants[language] == (OUTPUT / f"torneko3-item-contexts-{language}.gba").read_bytes(), "Context build differs from delivered ROM")
    with Session(original, output / "fresh-japanese-save") as session:
        session.frames(600)
        session.press("START", 240)
        save, _, _ = create_adventure(session)
    require(save == session.disk_save, "Native fixture save did not persist")
    images, names, wrappers, checks, diagnostics = {}, {}, {}, [], {}
    for language, data in variants.items():
        folder = output / language
        with Session(data, folder, save) as session:
            state = enter_world(session)
            write_json(folder / "route.json", {"rom_sha256": digest(data), "initial_save_sha256": digest(save), "inputs": session.frames_recorded})
            images[language], observed, wrappers[language], diagnostics[language] = capture_contexts(session, state, original, catalog, language, folder)
            checks.extend(observed)
            names[language] = guarded_names(session, state, original, folder)
            if language == "english":
                inventory_checks(session, state, items, "english", folder / "ordinary-item-regression")
        print(f"{language}: {len(images[language])} native UI cases and {len(names[language])} guarded formatter calls passed", flush=True)
    sprite_diagnostics = []
    for key, image in images["baseline"].items():
        require(ImageChops.difference(image, images["japanese"][key]).getbbox() is None, f"Japanese relocation changed pixels: {key}")
        diff = ImageChops.difference(images["japanese"][key], images["english"][key]).getbbox()
        family, row = key.split("-")[:2]
        entry = next(e for e in catalog["entries"] if e["family"] == family and int(row) in e["rows"])
        if entry["english"] is None:
            require(diff is None, "Undrafted context changed pixels")
        else:
            box = (24, 72, 216, 124) if family == "synthesis" else (8, 16, 184, 152)
            require(diff, "English context did not change pixels")
            within_text = box[0] <= diff[0] and box[1] <= diff[1] and diff[2] <= box[2] and diff[3] <= box[3]
            if not within_text:
                require(family == "synthesis" and 24 <= diff[0] and 24 <= diff[1] and diff[2] <= 216 and diff[3] <= 136,
                        f"English changed pixels outside item UI: {key}/{diff}")
                diagnostic = ImageChops.difference(diagnostics["japanese"][key], diagnostics["english"][key])
                diagnostic.paste((0, 0, 0), box)
                require(diagnostic.getbbox() is None, f"Non-object pixels changed outside translated text: {key}")
                extra = ImageChops.difference(images["japanese"][key], images["english"][key])
                extra.paste((0, 0, 0), box)
                sprite_diagnostics.append({"case": key, "normal_extra_bounds": extra.getbbox(),
                                           "diagnostic": "one additional frame with OBJ rendering disabled",
                                           "outside_text_background_pixels_identical": True})
    for before, japanese, english in zip(names["baseline"], names["japanese"], names["english"]):
        require(before["output_hex"] == japanese["output_hex"], "Japanese relocation changed unidentified formatting")
        entry = next(e for e in catalog["entries"] if e["family"] == "unidentified" and before["row"] in e["rows"])
        if before["mode"] == "unknown" and entry["english"] is not None:
            require(entry["english"].encode() in bytes.fromhex(english["output_hex"]), "English unidentified name missing")
        else:
            require(before["output_hex"] == english["output_hex"], "Relocation changed an undrafted/identified/custom name")
    require({c["id"] for c in checks} == {e["id"] for e in catalog["entries"] if e["english"] is not None}, "English context lacks native coverage")
    new_save, _ = creation(variants["english"], output / "combined-save/create", 1)
    reload_name(variants["english"], new_save, output / "combined-save/reload", compact_name("Torneko"))
    keys = [f"unidentified-{r:03d}" for r in UNKNOWN_ROWS] + [f"synthesis-{r:03d}" for r in SYNTHESIS_ROWS]
    montage = Image.new("RGB", (480, len(keys) * 180), "#1c2025")
    draw = ImageDraw.Draw(montage)
    for row, key in enumerate(keys):
        for column, language in enumerate(("japanese", "english")):
            draw.text((column * 240 + 4, row * 180 + 3), f"{key}: {language}", fill="white")
            montage.paste(images[language][key], (column * 240, row * 180 + 20))
    montage.save(output / "comparison.png")
    report = {"source_sha256": digest(original), "rom_sha256": {k: digest(v) for k, v in variants.items()},
              "emulator": "mGBA 0.10.5; built-in BIOS", "japanese_pixel_pairs_identical": len(images["baseline"]),
              "unidentified_table_words_native": 246, "synthesis_table_words_native": 100,
              "name_formatter_cases_per_variant": len(names["baseline"]), "synthesis_wrapper_cases_per_variant": len(wrappers["baseline"]),
              "native_english_checks": checks, "buffer_guards_and_neighbors_preserved": True,
              "background_sprite_diagnostics": sprite_diagnostics,
              "identified_and_custom_name_regressions": True, "ordinary_english_items_regression": True,
              "torneko_save_cold_load": True, "save_bytes": len(new_save),
              "scope": "Controlled inventory/identification/effect fixtures; no claim of dungeon playthrough, natural identification, or synthesis execution."}
    write_json(output / "report.json", report)
    require(ORIGINAL_ROM.read_bytes() == original, "Original ROM changed")
    print(json.dumps({k: v for k, v in report.items() if k != "native_english_checks"}, indent=2))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT / "verification")
    args = parser.parse_args()
    verify(args.output)
