# Models directory

This directory is mounted into the containers at `/app/models`: read-only in `ros2-nodes`, read-write in `vision` (a TensorRT export writes its engine here).

## Vision model

| File | Shipped in the repository | Used by |
|---|---|---|
| `vision/yolov8n-pose.pt` | yes (about 6.8 MB) | `pose_estimation` (YOLOv8n-pose, 17 COCO keypoints), on CPU and on GPU |
| `vision/yolov8n-pose.engine` | no, you export it | `pose_estimation` on a GPU, if present |

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

`.gitignore` does **not** list `*.engine`, so the file shows up in `git status`. Do not commit it: it works only on the GPU that built it.

## Apnea detection model (no longer used)

The Keras apnea model (`.h5`, default name `apenaDetection_AIMS_model1.h5`) was never shipped and is **no longer used**. The `apnea_ai` node and TensorFlow were removed from the core image; the code is in [deprecated/apnea_ai/](../deprecated/apnea_ai/README.md) with the steps to restore it. See [ADR-0010](../docs/adrs/ADR-0010-deprecate-apnea-ai-and-tensorflow.md). The dashboard's apnea alert comes from `/breath_estimate`, not from a model file here.

This file also keeps the directory tracked by git.
