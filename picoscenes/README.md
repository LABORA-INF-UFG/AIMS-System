# PicoScenes — Host-Only Setup

> **PicoScenes must run directly on the Linux host machine.**
> It cannot be containerized because it requires direct access to the Intel
> IWL5300 NIC hardware and kernel-level firmware switching.

## Prerequisites

1. Linux machine with Intel IWL5300 NIC
2. PicoScenes installed ([installation guide](https://ps.zpj.io/))
3. PicoScenes firmware switching tools (`switch5300Firmware`, `array_prepare_for_picoscenes`)

## Installation

Run the installation scripts from the repository root:

```bash
cd scripts
source 1_install_picoscenes.bash
source 2_install_PicoScenesToolbox.bash
```

## Configuration

PicoScenes forwards captured CSI frames via UDP packet-forwarding.
The target address is configured via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `PICOSCENES_FORWARD_HOST` | `127.0.0.1` | IP where ROS2 CSI publisher listens |
| `PICOSCENES_FORWARD_PORT` | `1025` | UDP port for CSI frame forwarding |
| `PICOSCENES_NIC` | `wlp2s0` | Network interface name for the IWL5300 |

Set these in the root `.env` file or export them in your shell.

## Usage

### Receiver (RX) Machine

Start CSI frame capture and forwarding:

```bash
./picoscenes_routine_rx.bash
```

This will:
1. Switch firmware to CSI mode
2. Prepare the antenna array
3. Start PicoScenes in logger mode, forwarding frames to the configured address

### Transmitter (TX) Machine

Start continuous packet injection:

```bash
./picoscenes_routine_tx.bash
```

## Architecture

```
┌─────────────────────┐         UDP          ┌─────────────────────────┐
│                     │    (packet-forward)   │                         │
│  PicoScenes (Host)  │ ──────────────────>   │  ROS2 Container         │
│  - logger mode      │   127.0.0.1:1025      │  - csi_publisher node   │
│  - IWL5300 NIC      │                       │  - network_mode: host   │
│                     │                       │                         │
└─────────────────────┘                       └─────────────────────────┘
```

Since the ROS2 container uses `network_mode: host`, it shares the host's
network stack. PicoScenes can forward to `127.0.0.1:1025` and the
`csi_publisher` node inside the container will receive the frames normally.

## Troubleshooting

- **"PicoScenes not found"**: Ensure PicoScenes is installed and on PATH
- **No frames received**: Check that the NIC interface name matches (`wlp2s0` vs `wlan0`)
- **Permission denied**: Firmware switching requires `sudo`
