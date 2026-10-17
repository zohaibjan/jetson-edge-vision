"""Content-addressed inference configuration; nvinfer owns TensorRT construction."""
import hashlib
import json
from pathlib import Path

def build_config(model: Path, labels: Path, parser: Path, cache: Path,
                 runtime_id: str, size: int = 640, fp16: bool = True) -> tuple[Path, Path]:
    if model.suffix.lower() != ".onnx":
        raise ValueError("Supply a batch-one decoded YOLO ONNX export, not .pt weights")
    if not runtime_id.strip() or not 32 <= size <= 4096:
        raise ValueError("A target-specific runtime fingerprint and valid image size are required")
    for path in (model, labels, parser):
        if not path.is_file() or any(c in str(path.resolve()) for c in "\n\r;"):
            raise ValueError("Model, labels and parser must be existing single-line paths")
    names = labels.read_text(encoding="utf-8").splitlines()
    if not names or len(names) > 1000 or any(not n or len(n)>128 for n in names):
        raise ValueError("Supply one nonempty label per class")
    digest = hashlib.sha256()
    for path in (model, labels, parser):
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024*1024), b""):
                digest.update(block)
    digest.update(json.dumps([runtime_id, size, fp16, len(names)], sort_keys=True).encode())
    folder = cache.resolve() / digest.hexdigest()[:24]
    folder.mkdir(parents=True, exist_ok=True)
    engine = folder / "model.engine"
    config = folder / "infer.ini"
    # No shell interpolation. The native SDK caches the serialized engine here.
    config.write_text("\n".join([
        "[property]", "gpu-id=0", "batch-size=1", "network-type=0", "process-mode=1",
        "gie-unique-id=1", f"onnx-file={model.resolve()}", f"model-engine-file={engine}",
        f"labelfile-path={labels.resolve()}", f"num-detected-classes={len(names)}",
        f"custom-lib-path={parser.resolve()}", "parse-bbox-func-name=NvDsInferParseEdgeYolo",
        "network-mode=2" if fp16 else "network-mode=0", "net-scale-factor=0.00392156862745098",
        "model-color-format=0", "maintain-aspect-ratio=0", "cluster-mode=2",
        "", "[class-attrs-all]", "pre-cluster-threshold=0.25", "nms-iou-threshold=0.45", "topk=128", ""
    ]), encoding="utf-8")
    return config, engine
