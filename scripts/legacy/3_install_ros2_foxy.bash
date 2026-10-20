# Setup sources
sudo apt update && sudo apt install -y locales
sudo locale-gen en_US en_US.UTF-8
sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
export LANG=en_US.UTF-8
sudo apt install -y software-properties-common
sudo add-apt-repository universe
sudo apt update && sudo apt install -y curl
sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) main" | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null

# Install ros2

sudo apt update
sudo apt upgrade -y
sudo apt install -y ros-foxy-ros-base python3-argcomplete
sudo apt install -y ros-dev-tools
curl -fsSL https://deb.nodesource.com/setup_19.x | sudo -E bash - && sudo apt-get install -y nodejs

# Creates an env variable for the current directory's path
# and adds it to .bashrc
cd ..
echo "export AIMS=$(pwd)" >> ~/.bashrc

source ~/.bashrc

# Adds the source of the ROS2 main overlay to .bashrc
echo "source /opt/ros/foxy/setup.bash" >> ~/.bashrc

# Creates an env variable with the path to the local_setup build script
# and adds it to .bashrc
echo "AIMSWS_LOCALSETUP=$AIMS/aims_ws/install/local_setup.bash" >> ~/.bashrc

# Add env for apnea AI Keras model
echo "export KERAS_APNEA_MODEL=$AIMS/aims_ws/src/csi/csi/resource/apenaDetection_AIMS_model1.h5" >> ~/.bashrc

# Add defaults for rmw
echo "export RMW_IMPLEMENTATION=rmw_fastrtps_cpp" >> ~/.bashrc
echo "export FASTRTPS_DEFAULT_PROFILES_FILE=$AIMS/aims_ws/src/fastdds_profile.xml" >> ~/.bashrc
echo "export ROS_DOMAIN_ID=5" >> ~/.bashrc

source ~/.bashrc
sudo apt install -y ros-$ROS_DISTRO-rosbridge-server
sudo rosdep init
rosdep update

echo "ROS2 configuration complete on this machine"
echo "Building AIMS system"
sleep 5s
cd aims_ws/src
python3 -m pip install -r requirements.txt 
cd $AIMS
source build.bash

cd $AIMS/web
npm install
