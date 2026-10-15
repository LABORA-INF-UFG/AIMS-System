# breath_control (deprecated)

Deprecated on 2026-10-15. The node listened to the operator's mouse clicks with
`pynput`, which needs a GUI session on the host and cannot see the mouse from inside a
container. The dashboard now has a **Breath** button that publishes the same
`/breath_control` message (`custom_interfaces/msg/BreathControl`, `timestamp` in ns)
through rosbridge, so `persistence_action` still writes the `Breaths-` file.
Removing it dropped `pynput` and `evdev` from the core image.

## Restore

1. Copy `breath_control_publisher.py` to `aims_ws/src/csi/csi/`.
2. Re-add `'breath_control = csi.breath_control_publisher:main'` to `console_scripts` in
   `aims_ws/src/csi/setup.py`.
3. Add `pynput` and `evdev<1.7` to `requirements/core.in`, re-run `uv pip compile`
   (see the header of `requirements/core.lock`), and copy the `evdev` build from the
   builder stage in `docker/ros2/Dockerfile` again (it has no wheel).
4. Run it on a host with a display: it needs the real mouse.
