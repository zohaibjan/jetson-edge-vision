#!/usr/bin/env bash
set -euo pipefail
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"
exec "$root/.venv/bin/python" -m uvicorn edgevision.bridge:app --host 127.0.0.1 --port 8000 "$@"
