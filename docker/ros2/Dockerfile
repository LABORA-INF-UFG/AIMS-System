# =============================================================================
# AIMS-System ROS2 Dockerfile (Multi-Stage Build)
# Base: ROS2 Humble Hawksbill (LTS until May 2027)
# =============================================================================

# ============ STAGE 1: Builder ============
ARG ROS_IMAGE=ros:humble@sha256:860e53793ccf575e5369b5e9a19939de2bfcfb46a299954d06f54f2af54fed19
FROM ${ROS_IMAGE} AS builder

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
COPY aims_ws/src/vision/vision_interfaces/package.xml /tmp/aims_ws/src/vision/vision_interfaces/

# Resolve ROS2 package dependencies via rosdep
RUN cd /tmp/aims_ws && \
    source /opt/ros/${ROS_DISTRO}/setup.bash && \
    rosdep update && \
    rosdep install -i --from-path src --rosdistro ${ROS_DISTRO} -y

# Install Python dependencies (without oct2py — experimental only)
COPY requirements/core.lock /tmp/core.lock
RUN pip3 install --no-cache-dir --require-hashes -r /tmp/core.lock

# Build the patched PicoScenes parser (resources/picoscenes.pyx parses one UDP
# frame instead of a file). Pinned to the toolbox commit the patch was written
# against (Nov 2022); newer upstream commits change the parsing core API.
# Built after core.lock so it compiles against the runtime numpy.
ARG PICOSCENES_TOOLBOX_COMMIT=6e4c6cbdc037a80d0e707b53440c9ef139b750cc
COPY resources/picoscenes.pyx /tmp/picoscenes.pyx
COPY requirements/core-build.lock /tmp/core-build.lock
RUN pip3 install --no-cache-dir --require-hashes -r /tmp/core-build.lock && \
    git clone https://github.com/Herrtian/PicoscenesToolbox.git /opt/PicoscenesToolbox && \
    cd /opt/PicoscenesToolbox && \
    git checkout ${PICOSCENES_TOOLBOX_COMMIT} && \
    git submodule update --init --recursive && \
    cp /tmp/picoscenes.pyx picoscenes.pyx && \
    python3 setup.py build_ext --inplace

# Copy source code and build the colcon workspace
COPY aims_ws/src/csi/ /app/aims_ws/src/csi/
COPY aims_ws/src/custom_interfaces/ /app/aims_ws/src/custom_interfaces/
COPY aims_ws/src/vision/vision_interfaces/ /app/aims_ws/src/vision/vision_interfaces/
WORKDIR /app/aims_ws

# vision_interfaces: rosbridge needs it to serialize vision messages.
RUN source /opt/ros/${ROS_DISTRO}/setup.bash && \
    colcon build --packages-up-to csi vision_interfaces --cmake-args -DCMAKE_BUILD_TYPE=Release && \
    rm -rf build/ log/


# ============ STAGE 2: Runtime ============
FROM ${ROS_IMAGE} AS runtime

SHELL ["/bin/bash", "-c"]
ENV DEBIAN_FRONTEND=noninteractive

# Install runtime-only system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ros-${ROS_DISTRO}-rosbridge-server \
        python3-pip && \
    rm -rf /var/lib/apt/lists/*

# Install Python runtime dependencies. evdev (pynput on Linux) has no wheel, so
# take the copy compiled in the builder instead of shipping a toolchain here.
COPY --from=builder /usr/local/lib/python3.10/dist-packages/evdev /usr/local/lib/python3.10/dist-packages/evdev
COPY --from=builder /usr/local/lib/python3.10/dist-packages/evdev-1.6.1.dist-info /usr/local/lib/python3.10/dist-packages/evdev-1.6.1.dist-info
COPY requirements/core.lock /tmp/core.lock
RUN pip3 install --no-cache-dir --require-hashes -r /tmp/core.lock && \
    rm /tmp/core.lock

# Copy built workspace from builder (install/ contains all compiled packages)
COPY --from=builder /app/aims_ws/install/ /app/aims_ws/install/

# Copy source files needed at runtime (resource files, launch files, libs)
COPY aims_ws/src/csi/ /app/aims_ws/src/csi/
COPY aims_ws/src/custom_interfaces/ /app/aims_ws/src/custom_interfaces/
COPY aims_ws/src/fastdds_profile.xml /app/aims_ws/src/fastdds_profile.xml

# Patched PicoScenes parser, imported as PicoscenesToolbox.picoscenes ($AIMS=/app)
COPY --from=builder /opt/PicoscenesToolbox/picoscenes*.so /opt/PicoscenesToolbox/LICENSE.md /app/PicoscenesToolbox/

# Copy entrypoint (strip CR in case of a Windows checkout with CRLF endings)
COPY docker/ros2/entrypoint.sh /entrypoint.sh
RUN sed -i 's/\r$//' /entrypoint.sh && chmod +x /entrypoint.sh

# `docker compose exec <service> ros2 ...` skips the entrypoint; this wrapper
# sources the overlays so the ros2 CLI works there too.
RUN printf '#!/bin/bash\nexec /entrypoint.sh /opt/ros/%s/bin/ros2 "$@"\n' "$ROS_DISTRO" > /usr/local/bin/ros2 && \
    chmod +x /usr/local/bin/ros2

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
