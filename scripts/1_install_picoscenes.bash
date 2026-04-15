sudo apt install -y wget git debconf-utils
echo "deb [arch=amd64 trusted=yes] https://zpj.io/PicoScenes/ stable sse4.2 main" | sudo tee -a /etc/apt/sources.list
sudo apt install --reinstall -y ca-certificates
sudo apt update
echo "picoscenes-platform	PicoScenes/accepted_license	boolean	true" | sudo debconf-set-selections
echo "picoscenes-platform	PicoScenes/rejected_license	error" | sudo debconf-set-selections
echo "picoscenes-platform	PicoScenes/license	note" | sudo debconf-set-selections
sudo apt install -y picoscenes-all
echo "PicoScenes installation completed, rebooting the system."
sleep 5s
shutdown -r now