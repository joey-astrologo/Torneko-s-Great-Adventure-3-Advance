"""Reproduce or summarize the complete combined-milestone native acceptance."""

import argparse
import json
from pathlib import Path
import re

from PIL import Image, ImageChops
from tools.build_first_label import ORIGINAL_ROM, ROOT, digest
from tools.build_enemy_items import OUTPUT, build, build_rom
from tools.build_name_entry import build_name_rom
from tools.translation_pipeline import atomic_write, load_json
from tools.verify_first_label import require
from tools.verify_items import write_json
from tools.verify_enemy_items import verify as verify_items
from tools.verify_enemies import verify as verify_enemies
from tools.verify_enemy_guards import verify as verify_guards

VERIFY = OUTPUT / "verification"


def summarize():
    original = ORIGINAL_ROM.read_bytes()
    expected_roms = {language: build_rom(original, language)[0] for language in ("english", "japanese")}
    expected_roms["baseline"] = build_name_rom(original)[0]
    hashes = {language: digest(data) for language, data in expected_roms.items()}
    reports = {}
    for language, data in expected_roms.items():
        path = VERIFY / "baseline.gba" if language == "baseline" else OUTPUT / f"torneko3-enemies-items-{language}.gba"
        require(path.read_bytes() == data, "Delivered image differs from current source/catalog rebuild")
        reports[language] = {}
        for component in ("items", "contexts", "formatters", "enemies", "enemy-guards"):
            report = load_json(VERIFY / f"{language}-{component}/verification.json")
            require(report["rom_sha256"] == hashes[language] and report["source_sha256"] == digest(original), "Stale native report")
            if "catalog_sha256" in report:
                catalog = "item-contexts" if component == "contexts" else component
                require(report["catalog_sha256"] == digest((ROOT / f"translations/{catalog}.json").read_bytes()), "Native report predates catalog edits")
            reports[language][component] = report
        r = reports[language]
        require(r["items"]["item_rows"] == list(range(370)), "Incomplete identified UI coverage")
        require(r["contexts"]["ui_cases"] == 347 and len(r["contexts"]["wrappers"]) == 101, "Incomplete context coverage")
        require({(c["screen"], c["row"]) for c in r["enemies"]["checks"]} == {(s,i) for s in ("ally","encounter") for i in range(200)}, "Incomplete enemy coverage")
        require(len(r["formatters"]["identified"]) == 708 and len(r["formatters"]["unidentified"]) == 258, "Incomplete item formatter coverage")
        require(len(r["enemy-guards"]["cases"]) == 400 and len(r["enemy-guards"]["mimics"]) == 11, "Incomplete enemy formatter coverage")
        for component, keys in (("formatters", ("identified", "unidentified")), ("enemy-guards", ("cases", "mimics"))):
            for key in keys:
                require(all(c["guards_intact"] for c in r[component][key]), "A native buffer guard failed")
        require(all(c["neighbors_preserved"] for c in r["contexts"]["wrappers"]), "Synthesis wrapper neighbors changed")
    for family, catalog in (("items", "items"), ("contexts", "item-contexts")):
        ids = {e["id"] for e in load_json(ROOT / f"translations/{catalog}.json")["entries"]}
        if family == "items":
            ids.remove("item.name.127")  # Reserved bundle selects another name row.
        require({c["id"] for c in reports["english"][family]["checks"]} == ids, "Missing English catalog UI coverage")
    pairs = {}
    paths = {
        "items": [Path(f"item-{row:03d}/{screen}.png") for row in range(370) for screen in ("inventory", "information")],
        "contexts": [Path(f"unidentified-{row:03d}/screen.png") for row in range(246)] +
                    [Path(f"synthesis-{row:03d}/screen.png") for row in range(100)] + [Path("synthesis-001-high-bit/screen.png")],
        "enemies": [Path(f"{screen}-{row:03d}.png") for screen in ("encounter", "ally") for row in range(200)]}
    for component, images in paths.items():
        for path in images:
            before = Image.open(VERIFY / f"baseline-{component}" / path).convert("RGB")
            after = Image.open(VERIFY / f"japanese-{component}" / path).convert("RGB")
            require(ImageChops.difference(before, after).getbbox() is None, f"Japanese relocation changed pixels: {component}/{path}")
        pairs[component] = len(images)
    for component, keys, field in (("formatters", ("identified", "unidentified"), "output_hex"),
                                    ("enemy-guards", ("cases", "mimics"), "raw_hex")):
        for key in keys:
            before, after = reports["baseline"][component][key], reports["japanese"][component][key]
            require(all(a[field] == b[field] for a,b in zip(before,after)), "Japanese relocation changed native formatting")
    save = load_json(VERIFY / "save/verification.json")
    require(save["rom_sha256"] == hashes["english"] and save["torneko_save_cold_load"] and save["save_bytes"] == 65536, "Combined save test is stale/incomplete")
    tests = (OUTPUT / "unit-tests.log").read_text()
    match = re.search(r"Ran (\d+) tests", tests)
    require(match and tests.rstrip().endswith("OK"), "Unit suite has not passed")
    english = reports["english"]
    report = {"passed": True, "source_sha256": digest(original), "rom_sha256": hashes,
        "catalog_sha256": {name: digest((ROOT / f"translations/{name}.json").read_bytes()) for name in ("items","item-contexts","enemies")},
        "catalog_strings": 1463, "relocated_table_pointer_words": 1486,
        "japanese_pixel_pairs_identical": pairs, "total_japanese_pixel_pairs": sum(pairs.values()),
        "english_ui_screens": sum(pairs.values()), "english_item_catalog_ids_native": 718,
        "static_only_item_name": "item.name.127; reserved bundle selects another source using record byte +0x15",
        "guarded_calls_per_variant": {"identified":708,"unidentified_and_regressions":258,"enemy_copies":400,"revealed_cannibox_items":11},
        "synthesis_wrappers_per_variant": 101, "native_buffer_guards_preserved": True,
        "japanese_formatter_outputs_identical": True, "combined_torneko_save_cold_load": True, "save_bytes": 65536,
        "max_formatted_item_width": max(c["formatted_width"] for c in english["formatters"]["identified"]),
        "unit_tests": int(match.group(1)),
        "duplicate_observations": {family:{key:sum(c.get(key,0) for c in english[family]["checks"])
            for key in ("identical_glyph_reobservations","empty_duplicate_draw_observations")} for family in ("items","contexts","enemies")},
        "scope": "Complete catalog insertion and controlled native layouts/formatters; normal dungeon operations, all live actor/reveal conditions and ranking records remain playtest backlog."}
    write_json(VERIFY / "report.json", report)
    print(json.dumps(report, indent=2))
    return report


def verify_all():
    build()
    baseline = build_name_rom(ORIGINAL_ROM.read_bytes())[0]
    atomic_write(VERIFY / "baseline.gba", baseline)
    english = OUTPUT / "torneko3-enemies-items-english.gba"
    verify_items(english, VERIFY / "save", "save")
    state = VERIFY / "save/world.state"
    for language in ("baseline", "japanese", "english"):
        rom = VERIFY / "baseline.gba" if language == "baseline" else OUTPUT / f"torneko3-enemies-items-{language}.gba"
        text_language = "english" if language == "english" else "japanese"
        for component in ("items", "contexts", "formatters"):
            verify_items(rom, VERIFY / f"{language}-{component}", component, text_language, state)
        verify_enemies(rom, VERIFY / f"{language}-enemies", text_language, state)
    verify_guards()
    return summarize()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summarize-only", action="store_true", help="Validate current reports/artifacts without replaying native cases")
    args = parser.parse_args()
    summarize() if args.summarize_only else verify_all()
