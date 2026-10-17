import shlex
import shutil
import subprocess
import sys
from pathlib import Path
import pytest
from edgevision.cli import engine_lock
from edgevision.pipeline import gst_string, pipeline_command, validate_rtsp

def test_file_pipeline(tmp_path):
    command = pipeline_command(tmp_path/"infer.ini", "tcp://127.0.0.1:5556", 640,
                               input_file=tmp_path/"video.mp4")
    assert command[:3] == ["gst-launch-1.0", "-e", "filesrc"]
    assert "qtdemux" in command and "live-source=false" in command and "sync=true" in command
    assert "edgeyolo" in command and "edgeevents" in command and "mux.sink_0" in command
    assert shlex.split(shlex.join(command)) == command

def test_rtsp_pipeline(tmp_path):
    command = pipeline_command(tmp_path/"infer.ini", "tcp://127.0.0.1:5556", 640,
                               rtsp="rtsp://127.0.0.1:8554/camera", latency=300)
    assert "rtspsrc" in command and "rtph264depay" in command and "latency=300" in command
    assert "live-source=true" in command and "sync=false" in command
    assert "qtdemux" not in command

@pytest.mark.parametrize("uri", ["http://camera", "rtsp://", "rtsp://user:secret@camera/live",
                                  "rtsp://camera/live?token=secret", "rtsp://camera/live\n! fakesink"])
def test_invalid_camera_urls(uri):
    with pytest.raises(ValueError):
        validate_rtsp(uri)

@pytest.mark.parametrize("kwargs", [{}, {"input_file":Path("x"),"rtsp":"rtsp://camera/live"},
                                    {"input_file":Path("x"),"size":0},
                                    {"rtsp":"rtsp://camera/live","latency":-1}])
def test_invalid_pipeline_options(tmp_path, kwargs):
    size = kwargs.pop("size",640)
    with pytest.raises(ValueError):
        pipeline_command(tmp_path/"infer.ini","tcp://127.0.0.1:5556",size,**kwargs)

def test_gstreamer_parser_handles_special_paths(tmp_path):
    if not shutil.which("gst-launch-1.0"):
        pytest.skip("Install GStreamer for this real parser integration test")
    source = tmp_path/'clip with spaces "quotes" !.bin'
    source.write_bytes(b"real GStreamer read test")
    result = subprocess.run(["gst-launch-1.0","-q","filesrc",
                             "location="+gst_string(str(source)),"!","fakesink"],
                            capture_output=True,text=True,timeout=10)
    assert result.returncode == 0, result.stderr

def test_cache_lock_rejects_second_producer(tmp_path):
    with engine_lock(tmp_path):
        with pytest.raises(RuntimeError,match="already in use"):
            with engine_lock(tmp_path):
                pass
    with engine_lock(tmp_path):
        pass

def test_dry_run_works_without_sdk(tmp_path):
    model = tmp_path/"model.onnx"; model.write_bytes(b"synthetic bytes, not a usable model")
    labels = tmp_path/"labels.txt"; labels.write_text("person\n")
    build = tmp_path/"build"; build.mkdir()
    (build/"libnvdsinfer_edge_yolo.so").write_bytes(b"synthetic parser bytes")
    video = tmp_path/"clip.mp4"; video.write_bytes(b"synthetic bytes, not a video")
    result = subprocess.run([sys.executable,"-m","edgevision.cli","--dry-run",
        "--model",str(model),"--labels",str(labels),"--build",str(build),
        "--cache",str(tmp_path/"cache"),"--input",str(video)],
        capture_output=True,text=True,timeout=10)
    assert result.returncode == 0, result.stderr
    assert "PREVIEW ONLY" in result.stdout and "gst-launch-1.0" in result.stdout
    configs = list((tmp_path/"cache").glob("*/infer.ini"))
    assert len(configs)==1 and "num-detected-classes=1" in configs[0].read_text()
    assert not list((tmp_path/"cache").glob("*/model.engine"))
