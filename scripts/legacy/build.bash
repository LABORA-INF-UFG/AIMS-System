#!/bin/bash

# Sourcing main ROS2 overlay to use ROS2
source /opt/ros/$ROS_DISTRO/setup.bash

cd aims_ws

# Resolving package dependencies
rosdep update
rosdep install -i --from-path src --rosdistro $ROS_DISTRO -y

# Build the workspace
# --symlink-install: saves you from having to rebuild every time you tweak python scripts
colcon build --symlink-install
