"""Rebuild cumulative English and publish the latest ROM, BPS and build receipt."""

import argparse
from datetime import datetime, timezone
import fcntl
import json
from pathlib import Path
import subprocess
import tempfile

from tools import build_reference_coverage as current
from tools.build_first_label import ORIGINAL_ROM, ROOT, digest
from tools.translation_pipeline import atomic_write, check

OUTPUT = ROOT / "build"
STEM = "torneko-3-english"
FLIPS = ROOT / ".tools/bin/flips"
DETAILS = OUTPUT / "latest/english-build.json"


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def run_flips(*args):
    result = subprocess.run([str(FLIPS), *map(str, args)], cwd=ROOT,
                            capture_output=True, text=True)
    check(result.returncode == 0, "Floating IPS failed:\n" + result.stdout + result.stderr)
    return result.stdout.strip()


def build():
    check(FLIPS.is_file(), "Missing .tools/bin/flips; see docs/BUILD.md for setup.")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with (OUTPUT / ".english-build.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        original = ORIGINAL_ROM.read_bytes()
        print("Rebuilding cumulative English with source and allocation checks...", flush=True)
        data, component_report = current.build_rom(original)
        source_hash, target_hash = digest(original), digest(data)
        check(component_report["source_sha256"] == source_hash, "Builder source hash differs")
        check(component_report["rom_sha256"] == target_hash, "Builder output hash differs")
        with tempfile.TemporaryDirectory(prefix=".english-build-", dir=OUTPUT) as directory:
            staging = Path(directory)
            source = staging / "japanese.gba"
            target = staging / f"{STEM}.gba"
            patch = staging / f"{STEM}.bps"
            roundtrip = staging / "roundtrip.gba"
            # Use the exact source bytes that passed the cumulative build checks.
            source.write_bytes(original)
            target.write_bytes(data)
            print("Running native menu regression checks before publication...", flush=True)
            from tools import verify_menu_fixes as menu_checks
            suite_id = digest(Path(menu_checks.__file__).read_bytes() + menu_checks.FIXTURES.read_bytes())[:16]
            regression_dir = OUTPUT / "menu-fixes/publication-checks" / target_hash / suite_id
            regressions = menu_checks.run(data, regression_dir)
            check(regressions["rom_sha256"] == target_hash, "Emulator tested a different ROM")
            regression_path = regression_dir / "report.json"
            print("Running native combat and existing damage/XP regression checks...", flush=True)
            from tools import verify_combat_lines as combat_checks, verify_damage_lines as damage_checks
            combat_suite = digest(Path(combat_checks.__file__).read_bytes() +
                                  Path(damage_checks.__file__).read_bytes() + combat_checks.b.SELECTION.read_bytes())[:16]
            combat_dir = OUTPUT / "combat-lines/publication-checks" / target_hash / combat_suite
            combat = combat_checks.run(data, combat_dir)
            damage = damage_checks.run(data, combat_dir / "legacy-damage")
            check(combat["rom_sha256"] == damage["rom_sha256"] == target_hash,
                  "Combat checks tested a different ROM")
            combat_path = combat_dir / "report.json"
            damage_path = combat_dir / "legacy-damage/acceptance.json"
            from tools import verify_medal_trade as trade_checks
            trade_suite = digest(Path(trade_checks.__file__).read_bytes() +
                                 b''.join(p.read_bytes() for p in trade_checks.FIXTURES))[:16]
            trade_dir = OUTPUT / "medal-trade/publication-checks" / target_hash / trade_suite
            trade = trade_checks.run(data, trade_dir)
            check(trade["rom_sha256"] == target_hash, "Trade checks tested a different ROM")
            trade_path = trade_dir / "report.json"
            from tools import verify_companion_combat as companion_checks
            companion_suite = digest(Path(companion_checks.__file__).read_bytes() +
                                     b''.join(p.read_bytes() for p in companion_checks.FIXTURES))[:16]
            companion_dir = OUTPUT / "companion-combat/publication-checks" / target_hash / companion_suite
            companion = companion_checks.run(data, companion_dir)
            check(companion["rom_sha256"] == target_hash, "Companion checks tested a different ROM")
            companion_path = companion_dir / "report.json"
            print("Running native item-message and acquisition regression checks...", flush=True)
            from tools import verify_item_lines as item_checks
            item_suite = digest(Path(item_checks.__file__).read_bytes() +
                                b''.join(p.read_bytes() for p in item_checks.FIXTURES))[:16]
            item_dir = OUTPUT / "item-lines/publication-checks" / target_hash / item_suite
            item = item_checks.run(data, item_dir)
            check(item["rom_sha256"] == target_hash, "Item checks tested a different ROM")
            item_path = item_dir / "report.json"
            from tools import verify_dungeon_save_prompt as save_checks
            save_suite = digest(Path(save_checks.__file__).read_bytes() +
                                b''.join(p.read_bytes() for p in save_checks.FIXTURES))[:16]
            save_dir = OUTPUT / "dungeon-save-prompt/publication-checks" / target_hash / save_suite
            save_prompt = save_checks.run(data, save_dir)
            check(save_prompt["rom_sha256"] == target_hash, "Save prompt checks tested a different ROM")
            save_path = save_dir / "report.json"
            print("Checking expected English in menus, startup caches and post-game replay...", flush=True)
            from tools import verify_reference_coverage as reference_checks
            reference_suite = digest(Path(reference_checks.__file__).read_bytes() +
                                     Path(current.__file__).read_bytes() +
                                     b''.join(p.read_bytes() for p in reference_checks.FIXTURES))[:16]
            reference_dir = OUTPUT / "reference-coverage/publication-checks" / target_hash / reference_suite
            references = reference_checks.run(data, reference_dir)
            check(references["rom_sha256"] == target_hash, "Reference checks tested a different ROM")
            reference_path = reference_dir / "report.json"
            print("Creating BPS and checking the complete patched ROM...", flush=True)
            run_flips("--create", "--bps-linear", source, target, patch)
            run_flips("--apply", patch, source, roundtrip)
            check(roundtrip.read_bytes() == data, "BPS did not reproduce the English ROM exactly")
            patch_data = patch.read_bytes()
            check(digest(ORIGINAL_ROM.read_bytes()) == source_hash, "Japanese original changed during build")

            component_report = {**component_report, "output_rom": f"build/{STEM}.gba"}
            detail_data = json_bytes(component_report)
            receipt = {
                "schema": 1,
                "built_at_utc": datetime.now(timezone.utc).isoformat(),
                "build_id": target_hash[:12],
                "source_rom": str(ORIGINAL_ROM.relative_to(ROOT)),
                "source_sha256": source_hash,
                "output_rom": f"build/{STEM}.gba",
                "rom_sha256": target_hash,
                "rom_bytes": len(data),
                "patch": f"build/{STEM}.bps",
                "patch_format": "BPS",
                "patch_sha256": digest(patch_data),
                "patch_bytes": len(patch_data),
                "component_builder": current.__name__,
                "component_report": str(DETAILS.relative_to(ROOT)),
                "component_report_sha256": digest(detail_data),
                "publisher_sha256": digest(Path(__file__).read_bytes()),
                "flips_sha256": digest(FLIPS.read_bytes()),
                "flips_version": run_flips("--version"),
                "validation": {
                    "cumulative_source_and_allocation_checks": True,
                    "bps_roundtrip_byte_identical": True,
                    "emulator_checks_run_by_this_command": True,
                    "menu_regression_cases": len(regressions["cases"]),
                    "menu_regression_report": str(regression_path.relative_to(ROOT)),
                    "menu_regression_report_sha256": digest(regression_path.read_bytes()),
                    "trap_coverage": regressions["trap"],
                    "trade_regression_cases": len(trade["cases"]),
                    "trade_regression_report": str(trade_path.relative_to(ROOT)),
                    "trade_regression_report_sha256": digest(trade_path.read_bytes()),
                    "companion_regression_counts": companion["counts"],
                    "save_prompt_regression_report": str(save_path.relative_to(ROOT)),
                    "save_prompt_regression_report_sha256": digest(save_path.read_bytes()),
                    "reference_coverage_report": str(reference_path.relative_to(ROOT)),
                    "reference_coverage_report_sha256": digest(reference_path.read_bytes()),
                    "item_regression_counts": item["counts"],
                    "item_regression_report": str(item_path.relative_to(ROOT)),
                    "item_regression_report_sha256": digest(item_path.read_bytes()),
                    "companion_regression_report": str(companion_path.relative_to(ROOT)),
                    "companion_regression_report_sha256": digest(companion_path.read_bytes()),
                    "combat_regression_counts": combat["counts"],
                    "combat_regression_report": str(combat_path.relative_to(ROOT)),
                    "combat_regression_report_sha256": digest(combat_path.read_bytes()),
                    "legacy_damage_cases_per_rom": damage["cases_per_rom"],
                    "legacy_damage_report": str(damage_path.relative_to(ROOT)),
                    "legacy_damage_report_sha256": digest(damage_path.read_bytes()),
                },
            }
            # Validate everything before replacing the convenient output paths.
            # Each replacement is atomic; the receipt is written last.
            atomic_write(DETAILS, detail_data)
            atomic_write(OUTPUT / f"{STEM}.gba", data)
            atomic_write(OUTPUT / f"{STEM}.bps", patch_data)
            atomic_write(OUTPUT / f"{STEM}.json", json_bytes(receipt))
        print(f"Built build/{STEM}.gba ({len(data):,} bytes)")
        print(f"Patch build/{STEM}.bps ({len(patch_data):,} bytes)")
        print(f"Build {target_hash[:12]}; full hashes in build/{STEM}.json")
        return receipt


if __name__ == "__main__":
    argparse.ArgumentParser(description=__doc__).parse_args()
    build()
