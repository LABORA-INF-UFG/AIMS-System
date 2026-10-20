#!/bin/bash

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
# Manual tool: run it on the GPU machine that will use the engine (TensorRT engines are not portable).
WEIGHTS_DIR="$SCRIPT_DIR/../../models/vision"
MODEL_PT="$WEIGHTS_DIR/yolov8n-pose.pt"

echo "=== YOLOv8n-pose TensorRT Export Script ==="

# Check if the .pt file exists
if [ ! -f "$MODEL_PT" ]; then
    echo "Error: Model file $MODEL_PT not found!"
    exit 1
fi

echo "Found model: $MODEL_PT"

# Check for dependencies
echo "Checking dependencies..."
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is not installed!"
    exit 1
fi

# Check if ultralytics is installed
if ! python3 -c "import ultralytics" &> /dev/null; then
    echo "Error: 'ultralytics' is not installed for the current python3!"
    echo "Please run: pip3 install ultralytics --break-system-packages"
    exit 1
fi

# Check if tensorrt is installed
if ! python3 -c "import tensorrt" &> /dev/null; then
    echo "Error: 'tensorrt' is not installed for the current python3!"
    echo "Please run: pip3 install tensorrt --break-system-packages"
    exit 1
fi

echo "Dependencies verified."

# Perform the export
echo "Starting export (int8=True, imgsz=320)... This may take several minutes."
cd "$WEIGHTS_DIR" || exit
python3 -c "from ultralytics import YOLO; model = YOLO('$MODEL_PT'); model.export(format='engine', int8=True, imgsz=320, simplify=True)"

# Success message
if [ -f "$WEIGHTS_DIR/yolov8n-pose.engine" ]; then
    echo "=== Success! ==="
    echo "Engine file created: $WEIGHTS_DIR/yolov8n-pose.engine"
    echo "The pose_estimation node uses it when its device parameter is not 'cpu'."
else
    echo "=== Export Failed ==="
    echo "Check the errors above. You might need to install more dependencies or check your GPU/TensorRT version."
    exit 1
fi
