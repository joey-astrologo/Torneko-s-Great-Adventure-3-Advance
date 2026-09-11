"""Whole-catalog native acceptance for the combined build, one component per run."""

import argparse
from pathlib import Path
import json

import mgba.log
from tools.build_first_label import ORIGINAL_ROM, digest
from tools import build_items, build_item_contexts
from tools.game_text import GameTextCodec
from tools.translation_pipeline import FontZero, load_json
from tools.verify_expansion import Session
from tools.verify_first_label import require
from tools.verify_items import enter_world, inventory_checks, native_names, write_json
from tools.verify_item_contexts import capture_contexts, guarded_names
from tools.verify_name_entry import creation, reload_name
from tools.build_name_entry import compact_name


def verify(rom, output, component, language="english", state_path=None, rows=None):
    mgba.log.silence()
    data, original = Path(rom).read_bytes(), ORIGINAL_ROM.read_bytes()
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    report = {"rom_sha256": digest(data), "source_sha256": digest(original), "language": language,
              "component": component, "checks": []}
    if component == "save":
        save, _ = creation(data, output / "create", 1)
        reload_name(data, save, output / "reload", compact_name("Torneko"))
        report.update(torneko_save_cold_load=True, save_bytes=len(save), save_sha256=digest(save))
        with Session(data, output / "world", save) as session:
            state = enter_world(session)
            (output / "world.state").write_bytes(state)
            session.capture("world")
            report["inputs"] = session.frames_recorded
    else:
        require(state_path is not None, "A documented disposable world state is required")
        state = Path(state_path).read_bytes()
        report.update(fixture_state=str(state_path), fixture_state_sha256=digest(state))
        with Session(data, output) as session:
            if component == "items":
                catalog = load_json(build_items.CATALOG)
                report["catalog_sha256"] = digest(build_items.CATALOG.read_bytes())
                rows = list(range(370)) if rows is None else rows
                for row in rows:
                    _, checks = inventory_checks(session, state, catalog, language, output, [row])
                    report["checks"].extend(checks)
                    if row % 25 == 0:
                        print(f"{language}: item {row} passed", flush=True)
                report["item_rows"] = rows
            elif component == "contexts":
                catalog = load_json(build_item_contexts.CATALOG)
                report["catalog_sha256"] = digest(build_item_contexts.CATALOG.read_bytes())
                cases = [("unidentified", r, False) for r in range(246)] + [("synthesis", r, False) for r in range(100)] + [("synthesis", 1, True)]
                report["wrappers"] = []
                for start in range(0, len(cases), 20):
                    _, checks, wrappers, _ = capture_contexts(session, state, original, catalog, language, output, cases[start:start+20])
                    report["checks"].extend(checks)
                    report["wrappers"].extend(wrappers)
                    print(f"{language}: context {min(start+20,len(cases))}/{len(cases)} passed", flush=True)
                report["ui_cases"] = len(cases)
            else:
                require(component == "formatters", "Unknown verification component")
                codec, font = GameTextCodec(original), FontZero(original)
                # Every item row plus signed decorations across all weapons,
                # shields, staffs and rings, including the longest raw names.
                cases = [(i, 0) for i in range(370)] + [(i, n) for i in list(range(1,113))+list(range(133,190)) for n in (-99,99)]
                for label in ("identified", "unidentified"):
                    (output / label).mkdir(exist_ok=True)
                report["identified"] = native_names(session, state, codec, output / "identified", cases)
                report["unidentified"] = guarded_names(session, state, original, output / "unidentified")
                write_json(output / "formatter-observations.json", report)
                if language == "english":
                    names = {r: e for e in load_json(build_items.CATALOG)["entries"] if e["family"] == "name" for r in e["item_indices"]}
                    for result in report["identified"]:
                        raw = bytes.fromhex(result["output_hex"])
                        # Special record types (e.g. Mimic/projectile records)
                        # can intentionally select a monster or dynamic name.
                        direct = result["pointer_loads_at_08080B62"]
                        if direct:
                            selected = [(int(load["word"], 16) - 0x0818F16C) // 4 for load in direct]
                            require(all(names[r]["english"].encode() in raw for r in selected), "Formatter lost English item name")
                            result["selected_name_rows"] = selected
                        x = right = 0
                        for token in codec.parse(raw, 0)["tokens"]:
                            if token["kind"] == "text":
                                for char in token["text"]:
                                    _, advance, ink = font.glyph(char)
                                    right = max(right, x+ink)
                                    x += advance
                        result["formatted_width"] = max(x,right)
                        require(max(x,right) <= 144, f"Decorated item exceeds header: {result['item']}")
                    unknown = {r: e for e in load_json(build_item_contexts.CATALOG)["entries"] if e["family"] == "unidentified" for r in e["rows"]}
                    for result in report["unidentified"]:
                        if result["mode"] == "unknown":
                            require(unknown[result["row"]]["english"].encode() in bytes.fromhex(result["output_hex"]), "Formatter lost English disguise")
    report["scope"] = "Controlled native display/format fixtures; no claim of natural dungeon identification, synthesis execution or encounter progression."
    write_json(output / "verification.json", report)
    print(f"{language}: {component} completed", flush=True)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rom", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--component", choices=("items", "contexts", "formatters", "save"), required=True)
    parser.add_argument("--language", choices=("english", "japanese"), default="english")
    parser.add_argument("--state", type=Path)
    parser.add_argument("--rows")
    args = parser.parse_args()
    verify(args.rom, args.output, args.component, args.language, args.state,
           [int(r) for r in args.rows.split(",")] if args.rows else None)
