# H10 bridge

Reads a Polar H10 chest strap over BLE (bleak + bleakheart) and publishes to ROS 2 through
rosbridge (roslibpy, WebSocket). It is not a ROS node: it only needs Python 3.

## Topics

| Topic | Type | Content |
|-------|------|---------|
| `/h10/ecg` | `aims_msgs/msg/H10Ecg` | ECG packet, 130 Hz, about 73 samples (uV) |
| `/h10/acc` | `aims_msgs/msg/H10Acc` | accelerometer packet, about 36 samples (mG) |
| `/h10/hr` | `aims_msgs/msg/H10Hr` | heart rate and RR intervals, about 1 per second |
| `/heart_control` | `aims_msgs/msg/ControlEvent` | `source: 'h10'`, one event per RR interval (per beat) |

Beat times keep a running clock so consecutive events are exactly one RR apart. The clock is
re-anchored to the receive time when it drifts more than 2 s from the host clock.

## Run on Windows

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python h10_bridge.py --rosbridge ws://<host>:9090
```

Without `--address` it scans for a device named "Polar H10". ECG/ACC can take about 30 s after
connecting before the first packet. If rosbridge is down it keeps retrying; if BLE drops it
reconnects with backoff. A status line with packet counts is logged every 10 s. Ctrl+C stops it.

Options (each also an env var): `--address` (`H10_ADDRESS`), `--rosbridge` (`H10_ROSBRIDGE`,
default `ws://localhost:9090`), `--acc-rate` (`H10_ACC_RATE`, 25/50/100/200, default 200),
`--acc-range` (`H10_ACC_RANGE`, 2/4/8, default 8), `--replay` (`H10_REPLAY`), `--loop`
(`H10_LOOP`), `--dry-run` (`H10_DRY_RUN`).

## Replay and dry run

```
python h10_bridge.py --replay recording.jsonl --loop --rosbridge ws://<host>:9090
python h10_bridge.py --replay recording.jsonl --dry-run     # prints messages, no rosbridge
```

The recording is JSONL: a header line (with `start_host_ns`), then one
`{"kind", "host_ns", "sensor_ns", "data"}` per packet. Packets are replayed with their original
relative timing and `sensor_ns` is shifted so it looks live. Replay and live share the same
publish path. Keep recordings out of the repository (they are personal ECG data).

## Linux notes

- BlueZ must be running and the strap paired.
- In a container, mount `/run/dbus:/run/dbus:ro` and add `--security-opt apparmor=unconfined`.
- On the lab machine the BE200 Bluetooth fails to pair: use a USB dongle.
- Use `--rosbridge ws://localhost:9090` there.

## Clocks

Three clocks are involved:

- `sensor_ns`: strap time. Its offset to the host clock varies per session and it drifts.
- `bridge_ns`: `time.time_ns()` on the machine running the bridge when it receives the packet.
- `host_ns`: stamped by the capture node when it receives the message.

On Windows, sync the clock before a session: `w32tm /resync`.

## Tests

```
pip install pytest
python -m pytest
```
