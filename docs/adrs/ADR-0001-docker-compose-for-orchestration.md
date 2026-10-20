# ADR-0001: Docker Compose for Stack Orchestration

- **Status**: Accepted
- **Date**: 2026-06-17 (updated 2026-10-12)
- **Deciders**: Luiz Fernando de Freitas Oliveira
- **Technical context**: Containerization of the AIMS-System infrastructure

---

## Context

AIMS-System used to be run by hand through several Bash scripts and individual commands (`docker run`, `ros2 launch`, `npm start`), so every lab member had to follow a fragile, informally documented start-up sequence. The environment combined:

- A real hardware node (PicoScenes, on the Linux host)
- Python ROS2 processing nodes
- An Express.js web server
- A MongoDB database (removed later, see [ADR-0006](./ADR-0006-remove-mongodb-and-patient-management.md))

Each component needed manual configuration of environment variables, ports and IP addresses.

## Decision

Adopt **Docker Compose** to orchestrate the development and production stack of AIMS-System, with every service (except PicoScenes, which needs direct hardware access) defined in `docker-compose.yml`.

## Alternatives Considered

| Alternative | Why it was rejected |
|---|---|
| Keep manual Bash scripts | Fragile, hard to reproduce, no environment isolation. |
| Kubernetes (k8s) | Overkill for an academic/lab setting with a single machine. Needlessly steep learning curve for the team. |
| Podman Compose | Smaller support ecosystem; the team is more familiar with Docker. |
| Docker Swarm | More complexity with no clear benefit for a single-node deployment. |

## Consequences

### Positive
- The whole stack starts with one command: `docker compose up -d --build`.
- Environment variables have built-in defaults; `.env` / `.env.example` is only needed to override them.
- Dependency isolation between services.
- CSI captures are written to a bind mount (`./captures:/app/captures`), so they appear directly in the repository folder on the host.
- Declarative healthchecks check service readiness.
- Mock mode (`CSI_SOURCE=mock`, the default) runs on Linux, Windows and macOS with Docker, because the default network is a bridge network (see [ADR-0008](./ADR-0008-bridge-networking-as-default.md)).

### Negative / Trade-offs
- PicoScenes cannot be containerized, so hardware mode still needs a Linux host (see [ADR-0007](./ADR-0007-picoscenes-on-host-explicit-csi-source.md)).
- The optional `env_file: required: false` syntax needs Docker Compose >= 2.24.

## Related Links
- [ADR-0002](./ADR-0002-ros2-humble-as-target-version.md) — ROS2 Humble as target version
- [ADR-0003](./ADR-0003-host-networking-for-ros2-dds.md) — Host networking for ROS2 DDS (superseded)
- [ADR-0008](./ADR-0008-bridge-networking-as-default.md) — Bridge networking as default
