"""Native display/copy fixtures for the complete dungeon-interface catalog."""

import json
from pathlib import Path
import struct

import mgba.log
from mgba._pylib import ffi, lib
from PIL import ImageChops

from tools.build_first_label import ORIGINAL_ROM, digest
from tools.build_dungeon_interface import CATALOG, OUTPUT, TABLES, ACTION_BASE, ACTION_STRIDE
from tools.game_text import GameTextCodec
from tools.translation_pipeline import FontZero, load_json
from tools.verify_expansion import Session
from tools.verify_first_label import require
from tools.verify_items import ItemTrace, install_item, write_json, distinct_glyph_observations

STATE = Path("build/enemy-items/verification/save/world.state")
BREAKS = (0x0808C72C, 0x0808CBA0, 0x0808BC4C, 0x0808BC78, 0x0807D8CC, 0x0807DBDE)


def registers(core, values):
    for name, value in values.items():
        require(core._core.writeRegister(core._core, name.encode(), ffi.new("uint32_t*", value & 0xFFFFFFFF)),
                f"Cannot set register {name}")


class InterfaceTrace(ItemTrace):
    def __init__(self, core, action=None, story_source=None, watch_addresses=()):
        self.action, self.fixture_story_source, self.redirects = action, story_source, 0
        self.table_reads = []
        super().__init__(core, watch_addresses)
        for address in (0x0806FBC4, 0x0807000C, 0x08061680):
            point = ffi.new("struct mBreakpoint*")
            point.address, point.segment, point.type = address, -1, lib.BREAKPOINT_HARDWARE
            require(self.debugger.platform.setBreakpoint(self.debugger.platform, point) >= 0, "Cannot install interface probe")

    def entered(self, debugger, reason, info):
        try:
            if info != ffi.NULL and reason == lib.DEBUGGER_ENTER_BREAKPOINT:
                if info.address in (0x0806FBC4, 0x0807000C) and self.action is not None:
                    registers(self.core, {"r4": self.action})
                    if self.action == 9:
                        # Command 9 intentionally takes a caller's label; feed
                        # its own placeholder in this synthetic coverage case.
                        stack = int(self.cpu.gprs[13]) & 0xFFFFFFFF
                        delta = 0x118 if info.address == 0x0806FBC4 else 0xD0
                        literal = 0x0806FBF4 if info.address == 0x0806FBC4 else 0x0807003C
                        self.core.memory.u32[stack + delta] = self.core.memory.u32[literal] + 9 * 12
                    self.redirects += 1
                if (info.address == 0x0807D8CC and self.fixture_story_source is not None and self.redirects == 0
                        and (int(self.cpu.gprs[14]) & ~1) == 0x0806172A):
                    registers(self.core, {"r0": self.fixture_story_source})
                    self.redirects += 1
            super().entered(debugger, reason, info)
            if info != ffi.NULL and reason == lib.DEBUGGER_ENTER_BREAKPOINT and info.address == 0x0808BC78:
                window = int(self.cpu.gprs[4]) & 0xFFFFFFFF
                self.positions[-1]["window_height"] = self.core.memory.u16[window + 6] * 8
        except Exception as error:
            self.errors.append(str(error))
        finally:
            debugger.state = lib.DEBUGGER_RUNNING


