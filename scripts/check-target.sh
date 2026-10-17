#!/usr/bin/env bash
set -euo pipefail
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
sdk="${DEEPSTREAM_ROOT:-/opt/nvidia/deepstream/deepstream}"
for command in gst-launch-1.0 gst-inspect-1.0 pkg-config; do
  command -v "$command" >/dev/null || { printf 'Missing command: %s\n' "$command" >&2; exit 1; }
done
test -f "$sdk/sources/includes/nvdsmeta.h" || { printf 'Missing SDK headers: %s\n' "$sdk" >&2; exit 1; }
pkg-config --exists gstreamer-1.0 gstreamer-base-1.0 libzmq json-glib-1.0
export GST_PLUGIN_PATH="$root/build${GST_PLUGIN_PATH:+:$GST_PLUGIN_PATH}"
export USE_NEW_NVSTREAMMUX=no
for plugin in nvinfer nvstreammux nvv4l2decoder qtdemux h264parse rtspsrc rtph264depay edgeyolo edgeevents; do
  gst-inspect-1.0 "$plugin" >/dev/null
done
printf 'Target prerequisites and custom plugin registration passed. Inference is still untested.\n'
