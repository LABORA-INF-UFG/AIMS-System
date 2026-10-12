#!/usr/bin/env bash
# =============================================================================
# Installs PicoScenes on the host (Ubuntu amd64, SSE4.2 CPU, Intel IWL5300).
# Idempotent and non-interactive. It does NOT reboot: reboot yourself after a
# fresh install. The CSI parser (PicoscenesToolbox) is built inside the ros2
# Docker image, so it is not installed here.
#
# Usage: scripts/host/install_picoscenes.sh
# =============================================================================
set -euo pipefail
# shellcheck source=common.sh
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

if dpkg -s picoscenes-all >/dev/null 2>&1; then
    echo "PicoScenes (picoscenes-all) is already installed. Nothing to do."
    exit 0
fi

# Prerequisites
# shellcheck disable=SC1091
os_id="$(. /etc/os-release && echo "${ID:-}")"
[ "$os_id" = ubuntu ] || die "Ubuntu is required (found: ${os_id:-unknown})."
[ "$(dpkg --print-architecture)" = amd64 ] || die "amd64 is required (found: $(dpkg --print-architecture))."
grep -qw sse4_2 /proc/cpuinfo || die "this CPU lacks SSE4.2, required by the PicoScenes packages."
command -v lspci >/dev/null || die "lspci not found; install it with: sudo apt-get install -y pciutils"
lspci | grep -qiE 'WiFi Link 5300|IWL5300' || die "no Intel IWL5300 NIC found (lspci)."

export DEBIAN_FRONTEND=noninteractive
sudo -E apt-get update
sudo -E apt-get install -y wget git debconf-utils ca-certificates

echo "deb [arch=amd64 trusted=yes] https://zpj.io/PicoScenes/ stable sse4.2 main" \
    | sudo tee /etc/apt/sources.list.d/picoscenes.list >/dev/null

# Accept the PicoScenes license non-interactively
printf '%s\n' \
    "picoscenes-platform	PicoScenes/accepted_license	boolean	true" \
    "picoscenes-platform	PicoScenes/rejected_license	error" \
    "picoscenes-platform	PicoScenes/license	note" \
    | sudo debconf-set-selections

sudo -E apt-get update
sudo -E apt-get install -y picoscenes-all

echo "PicoScenes installed. Reboot required before first use: sudo reboot"
