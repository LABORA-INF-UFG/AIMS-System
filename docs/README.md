# Documentation — AIMS-System

This directory holds the technical documentation of the AIMS-System project. For setup and usage, start with the [root README](../README.md).

## Structure

```
docs/
├── README.md          # This file
├── CHANGELOG.md       # Project change history
└── adrs/              # Architectural Decision Records
    ├── README.md      # ADR index and template
    ├── ADR-0001-docker-compose-for-orchestration.md
    ├── ADR-0002-ros2-humble-as-target-version.md
    ├── ADR-0003-host-networking-for-ros2-dds.md
    ├── ADR-0004-rosbridge-as-web-ros2-integration-layer.md
    ├── ADR-0005-tailwindcss-v4-as-styling-framework.md
    ├── ADR-0006-remove-mongodb-and-patient-management.md
    ├── ADR-0007-picoscenes-on-host-explicit-csi-source.md
    ├── ADR-0008-bridge-networking-as-default.md
    ├── ADR-0009-vision-subsystem-separate-image.md
    └── ADR-0010-deprecate-apnea-ai-and-tensorflow.md
```

## What each document is

### [CHANGELOG.md](./CHANGELOG.md)
Chronological record of significant project changes, following [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). It lists breaking renames, so read it if you have captures or scripts from before v0.3.0.

### [adrs/](./adrs/README.md)
**Architectural Decision Records (ADRs)** document the architectural decisions made during development, including the context, the alternatives considered and the consequences of each decision. The format is **MADR (Markdown Any Decision Records)**.
