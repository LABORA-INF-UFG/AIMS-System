# AIMS Project

## Motion

- [Pose Estimation README](pose_estimation/README.md)
- [Visualization README](visualization/README.md)
- [Moving README](moving/README.md)
- [There is Person README](there_is_person/README.md)

## Index

- [Introduction](#introduction)
- [Features](#features)
- [Usage](#usage)

## Introduction
This project aims to extract various information that can be obtained through framing a person in the camera. The project was built on the NVIDIA Jetson Nano board, although an original NVIDIA Jetpack was not used (due to the lack of new versions of the Jetpack for this embedded computer). Instead, the project utilizes the following project by the author **Q-engineering**, which offers a modified version of a Jetpack for Jetson: [Jetson_Nano_Ubuntu_20.04](https://github.com/Qengineering/Jetson-Nano-Ubuntu-20-image). The foundation of this project is built using TensorFlow and ROS2 and is currently capable of providing the following information:

- Detection of a person in the frame
- Plotting the frame observed by the camera
- Checking for movement performed by a person based solely on the points of the joints

It is also worth noting that we are using a lightweight version of TensorFlow to achieve better performance with lower computational costs. Currently, this project runs at about 8Hz on the aforementioned Jetson Nano.

## Features

Each ROS2 package in the project has its functionality, and within them, there is a README.md explaining this functionality in detail. Here is a summary of each package:

| Package Name    | Description                                |
| --------------- | ------------------------------------------ |
| pose_estimation        | Main package. Loads the TensorFlow model and publishes the observed frame along with the detected joint points to a ROS2 topic.   |
| visualization   | Upon receiving the topic from the "pose_estimation" package, it plots the observed frame.     |
| there_is_person | Upon receiving the topic from the "pose_estimation" package, checks if there is a person in the frame and publishes this response on a ROS2 topic containing a boolean message.    |
| moving          | Upon receiving the topic from the "pose_estimation" package, checks if the joint points observed in the current frame have produced movement compared to the previous frame.      |
| bringup         | Package that stores the launch file     |
| weights         | Directory that stores the weights of the TensorFlow lite  |
| trt_interfaces  | Package that contains the custom ROS2 message for the topic of the "pose_estimation" package   |

## Usage

After cloning the ROS2 packages from this repository and executing the following commands:

```bash
colcon build --symlink-install
source install/setup.bash
```
Execute the following ROS2 command to run the project:

```bash
ros2 launch bringup pose_estimation.launch.xml
