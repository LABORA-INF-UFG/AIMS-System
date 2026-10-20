# apnea_ai (deprecated)

Deprecated on 2026-10-15. The node was not in the default launch (the dashboard's
apnea alert comes from `/breath_estimate`), and it pulled TensorFlow/CUDA into the
core image (about 12 GB). `custom_interfaces/msg/ApneaAI.msg` was kept.

## Restore

1. Copy `apnea_ai_publisher.py` to `aims_ws/src/csi/csi/` and `ApneaDetectionAI.py`
   to `aims_ws/src/csi/csi/libs/`.
2. Re-add `'apnea_ai = csi.apnea_ai_publisher:main'` to `console_scripts` in
   `aims_ws/src/csi/setup.py`.
3. Add `tensorflow` and `keras` to `requirements/core.in`, then re-run
   `uv pip compile` (see the header of `requirements/core.lock`) and rebuild the image.
4. Set `KERAS_APNEA_MODEL` to the path of the Keras `.h5` model.
