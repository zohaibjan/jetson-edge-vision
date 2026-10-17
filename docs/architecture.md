# Architecture decisions

1. **Use nvinfer for engine lifecycle.** A custom GstBin exposes the inference stage; NVIDIA's maintained loader/parser integration constructs and serializes the engine. Model weights and engine binaries are local inputs.
2. **Separate decoder from SDK.** The portable decoder has no CUDA/DeepStream dependency and is exercised with synthetic tensors. Its SDK adapter rejects unsupported layouts instead of guessing a YOLO version.
3. **Do not block the camera on a dashboard.** The C element copies bounded JSON into a 32-message queue. The publisher worker owns the ZeroMQ socket and drops old queued events under load. PUB/SUB is best-effort; it provides no delivery/replay guarantee.
4. **Bridge native messages to browser WebSockets.** The Python subscriber validates two-frame topic/JSON messages, class IDs, dimensions, finite confidence and box values. Browser queues retain at most two events and slow clients have a send timeout.
5. **Publish metadata only.** No image pixels are sent. Boxes use mux-surface coordinates and the launcher supplies matching frame dimensions. The current producer is single-source, named camera-0. Tracking IDs, multi-camera identity and video synchronization need an explicit later contract.
6. **Keep demonstration status visible.** Every frame contains a simulated boolean. The simulator always sets it true; the native exporter sets it false. The UI also marks stale inputs.

Bounds: 128 objects/frame, 256 KiB/message, 32 ZMQ HWM, 16 browser connections, 2 queued frames/client. These limits do not constitute formal real-time guarantees.
