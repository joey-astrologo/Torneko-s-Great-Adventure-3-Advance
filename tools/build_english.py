"""Rebuild cumulative English and publish the latest ROM, BPS and build receipt."""

import argparse
from datetime import datetime, timezone
import fcntl
import json
from pathlib import Path
import subprocess
import tempfile

from tools import build_rendering_fixes as current
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
                    "emulator_checks_run_by_this_command": False,
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
