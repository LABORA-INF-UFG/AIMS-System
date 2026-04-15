cd ..
git clone https://github.com/Herrtian/PicoscenesToolbox.git --recursive
cd PicoscenesToolbox
sudo apt update
sudo apt install -y python3
sudo apt install -y python3-pip
sudo apt install -y liboctave-dev
pip3 install -r requirements.txt
rm picoscenes.pyx 
cp ../resources/picoscenes.pyx .
python3 setup.py build_ext --inplace
