# pose_estimation

Node `pose_estimation`: reads frames with OpenCV (`camera` is a V4L2 device index or a video
file path that loops at its end), runs YOLOv8n-pose (ultralytics) on `device` (`cpu` or
`cuda:0`) at `rate_hz`, and publishes for the largest detected person:

- `/estimation_points` (`vision_interfaces/msg/PoseKeypoints`): 17 COCO keypoints, x and y
  normalized to [0, 1]; keypoints below `conf_threshold` are (0, 0) with confidence 0.
- `/vision/image_raw` (`sensor_msgs/msg/Image`, bgr8, best effort) with the same header
  stamp, when `publish_image` is true.

On a non-CPU device a TensorRT `.engine` next to `model_path` (same stem) is loaded instead of
the `.pt`. The model and device actually used are logged at startup.
See `vision_bringup/config/vision.yaml` for all parameters.
