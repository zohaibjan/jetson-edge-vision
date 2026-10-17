# Inference configuration

`infer-yolo.ini.example` documents the generated nvinfer settings; replace every placeholder before manual use. Prefer `scripts/generate-config.sh`, which supplies absolute paths and a cache specific to the model, parser and installed target runtime.

`labels.demo.txt` matches the synthetic dashboard's three categories only. Real models need their own label vocabulary in exactly the output tensor's class order. No model weights, camera credentials or production configuration are stored here.

See [the runbook](../docs/runbook.md) for complete commands and the supported ONNX tensor contract in the main README.
