# pose_estimation

Node `pose_estimation`: reads frames with OpenCV (`camera` is a V4L2 device index or a video
file path that loops at its end) or, with `camera: oak`, from a Luxonis OAK camera through
depthai (`oak_camera.py`; installed only in the Jetson image), runs YOLOv8n-pose (ultralytics) on `device` (`cpu` or
`cuda:0`) at `rate_hz`, and publishes for the largest detected person:

- `/estimation_points` (`vision_interfaces/msg/PoseKeypoints`): 17 COCO keypoints, x and y
  normalized to [0, 1]; keypoints below `conf_threshold` are (0, 0) with confidence 0.
- `/vision/image_raw` (`sensor_msgs/msg/Image`, bgr8, best effort) with the same header
  stamp, when `publish_image` is true.

On a non-CPU device a TensorRT `.engine` next to `model_path` (same stem) is loaded instead of
the `.pt`. The model and device actually used are logged at startup.

With `backend: tensorrt` (the Jetson image, JetPack 4.6) the node does not use ultralytics or
PyTorch: `trt_pose.py` runs `<stem>.jetson.engine` on plain TensorRT 8.0, building it (FP16) from
`<stem>.onnx` when it is missing, and decodes the YOLOv8-pose output itself (same letterbox,
box confidence 0.25 and NMS IoU 0.7 as ultralytics). It stays Python 3.6 compatible.
See `vision_bringup/config/vision.yaml` for all parameters.
