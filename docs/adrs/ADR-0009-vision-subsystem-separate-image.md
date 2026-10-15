# ADR-0009: Vision Subsystem in the Monorepo, in Its Own Image Behind a Compose Profile

- **Status**: Accepted
- **Date**: 2026-10-15
- **Deciders**: Luiz Fernando de Freitas Oliveira
- **Technical context**: Integration of the MyCareBed ROS 2 vision pipeline (camera, YOLOv8n-pose) into AIMS

---

## Context

The dashboard already subscribes to `/vision_image` and `/there_is_person`, but nothing in this repository published them reliably. The only producer was a legacy `there_is_person` package that ran a TensorFlow Lite MoveNet model. It was outside the default launch and had no camera handling, no tests and no pinned dependencies.

MyCareBed, a sibling project, has a working ROS 2 Humble vision pipeline: YOLOv8n-pose for body keypoints, a presence rule, a movement detector based on Kalman filters, and an overlay publisher. AIMS needs it to show presence and movement next to the CSI breathing estimate.

Constraints:

- Vision needs `ultralytics` and PyTorch, and the CUDA variant adds the CUDA wheels and TensorRT. The core stack (CSI, breathing, rosbridge) must not pay that cost, and mock mode must keep working with `docker compose up -d --build` and nothing else.
- Most users have no camera, and Docker Desktop on Windows/macOS cannot pass a webcam to a container.
- A GPU is optional. The pipeline is configured at 15 Hz with a 320 px model, which runs on CPU; a GPU lowers the CPU load (tested on a GTX 1650, Turing).
- The camera may be on a different machine from the dashboard, so DDS discovery across the LAN must remain possible (see [ADR-0008](./ADR-0008-bridge-networking-as-default.md)).

## Decision

1. **Import the packages into the monorepo** under `aims_ws/src/vision/` (`vision_interfaces`, `pose_estimation`, `there_is_person`, `moving`, `visualization`, `vision_bringup`). The import is a separate commit with the code as-is, so later changes stay readable against upstream. The legacy top-level `there_is_person` package (TensorFlow Lite) and its `.tflite` model were removed.

2. **Run vision in its own image and service.** `docker/vision/Dockerfile` has a build argument `VISION_VARIANT` (`cpu` by default, or `cuda`). The service `vision` in `docker-compose.yml` sits behind the Compose profile `vision`, so `docker compose up -d --build` does not build or start it. It uses the same ROS 2 Humble base image, entrypoint and DDS profile as the core image, and joins the same bridge network and `ROS_DOMAIN_ID`.

3. **CPU by default, CUDA as an override.** `docker-compose.gpu.yml` switches the service to the `:cuda` image (PyTorch cu124 and TensorRT 10.7, from `requirements/vision-cuda.lock`), defaults `VISION_DEVICE` to `cuda:0` and reserves the NVIDIA device. The host needs only the NVIDIA driver plus the NVIDIA Container Toolkit (Linux) or Docker Desktop with WSL2 GPU support (Windows). A TensorRT engine is optional and is exported by `scripts/vision/export_tensorrt.sh` inside the `:cuda` image.

4. **Camera or video file.** `VISION_VIDEO_DEVICE` (default `/dev/video0`) is mapped to `/dev/video0` in the container, and `VISION_CAMERA` is a device index or a video path. Without a camera, map `/dev/null` and point `VISION_CAMERA` at a file in `./captures`.

5. **Host networking for a camera on another machine.** `docker-compose.hostnet.yml` also puts `vision` on the host network, as it does for `ros2-nodes` and `rosbridge`. The vision container can then run on the machine that has the camera.

6. **Hashed, locked dependencies.** `requirements/vision-cpu.in|lock` and `vision-cuda.in|lock` are installed with `pip --require-hashes`, like the core lock.

7. **Topic contracts.** Names and types are fixed so the dashboard and other clients can rely on them:

