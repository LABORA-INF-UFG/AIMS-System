## there_is_person

Person detection node based on TensorFlow Lite.

## Build

```bash
cd aims_ws
source /opt/ros/foxy/setup.bash
colcon build
source install/setup.bash
```

## Run

```bash
ros2 run there_is_person is_person
```

## Requirements

- `AIMS` variable pointing to the repository root.
- Model file at `resources/lite-model_movenet_singlepose_thunder_tflite_float16_4.tflite`.
- Webcam connected for video capture.