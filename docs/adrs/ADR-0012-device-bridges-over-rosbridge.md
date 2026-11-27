# ADR-0012: External Ground-Truth Devices Publish Through Rosbridge

- **Status**: Accepted
- **Date**: 2026-11-27
- **Deciders**: Luiz Fernando de Freitas Oliveira
- **Technical context**: Polar H10 chest strap and other ground-truth devices (`devices/`)

---

## Context

- The Polar H10 talks BLE and must sit near the subject, which is often not the machine that runs the AIMS stack.
- On the lab machine the Intel BE200 Bluetooth fails to pair with the H10 (`AuthenticationTimeout`). On Linux the strap needs BLE pairing, and a container needs `/run/dbus` and `--security-opt apparmor=unconfined`. Docker Desktop for Windows cannot reach BLE from Linux containers.
- A ROS 2 node would tie the device to a ROS install on the machine that holds the radio.

## Decision

- External ground-truth devices publish through rosbridge (WebSocket) with a small standalone program, not a ROS node, so they run on any OS and machine near the subject. The first one is `devices/h10_bridge/` (bleak, bleakheart, roslibpy); see its [README](../../devices/h10_bridge/README.md).
- It publishes `aims_msgs/msg/H10Ecg`, `H10Acc` and `H10Hr` on `/h10/ecg`, `/h10/acc` and `/h10/hr`, and one `ControlEvent` (`source: h10`) per RR interval on `/heart_control`.
- The raw topics are declared in `capture_sources.yaml` as `h10_ecg`, `h10_acc` and `h10_hr`. Every row carries `host_ns` (capture node, same clock as CSI); ECG and ACC rows also carry `sensor_ns` (strap) and `bridge_ns` (bridge machine), and HR rows only `bridge_ns`.

## Alternatives Considered

| Alternative | Why it was rejected |
|---|---|
| ROS 2 node in `csi` | Needs ROS and BLE on the same machine; BLE does not work from the lab machine's container or Bluetooth chip |
| BLE gateway inside the Docker stack | Needs D-Bus, AppArmor and host Bluetooth; no Windows support |

## Consequences

### Positive
- Runs on a notebook (today, over Tailscale) or on the Linux host later, with no ROS install.
- Adding another device is a program plus a YAML entry.

### Negative / Trade-offs
- Not listed in `ros2 node list`.
- Configuration by CLI/env, not ROS parameters.
- Depends on rosbridge being reachable (it has no authentication; keep the network trusted).
- Network latency is part of `host_ns`; `sensor_ns` and `bridge_ns` allow correcting it. The strap clock offset varies per session.

## Related Links
- [h10_bridge README](../../devices/h10_bridge/README.md)
- [ground-truth-topics.md](../ground-truth-topics.md)
- [ADR-0004](./ADR-0004-rosbridge-as-web-ros2-integration-layer.md) — Rosbridge as the integration layer
- [ADR-0011](./ADR-0011-modular-capture-and-control-events.md) — Modular capture sources