| Topic | Type | QoS |
|---|---|---|
| `/estimation_points` | `vision_interfaces/msg/PoseKeypoints` | reliable, volatile, depth 10 |
| `/vision/image_raw` | `sensor_msgs/msg/Image` | best effort, depth 1 |
| `/there_is_person` | `std_msgs/msg/Bool` | reliable, transient local, depth 1 |
| `/is_moving` | `std_msgs/msg/Bool` | reliable, transient local, depth 1 |
| `/vision_image` | `sensor_msgs/msg/CompressedImage` (JPEG) | reliable, volatile, depth 1 |

   - The two Bool topics are latched (`transient_local`) and publish `false` at startup, so a dashboard that connects late gets the current state immediately.
   - `/vision_image` changed from `sensor_msgs/Image` to `CompressedImage`. The `visualization` node draws the overlay and encodes the JPEG (5 Hz, quality 70), so rosbridge sends a small message instead of a raw frame.
   - Node names are snake_case. The dashboard detects the camera by the node `/pose_estimation`.

## Alternatives Considered

| Alternative | Why it was rejected |
|---|---|
| Keep MyCareBed in its own repository and only document how to run it | Two repositories to version, two sets of topic names to keep in sync, and no single `docker compose` entry point. A change in one repository could break the dashboard contract unnoticed. |
| One image for everything, with CUDA for all | Every user, including mock-mode users without a camera or a GPU, would download and build the CUDA PyTorch stack (the CUDA image is 16.7 GB). It would also tie the core image to NVIDIA wheels. |
| Build the vision image on an `nvidia/cuda` base image | Needs a second base distribution next to `ros:humble`, with ROS 2 installed on top. The PyTorch cu124 wheels already bundle the CUDA runtime, so the host needs only the driver. |
| A separate Compose project (own file and own network) | Two commands to start and stop, and the user must align the network and `ROS_DOMAIN_ID` by hand. A profile keeps one project, one network and one `docker compose --profile vision down`. |
| Put the vision dependencies in the core image | Core would grow from 2.15 GB to at least the size of the vision image for everyone, and the CUDA variant would still need its own image. |
| Keep the legacy TensorFlow Lite `there_is_person` | No camera handling, no tests, no movement detection, and it needed TensorFlow (see [ADR-0010](./ADR-0010-deprecate-apnea-ai-and-tensorflow.md)). |

## Consequences

### Positive
- `docker compose up -d --build` is unchanged and builds only the 2.15 GB core image. Vision is built only when asked for (`make up-vision`, `make up-vision-gpu`).
- The same code runs on CPU, on a GPU and on a GPU with a TensorRT engine. Only `device` changes.
- Testing without a camera works with any video file.
- The vision node can run on another machine with host networking.
- The topic contracts are written down in one place, and the presence rule and the keypoint filter have unit tests.

### Negative / Trade-offs
- Image sizes: vision CPU 4.1 GB, vision CUDA 16.7 GB. The first build of either is slow.
- The core and vision images share a base image but are built separately, so ROS packages are installed in both.
- A TensorRT engine is specific to the GPU and the TensorRT version. It must be exported on the machine that uses it and is not portable.
- The `:cuda` image was tested only on a Turing GPU (GTX 1650).
- A webcam cannot reach a container on Docker Desktop. Windows and macOS users need a video file, or the camera on a Linux machine with host networking.
- The presence rule (`min_points` 6, `min_std` 0.045 on both axes) was tuned for a close webcam. A person far away or narrow in the frame is not detected; tune `min_std` in `vision.yaml`.
- Privacy: `/vision_image` is a live JPEG stream of the subject, and rosbridge serves every topic on `0.0.0.0:9090` without authentication. Accepted for lab use on a trusted network; the README documents how to stop the stream (`publish_image: false`) or bind rosbridge to localhost.
- The CPU and CUDA variants use different image tags (`aims-system-vision:cpu` and `:cuda`), so switching between them builds the other image the first time.

## Related Links
- [ADR-0001](./ADR-0001-docker-compose-for-orchestration.md) — Docker Compose for orchestration
- [ADR-0004](./ADR-0004-rosbridge-as-web-ros2-integration-layer.md) — Rosbridge as the web integration layer
- [ADR-0008](./ADR-0008-bridge-networking-as-default.md) — Bridge networking as default
- [ADR-0010](./ADR-0010-deprecate-apnea-ai-and-tensorflow.md) — Deprecate apnea_ai and drop TensorFlow
- [aims_ws/src/vision/README.md](../../aims_ws/src/vision/README.md) — Packages, topics and parameters
