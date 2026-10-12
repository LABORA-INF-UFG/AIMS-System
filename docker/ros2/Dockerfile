# =============================================================================
# AIMS-System ROS2 Dockerfile (Multi-Stage Build)
# Base: ROS2 Humble Hawksbill (LTS until May 2027)
# =============================================================================

# ============ STAGE 1: Builder ============
FROM ros:humble AS builder

SHELL ["/bin/bash", "-c"]
ENV DEBIAN_FRONTEND=noninteractive

# Install build tools
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ros-dev-tools \
        python3-pip \
        python3-dev \
        build-essential \
        git && \
    rm -rf /var/lib/apt/lists/*

# Copy package manifests first for rosdep layer caching
COPY aims_ws/src/csi/package.xml /tmp/aims_ws/src/csi/
COPY aims_ws/src/custom_interfaces/package.xml /tmp/aims_ws/src/custom_interfaces/

# Resolve ROS2 package dependencies via rosdep
RUN cd /tmp/aims_ws && \
    source /opt/ros/${ROS_DISTRO}/setup.bash && \
    rosdep update && \
    rosdep install -i --from-path src --rosdistro ${ROS_DISTRO} -y

# Install PicoscenesToolbox from GitHub (Cython-based, requires build tools)
RUN pip3 install --no-cache-dir \
    git+https://github.com/wifisensing/PicoScenes-Python-Toolbox.git@master

# Install Python dependencies (without oct2py — experimental only)
COPY aims_ws/src/requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt

# Copy source code and build the colcon workspace
COPY aims_ws/ /app/aims_ws/
WORKDIR /app/aims_ws

RUN source /opt/ros/${ROS_DISTRO}/setup.bash && \
    colcon build --cmake-args -DCMAKE_BUILD_TYPE=Release && \
    rm -rf build/ log/


# ============ STAGE 2: Runtime ============
FROM ros:humble AS runtime

SHELL ["/bin/bash", "-c"]
ENV DEBIAN_FRONTEND=noninteractive

# Install runtime-only system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ros-${ROS_DISTRO}-rosbridge-server \
        python3-pip && \
    rm -rf /var/lib/apt/lists/*

# Install PicoscenesToolbox runtime (pre-built in builder, but pip packages
# don't transfer between stages cleanly for Cython, so reinstall)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        python3-dev \
        build-essential \
        git && \
    pip3 install --no-cache-dir \
        git+https://github.com/wifisensing/PicoScenes-Python-Toolbox.git@master && \
    apt-get purge -y build-essential git && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

# Install Python runtime dependencies
COPY aims_ws/src/requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt && \
    rm /tmp/requirements.txt

# Copy built workspace from builder (install/ contains all compiled packages)
COPY --from=builder /app/aims_ws/install/ /app/aims_ws/install/

# Copy source files needed at runtime (resource files, launch files, libs)
COPY aims_ws/src/csi/ /app/aims_ws/src/csi/
COPY aims_ws/src/custom_interfaces/ /app/aims_ws/src/custom_interfaces/
COPY aims_ws/src/fastdds_profile.xml /app/aims_ws/src/fastdds_profile.xml

# Copy entrypoint
COPY docker/ros2/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Environment variables (can be overridden by docker-compose .env)
ENV AIMS=/app
ENV RMW_IMPLEMENTATION=rmw_fastrtps_cpp
ENV FASTRTPS_DEFAULT_PROFILES_FILE=/app/aims_ws/src/fastdds_profile.xml
ENV ROS_DOMAIN_ID=5

# Volume for AI models (mounted externally)
VOLUME ["/app/models"]

# Volume for CSI captures
VOLUME ["/app/captures"]

WORKDIR /app/aims_ws

ENTRYPOINT ["/entrypoint.sh"]
CMD ["ros2", "launch", "csi", "aims_launch.py"]
