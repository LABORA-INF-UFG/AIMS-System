#!/bin/bash

echo "Switching firmware to csi firmware..."

#Switch firmware and redirect the execution output
switch5300Firmware csi &> /dev/null

echo "Qual frequencia irá operar? [5180, 5200, ...]"

read freq_channel

echo "Qual bandwidth de operação? [HT20, HT40]"

read bandwidth

echo "*Algumas frequências operam somente em HT20 e outras em HT40."

echo -e "Preparing interface...\n"

#Prepare the interface
sudo array_prepare_for_picoscenes 2 "$freq_channel $bandwidth"

echo -e "\nPreparation is done."

echo "Inciando a captura dos frames..."

PicoScenes -d debug -i wlp2s0 --mode logger --forward-to 127.0.0.1:1025