#!/usr/bin/env bash
# =============================================================================
# Installs PicoScenes on the host (Ubuntu amd64, SSE4.2 CPU, Intel IWL5300).
# Idempotent and non-interactive. It does NOT reboot: reboot yourself after a
# fresh install. The CSI parser (PicoscenesToolbox) is built inside the ros2
# Docker image, so it is not installed here.
#
# Usage: scripts/host/install_picoscenes.sh [--skip-hardware-check]
#   --skip-hardware-check  warn instead of aborting when no Intel IWL5300 NIC is
#                          found (e.g. installing before the card is fitted).
#   -h, --help             show this help.
# =============================================================================
set -euo pipefail
# shellcheck source=common.sh
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

skip_hw_check=0
for arg in "$@"; do
    case "$arg" in
        --skip-hardware-check) skip_hw_check=1 ;;
        -h|--help)
            echo "Usage: $0 [--skip-hardware-check]"
            echo "  --skip-hardware-check  warn instead of aborting when no Intel IWL5300 NIC is found"
            exit 0 ;;
        *) die "unknown argument: $arg (see --help)" ;;
    esac
done

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
if ! lspci | grep -qiE 'WiFi Link 5300|IWL5300'; then
    if [ "$skip_hw_check" = 1 ]; then
        echo "WARNING: no Intel IWL5300 NIC found (lspci); continuing because of --skip-hardware-check." >&2
    else
        die "no Intel IWL5300 NIC found (lspci). Fit the card, or re-run with --skip-hardware-check to install anyway."
    fi
fi

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
