# ADR-0011: Modular Capture Sources and Shared Control-Event Messages

- **Status**: Accepted
- **Date**: 2026-11-27
- **Deciders**: Luiz Fernando de Freitas Oliveira
- **Technical context**: `persistence_action`, ground-truth topics and the capture file format

---

## Context

- `persistence_action` hard-coded what it recorded: CSI frames plus `Heartbeats-` / `Breaths-` events, written as one `str(dict)` per frame in `.txt` files (about 14.6 KB per frame), only after the capture ended. A crash lost everything, and the files were owned by root.
- Adding a ground-truth device (Polar H10, Nihon Kohden analyzer) meant editing that node.
- `/breath_control` and `/heart_control` used `custom_interfaces` messages with a bare `timestamp`, and a device in another repository could not depend on an internal package. The dashboard could not tell sources apart.

## Decision

- New package `aims_ws/src/aims_msgs` for messages shared with external devices: `ControlEvent` (`uint64 timestamp`, `string source`) and `WavePeak`, kept identical to the copy in the Nihon Kohden analyzer repository. `custom_interfaces` stays internal. `BreathControl.msg` and `HeartControl.msg` are removed.
- `/breath_control` and `/heart_control` carry `ControlEvent` with a free-text `source`, are for the UI only and are not captured. The dashboard shows one chip per source.
- `persistence_action` is rewritten with ROS-free writers (`csi/capture_writers.py`). Sources are declared in `aims_ws/src/csi/config/capture_sources.yaml`; each source publishes raw data on its own topics, and adding one is one YAML entry.
- The action takes `duration_s` instead of `num_frames`. A capture is a folder: `meta.json`, `csi/part-NNNN.npz` (about 10 s each) and one CSV per other source, with `host_ns` (receipt time, one clock) first. Files are written during the capture, and a failing source is disabled with its error recorded in `meta.json`.
- `load_capture(path)` in `utils/AIMSAPI-py/capture_loader.py` reads the folder.

## Alternatives Considered

| Alternative | Why it was rejected |
|---|---|
| Keep `.txt` and add sources in code | Large files, nothing written until the end, every source needs a code change |
| Keep the messages in `custom_interfaces` | External repositories would have to copy or depend on an internal package |
| Capture `/breath_control` and `/heart_control` | Mixes UI events with raw data; each source's own topics are the ground truth. The UI button publishes `/ui/breath_annotation` for that |
| Converter for old `.txt` captures | Not needed today; not written |

## Consequences

### Positive
- About 1.4 KB per frame instead of 14.6 KB (mock run, 22 s: 2201 frames, 3.1 MB).
- A crash loses at most the current CSI part; files belong to the owner of `captures/`.
- A new source touches the YAML only and only adds files.

### Negative / Trade-offs
- Breaking: external publishers of `BreathControl` / `HeartControl` must switch to `aims_msgs/ControlEvent`, and old `.txt` captures have no converter or loader.
- Both copies of `aims_msgs` must stay identical by hand; any change is a contract break.

## Related Links
- [ground-truth-topics.md](../ground-truth-topics.md)
- [aims_msgs README](../../aims_ws/src/aims_msgs/README.md)
- [ADR-0010](./ADR-0010-deprecate-apnea-ai-and-tensorflow.md) — Deprecate apnea_ai
