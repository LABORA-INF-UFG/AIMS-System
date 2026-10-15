# Ground-truth topics

**Status: the first part describes the current code; everything from "Proposal" on is a proposal, not implemented.**

Ground truth is a reference measurement (heartbeats, breaths, vital signs) recorded next to the CSI so the estimates can be checked. Sources publish `*_control` topics; the dashboard and `persistence_action` consume them.

## Current event topics

| Topic | Type (`custom_interfaces/msg`) | Content | Publisher today |
|---|---|---|---|
| `/heart_control` | `HeartControl` | `uint64 timestamp`: one message per heartbeat, wall-clock time in ns | `mock_heart_beat` only (1 per second, `time.time_ns()`) |
| `/breath_control` | `BreathControl` | `uint64 timestamp`: one message per breath, ns | Dashboard **Breath** button (rosbridge, `Date.now() * 1000000`) |

The old nodes `breath_control` (mouse clicks) and `heart_control` (second camera) are in `deprecated/`, see `deprecated/breath_control/README.md` and `deprecated/heart_control/README.md`. The message files were kept so new sources can reuse them.

### How they are consumed

- **Dashboard** (`web/public/scripts/rosControllerMonitoring.js`): subscribes to both topics through rosbridge and keeps the timestamps in a buffer. The window is 30 s (`window_size` / `window_time`): events older than 30 s are dropped and the rate shown is `events in window * 60 / 30`. For breaths, 20 s without an event shows "Apnea". The ground-truth rows are visible only with Debug on. With no heart publisher the heart row stays empty.
- **`persistence_action`** (`aims_ws/src/csi/csi/persistence_action.py`): subscribes to `heart_control` and `breath_control` (queue depth 10). During a capture each event is stored as `{'timestamp': msg.timestamp, 'pktid': <pktid of the latest /pktcsi frame>}`. After the CSI file is written it writes, only if the buffer is not empty, the same file name with the prefix `Heartbeats-` or `Breaths-` in `captures/`, one `str(dict)` per line. Note: an event that arrives before the first CSI frame of a capture would fail on `frame_buffer[-1]` (read from code, not tested).

## Contract

Keep the two event topics as they are: one message per event, `timestamp` in ns since the Unix epoch (same clock as the machine running the nodes; keep it NTP-synced). Anything downstream (dashboard, capture files, offline analysis) already understands them.

## Proposal: planned devices

### Polar chest strap

- BLE Heart Rate Service (0x180D), Heart Rate Measurement characteristic (0x2A37): heart rate in bpm and, when the strap sends them, RR intervals (to verify against the strap model).
- A node can turn RR intervals into one `HeartControl` per beat (timestamp = receive time, optionally minus a fixed latency) so everything downstream keeps working. It can also publish the numeric bpm on the new topic below.
- BLE from a container needs host networking plus access to the host's D-Bus / BlueZ (for example mounting `/var/run/dbus`) or privileged mode; the alternative is running the node on the host. To verify. On Docker Desktop for Windows, BLE is not reachable from Linux containers, so run the node on the host.

### ICU vital-signs monitor

- Numeric heart rate, respiratory rate and SpO2, exported over a serial or network protocol that depends on the model (for example HL7 or a vendor protocol).
- TODO: the exact monitor model is unknown; find out which export it supports before designing the node.
- Numeric values are about 1 Hz, so they cannot replace per-beat events; they are useful to compare with the estimated rates.

### New message for numeric vitals

```
# custom_interfaces/msg/VitalSignsReference.msg
std_msgs/Header header     # stamp = measurement time
string source              # e.g. "polar_h10", "icu_monitor"
float32 heart_rate         # bpm, NaN when unknown
float32 respiratory_rate   # breaths/min, NaN when unknown
float32 spo2               # percent, NaN when unknown
```

Topic: `/vitals_reference`.

What must change to support it:

1. `aims_ws/src/custom_interfaces`: add `msg/VitalSignsReference.msg`, list it in `msg_files` in `CMakeLists.txt`, and add the `std_msgs` dependency (`find_package(std_msgs REQUIRED)`, `DEPENDENCIES std_msgs` in `rosidl_generate_interfaces`, `<depend>std_msgs</depend>` in `package.xml`). The file does not exist yet.
2. `persistence_action.py`: add a subscription and a buffer (cleared in `clear_buffers`), and write a `Vitals-` file with the same naming scheme through `capture_file_name(req, date, 'Vitals-')`.
3. Dashboard: add a `ROSLIB.Topic` listener for `/vitals_reference` in `rosControllerMonitoring.js` and show the values in the ground-truth rows (Debug on), skipping NaN.
4. Docker: the core container needs the device. `docker-compose.yml` has no serial mapping for the mmWave radar today (`mmw_talker` is not run in a container); the only device mapping is the vision camera, `devices: "${VISION_VIDEO_DEVICE:-/dev/video0}:/dev/video0"`. Follow that pattern with a variable, for example `"${GT_SERIAL_DEVICE:-/dev/null}:/dev/ttyGT"`, or use host networking (`docker-compose.hostnet.yml`) for a network export or BLE. Docker Desktop on Windows cannot pass USB serial devices without extra tools.
5. Add the node's entry point to `console_scripts` in `aims_ws/src/csi/setup.py` and any new dependency (e.g. `bleak` for BLE; `pyserial` is already there) to `requirements/core.in`, then recompile `core.lock`.

## Checklist: adding a new ground-truth node

1. Pick the topic: a discrete event per beat or breath uses `/heart_control` or `/breath_control` (`timestamp` in ns); numeric values use `/vitals_reference`.
2. Write the node in `aims_ws/src/csi/csi/` (publish with `time.time_ns()` at the moment of the event) and register it in `setup.py`.
3. Add its dependencies to `requirements/core.in` and recompile the lock, or run it on the host.
4. Map the device (USB, serial, BLE/D-Bus or network) into the container, or document that it runs on the host.
5. Check the dashboard: the ground-truth row appears with Debug on and the 30 s rate is plausible.
6. Run a short capture and check that the `Heartbeats-` / `Breaths-` (or `Vitals-`) file appears in `captures/`.
7. Document the source and its clock offset or latency; update the README and CHANGELOG.
