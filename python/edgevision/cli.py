import argparse
import hashlib
import os
from pathlib import Path
import platform
import shutil
import subprocess
from .config import build_config

def runtime_fingerprint(sdk: Path) -> str:
    """Conservatively identify the local stack; target changes create a new cache."""
    parts = [platform.machine(), platform.release()]
    for command in (["dpkg-query", "-W", "nvidia-l4t-core", "libnvinfer10", "libnvinfer8"],
                    ["gst-inspect-1.0", "nvinfer"]):
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        parts.append(result.stdout)
    release = Path("/etc/nv_tegra_release")
    if release.exists():
        parts.append(release.read_text())
    library = sdk / "lib/gst-plugins/libnvdsgst_infer.so"
    if not library.exists():
        raise RuntimeError("Cannot fingerprint installed nvinfer library; check --sdk")
    parts.append(hashlib.sha256(library.read_bytes()).hexdigest())
    # Engine plans are not portable: also identify this physical target.
    machine_id = Path("/etc/machine-id")
    if not machine_id.exists():
        raise RuntimeError("Cannot identify target for safe engine caching")
    parts.append(machine_id.read_text())
    return hashlib.sha256("\n".join(parts).encode()).hexdigest()

def main():
    parser = argparse.ArgumentParser(description="One H.264 MP4 -> YOLO -> ZeroMQ events")
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--build", type=Path, default=Path("build"))
    parser.add_argument("--cache", type=Path, default=Path(".cache/engines"))
    parser.add_argument("--sdk", type=Path, default=Path("/opt/nvidia/deepstream/deepstream"))
    parser.add_argument("--endpoint", default="tcp://127.0.0.1:5556")
    parser.add_argument("--size", type=int, default=640)
    args = parser.parse_args()
    if not args.input.is_file():
        parser.error("Input must be an existing H.264 MP4 file")
    if not shutil.which("gst-launch-1.0"):
        parser.error("Install the target DeepStream/GStreamer runtime first")
    env = os.environ.copy()
    env["GST_PLUGIN_PATH"] = str(args.build.resolve()) + os.pathsep + env.get("GST_PLUGIN_PATH", "")
    env["DS_NEW_BUFAPI"] = "1"
    config, engine = build_config(args.model, args.labels,
        args.build / "libnvdsinfer_edge_yolo.so", args.cache, runtime_fingerprint(args.sdk), args.size)
    print("Engine cache:", engine, "(nvinfer builds it on first use)")
    # Individual argv entries preserve spaces in paths; no shell is invoked.
    command = ["gst-launch-1.0", "-e", "filesrc", f"location={args.input.resolve()}",
        "!", "qtdemux", "!", "h264parse", "!", "nvv4l2decoder", "!", "mux.sink_0",
        "nvstreammux", "name=mux", "batch-size=1", f"width={args.size}", f"height={args.size}",
        "batched-push-timeout=40000", "!", "edgeyolo", f"config-file={config}",
        "!", "edgeevents", f"endpoint={args.endpoint}", f"frame-width={args.size}", f"frame-height={args.size}",
        "!", "fakesink", "sync=true"]
    subprocess.run(command, env=env, check=True)

if __name__ == "__main__":
    main()
