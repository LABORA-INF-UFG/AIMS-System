# ADR-0008: Bridge Networking with Published Ports as Default; Host Networking as an Opt-in Override

- **Status**: Accepted (supersedes [ADR-0003](./ADR-0003-host-networking-for-ros2-dds.md))
- **Date**: 2026-10-12
- **Deciders**: Luiz Fernando de Freitas Oliveira
- **Technical context**: Container networking after the move to explicit CSI source selection

---

## Context

[ADR-0003](./ADR-0003-host-networking-for-ros2-dds.md) put `ros2-nodes` and `rosbridge` on host networking so DDS discovery and PicoScenes forwarding to `127.0.0.1` would work. The cost was that the default stack could not run on Docker Desktop (Windows/macOS), even in mock mode, which needs no hardware.

`ros2-nodes` and `rosbridge` only need to talk to each other and to the browser. Discovery between two containers on the same user-defined bridge network works without multicast tricks, and the browser only needs rosbridge's WebSocket port.

## Decision

- The default `docker-compose.yml` uses a **bridge network** and publishes only the ports the host needs: web `3001`, rosbridge `9090` and UDP `1025` (for PicoScenes frames).
- **Host networking is an optional override**, `docker-compose.hostnet.yml` (Linux only), for distributed multi-machine ROS2 setups where other machines on the LAN must discover the containers' DDS participants:

```bash
docker compose -f docker-compose.yml -f docker-compose.hostnet.yml up -d
```

- The frontend no longer assumes `localhost`: it reads the rosbridge port from `GET /config` and connects to the hostname that served the page (see [ADR-0004](./ADR-0004-rosbridge-as-web-ros2-integration-layer.md)).

## Alternatives Considered

| Alternative | Why it was rejected |
|---|---|
| Keep host networking as default | Blocks Windows/macOS and mock-mode users for no benefit on a single machine. |
| Host networking on Linux, bridge elsewhere (detect automatically) | Two behaviors behind one command; harder to reason about and document. |
| Only bridge, drop the override | Removes the option of multi-machine DDS discovery that the lab setup used. |

## Consequences

### Positive
- `docker compose up -d --build` works on Linux, Windows and macOS in mock mode.
- Only three ports are exposed on the host.
- Multi-machine setups remain possible through the override file.

### Negative / Trade-offs
- **Hardware mode with bridge networking on Linux is not tested yet.** PicoScenes forwarding to `127.0.0.1:1025` should reach the container through the published UDP port, but this has not been verified on real hardware. Fallbacks: use `docker-compose.hostnet.yml`, or forward to the host's LAN IP (`--forward <host-ip>:1025`).
- DDS discovery from machines outside the Docker host does not work with the bridge network; use the override for that case.
- The override uses `!reset` and needs Docker Compose >= 2.24.

## Related Links
- [ADR-0001](./ADR-0001-docker-compose-for-orchestration.md) — Docker Compose for orchestration
- [ADR-0003](./ADR-0003-host-networking-for-ros2-dds.md) — Host networking for ROS2 DDS (superseded)
- [ADR-0007](./ADR-0007-picoscenes-on-host-explicit-csi-source.md) — PicoScenes on the host, explicit CSI source
