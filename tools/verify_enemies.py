"""Exercise both native monster detail screens with disposable species fixtures."""

import argparse
import json
from pathlib import Path
import struct

import mgba.log
from mgba._pylib import ffi, lib

from tools.build_enemies import CATALOG, TABLES, encode_english
from tools.build_first_label import ORIGINAL_ROM, digest
from tools.translation_pipeline import FontZero
from tools.verify_expansion import Session
from tools.verify_first_label import require
from tools.verify_items import ItemTrace, enter_world, install_item, write_json


def distinct_glyph_observations(glyphs):
    """Validate glyph placement, allowing adjacent idempotent observations.

    The debugger occasionally observes the same placement twice. Its cause is
    not assumed here. Count repeats explicitly, collapsing only exact adjacent
    draw/position/code matches; two equal letters at different x remain distinct.
    """
    result, repeats = [], 0
    for glyph in glyphs:
        if result:
            fields = ("draw_serial", "caller", "code", "advance", "x", "y", "font", "spacing", "window_origin", "window_width", "window_height")
            if all(glyph[k] == result[-1][k] for k in fields):
                repeats += 1
                continue
        result.append(glyph)
    return result, repeats


class EnemyTrace(ItemTrace):
    def __init__(self, core, row, screen):
        self.row, self.screen, self.redirects = row, screen, 0
        super().__init__(core, [0x08000000 + base + row * 4 for base, _ in TABLES.values()])
        point = ffi.new("struct mBreakpoint*")
        point.address, point.segment, point.type = 0x0806DCDC, -1, lib.BREAKPOINT_HARDWARE
        require(self.debugger.platform.setBreakpoint(self.debugger.platform, point) >= 0, "No fixture redirect breakpoint")

    def entered(self, debugger, reason, info):
        super().entered(debugger, reason, info)
        try:
            if info != ffi.NULL and reason == lib.DEBUGGER_ENTER_BREAKPOINT:
                if info.address == 0x0808BC78:
                    window = int(self.cpu.gprs[4]) & 0xFFFFFFFF
                    self.positions[-1]["window_height"] = self.core.memory.u16[window + 6] * 8
                elif info.address == 0x0806DCDC:
                    self.redirects += 1
                    callback = int(self.cpu.gprs[1]) & 0xFFFFFFFF
                    if self.screen == "encounter":
                        self.core.memory.u16[0x020091D0] = self.row
                        self.core.memory.u16[0x020091D2] = 0
                        self.core.memory.u16[0x020091D4] = 99
                        self.core.memory.u16[0x020091D6] = 0
                        self.core.memory.u32[0x02009254] = 1
                        self.core.memory.u32[0x02009228] = 123  # 12.3 multiplier; all arguments visible.
                        registers = {"r0": callback, "r1": 0, "pc": 0x0807993C}
                    else:
                        for address in range(0x0203F000, 0x0203F080):
                            self.core.memory.u8[address] = 0
                        self.core.memory.u8[0x0203F000] = 1
                        self.core.memory.u8[0x0203F002] = self.row
                        self.core.memory.u8[0x0203F003] = 1
                        self.core.memory.u32[0x02000628] = 0
                        self.core.memory.u32[0x02000634] = 0
                        self.core.memory.u32[0x02008E68] = 0x0203F000
                        stack = int(self.cpu.gprs[13]) & 0xFFFFFFFF
                        self.core.memory.u32[stack] = 0x0203F040
                        registers = {"r0": callback, "r1": 0, "r2": 0, "r3": 1, "pc": 0x08072FBC}
                    for register, value in registers.items():
                        require(self.core._core.writeRegister(self.core._core, register.encode(), ffi.new("uint32_t*", value)),
                                "Enemy fixture register setup failed")
        except Exception as error:
            self.errors.append(str(error))
        finally:
            debugger.state = lib.DEBUGGER_RUNNING


