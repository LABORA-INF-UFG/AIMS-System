# presence

Node `presence`: subscribes to `/estimation_points` and publishes
`/person_present` (`std_msgs/msg/Bool`, latched) with `false` at startup and then on change.

A person is present when, among the body keypoints 5..14 (shoulders, elbows, wrists, hips,
knees), at least `min_points` (6) are detected and their standard deviation is at least
`min_std` (0.045) on both x and y, which rejects tight clusters of false detections. The
published state changes only after `min_frames` (4) consecutive frames disagree with it, so one
frame with a low-confidence limb does not flip presence.
The rule lives in `presence/rule.py` and is unit tested without ROS.

Imported from MyCareBed as `there_is_person` (topic `/there_is_person`) and renamed.
