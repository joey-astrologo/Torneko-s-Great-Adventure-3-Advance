"""Check the curated English batch with native, unmodified mGBA rendering."""

import argparse
import json
from pathlib import Path
import struct

import mgba.log
from mgba._pylib import ffi, lib
from PIL import Image, ImageChops, ImageDraw

from tools.build_first_label import ORIGINAL_ROM, digest
from tools.font_metrics import extract_fonts
from tools.review_fonts import draw_glyph
from tools.trace_text_systems import ReaderTrace, hex_address
from tools.translation_pipeline import ANCHORS, CATALOG, OUTPUT, build_rom, load_json
from tools.verify_expansion import Session, cold_reload, create_adventure
from tools.verify_first_label import battery_snapshot, require


def identify_wrapped_source(raw, sources, events):
    """Match complete payloads, disambiguating duplicates by traced source reads."""
    if not raw.startswith(b"\x03\x05"):
        return None
    matches = [source for source, payload in sources.items()
               if raw[3:].startswith(payload) or raw[3:].startswith(payload[:-1] + b"\x03\x06\0")]
    if not matches:
        return None
    source = max(matches, key=lambda s: events.get(s, -1))
    require(source in events, "Wrapped text lacks a traced source read")
    return source


def require_coverage(allocations, checks, expected=None):
    covered = {c["id"] for c in checks}
    require(covered == allocations.keys(), f"Translated entries lack native verification: {sorted(allocations.keys() - covered)}")
    if expected is not None:
        for ident in covered:
            required = {v["slot"] for v in expected[ident]["variants"]}
            observed = {c["slot"] for c in checks if c["id"] == ident}
            require(required <= observed, f"Substitution variants lack native verification: {ident}")
    return covered


class TranslationTrace(ReaderTrace):
    """Observe the selected font and positions without changing game memory."""

    def __init__(self, core, watch_addresses=(), sources=None, pointer_sources=None):
        self.positions = []
        self.formatted_sources = {}
        self.draw_source, self.glyph_caller = None, None
        self.message_source, self.story_source = None, None
        self.sources, self.pointer_sources = sources or {}, pointer_sources or {}
        self.source_events, self.event_counter = {}, 0
        self.draw_sources = []
        super().__init__(core, watch_addresses)
        try:
            point = ffi.new("struct mBreakpoint*")
            point.address, point.segment, point.type = 0x0808BC78, -1, lib.BREAKPOINT_HARDWARE
            require(self.debugger.platform.setBreakpoint(self.debugger.platform, point) >= 0,
                    "Could not install glyph-position breakpoint")
        except Exception:
            self.close()
            raise

    def entered(self, debugger, reason, info):
        try:
            if info != ffi.NULL and reason == lib.DEBUGGER_ENTER_WATCHPOINT:
                address = int(info.address)
                source = address if address in self.sources else self.pointer_sources.get(address)
                if source is not None:
                    self.event_counter += 1
                    self.source_events[source] = self.event_counter
            if info != ffi.NULL and reason == lib.DEBUGGER_ENTER_BREAKPOINT:
                regs = [int(r) & 0xFFFFFFFF for r in self.cpu.gprs]
                if info.address == 0x0807D8CC:
                    self.formatted_sources[regs[1]] = regs[0]
                    caller = (regs[14] & ~1) - 4
                    if caller == 0x0807AE04:
                        self.message_source = regs[0]
                    elif caller == 0x08061726:
                        self.story_source = regs[0]
                elif info.address == 0x0808CBA0:
                    self.draw_source = self.formatted_sources.get(regs[2], regs[2])
                    raw = bytes(self.core.memory[regs[2]:regs[2] + 512])
                    wrapped_source = identify_wrapped_source(raw, self.sources, self.source_events)
                    if wrapped_source is not None:
                        self.draw_source = wrapped_source
                    self.draw_sources.append({"phase": self.phase, "frame": self.core.frame_counter,
                                              "source": hex_address(self.draw_source),
                                              "address": hex_address(regs[2]), "x": regs[0], "y": regs[1],
                                              "wrapped": raw.startswith(b"\x03\x05")})
                elif info.address == 0x0808BC4C:
                    self.glyph_caller = (regs[14] & ~1) - 4
                elif info.address == 0x0808BC78:
                    descriptor, window = regs[0], regs[4]
                    _, code, advance = struct.unpack("<IHh", bytes(self.core.memory[descriptor:descriptor + 8]))
                    tile_x, tile_y, tiles_w = struct.unpack("<hhh", bytes(self.core.memory[window:window + 6]))
                    source = {0x0808CD04: self.draw_source, 0x0808CD38: self.draw_source,
                              0x0807AF6A: self.message_source, 0x08061B4E: self.story_source}.get(self.glyph_caller)
                    self.positions.append({"phase": self.phase, "frame": self.core.frame_counter,
                                           "caller": hex_address(self.glyph_caller),
                                           "source": hex_address(source) if source is not None else None,
                                           "code": code, "advance": advance, "x": regs[6], "y": regs[8],
                                           "font": self.core.memory.u32[0x020398F8],
                                           "spacing": struct.unpack("<h", bytes(self.core.memory[0x020398DC:0x020398DE]))[0],
                                           "window_origin": [tile_x * 8, tile_y * 8], "window_width": tiles_w * 8})
                    require(len(self.positions) < 20000, "Unexpectedly large position trace")
                    return
            super().entered(debugger, reason, info)
        except Exception as error:
            self.errors.append(str(error))
        finally:
            debugger.state = lib.DEBUGGER_RUNNING

    def report(self):
        return {**super().report(), "positions": self.positions, "draw_sources": self.draw_sources}


