# AIMS System

**A**dvanced **M**ulti**I**modal **S**ensing: a contactless vital-sign monitoring system based on Wi-Fi Channel State Information (CSI), ROS2 and a web interface.

AIMS captures CSI frames from an Intel IWL5300 NIC with [PicoScenes](https://ps.zpj.io/), publishes them as ROS2 messages, estimates breathing rate (and detects apnea) from them in real time, and shows the signals in a browser dashboard. Captures can be saved to text files for offline analysis. A mock CSI source lets you run the whole pipeline without any hardware. An optional camera pipeline (YOLOv8n-pose, CPU or NVIDIA GPU) adds person presence and movement to the dashboard.

## How to cite

If you use this software, please cite the article. Citation metadata for GitHub's "Cite this repository" button is in [CITATION.cff](CITATION.cff). The fields below are placeholders and must be completed by the authors:

```bibtex
@article{TODO_citation_key,
  author  = {TODO: authors},
  title   = {TODO: article title},
  journal = {TODO: venue},
  year    = {TODO: year},
  doi     = {TODO: DOI}
}
```

## Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  HOST (Linux, only for real hardware)                                        │
│  ┌───────────────────┐   UDP, one CSI frame per datagram                     │
│  │ PicoScenes        │────────────────────────────┐                          │
│  │ (IWL5300 NIC)     │   --forward 127.0.0.1:1025 │                          │
│  └───────────────────┘                            │                          │
├───────────────────────────────────────────────────┼──────────────────────────┤
│  DOCKER COMPOSE (bridge network, published ports) ▼ UDP 1025                 │
│  ┌──────────────────────────────────────────────────────────────────────┐    │
│  │ ros2-nodes                                                           │    │
│  │  CSI_SOURCE=mock       mock_csi ──────────┐                          │    │
│  │  CSI_SOURCE=picoscenes csi_publisher ─────┴─► /pktcsi                │    │
│  │  breath_estimator ─► /breath_estimate                                │    │
│  │  csi_heatmap_publisher ─► /heatmap                                   │    │
│  │  persistence_action + persistence_bridge ─► captures/*.txt           │    │
│  └──────────────────────────────────────────────────────────────────────┘    │
│  ┌──────────────────────────────────────────────────────────────────────┐    │
│  │ vision  (optional, profile "vision")                                 │    │
│  │  camera/video ─► pose_estimation ─► /estimation_points               │    │
│  │  there_is_person ─► /there_is_person      moving ─► /is_moving       │    │
│  │  visualization ─► /vision_image (JPEG)                               │    │
│  └──────────────────────────────────────────────────────────────────────┘    │
│                      │ DDS (inside the bridge network)                       │
│  ┌───────────────────▼──────────────────────────────────────────────────┐    │
│  │ rosbridge  (WebSocket :9090 <-> ROS2 topics)                         │    │
│  └──────────────────────────────────────────────────────────────────────┘    │
│  ┌──────────────────────────────────────────────────────────────────────┐    │
│  │ web  (Express.js :3001: serves the dashboard and GET /config)        │    │
│  └──────────────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────────────┘
        Browser ──HTTP :3001──► web      Browser ──WebSocket :9090──► rosbridge
```

The browser talks to rosbridge directly (roslib.js), at the same hostname that served the page. The full diagram of the original system is in [architecture-v0.png](architecture-v0.png). The reasoning behind the main decisions is in [docs/adrs/](docs/adrs/README.md).

## Quick start (mock mode, no hardware)

You need [Docker](https://docs.docker.com/get-docker/) with Docker Compose >= 2.24. Nothing else, and no `.env` file.

```bash
git clone https://github.com/LABORA-INF-UFG/AIMS-System.git
cd AIMS-System
docker compose up -d --build
```

Open http://localhost:3001 and go to **Monitoring**. The first build takes a while (core ROS2 image, about 2 GB). The breathing estimate needs about 35 seconds after start to publish its first value (30 s buffer at 100 Hz); the charts fill after that.

Stop with `docker compose down`. Logs: `docker compose logs -f`.

If you have `make`, `make up`, `make down`, `make logs` and `make build` wrap the same commands. `make down` runs `docker compose --profile vision down`, so it also stops the vision container.

## Hardware mode (real CSI)

Hardware mode needs a **Linux machine (Ubuntu, amd64) with an Intel IWL5300 NIC**. PicoScenes depends on the host's kernel driver and NIC firmware, so it runs on the host, not in Docker. It forwards each CSI frame by UDP to port 1025, where the container listens.

1. Install PicoScenes on the host (once), then reboot:
   ```bash
   scripts/host/install_picoscenes.sh      # or: make host-setup
   sudo reboot
   ```
2. Start the receiver on the host (adjust the NIC name; see `ip link`):
   ```bash
   scripts/host/picoscenes_rx.sh --nic wlp2s0 --freq 5180 --bw HT20
   ```
3. Start the stack with the real CSI source:
   ```bash
   CSI_SOURCE=picoscenes docker compose up -d --build     # or: make up-hardware
   ```
4. On a second machine, start the transmitter that injects packets:
   ```bash
   scripts/host/picoscenes_tx.sh --nic wlp1s0
   ```

Details, flags and the optional systemd service are in [picoscenes/README.md](picoscenes/README.md).

## Vision (camera, optional)

The vision pipeline runs in its own image behind the Compose profile `vision`, so the commands above do not build or start it. It reads a camera (or a video file), estimates body keypoints with YOLOv8n-pose and publishes person presence, movement and an annotated JPEG that the dashboard shows. Packages, topics and parameters are in [aims_ws/src/vision/README.md](aims_ws/src/vision/README.md); the reasoning is in [ADR-0009](docs/adrs/ADR-0009-vision-subsystem-separate-image.md).

| Image | Size | Build |
|---|---|---|
| `aims-system-ros2` (core) | 2.15 GB | `docker compose build` |
| `aims-system-vision:cpu` | 4.1 GB | `docker compose --profile vision build` |
| `aims-system-vision:cuda` | 16.7 GB | `docker compose -f docker-compose.yml -f docker-compose.gpu.yml --profile vision build` |

**CPU** (default; needs a camera at `/dev/video0` on a Linux host):

```bash
docker compose --profile vision up -d --build        # or: make up-vision
```

**NVIDIA GPU** (PyTorch cu124 and TensorRT 10.7; tested on a GTX 1650):

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml --profile vision up -d --build   # or: make up-vision-gpu
```

The host needs the NVIDIA driver plus the NVIDIA Container Toolkit (Linux), or Docker Desktop with WSL2 GPU support (Windows). Optionally export a TensorRT engine for the GPU; see [models/README.md](models/README.md).

**Video file instead of a camera** (Docker Desktop has no webcam; also useful for tests). Put a video in `./captures`, then map `/dev/null` in place of the camera device and point `VISION_CAMERA` at the file (it loops):

```bash
VISION_VIDEO_DEVICE=/dev/null VISION_CAMERA=/app/captures/clip.mp4 docker compose --profile vision up -d --build
```

In Git Bash on Windows, prefix the command with `MSYS_NO_PATHCONV=1`, otherwise `/dev/null` is rewritten to `nul`.

**Camera on another machine** (Linux, host networking): on the machine that has the camera, start only the vision service (same `ROS_DOMAIN_ID` as the rest of the stack):

```bash
docker compose -f docker-compose.yml -f docker-compose.hostnet.yml --profile vision up -d --build --no-deps vision
```

Add `-f docker-compose.gpu.yml` as a third file for a GPU.

When the first `/is_moving` arrives, the dashboard shows a movement pill (Moving / Still); before that it shows "Waiting for camera". The Camera tab appears when the node `/pose_estimation` exists.

**Limits to know about:**
- The presence rule (`min_points` 6, `min_std` 0.045 on both axes) was tuned for a close webcam. A person far away or narrow in the frame is not detected; lower `min_std` in `aims_ws/src/vision/vision_bringup/config/vision.yaml`.
- The ground-truth tools `breath_control` (operator mouse clicks, `pynput`) and `heart_control` (a second camera filming a reference device) are not in the default launch and need a host with a GUI. `heart_control` also opens camera index 0, the same default as the vision node.
- The **Position Map** tab shows `/heatmapmmw` from the mmWave radar node `mmw_talker` (TI IWR1642 over serial), which is not in the default launch. Without the radar the tab keeps spinning.

## Environment variables

All variables are optional: each has a built-in default (the value shown). To change one, set it in the shell or copy `.env.example` to `.env` (Compose >= 2.24 reads it if present).

| Variable | Default | Used by | Description |
|---|---|---|---|
| `CSI_SOURCE` | `mock` | ros2-nodes | `mock` replays a recorded frame; `picoscenes` reads UDP frames from PicoScenes |
| `CSI_UDP_HOST` | `0.0.0.0` | ros2-nodes | Address `csi_publisher` listens on (also hosts the published UDP port) |
| `CSI_UDP_PORT` | `1025` | ros2-nodes | UDP port for CSI frames |
| `ROS_DOMAIN_ID` | `5` | ros2-nodes, rosbridge | ROS2 DDS domain; must match across machines |
| `RMW_IMPLEMENTATION` | `rmw_fastrtps_cpp` | ros2-nodes, rosbridge | ROS2 middleware |
| `FASTRTPS_DEFAULT_PROFILES_FILE` | `/app/aims_ws/src/fastdds_profile.xml` | ros2-nodes, rosbridge | FastDDS profile |
| `ROS_DISTRO` | `humble` | `.env.example` only | Documents the target ROS2 distribution; not read by `docker-compose.yml` |
| `WEB_PORT` | `3001` | web | Host port of the dashboard |
| `NODE_ENV` | `development` | web | Node.js environment |
| `ROSBRIDGE_PORT` | `9090` | rosbridge, web | Host port of the rosbridge WebSocket; the web server hands it to the browser via `GET /config` |
| `VISION_DEVICE` | `cpu` (`cuda:0` with `docker-compose.gpu.yml`) | vision | Inference device of `pose_estimation`: `cpu` or `cuda:0` |
| `VISION_CAMERA` | `0` | vision | Camera index (`0` is `/dev/video0`) or a video file path inside the container, such as `/app/captures/clip.mp4` |
| `VISION_VIDEO_DEVICE` | `/dev/video0` | vision | Host device mapped to `/dev/video0` in the container; set to `/dev/null` when there is no camera |
| `PICOSCENES_FORWARD_HOST` | `127.0.0.1` | host scripts | Where `picoscenes_rx.sh` forwards frames |
| `PICOSCENES_FORWARD_PORT` | `1025` | host scripts | UDP port to forward to |
| `PICOSCENES_NIC` | `wlp2s0` | host scripts | RX NIC name |
| `PICOSCENES_PHYPATH` | `2` | host scripts | PicoScenes PhyPath of the RX NIC |
| `PICOSCENES_FREQ` | `5180` | host scripts | Center frequency in MHz |
| `PICOSCENES_BW` | `HT20` | host scripts | Bandwidth (`HT20`, `HT40`, `HT40+`, `HT40-`) |
| `PICOSCENES_TX_NIC` | none (required, or `--nic`) | `picoscenes_tx.sh` | TX NIC name |
| `PICOSCENES_TX_PHYPATH` | `1` | `picoscenes_tx.sh` | PicoScenes PhyPath of the TX NIC |
| `PICOSCENES_TX_DELAY_US` | `10000` | `picoscenes_tx.sh` | Gap between injected packets, in microseconds |

The `PICOSCENES_*` variables are read only by the host scripts, not by the containers. `VISION_*` are read only by the `vision` service (profile `vision`).

## ROS2 nodes and topics

| Executable | Role | Publishes | Subscribes |
|---|---|---|---|
| `csi_publisher` | Parses CSI frames received over UDP (`CSI_SOURCE=picoscenes`) | `/pktcsi` | |
| `mock_csi` | Replays a recorded CSI frame (`CSI_SOURCE=mock`) | `/pktcsi` | |
| `breath_estimator` | Breathing rate and apnea flag | `/breath_estimate` | `/pktcsi` |
| `csi_heatmap_publisher` | CSI heatmap image | `/heatmap` | `/pktcsi` |
| `persistence_action` | Action server `persist_csi`: saves N frames to `captures/` | | `/pktcsi`, `/heart_control`, `/breath_control` |
| `persistence_bridge` | Lets the web page start a capture | `/persistence_bridge/response`, `/persistence_bridge/feedback` | `/persistence_bridge/request` |

These six run in the default launch (`ros2 launch csi aims_launch.py`). Other executables exist in `aims_ws/src/csi` and are not started by default: `breath_estimator_cardiofi` (`/breath_estimate_cardiofi`, `/heart_estimate_cardiofi`), `heart_control`, `breath_control`, `mock_breathing`, `mock_heart_beat`, `breath_plotter`, `csi_heatmap_plotter`, `mmw_talker`, `octave_cardiofi`.

The vision nodes run in the `vision` service (profile `vision`, `ros2 launch vision_bringup vision.launch.py`):

| Executable | Role | Publishes | Subscribes |
|---|---|---|---|
| `pose_estimation` | Reads the camera or a video file, runs YOLOv8n-pose | `/estimation_points` (`vision_interfaces/PoseKeypoints`), `/vision/image_raw` | |
| `there_is_person` | Decides whether a person is in the frame | `/there_is_person` (`Bool`, latched) | `/estimation_points` |
| `moving` | Kalman-filtered keypoint speed: is the person moving | `/is_moving` (`Bool`, latched) | `/estimation_points`, `/there_is_person` |
| `visualization` | Draws the keypoints and encodes a JPEG | `/vision_image` (`sensor_msgs/CompressedImage`) | `/estimation_points`, `/vision/image_raw` |

The dashboard subscribes to `/vision_image`, `/there_is_person` and `/is_moving`. It detects the camera by the node name `/pose_estimation`. The `apnea_ai` node (Keras, TensorFlow) is no longer part of the `csi` package; the code is in [deprecated/apnea_ai/](deprecated/apnea_ai/README.md).

Message definitions are in `aims_ws/src/custom_interfaces` (`BreathEstimate` has `breath_rate`, `precision`, `apnea_detected`).

## Capture file format

In the dashboard, open the persistence panel, fill the form (capture name, **Subject ID**, NIC models, subject position, antenna distance, number of frames) and start. Files are written to `./captures/` in the repository folder (a bind mount of `/app/captures`).

The **Subject ID** is free text, required, and limited to letters, digits, `_` and `-`. It is the only identification of the subject; there is no patient database or login.

File name:

```
{capture_name}-{subject_id}-{rx_nic_model}-{tx_nic_model}-{subject_position}-{antenna_distance_cm}cm-{DD_MM_YYYY-HH-MM}.txt
```

- Every component is sanitized: characters outside `A-Za-z0-9_-` become `_`, so there is no `:` and the names are valid on Windows.
- Two extra files are written when the optional `heart_control` / `breath_control` publishers produced data: the same name with the prefix `Heartbeats-` or `Breaths-`.
- Each line of the CSI file is the Python `str()` of a dictionary built from one `/pktcsi` message (`aims_ws/src/csi/csi/libs/CsiMsgToDict.py`). Heartbeat and breath files hold `{'timestamp', 'pktid'}` dictionaries.
- `utils/AIMSAPI-py` holds helper functions for handling AIMS data; see its [README](utils/AIMSAPI-py/README.md).

Subject positions are the ASCII values of the position selector in the dashboard (for example `sitting_front`, `lying_45deg_feet_to_window`).

## Supported platforms

| Mode | Linux | Windows | macOS |
|---|---|---|---|
| Mock (`CSI_SOURCE=mock`) with Docker | yes | yes (Docker Desktop) | yes (Docker Desktop) |
| Hardware (`CSI_SOURCE=picoscenes`) | yes: Ubuntu amd64 host with IWL5300 | no | no |
| Host networking override | yes | no | no |
| Vision, CPU, with a video file | yes | yes (Docker Desktop) | yes (Docker Desktop) |
| Vision, CPU, with a webcam | yes (`/dev/video0`) | no (no webcam in containers) | no |
| Vision on an NVIDIA GPU | yes (NVIDIA Container Toolkit) | yes (Docker Desktop, WSL2 GPU support) | no |

Hardware mode needs PicoScenes on the host, which depends on the Linux kernel driver and NIC firmware, so it cannot run in Docker.

## Distributed setups (multiple machines)

Run nodes on different machines with the same `ROS_DOMAIN_ID` and use host networking so DDS discovery works across the LAN (Linux only):

```bash
docker compose -f docker-compose.yml -f docker-compose.hostnet.yml up -d
```

To run only the camera on one of the machines, see [Vision](#vision-camera-optional).

## Troubleshooting

| Symptom | What to check |
|---|---|
| Dashboard opens but charts are empty | Wait about 35 s after start for the first `/breath_estimate`. Check `docker compose logs ros2-nodes`. |
| `docker compose` complains about `env_file` / `required` | Compose is older than 2.24; update Docker Compose. |
| `exec /entrypoint.sh: no such file or directory` on Windows | `entrypoint.sh` got CRLF line endings. `.gitattributes` forces LF; re-checkout the file (`git rm --cached` and `git checkout`) or re-clone. |
| Port already in use | Change `WEB_PORT`, `ROSBRIDGE_PORT` or `CSI_UDP_PORT`. |
| Dashboard cannot connect to rosbridge from another machine | Port `ROSBRIDGE_PORT` (default 9090) must be reachable at the same hostname you use for the page. |
| `csi_publisher` logs "No PicoScenes UDP frames ... yet" (hardware mode) | Is `picoscenes_rx.sh` running? Is `CSI_SOURCE=picoscenes` set? Does the NIC name match (`ip link`)? Is the transmitter running? |
| `vision` container exits or `/dev/video0` error | No camera at `/dev/video0` (always the case on Docker Desktop). Use a video file: `VISION_VIDEO_DEVICE=/dev/null VISION_CAMERA=/app/captures/<file>.mp4`, see [Vision](#vision-camera-optional). |
| Git Bash: `/dev/null` becomes `nul` and the vision container does not start | Git Bash rewrites Unix paths. Prefix the command with `MSYS_NO_PATHCONV=1`. |
| Camera works but the dashboard says no person | The presence rule was tuned for a close webcam. A person far away or narrow in the frame is not detected; lower `min_std` (default 0.045) in `aims_ws/src/vision/vision_bringup/config/vision.yaml` and rebuild the vision image. |
| Movement pill says "Waiting for camera" | No `/is_moving` yet: the vision service is not running, or `ROS_DOMAIN_ID` differs. Check `docker compose logs vision`. |
| Position Map tab keeps spinning | It shows `/heatmapmmw` from the mmWave radar node `mmw_talker` (TI IWR1642 over serial), which is not in the default launch. Without the radar there is no data. |
| GPU not used (`device` is `cpu`, or CUDA errors) | Use the GPU override (`make up-vision-gpu`) and check the NVIDIA Container Toolkit (Linux) or WSL2 GPU support (Windows). `docker compose logs vision` shows the device the model loaded on. |
| `picoscenes_rx.sh`: PicoScenes not found | Run `scripts/host/install_picoscenes.sh` and reboot. |
| Installer says no IWL5300 found | It refuses without the card. Pass `--skip-hardware-check` to install anyway. |

**Hardware mode with bridge networking on Linux has not been tested yet.** The expected path is PicoScenes forwarding to `127.0.0.1:1025`, which reaches the container through the published UDP port. If frames do not arrive, use the host networking override (`docker-compose.hostnet.yml`, see above) or forward to the host's LAN IP (`scripts/host/picoscenes_rx.sh --forward <host-ip>:1025`).

## Project layout

```
.
├── aims_ws/src/            # ROS2 workspace
│   ├── csi/                # CSI nodes, launch files, signal processing libs
│   ├── custom_interfaces/  # .msg / .srv / .action definitions
│   └── vision/             # camera pipeline (YOLOv8n-pose): pose_estimation, there_is_person,
│                           #   moving, visualization, vision_interfaces, vision_bringup
├── web/                    # Express.js server and dashboard (Tailwind CSS, roslib.js)
├── docker/                 # Dockerfiles (ros2, vision, web)
├── docker-compose.yml      # default stack (bridge network); vision behind profile "vision"
├── docker-compose.gpu.yml  # optional override: vision on an NVIDIA GPU (CUDA image)
├── docker-compose.hostnet.yml  # optional host-networking override
├── requirements/           # Python dependencies: *.in sources, hashed *.lock, constraints.txt
├── scripts/host/           # PicoScenes install / RX / TX scripts (run on the host)
├── scripts/vision/         # export_tensorrt.sh (optional TensorRT engine, run in the :cuda image)
├── scripts/legacy/         # old bare-metal scripts, kept for reference
├── picoscenes/             # PicoScenes host setup guide
├── models/                 # AI model files (mounted at /app/models); vision/yolov8n-pose.pt is shipped
├── deprecated/apnea_ai/    # retired Keras apnea node, with restore steps
├── captures/               # capture output (bind mount)
├── resources/              # patched PicoScenes parser, test assets
├── utils/AIMSAPI-py/       # Python helpers to read capture files
├── docs/                   # changelog and ADRs
├── Makefile                # thin wrapper around docker compose
└── CITATION.cff
```

## Local development without Docker

Requirements: [ROS2 Humble](https://docs.ros.org/en/humble/Installation.html), Node.js 20, Python 3.10+.

```bash
# ROS2 workspace
source /opt/ros/humble/setup.bash
cd aims_ws
colcon build --symlink-install
source install/local_setup.bash

# Web server (in another terminal)
cd web
npm install
npm run build:css
npm run dev
```

See [web/README.md](web/README.md) for the web server. The core Python dependencies are pinned in `requirements/core.lock`; the vision packages need `requirements/vision-cpu.lock` (or `vision-cuda.lock`), installed with `pip install --require-hashes -r`.

## Contributing and history

- Changes: [docs/CHANGELOG.md](docs/CHANGELOG.md). v0.3.0 contains breaking renames; read it if you have data from earlier versions.
- Decisions: [docs/adrs/](docs/adrs/README.md).
- Repository: https://github.com/LABORA-INF-UFG/AIMS-System
