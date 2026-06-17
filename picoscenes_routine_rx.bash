#!/bin/bash
# =============================================================================
# PicoScenes Receiver (RX) Routine
#
# Switches firmware, prepares antenna array, and starts PicoScenes
# in logger mode with UDP packet-forwarding to the configured address.
#
# Configuration (via environment variables or .env file):
#   PICOSCENES_FORWARD_HOST  — Target IP (default: 127.0.0.1)
#   PICOSCENES_FORWARD_PORT  — Target port (default: 1025)
#   PICOSCENES_NIC           — Network interface (default: wlp2s0)
# =============================================================================

# Load .env if present
if [ -f "$(dirname "$0")/.env" ]; then
    set -a
    source "$(dirname "$0")/.env"
    set +a
fi

FORWARD_HOST=${PICOSCENES_FORWARD_HOST:-127.0.0.1}
FORWARD_PORT=${PICOSCENES_FORWARD_PORT:-1025}
NIC_INTERFACE=${PICOSCENES_NIC:-wlp2s0}

echo "Switching firmware to CSI firmware..."
switch5300Firmware csi &> /dev/null

echo "Qual frequencia irá operar? [5180, 5200, ...]"
read freq_channel

echo "Qual bandwidth de operação? [HT20, HT40]"
read bandwidth

echo "*Algumas frequências operam somente em HT20 e outras em HT40."

echo -e "Preparing interface...\n"
sudo array_prepare_for_picoscenes 2 "$freq_channel $bandwidth"

echo -e "\nPreparation is done."
echo "Iniciando a captura dos frames..."
echo "Forwarding to ${FORWARD_HOST}:${FORWARD_PORT} via ${NIC_INTERFACE}"

PicoScenes -d debug -i "$NIC_INTERFACE" --mode logger --forward-to "${FORWARD_HOST}:${FORWARD_PORT}"