# aims_msgs

Messages shared with external devices (ground-truth sources). `custom_interfaces` stays internal to AIMS.

| Message | Fields | Use |
|---|---|---|
| `ControlEvent` | `uint64 timestamp` (ns since the Unix epoch), `string source` (`ui_button`, `h10`, `nk`, `mock`, ...) | One breath or heartbeat on `/breath_control` / `/heart_control`. Dashboard only, not captured. |
| `WavePeak` | `header`, `wave` (`ecg`, `resp`, `pleth`), `kind` (`max`, `min`) | Peaks from the Nihon Kohden analyzer. |
| `H10Ecg` | `sensor_ns`, `bridge_ns`, `int32[] samples_uv` | Polar H10 ECG packet on `/h10/ecg` (130 Hz). |
| `H10Acc` | `sensor_ns`, `bridge_ns`, `sample_rate_hz`, `range_g`, `int16[] x_mg, y_mg, z_mg` | Polar H10 accelerometer packet on `/h10/acc`. |
| `H10Hr` | `bridge_ns`, `bpm`, `uint16[] rr_ms` | Polar H10 heart rate notification on `/h10/hr`. |

The `H10*` messages are published by [`devices/h10_bridge`](../../../devices/h10_bridge/README.md) and live only in this repository; the contract rule below covers `ControlEvent` and `WavePeak`.

**Contract rule:** `ControlEvent.msg` and `WavePeak.msg` are identical copies of the ones in [`LABORA-INF-UFG/NIHON-KOHDEN-SVM-7500-ANALYZER`](https://github.com/LABORA-INF-UFG/NIHON-KOHDEN-SVM-7500-ANALYZER) (`ros2_ws/src/aims_msgs`). Keep both copies identical; any change is a contract break and must be made in both repositories.

See [ADR-0011](../../../docs/adrs/ADR-0011-modular-capture-and-control-events.md) and [docs/ground-truth-topics.md](../../../docs/ground-truth-topics.md).
