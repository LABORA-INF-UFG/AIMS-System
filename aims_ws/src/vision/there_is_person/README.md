# there_is_person

Node `there_is_person`: subscribes to `/estimation_points` and publishes
`/there_is_person` (`std_msgs/msg/Bool`, latched) with `false` at startup and then on change.

A person is present when, among the body keypoints 5..14 (shoulders, elbows, wrists, hips,
knees), at least `min_points` (6) are detected and their standard deviation is at least
`min_std` (0.045) on both x and y, which rejects tight clusters of false detections.
The rule lives in `there_is_person/presence.py` and is unit tested without ROS.
