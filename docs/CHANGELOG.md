# Changelog

All notable changes to the AIMS-System project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

### Planned
- Phase 3: ROS2 node refactoring (type hints, structured logging, separation of concerns)
- Phase 4: CI/CD pipeline

---

## [0.3.0] — 2026-10-12

Public reference release: English everywhere, no database, plug-and-play in mock mode.

### Breaking changes

Captures, scripts or clients written for v0.2.0 or earlier must be migrated. Old Portuguese names (left side) are listed here for migration purposes only.

| Kind | Old | New |
|---|---|---|
| ROS field | `nome_coleta` | `capture_name` |
| ROS field | `nome_paciente` | `subject_id` |
| ROS field | `modelo_nic_rx` / `modelo_nic_tx` | `rx_nic_model` / `tx_nic_model` |
| ROS field | `posicao_paciente` | `subject_position` |
| ROS field | `distancia_antenas_centimetros` | `antenna_distance_cm` |
| ROS field | `distancia_antenas_metros` | `antenna_distance_m` |
| ROS message | `EstimativeBreath` | `BreathEstimate` |
| ROS field | `breath_estimative` | `breath_rate` |
| ROS field | `apneia_detected` | `apnea_detected` |
| Topic | `/estimativebreath` (and `/estimativebreath*` variants) | `/breath_estimate` (`/breath_estimate*`) |
| Topic | `/estimativeheart_cardiofi` | `/heart_estimate_cardiofi` |
| Topic | `/visao_image` | `/vision_image` |
| Folder | `Capturas/` | `captures/` (bind mount `./captures:/app/captures`) |
| Position values | `Sentado_frente`, `Deitado_encosto_45_graus_pés_pra_janela`, ... | ASCII values such as `sitting_front`, `lying_45deg_feet_to_window` (see the position selector in `web/views/monitoring.html`) |
| File | `resource/modelo_request_persistencia_csi.yaml` | `resource/persistence_request_example.yaml` |
| Node files | `breath_estimative_publisher.py`, `mocked_breathing_apneia_publisher.py` | `breath_estimate_publisher.py`, `mocked_breathing_apnea_publisher.py` |
| Capture file names | `{nome_coleta}-{nome_paciente}-{modelo_nic_rx}-{modelo_nic_tx}-{posicao_paciente}-{distancia_antenas_centimetros}cm-{data}.txt`, with `:` in the time and no sanitization | `{capture_name}-{subject_id}-{rx_nic_model}-{tx_nic_model}-{subject_position}-{antenna_distance_cm}cm-{DD_MM_YYYY-HH-MM}.txt` |
| Scripts | `picoscenes_routine_rx.bash`, `picoscenes_routine_tx.bash`, `scripts/1_*`, `scripts/2_*` | `scripts/host/picoscenes_rx.sh`, `scripts/host/picoscenes_tx.sh`, `scripts/host/install_picoscenes.sh` |
| Networking | `network_mode: host` for `ros2-nodes` and `rosbridge` | bridge network with published ports; host networking only via `docker-compose.hostnet.yml` |

Old capture files are not renamed or converted; only the file names and the folder differ from the new ones.

### Added
- `CSI_SOURCE=mock|picoscenes` (default `mock`), read as the `csi_source` launch argument by `aims_launch.py` and `aims_core_launch.py`.
- `CSI_UDP_HOST` / `CSI_UDP_PORT` are now honored by `csi_publisher`.
- `docker-compose.hostnet.yml`: optional host-networking override for distributed multi-machine ROS2 setups.
- `Makefile` wrapper with `up`, `up-hardware`, `down`, `logs`, `build` and `host-setup`.
- Host scripts in `scripts/host/`: `install_picoscenes.sh` (idempotent, no automatic reboot, `--skip-hardware-check` to install without an IWL5300), `picoscenes_rx.sh`, `picoscenes_tx.sh`, `aims-picoscenes-rx.service`.
- The ros2 image builds the patched PicoscenesToolbox parser from a pinned upstream commit.
- `GET /config` endpoint on the web server (rosbridge port); the frontend connects to the hostname that served the page.
- Free-text Subject ID field (`A-Za-z0-9_-`) in the persistence form.
- Rosbridge healthcheck; `.gitattributes` forcing LF endings for shell scripts and Dockerfiles.
- `CITATION.cff` (placeholders to be completed), ADR-0006, ADR-0007 and ADR-0008.

### Changed
- All code, identifiers, UI strings, logs and documentation translated to English.
- `.env` is optional (Docker Compose >= 2.24); every variable has a built-in default.
- Captures go to the host folder `./captures` through a bind mount instead of a named volume.
- Capture file names no longer contain `:` and their components are sanitized (any character outside `A-Za-z0-9_-` becomes `_`), so files are valid on Windows bind mounts.
- ADR files renamed to English slugs; ADR-0003 marked as superseded.
- Legacy Foxy install script and `build.bash` moved to `scripts/legacy/`.
- OpenCV switched to the headless build in the ros2 image (fixes `libGL.so.1` import error).

### Removed
- MongoDB (`mongo` service, `mongo_data` volume, `MONGO_URI`, `mongoose`) and the whole patient management feature (patient list, registration, patient selection).
- Dead page `web/views/backup_monitoring.html`.
- Root scripts `picoscenes_routine_rx.bash` / `picoscenes_routine_tx.bash` and `scripts/1_*`, `scripts/2_*`.
- Automatic `shutil.which('PicoScenes')` detection in the launch files (it always selected the mock inside the container).

