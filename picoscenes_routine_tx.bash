#!/bin/bash

echo "Switching firmware to csi firmware..."

#Switch firmware and redirect the execution output
switch5300Firmware csi &> /dev/null

echo "Qual frequencia irá operar? [5180, 5200, ...]"

#read freq_channel

echo "Qual bandwidth de operação? [HT20, HT40]"

#read bandwidth

echo "*Algumas frequências operam somente em HT20 e outras em HT40."

echo -e "Preparing interface...\n"

#Prepare the interface
#sudo array_prepare_for_picoscenes 1 "$freq_channel $bandwidth"
sudo array_prepare_for_picoscenes 1 "5180 HT20"

echo -e "\nPreparation is done."

echo -e "\nInicializando os procedimentos de injecao infinita..."

echo -e "\nQual a frequencia, em hertz, que deseja o envio dos pacotes?"

#read freq

#let frequencia=1000000/$freq 

#PicoScenes -d debug -i wlp1s0 --repeat 1e10 --mode injector --delay $frequencia
PicoScenes -d debug -i wlp1s0 --repeat 1e10 --mode injector --delay 10000