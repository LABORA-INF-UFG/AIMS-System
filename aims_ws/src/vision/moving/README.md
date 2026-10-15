# Motion Detection

## Index
- [Introduction](#introduction)
- [Overall Operation](#overall-operation)
- [Initialization](#initialization)
- [People Detection](#people-detection)
- [Collection of Joint Points](#collection-of-joint-points)
- [Movement Verification](#movement-verification)

## Introduction

This script was developed for motion detection based on the estimated joint coordinates of a human pose. The script is designed to operate in the context of the ROS 2 system (Robot Operating System 2) and uses ROS messages for communication and coordination with other nodes.

## Overall Operation

The script runs as a ROS 2 node called "Moving" and performs the following main tasks:

### Initialization

- ROS 2 Node Initialization: The ROS 2 node is initialized with the name "Moving" for communication within the ROS 2 system.

- Setup of Publishers and Subscribers: The script sets up a publisher to send boolean messages indicating whether motion is detected.

- Initialization of Parameters: The script defines parameters related to the standard deviation of joint points to check for movement. These standard deviations were collected through testing. Using the TensorFlow Lite model from the "Pose_Estimation" node, joint point samples were collected with the person standing still, and subsequently, the standard deviation of each joint was calculated.

### People Detection

The script receives information about people detection on a ROS topic named "/there_is_person". This is done by the `callback_person(msg)` function, which is aware of the state of people detection.

### Collection of Joint Points

The script collects relevant joint points from messages of estimated joint points on a ROS topic named "/estimation_points". The collected joint points are those considered "important" for people detection, such as shoulders, elbows, hips, and knees.

- The `complete(msg)` function collects the joint points, waiting until all relevant lists of points are filled with 3 elements.

### Movement Verification

After the initial collection of joint points, the script verifies movement based on the standard deviation of the x and y coordinates of the points. The verification is performed by the `check_movement(msg)` function.

- The standard deviation of coordinates is compared with predefined standard deviation values to determine if there is significant movement at each joint point.

- If movement is detected, a boolean message is published on the "/is_moving" topic.

