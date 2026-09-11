"""Check secondary action readers and protagonist-copy regressions."""

import struct

from tools.verify_dungeon_interface import (OUTPUT, STATE, CATALOG, ORIGINAL_ROM, Session, InterfaceTrace,
    native_step, check_glyphs, FontZero, load_json, write_json, digest, require, install_item, ffi, mgba)
from tools.verify_enemy_guards import native_call


def verify(rom=None, output=None, state_path=STATE):
    mgba.log.silence()
    data = (rom or OUTPUT / "torneko3-dungeon-interface-english.gba").read_bytes()
    state, original = state_path.read_bytes(), ORIGINAL_ROM.read_bytes()
    font, catalog = FontZero(original), load_json(CATALOG)
    out = output or OUTPUT / "verification/secondary-contexts"
    report = {"rom_sha256": digest(data), "source_sha256": digest(original),
              "catalog_file_sha256": digest(CATALOG.read_bytes()), "fixture_state_sha256": digest(state),
              "menus": [], "enemy_copy_guards": [], "hero_copy_guards": [], "natural_search": []}
    labels = {e["display"] or e["english"] for e in catalog["entries"] if e["family"] in ("action", "override")}
    with Session(data, out) as session:
        for function, name in ((0x080755C0, "warehouse"), (0x0806FC78, "container")):
            for item in (1, 64, 133, 190, 247, 273, 304):
                require(session.core.load_raw_state(state), "Cannot restore secondary context")
                core = session.core
                install_item(core, 0x0200A480, item)
                base = core.memory.u32[0x08075760]
                # Valid caller-supplied command, not a null pointer from the
                # unrelated opening-world state. No shop dialogue is injected.
                core.memory.u32[0x02009110] = base + 10 * 12
                args = [0, 1, 0x0200A480, 0, 16] if name == "warehouse" else [0, 1, 0x0200A480, 0, 0, base + 9*12, 0]
                trace = InterfaceTrace(core)
                checks = []
                try:
                    call = native_step(session, trace, function, args)
                    require(trace.payloads, "Secondary action reader did not draw")
                    for draw in trace.payloads:
                        raw = bytes.fromhex(draw["raw_hex"]).split(b"\0")[0]
                        require(raw.startswith(b"\x03\x05"), "Unexpected secondary menu style")
                        text = raw[3:].decode("ascii")
                        require(text in labels, "Secondary menu lost translated command")
                        checks.append(check_glyphs([g for g in trace.positions if g["draw_serial"] == draw["serial"]], text, font))
                    write_json(out / f"{name}-{item}.json", {"call": call, "trace": trace.report(), "payloads": trace.payloads})
                finally:
                    trace.close()
                session.frames(2)
                session.capture(f"{name}-{item}")
                report["menus"].append({"reader": name, "item": item, "checks": checks})
        print("All 14 secondary action menus passed", flush=True)
        for function in (0x08032D6C, 0x08032CA4):
            report["enemy_copy_guards"].extend(native_call(session, state, function, row) for row in range(200))
        for hero, name in enumerate(("Torneko", "Tipper")):
            require(session.core.load_raw_state(state), "Cannot restore protagonist-copy fixture")
            session.core.memory.u8[0x02004FF4] = hero
            hero_state = bytes(ffi.buffer(session.core.save_raw_state()))
            result = native_call(session, hero_state, 0x08032D6C, 0)
            require(bytes.fromhex(result["raw_hex"]) == name.encode() + b"\0", "Fixed protagonist copy differs")
            report["hero_copy_guards"].append({"hero": hero, "name": name, **result})
        # Concealed trap header uses the separate ???? override instead of a
        # table row. Stop after the native panel draw, before its input loop.
        require(session.core.load_raw_state(state), "Cannot restore concealed trap")
        trace = InterfaceTrace(session.core)
        try:
            native_step(session, trace, 0x080205A8, [0x0203F000, 0x081B42F0, 7, 0, 0, 0, 0],
                        stop=0x080206BC, overrides={0x0802065C: {"r0": 1}})
            draws = [d for d in trace.payloads if bytes.fromhex(d["raw_hex"]).startswith(b"????\0")]
            require(len(draws) == 1, "Concealed trap placeholder missing")
            report["concealed_trap"] = check_glyphs([g for g in trace.positions if g["draw_serial"] == draws[0]["serial"]], "????", font)
        finally:
            trace.close()
        session.frames(2)
        session.capture("concealed-trap")
        for hero, name in enumerate(("Torneko", "Tipper")):
            require(session.core.load_raw_state(state), "Cannot restore ground-search route")
            session.core.memory.u16[0x020014CE] = hero
            words = (0x0891784C, 0x08917854)
            trace = InterfaceTrace(session.core, watch_addresses=words)
            try:
                for phase, key in (("world", "B"), ("select", "DOWN"), ("search", "A"), ("result", "A")):
                    trace.phase = phase
                    session.press(key, 240, trace)
                    if phase in ("search", "result"):
                        session.capture(f"natural-{hero}-{phase}")
                require(trace.redirects == 0, "Natural route unexpectedly redirected text")
                require(set(words) <= {int(r["address"], 16) for r in trace.source_reads}, "Natural event pointers were not read")
                checks = []
                for word, text in zip(words, (f"{name} searches the ground!", "But nothing was found...")):
                    source = session.core.memory.u32[word]
                    formatted = [f for f in trace.formats if int(f["source"], 16) == source]
                    require(formatted and bytes.fromhex(formatted[0]["output_hex"]) == text.encode() + b"\0", "Natural search text differs")
                    checks.append(check_glyphs([g for g in trace.positions if g["caller"] == "0x08061B4E" and int(g["source"], 16) == source], text, font))
                report["natural_search"].append({"hero": hero, "checks": checks, "pointer_reads": trace.source_reads})
                write_json(out / f"natural-search-{hero}.json", trace.report())
            finally:
                trace.close()
    report["scope"] = "Controlled secondary popup readers across seven item categories, 400 enemy-copy guards, both fixed hero copies, and concealed trap header. Does not execute warehouse transactions or container effects."
    write_json(out / "report.json", report)
    print("400 enemy copies, both hero copies and concealed trap passed", flush=True)
    return report


if __name__ == "__main__":
    verify()
