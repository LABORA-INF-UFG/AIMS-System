# There is person

## Index
- [Introduction](#introduction)
- [def__init__](#def-__init__self)
- [def person_detection](#def-person_detectionself-msg)

## Introduction

The script performs people detection based on the estimated joint coordinates of a pose. It utilizes information received on a ROS 2 topic (named "articulation_points") to determine if a person is present in the scene based on the analysis of these points. To confirm the presence of a detected person, the following checks are used:

- Number of detected points greater than or equal to 6
    - Of the 10 joint points we attempt to detect, if 6 are found, this condition becomes true.
- Standard deviation of all detected points greater than 0.045
    - This condition was created to ensure a minimum spacing between the detected points to be considered a person in the frame. This value of 0.045 was determined through testing.

## `def __init__(self)`

The `__init__(self)` function is the constructor of the `Person_Detection` class. It is called when an object of this class is created. This function is responsible for initializing various settings and resources necessary for people detection. Here are some of the main tasks performed in the constructor:

- ROS 2 Node Initialization: A ROS 2 node is created with the name "Person_Detection". This allows the code to communicate with the ROS 2 system.

- Initialization of Publishers and Variables: Prepares the code to publish information about people detection as ROS messages. Additionally, initializes a boolean variable to indicate if a person has been detected.

- Creation of a Subscription Topic: Defines a subscription topic to receive messages from the "/estimation_points" topic. This allows the code to obtain information about the estimated joint points.

## `def person_detection(self, msg)`

The `person_detection(self, msg)` function is called when a message is received from the "/estimation_points" topic. It is responsible for checking if a person has been detected based on the received information. Here is an overview of the tasks performed in this function:

- Extraction of Points: The function extracts relevant joint points from the received message.

- Calculation of Standard Deviation: The function calculates the standard deviation of the x and y coordinates of the extracted joint points. This helps evaluate the dispersion of the points.

- Person Detection Verification: Based on the number of relevant joint points and the calculated standard deviations, the function determines if a person has been detected.

- Result Publication: If the person detection changes compared to the last check, the function publishes a boolean message on the "/there_is_person" topic. This message indicates whether a person has been detected.
