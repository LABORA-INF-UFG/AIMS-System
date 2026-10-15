# Copyright 2026 Lucas Reis
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import numpy as np

# Body keypoints tracked: shoulders, elbows, wrists, hips and knees (COCO indices 5..14).
JOINT_NAMES = [
    'left_shoulder', 'right_shoulder', 'left_elbow', 'right_elbow',
    'left_wrist', 'right_wrist', 'left_hip', 'right_hip',
    'left_knee', 'right_knee',
]
FIRST_JOINT = 5


class KalmanFilterKeypoint:
    """Constant-velocity Kalman filter of one keypoint, state [x, y, vx, vy]."""

    def __init__(self, x_init, y_init, dt=1.0 / 30.0):
        self.dt = dt
        self.x = np.array([[x_init], [y_init], [0.0], [0.0]], dtype=np.float32)

        # State transition matrix F
        self.F = np.array([
            [1, 0, self.dt, 0],
            [0, 1, 0, self.dt],
            [0, 0, 1, 0],
            [0, 0, 0, 1]
        ], dtype=np.float32)

        # Measurement matrix H
        self.H = np.array([
            [1, 0, 0, 0],
            [0, 1, 0, 0]
        ], dtype=np.float32)

        # Covariance P: small initial position uncertainty, large velocity uncertainty (as SORT)
        self.P = np.diag([0.01, 0.01, 10.0, 10.0]).astype(np.float32)

        # Process noise covariance Q
        q_pos = 0.0001
        q_vel = 0.01
        self.Q = np.diag([q_pos, q_pos, q_vel, q_vel]).astype(np.float32)

        # Measurement noise covariance R
        r_val = 0.001
        self.R = np.diag([r_val, r_val]).astype(np.float32)

    def predict(self, dt=None):
        if dt is not None and dt > 0.0:
            self.dt = dt
            self.F[0, 2] = dt
            self.F[1, 3] = dt
        self.x = np.dot(self.F, self.x)
        self.P = np.dot(np.dot(self.F, self.P), self.F.T) + self.Q
        return self.x

    def update(self, z):
        # z is [[mx], [my]]
        y = z - np.dot(self.H, self.x)
        S = np.dot(np.dot(self.H, self.P), self.H.T) + self.R
        K = np.dot(np.dot(self.P, self.H.T), np.linalg.inv(S))
        self.x = self.x + np.dot(K, y)
        self.P = np.dot(np.eye(4) - np.dot(K, self.H), self.P)
        return self.x

    def speed(self):
        return float(np.hypot(self.x[2, 0], self.x[3, 0]))


class MotionTracker:
    """Track the body keypoints with one Kalman filter each and flag the fast ones."""

    def __init__(self, velocity_threshold=0.15, max_lost_frames=5):
        self.velocity_threshold = velocity_threshold
        self.max_lost_frames = max_lost_frames
        self.reset()

    def reset(self):
        self.trackers = [None] * len(JOINT_NAMES)
        self.lost_counts = [0] * len(JOINT_NAMES)

    def update(self, keypoints, confidence, dt):
        """
        Feed one frame and return {joint name: speed} of the joints above the threshold.

        keypoints holds 17 normalized (x, y) pairs and confidence one value per keypoint
        (0 when not detected); dt is the time since the previous frame in seconds.
        """
        moving = {}
        for idx, name in enumerate(JOINT_NAMES):
            x, y = keypoints[FIRST_JOINT + idx]
            tracker = self.trackers[idx]

            if confidence[FIRST_JOINT + idx] <= 0.0:
                # Not detected in this frame: only predict, drop the track after too many misses.
                if tracker is not None:
                    tracker.predict(dt=dt)
                    self.lost_counts[idx] += 1
                    if self.lost_counts[idx] > self.max_lost_frames:
                        self.trackers[idx] = None
                continue

            if tracker is None:
                tracker = self.trackers[idx] = KalmanFilterKeypoint(x, y, dt=dt)
            else:
                tracker.predict(dt=dt)
                tracker.update(np.array([[x], [y]], dtype=np.float32))
            self.lost_counts[idx] = 0

            speed = tracker.speed()
            if speed > self.velocity_threshold:
                moving[name] = speed
        return moving