def native_step(session, trace, function, args, stop=0x08000000, overrides=None):
    """Execute original instructions, sampling the same reader/glyph entries.

    core.step() bypasses mDebuggerRunFrame, so observations are dispatched at
    exact instruction PCs here. No rendering/reflow is implemented in Python.
    CPU context is restored after the bounded UI/copy helper; fixture RAM is
    discarded when the next case restores the saved state.
    """
    core, cpu = session.core, trace.cpu
    saved = {f"r{i}": int(cpu.gprs[i]) & 0xFFFFFFFF for i in range(15)}
    cpsr = int(cpu.cpsr.packed)
    saved_pc = (int(cpu.gprs[15]) & 0xFFFFFFFF) - (2 if cpsr & 32 else 4)
    registers(core, {"cpsr": 0xFF, "sp": 0x03007E00, **{f"r{i}": x for i, x in enumerate(args[:4])},
                     "lr": 0x08000001, "pc": function})
    for i, value in enumerate(args[4:]):
        core.memory.u32[0x03007E00 + 4 * i] = value
    info = ffi.new("struct mDebuggerEntryInfo*")
    for steps in range(500000):
        thumb = bool(cpu.cpsr.packed & 32)
        pc = (int(cpu.gprs[15]) & 0xFFFFFFFF) - (2 if thumb else 4)
        if pc == stop:
            break
        if overrides and pc in overrides:
            registers(core, overrides[pc])
        if pc in BREAKS:
            info.address = pc
            trace.entered(trace.debugger, lib.DEBUGGER_ENTER_BREAKPOINT, info)
        if pc in (0x0805F35A, 0x0801B47A, 0x0802066E):
            word = int(cpu.gprs[0 if pc == 0x0802066E else 1]) & 0xFFFFFFFF
            trace.table_reads.append({"pc": hex(pc), "word": hex(word), "source": hex(core.memory.u32[word])})
        core.step()
    else:
        raise RuntimeError(f"Native fixture did not finish: {function:08x}/{pc:08x}")
    result = int(cpu.gprs[0]) & 0xFFFFFFFF
    require(not trace.errors, f"Native trace errors: {trace.errors[:3]}")
    registers(core, {"cpsr": cpsr, **saved, "pc": saved_pc})
    return {"steps": steps, "return_r0": result, "table_reads": trace.table_reads}


def check_glyphs(glyphs, text, font, exact=True):
    glyphs, repeats = distinct_glyph_observations(glyphs)
    expected = [font.glyph(c)[0] for c in text if c != "\n"]
    actual = [g["code"] for g in glyphs]
    require(actual == expected if exact else any(actual[i:i + len(expected)] == expected for i in range(len(actual))),
            f"Native glyph sequence differs: {text}")
    require(glyphs and all(g["font"] == 0 and g["spacing"] == 0 for g in glyphs), "Interface font/spacing changed")
    for glyph in glyphs:
        require(0 <= glyph["x"] and glyph["x"] + glyph["advance"] <= glyph["window_width"], "Native horizontal overflow")
        require(0 <= glyph["y"] and glyph["y"] + 12 <= glyph["window_height"], "Native vertical overflow")
        require(glyph["window_origin"][0] + glyph["window_width"] <= 240, "Window crosses screen edge")
    return {"glyphs": len(glyphs), "reobservations": repeats, "window_width": glyphs[0]["window_width"],
            "max_right": max(g["x"] + g["advance"] for g in glyphs)}


def action_case(session, state, row, english, font, entries, folder, item=247):
    require(session.core.load_raw_state(state), "Cannot load action fixture")
    install_item(session.core, 0x0200A480, item)
    trace = InterfaceTrace(session.core, action=row)
    try:
        for phase, key in (("world", "B"), ("inventory", "A"), ("actions", "A")):
            trace.phase = phase
            session.press(key, 120, trace)
        require(trace.redirects > 0, "Action reader fixture was not reached")
        # Force only the selected IDs; the game still copies and draws every
        # record with its original stride, style handling and popup geometry.
        source = session.core.memory.u32[0x0806FBF4] + row * ACTION_STRIDE
        payload = bytes(session.core.memory[source:source + 12]).split(b"\0")[0]
        draws = [d for d in trace.payloads if d["phase"] == "actions" and d["x"] == 0 and
                 bytes.fromhex(d["raw_hex"]).startswith(payload + b"\0")]
        require(draws, f"Action record {row} did not reach the popup")
        checks = []
        if english:
            e = entries[f"interface.action.{row:03d}"]
            for draw in draws:
                checks.append(check_glyphs([g for g in trace.positions if g["draw_serial"] == draw["serial"]], e["display"] or e["english"], font))
        image = session.capture(f"action-{row:02d}")
        write_json(folder / f"action-{row:02d}.json", {"checks": checks, "source": hex(source), "trace": trace.report(), "payloads": trace.payloads})
        return image, checks
    finally:
        trace.close()


