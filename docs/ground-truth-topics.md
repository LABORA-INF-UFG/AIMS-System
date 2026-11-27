# Ground-truth topics

Ground truth is a reference measurement (heartbeats, breaths, vital signs) recorded next to the CSI so the estimates can be checked. See [ADR-0011](./adrs/ADR-0011-modular-capture-and-control-events.md) and [ADR-0012](./adrs/ADR-0012-device-bridges-over-rosbridge.md).

**Status: the Contract and Dashboard sections describe the current code. Polar H10 is implemented through a bridge; Nihon Kohden is planned.**

## Contract

Each source does two separate things:

1. **For the dashboard (UI only):** publish one `aims_msgs/msg/ControlEvent` per breath on `/breath_control` or per heartbeat on `/heart_control`. `timestamp` is ns since the Unix epoch (NTP-synced machine clock), `source` is a free-text id (`ui_button`, `h10`, `nk`, `mock`, ...). These topics are **not captured**.
2. **For the capture:** publish its raw data on its own topics and add an entry to `aims_ws/src/csi/config/capture_sources.yaml` (keys `topic`, `type`, `fields`, `explode`, `qos: latched`, `writer: csv|csi_npz`). Each source becomes `<source>.csv` in the capture folder, with `host_ns` (receipt time, one clock for all sources) first. Adding a source only adds files.

`ControlEvent` lives in `aims_ws/src/aims_msgs`, shared with external repositories; see its [README](../aims_ws/src/aims_msgs/README.md). Any change there is a contract break.

| Topic | Type | Publisher today |
|---|---|---|
| `/heart_control` | `aims_msgs/msg/ControlEvent` | `mock_heart_beat` (1 per second, `source: mock`); `h10_bridge` (1 per RR interval, `source: h10`) |
| `/breath_control` | `aims_msgs/msg/ControlEvent` | Dashboard **Log exhale** button (Debug only) |
| `/ui/breath_annotation` | `aims_msgs/msg/ControlEvent` | Same button; raw copy, captured (`ui_breath_annotation` in `capture_sources.yaml`) |

The old nodes `breath_control` (mouse clicks) and `heart_control` (second camera) are in `deprecated/`, see `deprecated/breath_control/README.md` and `deprecated/heart_control/README.md`.

## Dashboard

`web/public/scripts/rosControllerMonitoring.js` (markup in `web/views/monitoring.html`), visible with Debug on:

- One chip per active source, with the icon from `CONTROL_SOURCES`; unknown sources get a generic icon (`bi-broadcast`) and their name.
- Rate = 60 / mean interval between that source's event timestamps in the last 30 s.
- The breath chip shows "Apnea" after 20 s without events from that source; a chip hides after 60 s idle.
- The large heart / lungs icon in each card blinks on every event of every source. With two or more sources active it blinks for all of them, so its pace looks faster than the real rate. Read the rate from the chips; each chip also highlights only on its own source's events.

| `source` | Icon | Label |
|---|---|---|
| `ui_button` | `bi-hand-index` | Button |
| `h10` | `bi-heart-pulse` | Polar H10 |
| `nk` | `bi-display` | Nihon Kohden |
| `mock` | `bi-robot` | Mock |

To give a new source its own icon, add a line to `CONTROL_SOURCES`.

## Polar H10 chest strap (implemented)

Standalone program `devices/h10_bridge/h10_bridge.py`, see its [README](../devices/h10_bridge/README.md). It reads the strap over BLE and publishes through rosbridge, so it runs on any machine near the subject (not a ROS node, [ADR-0012](./adrs/ADR-0012-device-bridges-over-rosbridge.md)).

| Topic | Type | Content | Capture source |
|---|---|---|---|
| `/h10/ecg` | `aims_msgs/msg/H10Ecg` | ECG, 130 Hz, uV | `h10_ecg` (one row per sample) |
| `/h10/acc` | `aims_msgs/msg/H10Acc` | Accelerometer, 25/50/100/200 Hz, 2/4/8 g (default 200 Hz, 8 g) | `h10_acc` (one row per sample, x/y/z) |
| `/h10/hr` | `aims_msgs/msg/H10Hr` | bpm and RR intervals (ms) | `h10_hr` (one row per notification, RR as a space-separated string) |
| `/heart_control` | `aims_msgs/msg/ControlEvent` | `source: h10`, one per RR interval (dashboard chip) | not captured |

- Clocks: `sensor_ns` (strap clock, offset varies per session), `bridge_ns` (bridge machine clock) and `host_ns` (capture node receipt, same clock as CSI). `host_ns` includes network latency; the other two allow correcting it. `h10_hr` has no `sensor_ns`.
- ECG and ACC can take about 30 s after start to stream.
- `--replay file.jsonl` replays a recording as a mock; `--dry-run` prints instead of publishing.
- Linux: the strap requires BLE pairing; a container needs `/run/dbus:/run/dbus:ro` and `--security-opt apparmor=unconfined`. The lab machine's Intel BE200 Bluetooth fails to pair with the H10 (`AuthenticationTimeout`), so the bridge runs on another machine (or use a USB Bluetooth dongle). No Docker service for the bridge yet.
- Verified: a replay from a notebook to the lab rosbridge over Tailscale during a 70 s capture produced `h10_ecg`, `h10_acc` and `h10_hr` CSVs (`meta.json` complete, no errors).

## Planned devices (not implemented)

### Nihon Kohden SVM-7500 analyzer

- Lives in its own repository, `LABORA-INF-UFG/NIHON-KOHDEN-SVM-7500-ANALYZER`, and shares `ControlEvent` and `WavePeak` through the identical `aims_msgs` package.
- Expected to publish `ControlEvent` with `source: nk` for the dashboard and raw topics for the capture. How its topics reach the AIMS network is to be defined.
- Numeric vitals are about 1 Hz, so they cannot replace per-beat events; they are useful to compare with the estimated rates.

## Checklist: adding a new ground-truth source

1. Decide the raw topic(s) and message type. Reuse an existing type, or add one to `aims_msgs` if an external repository must publish it (keep the copies identical).
2. Write the producer: a ROS node (in `aims_ws/src/csi/csi/` and registered in `setup.py`, or in the external repository), or a standalone bridge that publishes through rosbridge like `devices/h10_bridge/` (any OS, see ADR-0012). Publish with `time.time_ns()` at the moment of the event.
3. For the dashboard, publish a `ControlEvent` with a unique `source` on `/breath_control` or `/heart_control`. Optionally add the source to `CONTROL_SOURCES` in `rosControllerMonitoring.js`.
4. Add one entry to `aims_ws/src/csi/config/capture_sources.yaml` for the raw topic.
5. Add dependencies to `requirements/core.in` and recompile the lock, or run the node on the host.
6. Map the device (USB, serial, BLE/D-Bus or network) into the container, or document that it runs on the host. `docker-compose.yml` has no serial mapping today; the only device mapping is the vision camera (`VISION_VIDEO_DEVICE`). Follow that pattern with a variable.
7. Check the dashboard: the chip appears with Debug on and the 30 s rate is plausible.
8. Run a short capture and check that `<source>.csv` appears in the capture folder and `meta.json` lists it with rows and no error.
9. Document the source and its clock offset or latency; update the README and CHANGELOG.
