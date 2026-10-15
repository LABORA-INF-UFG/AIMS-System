# Visualization

## Index
- [Introduction](#introduction)
- [Overall Operation](#overall-operation)
- [Initialization](#initialization)
- [Processing of Joint Points](#processing-of-joint-points)
- [Real-Time Visualization](#real-time-visualization)

## Introduction

This script was developed for the visualization of joint points in an image based on information received from a ROS 2 topic (Robot Operating System 2). The script subscribes to the "/estimation_points" topic containing joint points and the observed frame, and publishes the combination of this information on the "/visao_image" topic.

## Overall Operation

The script runs as a ROS 2 node named "Visualization" and performs the following main tasks:

### Initialization

- ROS 2 Node Initialization: The ROS 2 node is initialized with the name "Visualization" for communication within the ROS 2 system.

- Setup of Subscriptions and Publishers: The script creates a subscription to receive messages of estimated joint points from the "/estimation_points" topic. Additionally, it sets up a publisher to send an image containing highlighted joint points on the "/visao_image" topic.

- Initialization of Data Structures: The script creates data structures to store received information and process the output image.

### Processing of Joint Points

The script receives information about estimated joint points and the observed frame in a ROS message. This is done by the `callback(msg)` function, which extracts relevant joint points from the message and positions them on an image.

- Joint points are extracted from the message, and their coordinates are used to highlight these points on the original image.

- Lines are drawn between the joint points, highlighting the left and right parts of the body, as well as some connections between the parts.

- The resulting image with highlighted joint points is published on the "/visao_image" topic for other nodes in the ROS 2 system to use.

### Real-Time Visualization

The script also displays the resulting image with highlighted joint points in a real-time visualization window using the OpenCV library. The image is continuously updated as new joint point messages are received.
