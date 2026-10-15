# =============================================================================
# AIMS-System vision Dockerfile (Multi-Stage Build)
# Camera -> YOLOv8n-pose (ultralytics) -> ROS 2 topics.
# Same ROS 2 Humble base as docker/ros2. CUDA comes from the PyTorch wheels;
# a GPU host only provides the NVIDIA driver.
#
#   VISION_VARIANT=cpu  (default) CPU-only PyTorch, requirements/vision-cpu.lock
#   VISION_VARIANT=cuda           CUDA PyTorch + TensorRT, requirements/vision-cuda.lock
# =============================================================================

# ============ STAGE 1: Builder ============
FROM ros:humble@sha256:860e53793ccf575e5369b5e9a19939de2bfcfb46a299954d06f54f2af54fed19 AS builder

SHELL ["/bin/bash", "-c"]
ENV DEBIAN_FRONTEND=noninteractive

COPY aims_ws/src/vision/ /app/aims_ws/src/vision/
WORKDIR /app/aims_ws

RUN apt-get update && \
    rosdep update --rosdistro ${ROS_DISTRO} && \
    rosdep install -i -y --from-paths src --rosdistro ${ROS_DISTRO} && \
    source /opt/ros/${ROS_DISTRO}/setup.bash && \
    colcon build --packages-up-to vision_bringup && \
    rm -rf build/ log/ /var/lib/apt/lists/*


# ============ STAGE 2: Runtime ============
FROM ros:humble@sha256:860e53793ccf575e5369b5e9a19939de2bfcfb46a299954d06f54f2af54fed19 AS runtime

SHELL ["/bin/bash", "-c"]
ENV DEBIAN_FRONTEND=noninteractive

# libgl1 + libglib2.0-0: runtime libs of opencv-python (pulled in by ultralytics)
RUN apt-get update && \
    apt-get install -y --no-install-recommends python3-pip libgl1 libglib2.0-0 && \
    rm -rf /var/lib/apt/lists/*

# Python deps first: the largest layer, cached across source changes.
# The tensorrt sdist (cuda) otherwise runs a nested, unhashed pip install.
# The _win builder resource (~1.4 GB) is Windows-only; rm -f is a no-op on cpu.
ARG VISION_VARIANT=cpu
ENV NVIDIA_TENSORRT_DISABLE_INTERNAL_PIP=1
COPY requirements/vision-${VISION_VARIANT}.lock /tmp/vision.lock
RUN pip3 install --no-cache-dir --require-hashes -r /tmp/vision.lock && \
    rm -f /tmp/vision.lock /usr/local/lib/python3.10/dist-packages/tensorrt_libs/libnvinfer_builder_resource_win*

# ROS runtime deps of the vision packages (cv_bridge, message_filters, ...)
COPY --from=builder /app/aims_ws/src/vision/ /tmp/vision_src/
RUN apt-get update && \
    rosdep update --rosdistro ${ROS_DISTRO} && \
    rosdep install -i -y --from-paths /tmp/vision_src --rosdistro ${ROS_DISTRO} -t exec && \
    rm -rf /tmp/vision_src /root/.ros/rosdep /var/lib/apt/lists/*

COPY --from=builder /app/aims_ws/install/ /app/aims_ws/install/
COPY aims_ws/src/fastdds_profile.xml /app/aims_ws/src/fastdds_profile.xml

# Same entrypoint as the core image (strip CR in case of a CRLF checkout)
COPY docker/ros2/entrypoint.sh /entrypoint.sh
RUN sed -i 's/\r$//' /entrypoint.sh && chmod +x /entrypoint.sh

# `docker compose exec vision ros2 ...` skips the entrypoint; this wrapper
# sources the overlays so the ros2 CLI works there too.
RUN printf '#!/bin/bash\nexec /entrypoint.sh /opt/ros/%s/bin/ros2 "$@"\n' "$ROS_DISTRO" > /usr/local/bin/ros2 && \
    chmod +x /usr/local/bin/ros2

ENV RMW_IMPLEMENTATION=rmw_fastrtps_cpp
ENV FASTRTPS_DEFAULT_PROFILES_FILE=/app/aims_ws/src/fastdds_profile.xml
ENV ROS_DOMAIN_ID=5
# No ultralytics network calls (DNS probe, pip auto-install, update check, telemetry)
ENV YOLO_OFFLINE=1

# models/vision/yolov8n-pose.pt (and the exported .engine) are mounted here
VOLUME ["/app/models"]

WORKDIR /app/aims_ws

ENTRYPOINT ["/entrypoint.sh"]
CMD ["ros2", "launch", "vision_bringup", "vision.launch.py"]
