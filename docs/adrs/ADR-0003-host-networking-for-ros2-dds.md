# ADR-0003: Host Networking for ROS2 Services in Docker

- **Status**: Superseded by [ADR-0008](./ADR-0008-bridge-networking-as-default.md)
- **Date**: 2026-06-17
- **Deciders**: Luiz Fernando de Freitas Oliveira
- **Technical context**: Network configuration for DDS communication between containers and the host

> **Historical record.** Host networking is no longer the default. It remains available as the opt-in override `docker-compose.hostnet.yml`. The text below is kept unchanged as the reasoning that was valid at the time.

---

## Context

ROS2 uses the **DDS (Data Distribution Service)** middleware for node discovery and communication. DDS participant discovery happens through **UDP multicast** on the local network, which conflicts with the default behavior of Docker bridge networks (`docker0`).

In a Docker bridge topology:
- Containers are isolated on a separate virtual network (`172.x.x.x`)
- UDP multicast does not cross the bridge interface by default
- ROS2 nodes inside containers cannot discover nodes on the host or in other containers without complex extra configuration

In addition, PicoScenes, which **must run on the Linux host** because it needs direct access to the Wi-Fi NIC, sends UDP packets through packet-forwarding to `127.0.0.1:1025`. Containers on bridge networking cannot receive packets sent to the host's `localhost`.

## Decision

Configure the `ros2-nodes` and `rosbridge` services with `network_mode: "host"` and `ipc: host` in `docker-compose.yml`.

```yaml
ros2-nodes:
  network_mode: "host"
  ipc: host

rosbridge:
  network_mode: "host"
  ipc: host
```

## Alternatives Considered

| Alternative | Why it was rejected |
|---|---|
| **Docker bridge + DDS multicast config** | Needs advanced multicast route and interface mapping, and is unstable with FastDDS in lab environments. |
| **Cyclone DDS with unicast discovery** | Possible, but needs deep knowledge of the `CYCLONE_URI` XML and is incompatible with the FastDDS profile (`fastdds_profile.xml`) already in use. |
| **Docker Macvlan** | Requires extra network privileges on the host and complex L2 configuration; unsuitable for a shared lab environment. |
| **ROS2 via socket proxy (zenoh-bridge)** | Adds latency and a new infrastructure component to an already complex system. |

## Consequences

### Positive
- DDS discovery between the host (PicoScenes) and the containers works natively without extra configuration.
- ROS2 nodes in the container receive UDP packets sent to the host's `localhost`.
- Zero NAT or proxy overhead for CSI data traffic (high rate, ~1000 packets/s).
- Full compatibility with the existing `fastdds_profile.xml`.

### Negative / Trade-offs
- **`network_mode: host` only works on Linux.** On macOS and Windows Docker does not support this mode, which made developing or testing the full stack outside Linux machines impossible.
- Reduced network isolation: ROS2 containers share the host's network namespace, exposing all ports without explicit binding.
- Possible port conflicts with other services on the host (e.g. rosbridge's 9090).

### Mitigation
- `ROS_DOMAIN_ID` (default: `5`) is configurable through `.env` to avoid collisions with other ROS2 instances on the lab network.
- FastDDS is configured through `fastdds_profile.xml` to restrict communication interfaces, reducing the risk of traffic collisions.

## Why it was superseded

Host networking made the default `docker compose up` impossible on Windows and macOS, even for mock mode, which needs no hardware. [ADR-0008](./ADR-0008-bridge-networking-as-default.md) moves the default to a bridge network with published ports and keeps host networking as an optional override.

## Related Links
- [ADR-0001](./ADR-0001-docker-compose-for-orchestration.md) — Docker Compose for orchestration
- [ADR-0002](./ADR-0002-ros2-humble-as-target-version.md) — ROS2 Humble as target version
- [ADR-0008](./ADR-0008-bridge-networking-as-default.md) — Bridge networking as default
