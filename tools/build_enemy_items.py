"""Rebuild the combined enemy/item milestone through one ownership ledger."""

import argparse
import json
from pathlib import Path

from tools.build_first_label import ORIGINAL_ROM, ROOT, digest
from tools.build_name_entry import build_name_rom
from tools import build_items, build_item_contexts, build_enemies
from tools.rom_build import RomBuild
from tools.translation_pipeline import atomic_write, check, load_json

OUTPUT = ROOT / "build/enemy-items"


def build_rom(original, language="english", catalogs=None):
    check(language in ("english", "japanese"), "Unsupported combined language")
    build = RomBuild(original)
    _, names = build_name_rom(original, build=build)
    report = {"source_sha256": digest(original), "language": language,
              "name_and_menu_build_sha256": names["rom_sha256"]}
    for label, module, add in (("items", build_items, build_items.add_items),
                               ("contexts", build_item_contexts, build_item_contexts.add_contexts),
                               ("enemies", build_enemies, build_enemies.add_enemies)):
        catalog = load_json(module.CATALOG) if catalogs is None else catalogs[label]
        check(all(e["english"] for e in catalog["entries"]), f"Incomplete {label} translation")
        report[label] = add(build, catalog, language)
    data, ledger = build.finish()
    report.update(rom_sha256=digest(data), ledger=ledger,
                  appended_used_with_padding=ledger["appended_used_with_padding"],
                  appended_remaining=ledger["appended_remaining"])
    return data, report


def build(output=OUTPUT):
    output = Path(output)
    original = ORIGINAL_ROM.read_bytes()
    prepared = {language: build_rom(original, language) for language in ("japanese", "english")}
    # Publish checked ownership reports before their ROMs. Components, source
    # ownership and the append arena are recorded in docs/MEMORY_MAP.md.
    for language, (_, report) in prepared.items():
        atomic_write(output / f"{language}-build.json", (json.dumps(report, indent=2) + "\n").encode())
    for language, (data, report) in prepared.items():
        target = output / f"torneko3-enemies-items-{language}.gba"
        atomic_write(target, data)
        print(json.dumps({"rom": str(target), "sha256": report["rom_sha256"],
                          "appended_bytes": report["appended_used_with_padding"],
                          "remaining_bytes": report["appended_remaining"]}))
    return prepared


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    build(parser.parse_args().output)
