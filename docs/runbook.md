# Build and run

This source reference includes native C/C++ plugins, ONNX parsing, generated inference configuration, a TensorRT engine cache, ZeroMQ metadata transport, a WebSocket bridge, a dashboard and portable tests. NVIDIA hardware validation is pending. No model weights, footage or historical deployment results are included.

## Portable dashboard and tests (Linux)

Use Python 3.11+, CMake 3.20+, a C++17 compiler, pkg-config, libzmq development headers, ShellCheck and GStreamer tools/base plugins. On Ubuntu:
```bash
sudo apt-get update
sudo apt-get install -y python3-venv cmake g++ pkg-config libzmq3-dev \
  shellcheck gstreamer1.0-tools gstreamer1.0-plugins-base
# PYTHON must refer to Python 3.11 or newer.
PYTHON=python3.11 scripts/setup-python.sh
scripts/test.sh
scripts/run-dashboard.sh
# Second terminal:
scripts/run-simulator.sh
```

Open http://127.0.0.1:8000. Stop the simulator before starting inference: both producers bind port 5556. The dashboard displays detection boxes on a coordinate grid, not camera video. PUB/SUB is best effort; slow consumers can lose events.

## Build on a Jetson

The adapter targets DeepStream 7.1-style APIs on Jetson Orin. First install the NVIDIA-supported JetPack/DeepStream development stack, TensorRT headers and documented prerequisites. Check the [NVIDIA support matrix](https://docs.nvidia.com/metropolis/deepstream/7.1/text/DS_Installation.html) for a matched stack. JetPack's default Python may need a separate Python 3.11+ environment.

Additional packages and build commands:
```bash
sudo apt-get install -y build-essential cmake pkg-config libzmq3-dev \
  libjson-glib-dev libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev
export DEEPSTREAM_ROOT=/opt/nvidia/deepstream/deepstream
scripts/build.sh --target
scripts/check-target.sh
```

| File | Purpose |
|---|---|
| build/libgstedgevision.so | edgeyolo and edgeevents GStreamer elements |
| build/libnvdsinfer_edge_yolo.so | Custom decoded-YOLO bbox parser |
| .cache/engines/<hash>/infer.ini | Generated target-specific nvinfer config |
| .cache/engines/<hash>/model.engine | TensorRT plan created by nvinfer on first run |

## Prepare the model

Supply ONNX meeting the exact main README contract: batch one, static input, RGB divided by 255, stretch resize, one decoded FP32 tensor [1,4+C,N] or [1,N,4+C]. Set --size to the square input resolution used by the export. Put one class per line in labels.txt, in output class order. Example labels are for the simulator only.

Arbitrary .pt weights, raw heads, objectness outputs and embedded end-to-end NMS are unsupported. The launcher checks files and generates settings; it cannot certify ONNX semantics.

## Generate config and run an H.264 MP4
```bash
scripts/generate-config.sh \
  --model /absolute/path/model.onnx --labels /absolute/path/labels.txt \
  --input /absolute/path/clip-h264.mp4 --size 640

scripts/run-file.sh \
  --model /absolute/path/model.onnx --labels /absolute/path/labels.txt \
  --input /absolute/path/clip-h264.mp4 --size 640
```

The launcher prints the exact config, engine path and shell-copyable command. NVIDIA nvinfer builds the engine on the first run and reuses it later. The cache key includes model, labels, parser, dimensions, precision and local runtime/device fingerprint. Do not copy plans between targets. A lock rejects concurrent producers using the same cache.

For a command preview without NVIDIA, use --dry-run with existing model, labels, parser and input files. Preview configs use a separate fingerprint and never create an engine. A preview does not validate a model or NVIDIA pipeline.

Equivalent manual pipeline (replace INFER_CONFIG with the generated absolute path). Manual runs bypass the cache lock; run one producer per cache.
```bash
export GST_PLUGIN_PATH="$PWD/build"
export DS_NEW_BUFAPI=1
export USE_NEW_NVSTREAMMUX=no
INFER_CONFIG=/absolute/path/to/generated/infer.ini
VIDEO=/absolute/path/clip-h264.mp4

gst-launch-1.0 -e \
  filesrc location="$VIDEO" ! qtdemux ! h264parse ! nvv4l2decoder ! mux.sink_0 \
  nvstreammux name=mux batch-size=1 width=640 height=640 live-source=false \
    batched-push-timeout=40000 \
  ! edgeyolo config-file="$INFER_CONFIG" \
  ! edgeevents endpoint=tcp://127.0.0.1:5556 frame-width=640 frame-height=640 \
  ! fakesink sync=true
```

Use the launcher for filenames with GStreamer metacharacters. It quotes both argv and GStreamer's parser; shell quoting alone does not handle every special path.

## Run an H.264 RTSP source
```bash
scripts/run-rtsp.sh \
  --model /absolute/path/model.onnx --labels /absolute/path/labels.txt \
  --rtsp rtsp://127.0.0.1:8554/camera --latency 200 --size 640
```

This selects H.264 video RTP caps, TCP transport and the requested jitter buffer. Authenticated camera provisioning and reconnection policy are extension points. Embedded credentials and query tokens are rejected to keep them out of process arguments and logs. Do not commit real camera URLs. H.265 is unsupported.

Equivalent pipeline, using the same environment and INFER_CONFIG:
```bash
gst-launch-1.0 -e \
  rtspsrc location=rtsp://127.0.0.1:8554/camera protocols=tcp latency=200 \
  ! 'application/x-rtp,media=video,encoding-name=H264' \
  ! rtph264depay ! h264parse ! nvv4l2decoder ! mux.sink_0 \
  nvstreammux name=mux batch-size=1 width=640 height=640 live-source=true \
    batched-push-timeout=40000 \
  ! edgeyolo config-file="$INFER_CONFIG" \
  ! edgeevents endpoint=tcp://127.0.0.1:5556 frame-width=640 frame-height=640 \
  ! fakesink sync=false
```

## Results and troubleshooting

Start scripts/run-dashboard.sh in another terminal before the producer. The multipart topic edge.detections.v1 carries source/frame IDs, timestamp, dimensions and labels/confidence/boxes. Native events have simulated=false; simulator events have simulated=true. Keep the default HTTP/WebSocket and ZeroMQ listeners on loopback. Remote use needs transport security and access control outside this reference.

| Symptom | Check |
|---|---|
| No edgeyolo / edgeevents | SDK build, GST_PLUGIN_PATH and shared-library dependencies |
| Tensor shape rejection | ONNX layout, class count and static batch-one dimensions |
| Engine failure | Stack compatibility, cache permissions, target fingerprint |
| No RTSP frames | H.264 stream, TCP reachability, source path, jitter buffer |
| No browser events | Stop simulator, match endpoints, inspect /health counters |
| Missing mux width/height | Legacy nvstreammux selected by USE_NEW_NVSTREAMMUX=no |

Portable CI tests the CPU decoder and actual C++ ZeroMQ worker, Python TCP/in-process transport, WebSockets, configs, dry-run commands and the real GStreamer core parser. NVIDIA adapters, TensorRT compilation, actual MP4/RTSP inference and performance await the [target validation procedure](target-validation.md).

References: [nvinfer](https://docs.nvidia.com/metropolis/deepstream/7.1/text/DS_plugin_gst-nvinfer.html), [nvstreammux](https://docs.nvidia.com/metropolis/deepstream/7.1/text/DS_plugin_gst-nvstreammux.html), [gst-launch](https://gstreamer.freedesktop.org/documentation/tools/gst-launch.html).
