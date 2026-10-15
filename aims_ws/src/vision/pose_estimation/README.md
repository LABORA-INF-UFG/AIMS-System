# Pose Estimation

## Index
- [Introduction](#introduction)
- [init](#def-__init__self)
- [get_frame](#def-get_frameself)
- [estimation_pose](#def-estimation_poseself)

## Introduction

This script is designed for pose estimation using the TensorFlow library and ROS 2 (Robot Operating System 2). It captures video from the webcam, performs real-time pose inference using a pre-trained neural network model, and publishes the estimated joint points as ROS messages.

## `def __init__(self)`

The `__init__(self)` function is the constructor of the `Pose_Estimation` class. It is called when an object of this class is created. This function is responsible for initializing various essential settings and resources necessary for real-time pose estimation. Here are some of the main tasks performed in the constructor:

- ROS 2 Node Initialization: A ROS 2 node is created with the name "Pose_Estimation". This allows the code to communicate with the ROS 2 system.

- GPU Configuration (if available): Checks for the availability of GPUs and, if present, configures TensorFlow to use the first GPU and allocate memory as needed for the neural network model.

- Video Capture Initialization: Configures webcam video capture, setting parameters such as resolution and frame rate. This allows the retrieval of video frames from the webcam for further processing.

- Initialization of Publishers and Variables: Prepares the code to publish pose estimation information as ROS messages. Additionally, initializes variables to store information about estimated joint points.

- Creation of Timers: Defines two timers, one for capturing frames from the webcam (`get_frame`) and another for performing pose estimation (`estimation_pose`). These timers ensure that the corresponding functions are called periodically.

## `def get_frame(self)`

The `get_frame(self)` function is responsible for capturing frames from the webcam and preparing them for pose estimation. It is called periodically by the timer defined in the constructor. Here is an overview of the tasks performed in this function:

- Frame Capture: Reads a frame from the webcam using the OpenCV library (`cv2`). This frame serves as input for pose estimation.

- Frame Preprocessing: Resizes the frame to the size expected by the neural network model and normalizes pixel values to the range between -1 and 1.

- Sending the Frame to the Model: Sends the normalized frame to the neural network model using TensorFlow. The model performs inference to estimate the pose's joint points.

- Obtaining Coordinates: Obtaining the coordinates of the estimated joint points after the model's inference.

## `def estimation_pose(self)`

The `estimation_pose(self)` function is called periodically by the second timer defined in the constructor. It is responsible for estimating the pose based on the coordinates of the joint points obtained in the `get_frame` function. Here is an overview of the tasks performed in this function:

- Pose Estimation: For each joint point (such as nose, eyes, shoulders, etc.), the function checks the confidence of the estimation. If the confidence is high (>= 0.3), the coordinates of the joint point are stored in the ROS message. Otherwise, the coordinates are set to (0, 0), indicating that the joint point was not confidently detected.

- Frame Conversion to ROS Message: Converts the image frame from OpenCV format to ROS message format using the `CvBridge` library. This allows the image to be transmitted as part of the ROS message.

- Message Publication: Publishes the message with the estimated joint points and the image frame on the "estimation_points" topic. This message will be used by other nodes for people detection and subsequently, motion detection.
