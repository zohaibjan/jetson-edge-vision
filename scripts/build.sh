#!/usr/bin/env bash
set -euo pipefail
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
mode="${1:---target}"
case "$mode" in
  --portable)
    cmake -S "$root" -B "$root/build-portable" -DCMAKE_BUILD_TYPE=Debug \
      -DBUILD_DEEPSTREAM=OFF -DBUILD_PUBLISHER_TESTS=ON
    cmake --build "$root/build-portable" --parallel "${JOBS:-2}"
    ctest --test-dir "$root/build-portable" --output-on-failure
    ;;
  --target)
    cmake -S "$root" -B "$root/build" -DCMAKE_BUILD_TYPE=RelWithDebInfo \
      -DBUILD_DEEPSTREAM=ON -DDEEPSTREAM_ROOT="${DEEPSTREAM_ROOT:-/opt/nvidia/deepstream/deepstream}"
    cmake --build "$root/build" --parallel "${JOBS:-2}"
    "$root/scripts/check-target.sh"
    ;;
  *) printf 'Usage: %s [--target|--portable]\n' "$0" >&2; exit 2 ;;
esac
