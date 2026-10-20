#!/usr/bin/env bash
# =============================================================================
# PicoScenes transmitter (TX): injects packets continuously so the RX machine
# can measure CSI. Non-interactive.
#
# Usage:
#   scripts/host/picoscenes_tx.sh --nic wlp1s0 [--freq 5180] [--bw HT20]
#                                 [--phypath 1] [--delay 10000]
#
# --delay is the gap between packets in microseconds (10000 = 100 packets/s).
# Defaults: environment, then the repo .env, then the values above.
#   PICOSCENES_TX_NIC (required unless --nic), PICOSCENES_FREQ, PICOSCENES_BW,
#   PICOSCENES_TX_PHYPATH, PICOSCENES_TX_DELAY_US
# =============================================================================
set -euo pipefail
# shellcheck source=common.sh
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

load_env
nic="${PICOSCENES_TX_NIC:-}"
freq="${PICOSCENES_FREQ:-5180}"
bw="${PICOSCENES_BW:-HT20}"
phypath="${PICOSCENES_TX_PHYPATH:-1}"
delay="${PICOSCENES_TX_DELAY_US:-10000}"

while [ "$#" -gt 0 ]; do
    case "$1" in
        --nic)     need_arg "$@"; nic="$2"; shift 2 ;;
        --freq)    need_arg "$@"; freq="$2"; shift 2 ;;
        --bw)      need_arg "$@"; bw="$2"; shift 2 ;;
        --phypath) need_arg "$@"; phypath="$2"; shift 2 ;;
        --delay)   need_arg "$@"; delay="$2"; shift 2 ;;
        -h|--help) sed -n '2,14p' "$0"; exit 0 ;;
        *) die "unknown option '$1' (see --help)" ;;
    esac
done

[ -n "$nic" ] || die "no TX interface: pass --nic or set PICOSCENES_TX_NIC"
check_nic "$nic"; check_freq "$freq"; check_bw "$bw"; check_phypath "$phypath"
[[ "$delay" =~ ^[0-9]{1,9}$ ]] || die "invalid --delay '$delay' (microseconds)"

prepare_nic "$phypath" "$freq" "$bw"

echo "Injecting packets on $nic every $delay us (Ctrl+C to stop)..."
exec PicoScenes -d debug -i "$nic" --repeat 1e10 --mode injector --delay "$delay"
