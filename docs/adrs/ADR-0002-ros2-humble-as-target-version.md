# ADR-0002: ROS2 Humble as the Target Version

- **Status**: Accepted
- **Date**: 2026-06-17 (updated 2026-10-12)
- **Deciders**: Luiz Fernando de Freitas Oliveira
- **Technical context**: Migration of the ROS2 base version used by the project

---

## Context

The project was originally developed with **ROS2 Foxy** (EOL: June 2023). Foxy no longer receives security patches or package updates. In addition, the project's essential packages (such as `rosbridge_suite` and `ros-dev-tools`) have better official support in newer ROS2 releases.

The team had to choose which LTS release of ROS2 to use as the base of the Docker container, balancing stability against long-term support.

## Decision

Move the base image of the ROS2 containers from `ros:foxy` to **`ros:humble-ros-base`** (ROS2 Humble Hawksbill).

## Alternatives Considered

| Alternative | Why it was rejected |
|---|---|
| **Foxy** (keep) | EOL since June 2023. No security patches. Reduced package support in the apt repositories. |
| **Galactic** | EOL since December 2022. Rejected for the same reason. |
| **Iron** | Short-lived (non-LTS) release, EOL in November 2024. |
| **Jazzy Jalisco** | Released in May 2024, too recent at decision time to guarantee stability of the Python/CSI ecosystem packages used by the project and compatibility with `PicoscenesToolbox`. |

## Why Humble

1. **LTS with extended support**: Humble is supported until May 2027, which covers the research period of the project.
2. **Ubuntu 22.04 (Jammy) compatibility**: the official `ros:humble-ros-base` image is built on Ubuntu 22.04, the lab platform.
3. **Full `rosbridge_suite` support**: `ros-humble-rosbridge-server` is available in the official apt repositories.
4. **`PicoscenesToolbox` compatibility**: the CSI parser was validated in this environment.

## Consequences

### Positive
- Smaller and more efficient Docker images (~1.5 GB vs ~2.5 GB with Foxy).
- Packages available and up to date in the official ROS2 apt repositories.
- LTS support until 2027, in line with the research project's horizon.

### Negative / Trade-offs
- The migration required reviewing the launch files (`aims_launch.py`, `aims_core_launch.py`) to remove integrations that depended on Foxy-specific behavior.
- Collaborators with older equipment (e.g. a Jetson Nano with ROS2 Foxy) must keep interface compatibility over DDS, handled through `ROS_DOMAIN_ID` and the FastDDS configuration.

### Update (2026-10-12): how the CSI parser is obtained
The original text said the PicoScenes deserialization library was installed with pip. That is no longer true. The upstream toolbox parses files, while AIMS needs to parse a single UDP packet, so the ros2 image now clones `Herrtian/PicoscenesToolbox` at a **pinned commit** (`6e4c6cbdc037a80d0e707b53440c9ef139b750cc`, build argument `PICOSCENES_TOOLBOX_COMMIT`), overlays the patched `resources/picoscenes.pyx` and compiles it in the builder stage. The result is imported as `PicoscenesToolbox.picoscenes`.

## Related Links
- [ADR-0001](./ADR-0001-docker-compose-for-orchestration.md) — Docker Compose for orchestration
- [ADR-0003](./ADR-0003-host-networking-for-ros2-dds.md) — Host networking for ROS2 DDS (superseded)
- [ADR-0007](./ADR-0007-picoscenes-on-host-explicit-csi-source.md) — PicoScenes on the host, explicit CSI source