### Fixed
- Hardcoded `127.0.0.1:1025` in `csi_publisher` ignoring `CSI_UDP_HOST` / `CSI_UDP_PORT`.
- Hardcoded `ws://localhost:9090` in the frontend, which broke access from other machines.
- CRLF line endings in `docker/ros2/entrypoint.sh` on Windows checkouts.

---

## [0.2.0] — 2026-06-17

### Phase 2 — Migration from Bootstrap to TailwindCSS v4

#### Added
- `web/public/assets/css/input.css`: TailwindCSS v4 entry point with custom design tokens through the `@theme` directive (primary colors, fonts and utilities of the AIMS visual identity).
- `web/package.json`: `build:css` script to compile the CSS with `@tailwindcss/cli`.

#### Changed
- **`docker/web/Dockerfile`**: base image updated from `node:18-alpine` to `node:20-alpine` (requirement of Tailwind v4's Rust-based compiler). Added a `builder` stage that compiles the static `tailwind.css`, copied to the `runtime` stage.
- **`web/app.js`**: removed the static mappings of the `node_modules/bootstrap/` and `node_modules/jquery/` folders, no longer needed.
- **`web/public/index.html`**: refactored to TailwindCSS v4. New card grid layout with animated hover, replacing the Bootstrap-based structure.
- **`web/views/registration.html`**: refactored to TailwindCSS v4. Form with custom focus inputs and smooth transitions.
- **`web/views/patients.html`**: refactored to TailwindCSS v4. The JavaScript that dynamically builds search results now injects Tailwind utility classes into the created elements.
- **`web/views/monitoring.html`**: refactored to TailwindCSS v4. The chart tab navigation and the sliding persistence panel (drawer) were reimplemented with Vanilla JavaScript + native Tailwind CSS transitions, removing the dependency on `bootstrap.min.js` and jQuery.

#### Removed
- `bootstrap` and `jquery` dependencies from `web/package.json`.
- Legacy CSS files: `main.css`, `style.css` and all `variables*.css` files.
- Unused vendor directories: `assets/vendor/aos`, `assets/vendor/bootstrap`, `assets/vendor/boxicons`, `assets/vendor/glightbox`, `assets/vendor/isotope-layout`, `assets/vendor/php-email-form`, `assets/vendor/purecounter`, `assets/vendor/remixicon`, `assets/vendor/swiper`.

---

## [0.1.0] — 2026-06-17

### Phase 1 — Containerization and Migration to ROS2 Humble

#### Added
- **`docker-compose.yml`**: multi-service orchestration with 4 services (`ros2-nodes`, `rosbridge`, `web`, `mongo`), replacing the manual `docker run` process.
- **`docker/ros2/Dockerfile`**: multi-stage Dockerfile for the ROS2 nodes (`builder` + `runtime`), based on the official `ros:humble-ros-base` image. Includes installation of `PicoscenesToolbox` from the official repository.
- **`docker/ros2/entrypoint.sh`**: entrypoint script that sources the ROS2 environment and the compiled workspace before running the CMD.
- **`docker/web/Dockerfile`**: multi-stage Dockerfile for the web server (`builder` + `runtime`), based on `node:20-alpine`.
- **`.env`** and **`.env.example`**: centralization of all stack environment variables (ports, URIs, ROS2 settings).
- **`web/.env.example`**: environment variable template for local runs without Docker.
- **`aims_ws/src/csi/launch/aims_mock_launch.py`**: dedicated launch file for tests with mocked data, without depending on PicoScenes hardware.
- **`picoscenes/README.md`**: documentation of PicoScenes installation and use on the Linux host.
- **`models/README.md`**: placeholder documenting the ML models directory mounted as an external volume.

#### Changed
- **`aims_ws/src/csi/launch/aims_launch.py`**: removed the `ExecuteProcess` entries that started PicoScenes, `npm start` and `xdg-open`. The launch is now responsible only for the ROS2 nodes.
- **`aims_ws/src/csi/launch/aims_core_launch.py`**: removed the built-in rosbridge startup. Fixed the executable `talker` → `csi_publisher`.
- **`web/app.js`**: replaced `process.argv[2]` with the `MONGO_URI` environment variable. Added `async/await` logic with automatic retry and graceful shutdown through `SIGTERM`/`SIGINT`.
- **`web/package.json`**: added a Docker-compatible `start` script.
- **`aims_ws/src/requirements.txt`**: removed the `oct2py` dependency (experimental). Added comments.
- **`aims_ws/src/csi/package.xml`**: removed the `<depend>octave</depend>` dependency.
- **`.gitignore`**: added entries for `.env`, `web/node_modules/` and `*.pyc`.
- **`.dockerignore`**: expanded with complete exclusions to reduce the build context.
- **`picoscenes_routine_rx.bash`**: parameterized through environment variables, removing hardcoded IP/port/interface values.
- **`README.md`**: fully rewritten with an architecture diagram, Docker-first instructions and an environment variable table.

#### Removed
- `docker/Dockerfile`: replaced by `docker/ros2/Dockerfile` (multi-stage).
- `docker/entrypoint.sh`: replaced by `docker/ros2/entrypoint.sh`.
- `docker/README.md`: content migrated to the main README.
- `rclnodejs` dependency from `web/package.json`: it was not used in the backend; ROS2 communication happens on the client through `roslib.js` + WebSocket to rosbridge.

#### Fixed
- **Docker build of the `web` service**: native addon compilation error (`int64-napi`) caused by the `rclnodejs` dependency, incompatible with Alpine without build tools.
- **Image export conflict**: the `ros2-nodes` and `rosbridge` services share the same Dockerfile, which caused a race condition in parallel image export (`image already exists`). Fixed by explicitly adding `image: aims-system-ros2:latest` to both services.
