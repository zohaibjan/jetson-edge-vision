"""Build auditable single-source GStreamer command lines without a shell."""
from pathlib import Path
from urllib.parse import urlsplit

def gst_string(value: str) -> str:
    """Escape for gst_parse_launch, not just for a shell."""
    if any(ord(c) < 32 for c in value):
        raise ValueError("GStreamer property strings must be single-line text")
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'

def validate_rtsp(uri: str) -> str:
    parsed = urlsplit(uri)
    if parsed.scheme not in {"rtsp", "rtsps"} or not parsed.hostname:
        raise ValueError("Supply an rtsp:// or rtsps:// camera URL")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("Do not put credentials, query tokens or fragments in camera URLs")
    gst_string(uri)
    return uri

def pipeline_command(config: Path, endpoint: str, size: int, *,
                     input_file: Path | None = None, rtsp: str | None = None,
                     latency: int = 200) -> list[str]:
    if (input_file is None) == (rtsp is None):
        raise ValueError("Choose exactly one MP4 file or RTSP source")
    if not 32 <= size <= 4096 or not 0 <= latency <= 10000:
        raise ValueError("Invalid mux dimensions or RTSP latency")
    address = urlsplit(endpoint)
    if (address.scheme != "tcp" or not address.hostname or not address.port
            or address.path or address.username or address.query or address.fragment):
        raise ValueError("Use a tcp://host:port metadata endpoint")
    if input_file is not None:
        source = ["filesrc", "location=" + gst_string(str(input_file.resolve())),
                  "!", "qtdemux", "!", "h264parse"]
    else:
        source = ["rtspsrc", "location=" + gst_string(validate_rtsp(rtsp)),
                  "protocols=tcp", f"latency={latency}", "!",
                  "application/x-rtp,media=video,encoding-name=H264", "!",
                  "rtph264depay", "!", "h264parse"]
    return ["gst-launch-1.0", "-e", *source, "!", "nvv4l2decoder", "!", "mux.sink_0",
            "nvstreammux", "name=mux", "batch-size=1", f"width={size}", f"height={size}",
            "live-source=" + ("true" if rtsp else "false"), "batched-push-timeout=40000",
            "!", "edgeyolo", "config-file=" + gst_string(str(config.resolve())),
            "!", "edgeevents", "endpoint=" + gst_string(endpoint),
            f"frame-width={size}", f"frame-height={size}", "!", "fakesink",
            "sync=" + ("false" if rtsp else "true")]
