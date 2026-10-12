# PicoScenes: Host-Only Setup

> **PicoScenes must run directly on the Linux host machine.**
> It cannot be containerized because it depends on the host's kernel driver
> and on switching the firmware of the Intel IWL5300 NIC.

You only need this for hardware mode (`CSI_SOURCE=picoscenes`). Mock mode needs none of it: see the [root README](../README.md).

## Prerequisites

1. Ubuntu, amd64, CPU with SSE4.2
2. An Intel IWL5300 NIC (the installer checks `lspci` and refuses to run without one, unless you pass `--skip-hardware-check`)
3. `sudo` access (firmware switching and array preparation need it)

The CSI parser (the patched PicoscenesToolbox) is built inside the ros2 Docker image; you do not install it on the host.

## Installation

```bash
scripts/host/install_picoscenes.sh      # or: make host-setup
sudo reboot
```

The script is idempotent (it exits early if `picoscenes-all` is already installed) and non-interactive. It adds the PicoScenes apt repository, accepts the PicoScenes license through debconf and installs `picoscenes-all`. It **does not reboot**: reboot yourself after a first install.

Flags: `--skip-hardware-check` installs even when no IWL5300 is found (prints a warning).

## Usage

### Receiver (RX) machine

```bash
scripts/host/picoscenes_rx.sh [--freq 5180] [--bw HT20] [--nic wlp2s0] [--phypath 2] [--forward 127.0.0.1:1025]
```

| Flag | Environment variable (default) | Meaning |
|---|---|---|
| `--freq` | `PICOSCENES_FREQ` (`5180`) | Center frequency in MHz |
| `--bw` | `PICOSCENES_BW` (`HT20`) | `HT20`, `HT40`, `HT40+` or `HT40-` |
| `--nic` | `PICOSCENES_NIC` (`wlp2s0`) | Interface name of the IWL5300 (see `ip link`) |
| `--phypath` | `PICOSCENES_PHYPATH` (`2`) | PicoScenes PhyPath number (see `array_status`) |
| `--forward` | `PICOSCENES_FORWARD_HOST`:`PICOSCENES_FORWARD_PORT` (`127.0.0.1:1025`) | UDP destination `HOST:PORT` |

Flags override the environment, which overrides the repo's `.env`, which overrides the defaults. The script switches the NIC to CSI firmware, prepares the PhyPath and runs PicoScenes in logger mode forwarding every frame by UDP. Stop it with Ctrl+C.

### Transmitter (TX) machine

```bash
scripts/host/picoscenes_tx.sh --nic wlp1s0 [--freq 5180] [--bw HT20] [--phypath 1] [--delay 10000]
```

`--nic` is required unless `PICOSCENES_TX_NIC` is set. `--delay` is the gap between injected packets in microseconds (`10000` = 100 packets/s); defaults come from `PICOSCENES_TX_PHYPATH` (`1`) and `PICOSCENES_TX_DELAY_US` (`10000`). Use the same frequency and bandwidth as the receiver.

### Start at boot (optional)

`scripts/host/aims-picoscenes-rx.service` is a systemd unit that runs `picoscenes_rx.sh` at boot and restarts it on failure. The installation commands are in the header of that file.

## Connecting to the containers

```
┌─────────────────────┐        UDP           ┌──────────────────────────┐
│ PicoScenes (host)   │  one frame/datagram  │ ros2-nodes container     │
│  logger mode        │ ───────────────────> │  csi_publisher           │
│  IWL5300 NIC        │   127.0.0.1:1025     │  (CSI_SOURCE=picoscenes) │
└─────────────────────┘                      └──────────────────────────┘
```

Start the containers with `CSI_SOURCE=picoscenes docker compose up -d` (or `make up-hardware`). Compose publishes UDP port `CSI_UDP_PORT` (default 1025) to the host, so forwarding to `127.0.0.1:1025` should reach `csi_publisher`.

**Status: hardware mode with the default bridge network on Linux is not tested yet.** If no frames arrive, use one of these:

- Host networking: `docker compose -f docker-compose.yml -f docker-compose.hostnet.yml up -d`
- Forward to the host's LAN IP: `scripts/host/picoscenes_rx.sh --forward <host-ip>:1025`

## Troubleshooting

- **"PicoScenes not found"**: run `scripts/host/install_picoscenes.sh` and reboot.
- **No frames received**: check that the NIC name matches (`ip link`, e.g. `wlp2s0` vs `wlan0`), that the transmitter is running on the same frequency and bandwidth, and that `CSI_SOURCE=picoscenes` is set. `csi_publisher` logs "No PicoScenes UDP frames ... yet" while it waits.
- **Permission denied**: firmware switching and array preparation use `sudo`.
- **Invalid `--bw`/`--freq`**: some frequencies only support HT20, others only HT40.