def label_case(session, state, family, row, english, font, entry, folder):
    require(session.core.load_raw_state(state), "Cannot load label fixture")
    core = session.core
    trace = InterfaceTrace(core)
    trace.phase = family
    try:
        if family == "dungeon":
            core.memory.u32[0x02004F8C] = row // 32
            core.memory.u8[0x02004FF0] = row % 32
            core.memory.u8[0x02004FF1] = 99
            result = native_step(session, trace, 0x0806C8C8, [1], overrides={0x0806CCDA: {"r0": 1}})
            expected_word = 0x081B3F60 + row * 4
        else:
            result = native_step(session, trace, 0x080205A8, [0x0203F000, 0x081B42F0, 7, row, 1, 0, 0], stop=0x080206BC)
            expected_word = 0x081B421C + row * 4
        require(any(int(r["word"], 16) == expected_word for r in trace.table_reads), "Native label table row not read")
        raw = bytes(core.memory[core.memory.u32[expected_word]:core.memory.u32[expected_word] + 100]).split(b"\0")[0]
        draws = [d for d in trace.payloads if raw in bytes.fromhex(d["raw_hex"]).split(b"\0")[0]]
        require(draws, f"Label missing from native UI: {family}/{row}")
        checks = []
        if english:
            for draw in draws:
                checks.append(check_glyphs([g for g in trace.positions if g["draw_serial"] == draw["serial"]], entry["display"] or entry["english"], font, exact=False))
        write_json(folder / f"{family}-{row:02d}.json", {"call": result, "checks": checks, "trace": trace.report(), "payloads": trace.payloads})
    finally:
        trace.close()
    session.frames(2)
    return session.capture(f"{family}-{row:02d}"), checks


def search_case(session, state, entry, source, hero, english, font, folder):
    require(session.core.load_raw_state(state), "Cannot load search fixture")
    # Protagonist selector read by native 08000E9C; fixture-only, never saved.
    session.core.memory.u16[0x020014CE] = hero
    trace = InterfaceTrace(session.core, story_source=source)
    try:
        for phase, key in (("world", "B"), ("select", "DOWN"), ("search", "A")):
            trace.phase = phase
            session.press(key, 240, trace)
        require(trace.redirects == 1, "Search story entry was not reached")
        formatted = [f for f in trace.formats if int(f["source"], 16) == source]
        require(formatted, "Selected search source did not reach native formatter")
        checks = []
        if english:
            text = (entry["display"] or entry["english"]).replace("$t", ("Torneko", "Tipper")[hero])
            require(bytes.fromhex(formatted[0]["output_hex"]) == text.encode() + b"\0", "Search substitution changed or truncated")
            checks.append(check_glyphs([g for g in trace.positions if g["caller"] == "0x08061B4E" and int(g["source"], 16) == source], text, font))
        name = f"search-{entry['rows'][0]:02d}-hero{hero}"
        write_json(folder / f"{name}.json", {"checks": checks, "trace": trace.report(), "fixture_source": hex(source)})
        return session.capture(name), checks
    finally:
        trace.close()


