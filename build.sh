#!/bin/bash
set -eu
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
exec .venv/bin/python -m tools.build_english "$@"
