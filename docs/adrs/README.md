# Architectural Decision Records (ADRs)

This directory holds the **Architectural Decision Records** of the AIMS-System project.

ADRs document significant architectural decisions: the context that motivated them, the alternatives considered and the expected consequences. The format is [MADR (Markdown Any Decision Records)](https://adr.github.io/madr/).

## Possible statuses

| Status | Meaning |
|--------|---------|
| `Proposed` | Decision proposed, awaiting review |
| `Accepted` | Decision approved and in force |
| `Deprecated` | Decision no longer applies |
| `Superseded by ADR-XXXX` | Replaced by a specific ADR |

## Index

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [ADR-0001](./ADR-0001-docker-compose-for-orchestration.md) | Docker Compose for Stack Orchestration | Accepted | 2026-06-17 |
| [ADR-0002](./ADR-0002-ros2-humble-as-target-version.md) | ROS2 Humble as the Target Version | Accepted | 2026-06-17 |
| [ADR-0003](./ADR-0003-host-networking-for-ros2-dds.md) | Host Networking for ROS2 Services in Docker | Superseded by ADR-0008 | 2026-06-17 |
| [ADR-0004](./ADR-0004-rosbridge-as-web-ros2-integration-layer.md) | Rosbridge as the Integration Layer between ROS2 and the Web | Accepted | 2026-06-17 |
| [ADR-0005](./ADR-0005-tailwindcss-v4-as-styling-framework.md) | TailwindCSS v4 as the Styling Framework of the Web Interface | Accepted | 2026-06-17 |
| [ADR-0006](./ADR-0006-remove-mongodb-and-patient-management.md) | Remove MongoDB and Patient Management; Subjects Identified by a Free-Text ID | Accepted | 2026-10-12 |
| [ADR-0007](./ADR-0007-picoscenes-on-host-explicit-csi-source.md) | PicoScenes Stays on the Host; Explicit CSI Source Selection | Accepted | 2026-10-12 |
| [ADR-0008](./ADR-0008-bridge-networking-as-default.md) | Bridge Networking as Default; Host Networking as an Opt-in Override | Accepted | 2026-10-12 |

## How to create a new ADR

1. Create a file named `ADR-XXXX-title-in-kebab-case.md`
2. Use the template below as a base
3. Update this index

### Template

```markdown
# ADR-XXXX: Decision Title

- **Status**: Proposed | Accepted | Deprecated | Superseded by ADR-XXXX
- **Date**: YYYY-MM-DD
- **Deciders**: [names or teams involved]
- **Technical context**: [short description of the context]

---

## Context

[Describe the problem or need that motivated the decision.]

## Decision

[Describe the decision clearly and objectively.]

## Alternatives Considered

| Alternative | Why it was rejected |
|---|---|
| Alternative A | ... |
| Alternative B | ... |

## Consequences

### Positive
- ...

### Negative / Trade-offs
- ...

## Related Links
- [ADR-XXXX](./ADR-XXXX-...) — Title
```
