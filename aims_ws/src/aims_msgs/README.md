# aims_msgs

Messages shared with external devices (ground-truth sources). `custom_interfaces` stays internal to AIMS.

| Message | Fields | Use |
|---|---|---|
| `ControlEvent` | `uint64 timestamp` (ns since the Unix epoch), `string source` (`ui_button`, `h10`, `nk`, `mock`, ...) | One breath or heartbeat on `/breath_control` / `/heart_control`. Dashboard only, not captured. |
| `WavePeak` | `header`, `wave` (`ecg`, `resp`, `pleth`), `kind` (`max`, `min`) | Peaks from the Nihon Kohden analyzer. |

**Contract rule:** `ControlEvent.msg` and `WavePeak.msg` are identical copies of the ones in [`LABORA-INF-UFG/NIHON-KOHDEN-SVM-7500-ANALYZER`](https://github.com/LABORA-INF-UFG/NIHON-KOHDEN-SVM-7500-ANALYZER) (`ros2_ws/src/aims_msgs`). Keep both copies identical; any change is a contract break and must be made in both repositories.

See [ADR-0011](../../../docs/adrs/ADR-0011-modular-capture-and-control-events.md) and [docs/ground-truth-topics.md](../../../docs/ground-truth-topics.md).
