# Security and deployment scope

Local reference demo, not an internet-facing monitoring service. Bind the bridge and ZeroMQ publisher to loopback by default.

ZeroMQ TCP messages are unauthenticated and unencrypted in this example. For a remote Jetson, use an authenticated encrypted tunnel or add reviewed transport security. Restrict producer access; a forged producer can supply false detections.

The browser route enforces Host/origin checks, bounded connections and queues. These are not substitutes for user authentication, TLS, rate limiting and authorization. Use one bridge worker; its connection hub is process-local.

No footage, credentials, engine files or customer models belong in this repository. TensorRT plans are executable model artifacts: accept only trusted exports/builds. Camera credentials must not be embedded in published URIs or logs.

This project performs generic object detection. It contains no face recognition, person identification, automated enforcement or targeting logic. Validate any intended operational use separately.
