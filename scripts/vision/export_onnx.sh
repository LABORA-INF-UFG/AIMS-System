#!/bin/bash

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
WEIGHTS_DIR="$( cd "$SCRIPT_DIR/../../models/vision" && pwd )"
IMGSZ="${IMGSZ:-320}"

if [ ! -f "$WEIGHTS_DIR/yolov8n-pose.pt" ]; then
    echo "Error: $WEIGHTS_DIR/yolov8n-pose.pt not found!"
    exit 1
fi

echo "=== Exporting yolov8n-pose.pt to ONNX (imgsz=$IMGSZ, opset 12) ==="
docker run --rm -v "$WEIGHTS_DIR:/w" -w /w -e YOLO_OFFLINE=1 python:3.10-slim bash -c "
    set -e
    apt-get update -qq && apt-get install -y -qq libgl1 libglib2.0-0 > /dev/null
    pip install -q --no-cache-dir torch==2.2.2 torchvision==0.17.2 'numpy<2' \
        --extra-index-url https://download.pytorch.org/whl/cpu
    pip install -q --no-cache-dir ultralytics==8.4.177 onnx==1.16.2
    yolo export model=yolov8n-pose.pt format=onnx imgsz=$IMGSZ opset=12 simplify=False dynamic=False
    chown $(id -u):$(id -g) yolov8n-pose.onnx
"

echo "=== Success! ==="
echo "Created $WEIGHTS_DIR/yolov8n-pose.onnx"
echo "Delete yolov8n-pose.jetson.engine (if any) so the vision container rebuilds it."
