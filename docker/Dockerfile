FROM ros:foxy

SHELL [ "/bin/bash", "-c" ]

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    . /opt/ros/foxy/setup.bash && \
    echo "source /opt/ros/foxy/setup.bash" >> ~/.bashrc && \
    echo "source /usr/share/colcon_argcomplete/hook/colcon-argcomplete.bash" >> ~/.bashrc && \
    mkdir -p /app/aims_ws/src/csi/ && \
    mkdir -p /app/aims_ws/src/custom_interfaces && \
    mkdir -p /app/aims_ws/src/there_is_person

COPY ./aims_ws/src/csi/package.xml app/aims_ws/src/csi/
COPY ./aims_ws/src/there_is_person/package.xml app/aims_ws/src/there_is_person/
COPY ./aims_ws/src/custom_interfaces/package.xml app/aims_ws/src/custom_interfaces/
COPY ./aims_ws/src/requirements.txt app/aims_ws/src/

RUN cd /app/aims_ws/ && \
    apt-get update && \
    apt-get install -y ros-dev-tools ros-${ROS_DISTRO}-rosbridge-server neovim unzip wget python3-pip liboctave-dev && \
    rosdep update --include-eol-distros && \
    rosdep install -i --from-path src --rosdistro ${ROS_DISTRO} -y

RUN octave --eval "pkg install -forge control signal" && \
    echo "pkg load signal" >> /usr/share/octave/site/m/startup/octaverc

RUN python3 -m pip install -r /app/aims_ws/src/requirements.txt

COPY ./ /app/
WORKDIR /app/aims_ws

RUN . /opt/ros/foxy/setup.bash && \
    colcon build && \
    . /app/aims_ws/install/local_setup.bash && \
    echo "source /app/aims_ws/install/local_setup.bash" >> ~/.bashrc

ENV AIMS=/app/
ENV KERAS_APNEA_MODEL=/app/aims_ws/src/csi/csi/resource/apenaDetection_AIMS_model1.h5
ENV RMW_IMPLEMENTATION=rmw_fastrtps_cpp
ENV FASTRTPS_DEFAULT_PROFILES_FILE=/app/aims_ws/src/fastdds_profile.xml
ENV ROS_DOMAIN_ID=5

ENTRYPOINT [ "/app/docker/entrypoint.sh" ]
CMD [ "/bin/bash", "-c", "ros2 launch csi aims_core_launch.py" ]
