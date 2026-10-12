#!/usr/bin/env bash
# =============================================================================
# PicoScenes receiver (RX): captures CSI on the IWL5300 and forwards every
# frame over UDP to the AIMS ros2-nodes container (run it with
# CSI_SOURCE=picoscenes, e.g. `make up-hardware`). Non-interactive.
#
# Usage:
#   scripts/host/picoscenes_rx.sh [--freq 5180] [--bw HT20] [--nic wlp2s0]
#                                 [--phypath 2] [--forward 127.0.0.1:1025]
#
# Defaults: environment, then the repo .env, then the values above.
#   PICOSCENES_FREQ, PICOSCENES_BW, PICOSCENES_NIC, PICOSCENES_PHYPATH,
#   PICOSCENES_FORWARD_HOST, PICOSCENES_FORWARD_PORT
# =============================================================================
set -euo pipefail
# shellcheck source=common.sh
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

load_env
freq="${PICOSCENES_FREQ:-5180}"
bw="${PICOSCENES_BW:-HT20}"
nic="${PICOSCENES_NIC:-wlp2s0}"
phypath="${PICOSCENES_PHYPATH:-2}"
forward="${PICOSCENES_FORWARD_HOST:-127.0.0.1}:${PICOSCENES_FORWARD_PORT:-1025}"

while [ "$#" -gt 0 ]; do
    case "$1" in
        --freq)    need_arg "$@"; freq="$2"; shift 2 ;;
        --bw)      need_arg "$@"; bw="$2"; shift 2 ;;
        --nic)     need_arg "$@"; nic="$2"; shift 2 ;;
        --phypath) need_arg "$@"; phypath="$2"; shift 2 ;;
        --forward) need_arg "$@"; forward="$2"; shift 2 ;;
        -h|--help) sed -n '2,14p' "$0"; exit 0 ;;
        *) die "unknown option '$1' (see --help)" ;;
    esac
done

check_freq "$freq"; check_bw "$bw"; check_nic "$nic"; check_phypath "$phypath"; check_forward "$forward"

echo "Note: some frequencies only support HT20, others only HT40."
prepare_nic "$phypath" "$freq" "$bw"

echo "Capturing CSI on $nic and forwarding frames to $forward (Ctrl+C to stop)..."
exec PicoScenes -d debug -i "$nic" --mode logger --forward-to "$forward"
