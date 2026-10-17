#!/usr/bin/env bash
set -euo pipefail
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"
for script in scripts/*.sh; do bash -n "$script"; done
shellcheck scripts/*.sh
"$root/scripts/build.sh" --portable
"$root/.venv/bin/python" -m pytest -q
