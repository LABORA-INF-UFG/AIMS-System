# heart_control (deprecated)

Deprecated on 2026-10-15. The node filmed the screen of a reference device with a
second camera (index 0, the same default as the vision node), asked the operator to
select an area in an OpenCV window and published a beat when that area turned white.
It needed a GUI on the host and a dedicated camera, and it was not in the default launch.

`custom_interfaces/msg/HeartControl.msg` was kept: new ground-truth sources (for
example a Polar chest strap or an ICU vital-signs monitor) publish the same
`/heart_control` topic, see [docs/ground-truth-topics.md](../../docs/ground-truth-topics.md).
Until one runs, the dashboard's heart ground truth stays empty; nothing else breaks.
`mock_heart_beat` still publishes `/heart_control` for tests.

## Restore

1. Copy `heart_control_publisher.py` to `aims_ws/src/csi/csi/` and
   `CameraHeartControl.py` to `aims_ws/src/csi/csi/libs/`.
2. Re-add `'heart_control = csi.heart_control_publisher:main'` to `console_scripts` in
   `aims_ws/src/csi/setup.py`.
3. It uses only `opencv-python-headless` and `numpy`, which the core image still has,
   but `cv2.imshow` needs a non-headless OpenCV and a display.
