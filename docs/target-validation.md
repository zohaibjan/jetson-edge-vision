# Target-device acceptance checklist

Portable validation: [GitHub Actions run 39000797020](https://github.com/zohaibjan/jetson-edge-vision/actions/runs/39000797020) passed on 17 October 2026: 27 Python tests, two C++ CTest executables, bash syntax and ShellCheck. Includes the actual native ZeroMQ publisher over TCP, Python TCP/in-process transport, WebSockets and GStreamer core parser integration.

Status: NVIDIA target validation pending. Record board model, JetPack, DeepStream, CUDA, TensorRT, GPU mode and model/exporter versions.

1. Compile BUILD_DEEPSTREAM=ON against the actual SDK. Check both plugin registrations with gst-inspect.
2. Use a known, licensed ONNX model matching the documented tensor contract and an H.264 MP4 with known annotations.
3. Start the bridge first, then the producer. Confirm real metadata has simulated=false and correct dimensions/labels.
4. Delete the cache, run once, confirm a nonempty engine file is created. Run again and verify the engine is loaded instead of rebuilt. Change model bytes or stack and verify a new cache location.
5. Compare decoded detections and NMS with the exporter's reference output. Test boxes touching image boundaries and images with no objects.
6. Confirm detection coordinates refer to the mux surface, not incorrectly to original video dimensions. Test non-square source footage.
7. Disconnect the subscriber, reconnect it and throttle the browser. Confirm frames continue and queues stay bounded.
8. Test EOS, missing plugins, invalid ONNX, wrong labels, unwritable cache and port-in-use. Fail clearly; do not report a successful inference run.
9. Record measured FPS/latency/resource usage only after testing. Keep hardware details, data provenance and cold/warm-engine timing with results.

10. Test the H.264 RTSP pipeline with a controlled stream, confirm live timestamps and valid metadata, then disconnect the camera. Record failure behavior; automatic reconnection is not implemented.

Do not claim the NVIDIA target checklist has passed until target-device evidence is available.
