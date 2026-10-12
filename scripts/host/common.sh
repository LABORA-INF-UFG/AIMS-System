# Shared helpers for the PicoScenes host scripts. Sourced, not executed.
# shellcheck shell=bash

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

die() { echo "ERROR: $*" >&2; exit 1; }

# Read PICOSCENES_* variables from the repo .env without executing it.
# Variables already set in the environment win over .env.
load_env() {
    local key value
    [ -f "$REPO_DIR/.env" ] || return 0
    while IFS='=' read -r key value; do
        case "$key" in
            PICOSCENES_[A-Z_]*)
                if [ -z "${!key:-}" ]; then export "$key=$value"; fi ;;
        esac
    done < <(tr -d '\r' < "$REPO_DIR/.env")
}

# Values below end up on a sudo command line: accept only known-safe shapes.
check_freq()    { [[ "$1" =~ ^[0-9]{4}$ ]] || die "invalid --freq '$1' (MHz, e.g. 5180)"; }
check_bw()      { [[ "$1" =~ ^(HT20|HT40|HT40\+|HT40-)$ ]] || die "invalid --bw '$1' (HT20, HT40, HT40+ or HT40-)"; }
check_nic()     { [[ "$1" =~ ^[A-Za-z0-9_.-]{1,15}$ ]] || die "invalid --nic '$1' (interface name, e.g. wlp2s0)"; }
check_phypath() { [[ "$1" =~ ^[0-9]{1,3}$ ]] || die "invalid --phypath '$1' (PicoScenes PhyPath number, see array_status)"; }
check_forward() {
    [[ "$1" =~ ^[A-Za-z0-9.-]+:([0-9]{1,5})$ ]] && [ "${BASH_REMATCH[1]}" -ge 1 ] && [ "${BASH_REMATCH[1]}" -le 65535 ] \
        || die "invalid --forward '$1' (HOST:PORT, e.g. 127.0.0.1:1025)"
}

need_arg() { [ "$#" -ge 2 ] && [ -n "$2" ] || die "option $1 needs a value"; }

# Switch the IWL5300 to CSI firmware and tune PhyPath $1 to "$2 $3".
prepare_nic() {
    command -v PicoScenes >/dev/null || die "PicoScenes not found. Run scripts/host/install_picoscenes.sh and reboot."
    echo "Switching IWL5300 firmware to CSI mode..."
    switch5300Firmware csi >/dev/null
    echo "Preparing PhyPath $1 for $2 MHz $3..."
    sudo array_prepare_for_picoscenes "$1" "$2 $3"
}
