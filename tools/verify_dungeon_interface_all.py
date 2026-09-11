"""Reproduce or summarize the complete dungeon-interface acceptance checks."""

import argparse
import json
import re
import subprocess
import sys

from tools.build_dungeon_interface import CATALOG, OUTPUT, ORIGINAL_ROM, ROOT, build, build_rom
from tools.build_first_label import digest, load_manifest
from tools.translation_pipeline import load_json, check
from tools.verify_items import write_json


def summarize():
    original = ORIGINAL_ROM.read_bytes()
    check(digest(original) == load_manifest()["base_sha256"], "Japanese source changed")
    catalog = load_json(CATALOG)
    main = load_json(OUTPUT / "verification/report.json")
    check(main["catalog_file_sha256"] == digest(CATALOG.read_bytes()), "Native catalog snapshot is stale")
    check(set(main["variants"]) == {"baseline", "japanese", "english"} and main["japanese_pixel_pairs"] == 156,
          "Incomplete Japanese relocation coverage")
    hashes = {}
    for language in ("japanese", "english"):
        data = (OUTPUT / f"torneko3-dungeon-interface-{language}.gba").read_bytes()
        expected, report = build_rom(original, language, catalog)
        check(data == expected, "Delivered image differs from a fresh shared-ledger rebuild")
        hashes[language] = digest(data)
        check(main["variants"][language]["rom_sha256"] == hashes[language], "Native ROM snapshot is stale")
        check(len(main["variants"][language]["screens"]) == 156 and len(main["variants"][language]["guards"]) == 23,
              "Incomplete native interface coverage")
        if language == "english":
            ledger = report["ledger"]
    paths = {"secondary": "secondary-contexts/report.json", "items": "items-regression/verification.json",
             "hero_details": "hero-details/verification.json", "save": "save/verification.json"}
    reports = {key: load_json(OUTPUT / "verification" / path) for key, path in paths.items()}
    for key, report in reports.items():
        check(report["rom_sha256"] == hashes["english"] and report["source_sha256"] == digest(original), f"Stale {key} regression")
    secondary = reports["secondary"]
    check(secondary["catalog_file_sha256"] == digest(CATALOG.read_bytes()), "Secondary catalog snapshot is stale")
    check(len(secondary["menus"]) == 14 and len(secondary["enemy_copy_guards"]) == 400 and
          len(secondary["hero_copy_guards"]) == 2 and len(secondary["natural_search"]) == 2 and secondary["concealed_trap"],
          "Incomplete secondary context coverage")
    check(reports["items"]["item_rows"] == [1, 64, 133, 190, 247, 273, 304], "Missing item categories")
    check(len(reports["hero_details"]["checks"]) == 4, "Missing hero detail screens")
    check(reports["save"]["torneko_save_cold_load"] and reports["save"]["save_bytes"] == 65536, "Save/cold-load acceptance failed")
    log = (OUTPUT / "unit-tests.log").read_text()
    match = re.search(r"Ran (\d+) tests", log)
    check(match and log.rstrip().endswith("OK"), "Unit suite did not pass")
    from tools.extract_master_text import verify_roundtrip
    master = load_json(ROOT / "translations/master.json")
    roundtrip = verify_roundtrip(original, master["entries"])
    fan = ROOT / "Dragon Quest Characters - Torneko no Daibouken 3 Advance - Fushigi no Dungeon (Japan) [T-En by Sam Steel v0.05] [i].gba"
    fan_hash = digest(fan.read_bytes())
    check(fan_hash == "e7108d76a0c9c3a40b3eb52dc622cfe9ac9f08e673d3f43e0996815cebf7a93f", "Reference cartridge changed")
    summary = {"status": "passed", "source_sha256": digest(original), "reference_sha256": fan_hash,
               "rom_sha256": hashes, "new_catalog_entries": len(catalog["entries"]),
               "english_interface_screens": 156, "japanese_pixel_pairs": 156, "secondary_action_menus": 14,
               "trap_guards_per_variant": 23, "enemy_copy_guards": 400, "hero_copy_guards": 2,
               "natural_ground_search_protagonists": 2, "item_inventory_information_screens": 14,
               "hero_detail_screens": 4, "save_bytes": 65536, "unit_tests": int(match[1]),
               "master_entries": len(master["entries"]), "master_roundtrip_sha256": roundtrip,
               "appended_used_with_padding": ledger["appended_used_with_padding"],
               "appended_remaining": ledger["appended_remaining"],
               "catalog_file_sha256": {p.name: digest(p.read_bytes()) for p in (ROOT / "translations").glob("*.json")},
               "reports": paths, "limits": main["scope"]}
    write_json(OUTPUT / "acceptance.json", summary)
    print(json.dumps({k: v for k, v in summary.items() if k not in ("catalog_file_sha256", "reports")}, indent=2))
    return summary


def verify_all():
    from tools.verify_dungeon_interface import verify, STATE
    from tools.verify_dungeon_contexts import verify as contexts
    from tools.verify_enemies import verify as enemies
    from tools.verify_enemy_items import verify as items
    from tools.extract_master_text import extract
    build()
    with (OUTPUT / "unit-tests.log").open("w") as log:
        subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)
    verify()
    contexts()
    rom = OUTPUT / "torneko3-dungeon-interface-english.gba"
    enemies(rom, OUTPUT / "verification/hero-details", state_path=STATE, rows=(0, 198))
    items(rom, OUTPUT / "verification/items-regression", "items", state_path=STATE, rows=[1,64,133,190,247,273,304])
    items(rom, OUTPUT / "verification/save", "save")
    extract()
    return summarize()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summarize-only", action="store_true")
    summarize() if parser.parse_args().summarize_only else verify_all()