def run_fixture(session, state, row, screen, entries, language, font, output):
    require(session.core.load_raw_state(state), "Could not restore enemy fixture state")
    install_item(session.core, 0x0200A480, 1)
    trace = EnemyTrace(session.core, row, screen)
    try:
        for phase, key in (("menu", "B"), ("inventory", "A"), ("actions", "A"), ("details", "A")):
            trace.phase = phase
            session.press(key, 120, trace)
        require(trace.redirects == 1, "Native details entry was not reached once")
        reads = {int(r["address"], 16) for r in trace.source_reads}
        trait_word = 0x08000000 + TABLES["trait"][0] + row * 4
        require(trait_word in reads, f"Trait table not read: {row}/{screen}")
        # The encounter helper substitutes the live hero's name for row 0 and
        # the son for row 198. Ally species labels directly read all 200 rows.
        dynamic_name = screen == "encounter" and row in (0, 198)
        if not dynamic_name:
            require(0x08000000 + TABLES["name"][0] + row * 4 in reads, "Name table not read")
        expected_y = 74 if screen == "ally" else 39 if language == "english" else 26
        draws = [d for d in trace.payloads if d["phase"] == "details" and d["y"] == expected_y]
        require(len(draws) == 1, f"Trait draw not found at y{expected_y}")
        draw = draws[0]
        glyphs = [g for g in trace.positions if g["draw_serial"] == draw["serial"]]
        glyphs, repeated_breakpoints = distinct_glyph_observations(glyphs)
        entry = entries[f"enemy.trait.{row:03d}"]
        raw = encode_english(entry, font)[0] if language == "english" else bytes.fromhex(entry["source_hex"])
        require(bytes.fromhex(draw["raw_hex"]).startswith(b"\x03\x05\x05" + raw[:-1] + b"\x03\x06\0"),
                "Native trait wrapper differs or is truncated")
        require(glyphs and all(g["font"] == 0 and g["spacing"] == 0 for g in glyphs), "Wrong trait font/spacing")
        if language == "english":
            text = entry["display"] or entry["english"]
            expected = [font.glyph(c)[0] for c in text if c != "\n"]
            if [g["code"] for g in glyphs] != expected:
                write_json(output / f"failure-{screen}-{row:03d}.json", {"expected": expected,
                    "glyphs": glyphs, "trace": trace.report(), "payloads": trace.payloads})
            require([g["code"] for g in glyphs] == expected, f"English trait glyphs differ: {row}/{screen}")
            index = 0
            for line_index, line in enumerate(text.split("\n")):
                x = 0
                for character in line:
                    g = glyphs[index]
                    _, advance, ink = font.glyph(character)
                    require((g["x"], g["y"]) == (x, expected_y + 13 * line_index), "Unexpected native trait wrap")
                    require(x + max(advance, ink) <= 188 and g["y"] + 12 <= g["window_height"], "Trait exceeds native window")
                    x += advance
                    index += 1
            if not dynamic_name:
                name = entries[f"enemy.name.{row:03d}"]
                name_bytes = encode_english(name, font)[0][:-1]
                names = [d for d in trace.payloads if d["phase"] == "details" and name_bytes in bytes.fromhex(d["raw_hex"]).split(b"\0", 1)[0]]
                require(names, "Full English species name did not reach details")
                for d in names:
                    ng = [g for g in trace.positions if g["draw_serial"] == d["serial"]]
                    require(all(g["x"] + g["advance"] <= 192 for g in ng), "Enemy name/header exceeds window")
        shot = session.screen.to_pil().convert("RGB")
        shot.save(output / f"{screen}-{row:03d}.png")
        return {"row": row, "screen": screen, "native_trait_source": f"0x{session.core.memory.u32[trait_word]:08X}",
                "pointer_reads": trace.source_reads, "trait_y": expected_y,
                "trait_width": max(g["x"] + g["advance"] for g in glyphs),
                "trait_bottom": max(g["y"] + 12 for g in glyphs), "window_height": glyphs[0]["window_height"],
                "dynamic_hero_name": dynamic_name, "native_payload_verified": True,
                "identical_glyph_reobservations": repeated_breakpoints,
                "glyphs_verified": language == "english"}, shot
    finally:
        trace.close()


def verify(rom, output, language="english", state_path=None, rows=range(200)):
    mgba.log.silence()
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    data = Path(rom).read_bytes()
    catalog = json.loads(CATALOG.read_text())
    entries = {e["id"]: e for e in catalog["entries"]}
    font, results = FontZero(ORIGINAL_ROM.read_bytes()), []
    with Session(data, output) as session:
        state = Path(state_path).read_bytes() if state_path else enter_world(session)
        for screen in ("encounter", "ally"):
            for row in rows:
                result, _ = run_fixture(session, state, row, screen, entries, language, font, output)
                results.append(result)
                if row % 25 == 0:
                    print(f"{language} {screen}: row {row} passed", flush=True)
    report = {"rom_sha256": digest(data), "catalog_sha256": digest(CATALOG.read_bytes()),
              "source_sha256": digest(ORIGINAL_ROM.read_bytes()), "language": language,
              "fixture_state": str(state_path) if state_path else "fresh boot route", "checks": results,
              "scope": "Native rendering via controlled callback-preserving entry; not normal encounter/recruitment progression."}
    write_json(output / "verification.json", report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rom", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--language", choices=("english", "japanese"), default="english")
    parser.add_argument("--state", type=Path)
    parser.add_argument("--rows", help="Comma-separated subset for investigation; omit for all 200 rows")
    args = parser.parse_args()
    verify(args.rom, args.output, args.language, args.state,
           [int(i) for i in args.rows.split(",")] if args.rows else range(200))
