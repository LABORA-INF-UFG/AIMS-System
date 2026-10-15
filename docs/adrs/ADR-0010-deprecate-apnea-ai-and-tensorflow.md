# ADR-0010: Deprecate the apnea_ai Node and Drop TensorFlow from the Core Image

- **Status**: Accepted
- **Date**: 2026-10-15
- **Deciders**: Luiz Fernando de Freitas Oliveira
- **Technical context**: Size and reproducibility of the `aims-system-ros2` image

---

## Context

The `apnea_ai` node ran a Keras model (`ApneaDetectionAI.py`) over the breathing signal and published `/apnea_ai`. Its state before this decision:

- It was not part of the default launch.
- The `.h5` model was never shipped with the repository. Without it the node logged a warning and disabled itself.
- Nothing consumed `/apnea_ai`. The dashboard's apnea alert comes from the `apnea_detected` field of `/breath_estimate`, published by `breath_estimator`.
- It was the only user of TensorFlow and Keras in the core image.

The core image installed `tensorflow[and-cuda]` from an unpinned `aims_ws/src/requirements.txt`. That pulled several GB of CUDA wheels that could never be used, because the container has no GPU. The image was 12.2 GB, took long to build and could not be reproduced exactly.

## Decision

- Move the node to `deprecated/apnea_ai/` (`apnea_ai_publisher.py`, `ApneaDetectionAI.py` and a README with the restore steps). The files keep their history (moved, not copied).
- Remove the `apnea_ai` entry point from `aims_ws/src/csi/setup.py` and the node from `test_aims_launch.py`.
- Remove TensorFlow and Keras from the core dependencies, and remove the `KERAS_APNEA_MODEL` variable.
- Replace `aims_ws/src/requirements.txt` with `requirements/core.in` and a hashed `requirements/core.lock`, built with `uv pip compile` and installed with `pip --require-hashes`. `requirements/constraints.txt` pins `numpy<2`, which ROS 2 Humble needs. The base image is pinned by digest.
- Keep `custom_interfaces/msg/ApneaAI.msg`, so a restored node and its clients still build.
- Remove the legacy `aims_ws/src/there_is_person` package (TensorFlow Lite) and its `.tflite` model; person detection now comes from the vision subsystem ([ADR-0009](./ADR-0009-vision-subsystem-separate-image.md)).

Core image size: 12.2 GB to 2.15 GB.

## Alternatives Considered

| Alternative | Why it was rejected |
|---|---|
| Keep TensorFlow in the core image | 10 GB of unused dependencies for a node that is not launched and has no model file. |
| Install TensorFlow CPU only (`tensorflow-cpu`) | Smaller than the CUDA build, but still a large dependency for an unused node, and still unpinned. |
| Move the node to its own image behind a profile | More Dockerfile, lock file and CI to maintain for a node nobody runs and that has no model. |
| Delete the node | Loses the code that a later apnea model study may want. `deprecated/` keeps it with the restore steps. |
| Keep TensorFlow, but only pin it | Fixes reproducibility, not size. |

## Consequences

### Positive
- The core image is 2.15 GB instead of 12.2 GB and builds faster.
- Core dependencies are pinned with hashes and rebuild to the same versions.
- No unused CUDA wheels in an image that has no GPU.
- The default launch and the dashboard are unaffected: `/breath_estimate` and its `apnea_detected` field are unchanged.

### Negative / Trade-offs
- **Breaking change**: the `apnea_ai` executable and `/apnea_ai` topic are gone from the `csi` package. `KERAS_APNEA_MODEL` is no longer read.
- Anyone who has a trained `.h5` model must restore the node by hand (below).
- `deprecated/` is not built, tested or covered by the lock file. It may drift from the rest of the code.
- Updating a core dependency now means re-running `uv pip compile`.

## How to restore

The steps are in [deprecated/apnea_ai/README.md](../../deprecated/apnea_ai/README.md):

1. Copy `apnea_ai_publisher.py` to `aims_ws/src/csi/csi/` and `ApneaDetectionAI.py` to `aims_ws/src/csi/csi/libs/`.
2. Re-add `'apnea_ai = csi.apnea_ai_publisher:main'` to `console_scripts` in `aims_ws/src/csi/setup.py`.
3. Add `tensorflow` and `keras` to `requirements/core.in`, re-run `uv pip compile` (the command is in the header of `requirements/core.lock`) and rebuild the image.
4. Set `KERAS_APNEA_MODEL` to the path of the Keras `.h5` model, for example under `./models` (mounted at `/app/models`), and start the node by hand with `ros2 run csi apnea_ai`.

## Related Links
- [ADR-0009](./ADR-0009-vision-subsystem-separate-image.md) — Vision subsystem in its own image
- [deprecated/apnea_ai/README.md](../../deprecated/apnea_ai/README.md) — Restore steps
- [models/README.md](../../models/README.md) — Model directory
