#!/bin/bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: bash tools/verify_ghidra.sh path/to/game.gba" >&2
  exit 2
fi

TORNEKO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TORNEKO_ROM="$("$TORNEKO_ROOT/.venv/bin/python" -c 'import pathlib, sys; print(pathlib.Path(sys.argv[1]).resolve(strict=True))' "$1")"
cd "$TORNEKO_ROOT"
export JAVA_HOME="/opt/homebrew/opt/openjdk@21/libexec/openjdk.jdk/Contents/Home"
TORNEKO_GHIDRA_USER_HOME="${TORNEKO_GHIDRA_USER_HOME:-$TORNEKO_ROOT/.tools/ghidra-home}"
export JAVA_TOOL_OPTIONS="${JAVA_TOOL_OPTIONS:-} -Duser.home=$TORNEKO_GHIDRA_USER_HOME"
mkdir -p build/toolchain-validation .tools/validation
# Ghidra project paths cannot contain hidden directory components such as .tools.
TORNEKO_PROJECT_DIR="$(mktemp -d "$TORNEKO_ROOT/build/toolchain-validation/ghidra.XXXXXX")"
trap 'rmdir "$TORNEKO_PROJECT_DIR" 2>/dev/null || true' EXIT
TORNEKO_LOG="$TORNEKO_ROOT/.tools/validation/ghidra-import.log"

if ! /opt/homebrew/opt/ghidra/libexec/support/analyzeHeadless \
  "$TORNEKO_PROJECT_DIR" ToolchainSmoke \
  -import "$TORNEKO_ROM" -loader GBALoader \
  -scriptPath "$TORNEKO_ROOT/tools/ghidra_scripts" \
  -postScript VerifyGbaImport.java -noanalysis -deleteProject > "$TORNEKO_LOG" 2>&1; then
  tail -n 60 "$TORNEKO_LOG" >&2
  exit 1
fi

# Some headless script failures are logged without a nonzero process exit code.
if ! /usr/bin/grep -F 'TORNEKO_GBA_IMPORT_OK' "$TORNEKO_LOG"; then
  tail -n 60 "$TORNEKO_LOG" >&2
  exit 1
fi
