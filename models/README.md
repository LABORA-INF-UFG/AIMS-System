# Models directory

This directory is mounted into the containers at `/app/models`: read-only in `ros2-nodes`, read-write in `vision` (a TensorRT export writes its engine here).

## Vision model

| File | Shipped in the repository | Used by |
|---|---|---|
| `vision/yolov8n-pose.pt` | yes (about 6.8 MB) | `pose_estimation` (YOLOv8n-pose, 17 COCO keypoints), on CPU and on GPU |
| `vision/yolov8n-pose.engine` | no, you export it | `pose_estimation` on a GPU, if present |
| `vision/yolov8n-pose.onnx` | yes (about 13 MB) | Jetson image only: source of the engine below |
| `vision/yolov8n-pose.jetson.engine` | no, built on first start | `pose_estimation` with `backend: tensorrt` (Jetson image) |

The node reads `model_path` from `aims_ws/src/vision/vision_bringup/config/vision.yaml` (default `/app/models/vision/yolov8n-pose.pt`). When `device` is not `cpu` and a `.engine` with the same name stem exists next to the `.pt`, the engine is loaded instead. The node logs the model and device it uses at startup.

### Optional TensorRT engine (NVIDIA GPU)

A TensorRT engine is faster than the `.pt` on a GPU, but it is specific to the GPU and the TensorRT version it was built with. It is not portable: export it on the machine that will run it. Run the export script inside the `:cuda` image, which has TensorRT, with `./models` mounted:

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml --profile vision build vision
docker run --rm --gpus all --entrypoint bash \
  -v "$PWD/models:/app/models" -v "$PWD/scripts:/app/scripts:ro" \
  aims-system-vision:cuda /app/scripts/vision/export_tensorrt.sh
```

The script exports with `int8=True` and `imgsz=320` and writes `models/vision/yolov8n-pose.engine`. Then start vision as usual with `make up-vision-gpu`.

### Jetson (JetPack 4.6) ONNX and engine

The Jetson image (`docker-compose.jetson.yml`) has no PyTorch, so it cannot read the `.pt`. Its `pose_estimation` runs with `backend: tensorrt`: it loads `<stem>.jetson.engine` next to `model_path` and, when the engine is missing, builds it (FP16) from `<stem>.onnx`. The ONNX is in the repository; after changing the `.pt`, export it again with Docker, on the Jetson or on any PC:

```bash
scripts/vision/export_onnx.sh
```

The script pins torch 2.2.2 and onnx 1.16.2 without onnxslim: newer versions die with "Illegal instruction" on the Nano's Cortex-A57. Building the engine takes about 10 minutes on a Nano, on the first start of the vision container. After a new ONNX or a JetPack upgrade, delete `yolov8n-pose.jetson.engine` so it is rebuilt.

`.gitignore` ignores `*.engine`, `*.onnx` and `*.cache` under `models/`, except `vision/yolov8n-pose.onnx`: an engine works only on the GPU and TensorRT version that built it, so it is never committed.

## Apnea detection model (no longer used)

The Keras apnea model (`.h5`, default name `apenaDetection_AIMS_model1.h5`) was never shipped and is **no longer used**. The `apnea_ai` node and TensorFlow were removed from the core image; the code is in [deprecated/apnea_ai/](../deprecated/apnea_ai/README.md) with the steps to restore it. See [ADR-0010](../docs/adrs/ADR-0010-deprecate-apnea-ai-and-tensorflow.md). The dashboard's apnea alert comes from `/breath_estimate`, not from a model file here.

This file also keeps the directory tracked by git.
