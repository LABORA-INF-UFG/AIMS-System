#!/bin/bash
set -e

# Source ROS2 main overlay
source /opt/ros/${ROS_DISTRO}/setup.bash

# Source the built workspace
if [ -f /app/aims_ws/install/setup.bash ]; then
    source /app/aims_ws/install/setup.bash
fi

exec "$@"
