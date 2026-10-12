# ADR-0007: PicoScenes Stays on the Host; Explicit CSI Source Selection

- **Status**: Accepted
- **Date**: 2026-10-12
- **Deciders**: Luiz Fernando de Freitas Oliveira
- **Technical context**: How the ROS2 nodes choose between real and simulated CSI

---

## Context

Two problems made the real-hardware path unusable inside Docker:

1. **Implicit mode selection.** The launch files chose real or mock CSI with `shutil.which('PicoScenes')` evaluated *inside the container*. PicoScenes is never installed there, so the mock was always selected, even when a real NIC was feeding frames on the host.
2. **Wrong parser and hardcoded address.** The image installed the upstream `PicoscenesToolbox`, which parses files, while the code imports a patched parser that handles a single UDP packet (`resources/picoscenes.pyx`). The UDP address was also hardcoded to `127.0.0.1:1025` in the publisher.

PicoScenes itself needs the Intel IWL5300 NIC, kernel driver and firmware switching on the host, so it cannot run in a container.

## Decision

- **PicoScenes stays on the Linux host.** Non-interactive scripts in `scripts/host/` install it (`install_picoscenes.sh`) and run the receiver and transmitter (`picoscenes_rx.sh`, `picoscenes_tx.sh`, optional `aims-picoscenes-rx.service`). PicoScenes forwards each CSI frame by UDP to the published port `1025`.
- **The mode is selected explicitly** with `CSI_SOURCE=mock|picoscenes` (default `mock`), read by `aims_launch.py` and `aims_core_launch.py` as the `csi_source` launch argument. `mock` replays a recorded frame; `picoscenes` runs `csi_publisher`, which reads `CSI_UDP_HOST` (default `0.0.0.0`) and `CSI_UDP_PORT` (default `1025`).
- **The patched parser is built into the image** from a pinned upstream commit (see [ADR-0002](./ADR-0002-ros2-humble-as-target-version.md)).

## Alternatives Considered

| Alternative | Why it was rejected |
|---|---|
| Containerize PicoScenes (privileged container, device passthrough) | Depends on kernel driver and firmware switching of the host; fragile and not reproducible across kernels. |
| Keep auto-detection (`shutil.which`) | Cannot work: the check runs in a different environment from where PicoScenes lives. |
| Separate Compose profiles/files for mock and hardware | Two entry points to keep in sync; a single variable is enough. |

## Consequences

### Positive
- Mock mode needs no hardware, no `.env` and works on Linux, Windows and macOS with Docker.
- Switching to hardware is one variable (`CSI_SOURCE=picoscenes`, or `make up-hardware`) plus running the host script.
- The mode in use is visible and reproducible (an environment variable, not a side effect of what is installed).

### Negative / Trade-offs
- Hardware mode requires a Linux host with an IWL5300 and a reboot after installing PicoScenes.
- Two moving parts (host script and containers) must be started by the user.
- The pinned toolbox commit dates from November 2022; updating it means re-validating the patched `picoscenes.pyx`.

## Related Links
- [ADR-0002](./ADR-0002-ros2-humble-as-target-version.md) — ROS2 Humble as target version
- [ADR-0008](./ADR-0008-bridge-networking-as-default.md) — Bridge networking as default
