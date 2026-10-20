# moving

Node `moving`: while `/person_present` is true, tracks the body keypoints 5..14 of
`/estimation_points` with one constant-velocity Kalman filter each, using the header stamps
for the time step. It publishes `/is_moving` (`std_msgs/msg/Bool`, latched) with `false` at
startup and then on change: true when any keypoint speed exceeds `velocity_threshold`
(normalized image units per second), and it stays true for `hold_sec` (1.0 s) after the last
such frame. A keypoint missing for more than `max_lost_frames`
frames loses its track; all tracks reset (and `/is_moving` goes false) when the person leaves.
The filter lives in `moving/tracker.py` and is unit tested without ROS.