def trap_guard(session, state, row):
    require(session.core.load_raw_state(state), "Cannot load trap-copy fixture")
    core, record, dest = session.core, 0x0203F000, 0x0203F200
    for i, value in enumerate((3, 0, row)):
        core.memory.u32[record + i * 4] = value
    for at in range(dest - 8, dest + 38):
        core.memory.u8[at] = 0xA5
    trace = InterfaceTrace(core)
    try:
        result = native_step(session, trace, 0x0801B454, [record, dest])
        word = 0x081B421C + 4 * row
        require(any(int(r["word"], 16) == word for r in trace.table_reads), "Trap helper missed table row")
        source = core.memory.u32[word]
        raw = bytes(core.memory[source:source + 30]).split(b"\0")[0] + b"\0"
        require(bytes(core.memory[dest:dest + len(raw)]) == raw and core.memory.u8[dest + 29] == 0, "Trap copy truncated or unterminated")
        require(bytes(core.memory[dest - 8:dest]) == b"\xA5" * 8 and bytes(core.memory[dest + 30:dest + 38]) == b"\xA5" * 8, "Trap copy overwrote guards")
        return {"row": row, "raw_hex": raw.hex(), "guards_intact": True, **result}
    finally:
        trace.close()


def verify():
    mgba.log.silence()
    original, state = ORIGINAL_ROM.read_bytes(), STATE.read_bytes()
    font, catalog = FontZero(original), load_json(CATALOG)
    entries = {e["id"]: e for e in catalog["entries"]}
    by_row = {(e["family"], row): e for e in entries.values() for row in e["rows"]}
    output = OUTPUT / "verification"
    output.mkdir(exist_ok=True)
    report = {"source_sha256": digest(original), "catalog_file_sha256": digest(CATALOG.read_bytes()),
              "fixture_state_sha256": digest(state), "variants": {}, "japanese_pixel_pairs": 0}
    baseline_images, baseline_guards = {}, None
    for language in ("baseline", "japanese", "english"):
        path = Path("build/enemy-items/torneko3-enemies-items-english.gba") if language == "baseline" else OUTPUT / f"torneko3-dungeon-interface-{language}.gba"
        data, folder = path.read_bytes(), output / language
        folder.mkdir(exist_ok=True)
        variant = {"rom_sha256": digest(data), "screens": [], "guards": []}
        english = language == "english"
        build_report = load_json(OUTPUT / f"{language}-build.json") if language != "baseline" else None

        def record(key, result):
            shot, checks = result
            variant["screens"].append({"case": key, "checks": checks})
            if language == "baseline":
                baseline_images[key] = shot
            elif language == "japanese":
                require(ImageChops.difference(baseline_images[key], shot).getbbox() is None, f"Japanese relocation pixels changed: {key}")
                report["japanese_pixel_pairs"] += 1

        with Session(data, folder) as session:
            for row in range(41):
                record(f"action-{row}", action_case(session, state, row, english, font, entries, folder))
            print(f"{language}: all 41 action records passed", flush=True)
            for family, count in (("dungeon", 64), ("trap", 23)):
                for row in range(count):
                    record(f"{family}-{row}", label_case(session, state, family, row, english, font, by_row[family, row], folder))
                print(f"{language}: all {count} {family} rows passed", flush=True)
            for e in entries.values():
                if e["family"] != "search":
                    continue
                source = (int(e["offset"], 0) if language == "baseline" else build_report["interface"]["relocated"][e["id"]]["offset"]) + 0x08000000
                for hero in (0, 1):
                    record(f"{e['id']}-hero{hero}", search_case(session, state, e, source, hero, english, font, folder))
            variant["guards"] = [trap_guard(session, state, row) for row in range(23)]
            if language == "baseline":
                baseline_guards = [g["raw_hex"] for g in variant["guards"]]
            elif language == "japanese":
                require(baseline_guards == [g["raw_hex"] for g in variant["guards"]], "Japanese trap helper output changed")
        report["variants"][language] = variant
        write_json(output / "report.json", report)
        print(f"{language}: {len(variant['screens'])} screens and 23 trap guards passed", flush=True)
    report["scope"] = "Controlled native action IDs, dungeon status headers (puzzle number 99), trap panels/copies, and search messages routed through the native story engine for both protagonists. Object triples statically verified; not all natural object branches or dungeon transitions played."
    write_json(output / "report.json", report)
    return report


if __name__ == "__main__":
    verify()