def capture(data, output, route, watch_addresses, initial_save=None, sources=None, pointer_sources=None):
    with Session(data, output, initial_save) as session:
        session.frames(600)
        trace = TranslationTrace(session.core, watch_addresses, sources, pointer_sources)
        original_frames, original_capture = session.frames, session.capture
        session.frames = lambda count, unused=None: trace.frames(count)

        screenshots = []

        def screenshot(name):
            result = original_capture(name)
            screenshots.append(name + ".png")
            trace.phase = "after-" + name
            return result

        session.capture = screenshot
        created = None
        try:
            trace.phase = "title-menu"
            session.press("START", 240)
            session.capture("title-menu")
            if route in ("creation", "creation-two"):
                created, _, _ = create_adventure(session, slot=2 if route == "creation-two" else 1)
            elif route == "settings":
                session.press("DOWN", 30)
                session.press("A")
                session.capture("settings")
                session.press("RIGHT", 30)
                session.capture("settings-fast")
                session.press("LEFT", 30)
                session.capture("settings-normal")
                session.press("LEFT", 30)
                session.capture("settings-slow")
                session.press("RIGHT", 30)
                session.press("DOWN", 30)
                session.press("LEFT", 30)
                session.capture("display-bold")
                session.press("LEFT", 30)
                session.capture("display-light")
                session.press("RIGHT", 30)
                session.press("RIGHT", 30)
                session.capture("display-normal")
                session.press("B")
                session.capture("settings-back")
            elif route == "slot-two":
                session.press("A")
                session.capture("slots")
                session.press("DOWN", 30)
                session.press("A")
                session.capture("new-log-explanation")
            elif route in ("story", "story-two"):
                session.press("A")
                session.capture("slots")
                # Continue selects the populated slot automatically on these one-save fixtures.
                session.press("A")
                session.capture("loaded")
                session.press("A", 1200)
                session.capture("story-page-1")
                session.press("A", 600)
                session.capture("story-page-2")
            report = {**trace.report(), "route": route, "rom_sha256": digest(data),
                      "initial_save_sha256": digest(initial_save) if initial_save else None,
                      "inputs": session.frames_recorded, "screenshots": screenshots}
            report["battery_sha256"] = digest(battery_snapshot(session.core))
        finally:
            session.frames = original_frames
            trace.close()
    require(digest(session.disk_save) == report["battery_sha256"], "Native save did not persist to disk")
    if created is not None:
        require(created == session.disk_save, "Created save differs from the native file")
    (output / "readers.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return report, session.disk_save


def check_entry(trace, anchor, allocation, expected, profile, slot):
    ident, source = anchor["id"], allocation["address"]
    variant = next(v for v in expected["variants"] if v["slot"] in (None, slot))
    formats = [f for f in trace["formats"] if f["source"] == source]
    reader = anchor["reader"]
    glyphs = [g for g in trace["positions"] if g["source"] == source]
    require(glyphs, f"No native glyphs for {ident}")
    phase = glyphs[0]["phase"]
    glyphs = [g for g in glyphs if g["phase"] == phase]
    if reader in ("settings", "message", "story"):
        require(formats, f"Formatter did not receive {ident}")
        for call in formats:
            require(call["output_hex"] == variant["payload_hex"] + "00", f"Formatter changed/truncated {ident}")
            require(call["written_bytes"] == variant["payload_bytes"], f"Wrong formatted size for {ident}")
            require(call["payload_limit"] == profile["payload_limit"], f"RAM limit changed for {ident}")
            require(call["line_mode"] == (1 if reader == "settings" else 0), f"Line mode changed for {ident}")
        require(any(r["address"] == source and r["instruction"] == "0x0807DBB2"
                    for r in trace["source_reads"]), f"Formatter did not read appended text for {ident}")
    else:
        require(any(r["address"] == source for r in trace["source_reads"]), f"Source text was not read for {ident}")
        require(any(d["source"] == source for d in trace["draw_sources"]), f"No direct/menu draw for {ident}")
    if reader in ("menu", "settings"):
        require(any(d["source"] == source and d["wrapped"] for d in trace["draw_sources"]),
                f"No verified drawing wrapper for {ident}")
    require(all(any(int(r["address"], 16) == 0x08000000 + int(p, 0) for r in trace["source_reads"])
                for p in anchor["pointers"]), f"Source pointer was not read for {ident}")
    expected_glyphs = [g for line in variant["lines"] for g in line["glyphs"]]
    require([g["code"] for g in glyphs] == [g["code"] for g in expected_glyphs],
            f"Native glyph sequence differs for {ident}: observed {len(glyphs)}, expected {len(expected_glyphs)}")
    for actual, predicted in zip(glyphs, expected_glyphs):
        require(actual["font"] == 0 and actual["spacing"] == 0, f"Unexpected font/spacing in {ident}")
        require((actual["x"], actual["advance"]) == (predicted["x"], predicted["advance"]),
                f"Native glyph position differs for {ident}: {actual} vs {predicted}")
        if profile.get("dynamic_width"):
            require(actual["window_width"] <= profile["width"], f"Menu expanded beyond its original width for {ident}")
            require(max(variant["lines"][0]["end_x"], variant["lines"][0]["ink_right"]) <= actual["window_width"],
                    f"Translated menu label is clipped for {ident}")
        else:
            require(actual["window_width"] == profile["width"], f"Window width changed for {ident}")
    offset, ys = 0, []
    for line in variant["lines"]:
        count = len(line["glyphs"])
        row = glyphs[offset:offset + count]
        require(row and len({g["y"] for g in row}) == 1, f"Unexpected line layout for {ident}")
        ys.append(row[0]["y"])
        offset += count
    require(all(b - a == 12 for a, b in zip(ys, ys[1:])), f"Unexpected line spacing in {ident}")
    return {"id": ident, "route": trace["route"], "slot": variant["slot"], "phase": phase,
            "glyph_count": len(glyphs), "native_font": 0, "glyph_positions_match": True,
            "window_widths": sorted({g["window_width"] for g in glyphs}),
            "formatter_output_matches": bool(formats), "line_y": ys,
            "formatter_payload_limits": sorted({f["payload_limit"] for f in formats}),
            "glyphs": glyphs}


def compare_screens(original_dir, english_dir, names):
    """Allow translated text and the enclosing automatically sized menu panels."""
    masks = {
        "title-menu": [(28, 16, 104, 64)],
        "slots": [(28, 16, 104, 64), (124, 16, 200, 40), (16, 112, 224, 124)],
        "slot-two-selected": [(28, 16, 104, 64), (124, 16, 200, 40), (16, 112, 224, 124)],
        "new-log-explanation": [(16, 122, 224, 158)],
        "settings": [(28, 16, 176, 54)],
        "settings-fast": [(28, 16, 176, 54)],
        "settings-normal": [(28, 16, 176, 54)],
        "settings-slow": [(28, 16, 176, 54)],
        "display-bold": [(28, 16, 176, 54)],
        "display-light": [(28, 16, 176, 54)],
        "display-normal": [(28, 16, 176, 54)],
        "settings-back": [(28, 16, 104, 64)],
        "story-page-1": [(16, 66, 224, 102)],
        "name-confirmation": [(168, 72, 232, 120)],
        "mode-menu": [(136, 32, 232, 120), (16, 122, 224, 158)],
        "mode-confirmation": [(168, 72, 232, 120), (16, 122, 224, 158)],
        "save-created": [(16, 122, 224, 158)],
        "loaded": [(16, 122, 224, 158)],
    }
    screenshots = []
    for name in names:
        path = original_dir / name
        with Image.open(path) as a, Image.open(english_dir / path.name) as b:
            original, english = a.convert("RGB"), b.convert("RGB")
            difference = ImageChops.difference(original, english)
            original_bounds = difference.getbbox()
            for box in masks.get(path.stem, []):
                difference.paste((0, 0, 0), box)
            require(difference.getbbox() is None, f"Unexpected pixels outside translated regions: {path}; {difference.getbbox()}")
            screenshots.append({"name": path.name, "text_difference_bounds": original_bounds,
                                "allowed_regions": masks.get(path.stem, []),
                                "outside_translated_regions_identical": True,
                                "english_rgb_sha256": digest(english.tobytes())})
    require(screenshots, "No screenshots to compare")
    return screenshots


def verify(rom=ORIGINAL_ROM, catalog_path=CATALOG, anchors_path=ANCHORS, output=OUTPUT):
    rom, output = Path(rom).resolve(), Path(output).resolve()
    original = rom.read_bytes()
    catalog, anchors = load_json(catalog_path), load_json(anchors_path)
    japanese, ja_report = build_rom(original, catalog, anchors, "japanese")
    english, en_report = build_rom(original, catalog, anchors)
    require(japanese == original, "Japanese round trip changed bytes")
    require((output / "torneko3-japanese-roundtrip.gba").read_bytes() == japanese, "Rebuild Japanese output before verification")
    require((output / "torneko3-english.gba").read_bytes() == english, "Rebuild English output before verification")
    allocations = {a["id"]: a for a in en_report["allocations"]}
    require(allocations, "No translated entries to verify")
    sources, pointers = {}, {}
    for variant, data in (("original", original), ("english", english)):
        sources[variant], pointers[variant] = {}, {}
        for anchor in anchors["entries"]:
            if anchor["id"] not in allocations:
                continue
            offset = (int(anchor["offset"], 0) if variant == "original" else allocations[anchor["id"]]["offset"])
            source = 0x08000000 + offset
            raw = bytes.fromhex(next(e["source_hex"] for e in catalog["entries"] if e["id"] == anchor["id"])) if variant == "original" else data[offset:offset + allocations[anchor["id"]]["bytes"]]
            sources[variant][source] = raw[1:] if anchor["reader"] == "menu" and raw.startswith(b"*") else raw
            for p in anchor["pointers"]:
                pointers[variant][0x08000000 + int(p, 0)] = source
    mgba.log.silence()
    saves, traces, screens, checks = {}, {}, {}, []
    for route in ("settings", "creation", "story", "slot-two", "creation-two", "story-two"):
        for variant, data in (("original", original), ("english", english)):
            watched = list(sources[variant]) + list(pointers[variant])
            trace, save = capture(data, output / "verification" / variant / route, route,
                                  watched, saves[(variant, route == "story-two")] if route in ("story", "story-two") else None,
                                  sources[variant], pointers[variant])
            traces[(variant, route)] = trace
            if route in ("creation", "creation-two"):
                saves[(variant, route == "creation-two")] = save
        require(traces[("original", route)]["screenshots"] == traces[("english", route)]["screenshots"],
                "Screenshot routes differ")
        screens[route] = compare_screens(output / "verification/original" / route,
                                        output / "verification/english" / route,
                                        traces[("original", route)]["screenshots"])
        for anchor in anchors["entries"]:
            profile = anchor["profile"]
            include = anchor["id"] in allocations and any(
                g["source"] == allocations[anchor["id"]]["address"] for g in traces[("english", route)]["positions"])
            if include:
                checks.append(check_entry(traces[("english", route)], anchor, allocations[anchor["id"]],
                                          en_report["checks"][anchor["id"]], anchors["profiles"][profile],
                                          "２" if route in ("slot-two", "creation-two", "story-two") else "１"))
        print(f"Passed {route}: pixels outside translated regions, source reads, and native glyph positions", flush=True)
    covered = require_coverage(allocations, checks, en_report["checks"])
    for second in (False, True):
        require(saves[("original", second)] == saves[("english", second)], "The new-adventure route produced different save data")
    _, cross_report = cold_reload(original, saves[("english", False)], output / "verification/cross-load-original")
    # Reproduce translated narration from font pixels; null narration must match Japanese.
    story_check = next((c for c in checks if c["id"] == "story.opening_01"), None)
    story_path = output / "verification/english/story/story-page-1.png"
    if story_check is not None:
        font = extract_fonts(original)[0]
        expected = Image.new("RGB", (240, 160), "black")
        for glyph in story_check["glyphs"]:
            bitmap = draw_glyph(font, chr(glyph["code"]), [(255, 255, 255)] * 16)
            ox, oy = glyph["window_origin"]
            expected.paste(bitmap, (ox + glyph["x"], oy + glyph["y"]), bitmap)
    else:
        with Image.open(output / "verification/original/story/story-page-1.png") as source_image:
            expected = source_image.convert("RGB")
    with Image.open(story_path) as observed:
        require(ImageChops.difference(expected, observed.convert("RGB")).getbbox() is None,
                "English story pixels differ from the expected font rendering or untranslated source")
    require(rom.read_bytes() == original, "Japanese source ROM changed")
    report = {"passed": True, "emulator": "mGBA 0.10.5; built-in BIOS; no font or memory overrides",
              "japanese_roundtrip_identical": True, "japanese_sha256": ja_report["rom_sha256"],
              "english_sha256": en_report["rom_sha256"], "catalog_sha256": en_report["catalog_sha256"],
              "anchors_sha256": en_report["anchors_sha256"],
              "appended_used_with_padding": en_report["appended_used_with_padding"],
              "appended_remaining": en_report["appended_remaining"], "screenshots": screens,
              "translated_entries": len(allocations), "verified_entries": sorted(covered),
              "entry_checks": [{k: v for k, v in c.items() if k != "glyphs"} for c in checks],
              "native_saves_identical_and_persisted": True, "save_bytes": len(saves[("english", False)]),
              "save_sha256": digest(saves[("english", False)]),
              "slot_two_save_sha256": digest(saves[("english", True)]),
              "english_save_loads_in_original": cross_report,
              "story_pixels_reconstructed_from_original_font": story_check is not None,
              "scope": "Curated early-menu batch, both new-log slot numbers, settings navigation, adventure creation, cold load, and two story pages. Name-entry and full gameplay remain outside this batch."}
    (output / "verification.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    # Small native-pixel contact sheet for visual review.
    sheet = Image.new("RGB", (720, 360), "#18202b")
    draw = ImageDraw.Draw(sheet)
    for index, (label, path) in enumerate((("Saved title / slots", "story/slots.png"),
                                         ("Settings", "settings/settings.png"),
                                         ("Mode selection", "creation/mode-menu.png"),
                                         ("Mode confirmation", "creation/mode-confirmation.png"),
                                         ("Adventure created", "creation/save-created.png"),
                                         ("Opening narration", "story/story-page-1.png"))):
        x, y = index % 3 * 240, index // 3 * 180
        draw.text((x + 4, y + 2), label, fill="white")
        with Image.open(output / "verification/english" / path) as screenshot:
            sheet.paste(screenshot, (x, y + 20))
    sheet.save(output / "early-menus.png")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rom", nargs="?", type=Path, default=ORIGINAL_ROM)
    parser.add_argument("--catalog", type=Path, default=CATALOG)
    parser.add_argument("--anchors", type=Path, default=ANCHORS)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    result = verify(args.rom, args.catalog, args.anchors, args.output)
    print(json.dumps({k: v for k, v in result.items() if k not in ("screenshots", "entry_checks")}, indent=2))
