# AIMS vision

ROS 2 Humble packages that watch a person with a camera: YOLOv8n-pose estimates the body
keypoints, then simple rules decide whether a person is in the frame and whether they move.
Runs on CPU by default; a CUDA GPU (optionally with a TensorRT engine) is used when
`device` is set to `cuda:0`.

## Packages

| Package | Executable | Role |
| --- | --- | --- |
| `vision_interfaces` | - | `PoseKeypoints` message |
| `pose_estimation` | `pose_estimation` | Reads the camera (or a looping video file), runs YOLOv8n-pose and publishes the keypoints of the largest person and the raw frame |
| `there_is_person` | `there_is_person` | Decides whether a person is in the frame |
| `moving` | `moving` | Tracks the body keypoints with Kalman filters and decides whether the person moves |
| `visualization` | `visualization` | Draws the keypoints on the frame and publishes it as JPEG |
| `vision_bringup` | - | `vision.launch.py` and `config/vision.yaml` |

## Topics

| Topic | Type | QoS | Publisher |
| --- | --- | --- | --- |
| `/estimation_points` | `vision_interfaces/msg/PoseKeypoints` | reliable, volatile, depth 10 | `pose_estimation` |
| `/vision/image_raw` | `sensor_msgs/msg/Image` (bgr8, same stamp as the keypoints) | best effort, depth 1 | `pose_estimation` (if `publish_image`) |
| `/there_is_person` | `std_msgs/msg/Bool` | reliable, transient local (latched), depth 1 | `there_is_person` |
| `/is_moving` | `std_msgs/msg/Bool` | reliable, transient local (latched), depth 1 | `moving` |
| `/vision_image` | `sensor_msgs/msg/CompressedImage` (jpeg) | reliable, volatile, depth 1 | `visualization` |

Keypoints are the 17 COCO points (`nose`, `left_eye`, ..., `right_ankle`), x and y normalized
to [0, 1]; a keypoint below `conf_threshold` is reported as (0, 0) with confidence 0.
`/there_is_person` and `/is_moving` publish `false` at startup and then only on change.

## Parameters (`vision_bringup/config/vision.yaml`)

| Node | Parameter | Default | Meaning |
| --- | --- | --- | --- |
| `pose_estimation` | `device` | `cpu` | `cpu` or `cuda:0` |
| | `model_path` | `/app/models/vision/yolov8n-pose.pt` | On GPU, a `.engine` with the same stem next to it is used instead |
| | `camera` | `"0"` | Device index or video file path (files loop) |
| | `width`, `height`, `fps` | 352, 288, 30 | Real cameras only (V4L2, MJPG) |
| | `imgsz` | 320 | Inference size |
| | `conf_threshold` | 0.4 | Minimum keypoint confidence |
| | `rate_hz` | 15 | Inference rate |
| | `publish_image` | true | Publish `/vision/image_raw` |
| `there_is_person` | `min_points` | 6 | Minimum detected body keypoints (shoulders to knees) |
| | `min_std` | 0.045 | Minimum spread of those keypoints on x and on y |
| `moving` | `velocity_threshold` | 0.15 | Keypoint speed (normalized units/s) counted as movement |
| | `max_lost_frames` | 5 | Frames a missing keypoint keeps its track |
| `visualization` | `image_rate_hz` | 5 | `/vision_image` rate |
| | `jpeg_quality` | 70 | JPEG quality |
| | `show_window` | false | Also show an OpenCV window |

## Running

The model is `models/vision/yolov8n-pose.pt` in the repository, mounted at `/app/models`
in the container. `ultralytics` and `torch` come from `requirements/vision-*.lock`
(no rosdep key).

```bash
colcon build && source install/setup.bash
ros2 launch vision_bringup vision.launch.py device:=cpu camera:=0
```

`device` defaults to `$VISION_DEVICE` and `camera` to `$VISION_CAMERA` (else `cpu` and `0`).
Pass a video path as `camera` to test without a camera.

For a TensorRT engine, run `scripts/vision/export_tensorrt.sh` once inside the `:cuda` image on the GPU machine that will use it (steps in [models/README.md](../../../models/README.md)). Under Docker, `make up-vision` (CPU) and `make up-vision-gpu` start the pipeline; see the root [README](../../../README.md#vision-camera-optional).
