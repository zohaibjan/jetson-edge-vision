"""Target launcher: build a config, then let nvinfer create/reuse its engine."""
import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import os
from pathlib import Path
import platform
import shlex
import shutil
import subprocess
from .config import build_config
from .pipeline import pipeline_command, validate_rtsp

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


@contextmanager
def engine_lock(folder: Path):
    """Keep concurrent producers from writing the same TensorRT plan."""
    with (folder / ".lock").open("a") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("This engine cache is already in use by another producer") from exc
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)

def main():
    parser = argparse.ArgumentParser(description="One H.264 MP4 or RTSP stream -> YOLO -> ZeroMQ")
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--labels", type=Path, required=True)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input", type=Path, help="Existing H.264 MP4 file")
    source.add_argument("--rtsp", help="H.264 RTSP URL without embedded credentials")
    parser.add_argument("--build", type=Path, default=Path("build"))
    parser.add_argument("--cache", type=Path, default=Path(".cache/engines"))
    parser.add_argument("--sdk", type=Path, default=Path("/opt/nvidia/deepstream/deepstream"))
    parser.add_argument("--endpoint", default="tcp://127.0.0.1:5556")
    parser.add_argument("--size", type=int, default=640)
    parser.add_argument("--latency", type=int, default=200, help="RTSP jitter buffer milliseconds")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Portable command/config preview; no inference")
    mode.add_argument("--configure-only", action="store_true", help="Write target-specific config, then exit")
    args = parser.parse_args()
    try:
        if args.input is not None and not args.input.is_file():
            raise ValueError("Input must be an existing H.264 MP4 file")
        if args.rtsp is not None:
            validate_rtsp(args.rtsp)
        env = os.environ.copy()
        env["GST_PLUGIN_PATH"] = str(args.build.resolve()) + os.pathsep + env.get("GST_PLUGIN_PATH", "")
        env["DS_NEW_BUFAPI"] = "1"
        env["USE_NEW_NVSTREAMMUX"] = "no"
        if args.dry_run:
            runtime = "preview-only-not-a-validated-target"
        else:
            for command in ("gst-launch-1.0", "gst-inspect-1.0", "dpkg-query"):
                if not shutil.which(command):
                    raise RuntimeError(f"Missing target prerequisite: {command}")
            runtime = runtime_fingerprint(args.sdk)
            plugins = ["nvinfer", "nvstreammux", "nvv4l2decoder", "edgeyolo", "edgeevents", "h264parse"]
            plugins += ["rtspsrc", "rtph264depay"] if args.rtsp else ["qtdemux"]
            for plugin in plugins:
                result = subprocess.run(["gst-inspect-1.0", plugin], env=env, capture_output=True)
                if result.returncode:
                    raise RuntimeError(f"Unavailable GStreamer element: {plugin}")
        config, engine = build_config(args.model, args.labels,
            args.build / "libnvdsinfer_edge_yolo.so", args.cache, runtime, args.size)
        command = pipeline_command(config, args.endpoint, args.size, input_file=args.input,
                                   rtsp=args.rtsp, latency=args.latency)
        print("Config:", config, flush=True)
        print("Engine cache:", engine, "(nvinfer builds it on first use)", flush=True)
        print(shlex.join(command), flush=True)
        if args.dry_run:
            print("PREVIEW ONLY: no model validation, SDK execution or engine build occurred.")
            return
        if args.configure_only:
            return
        with engine_lock(engine.parent):
            subprocess.run(command, env=env, check=True)
    except (ValueError, RuntimeError, OSError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f"edge-vision: {exc}\n")

if __name__ == "__main__":
    main()
