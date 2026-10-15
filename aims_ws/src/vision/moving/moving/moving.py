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

from interfaces.msg import ArticulationPoints
from cv_bridge import CvBridge
from std_msgs.msg import Bool
from rclpy.node import Node
import numpy as np
import rclpy
import cv2


class KalmanFilterKeypoint:

    def __init__(self, x_init, y_init, dt=1.0/30.0):
        self.dt = dt
        # State vector: [x, y, vx, vy]^T
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

        # Covariance matrix P
        # Initial position uncertainty is small, velocity uncertainty is large (as per SORT)
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


class Moving(Node):

    def __init__(self):
        super().__init__('Moving')
        self.get_logger().info('Moving node initialized.')

        self.Hz = 30
        self.publisher_ = self.create_publisher(Bool, '/is_moving', self.Hz)
        self.sub_points = self.create_subscription(
            ArticulationPoints,
            '/estimation_points',
            self.callback_moving,
            self.Hz
        )
        self.sub_person = self.create_subscription(
            Bool,
            '/there_is_person',
            self.callback_person,
            self.Hz
        )
        self.msg = Bool()
        self.msg.data = False

        self.name_joints = [
            'left_shoulder', 'right_shoulder', 'left_elbow', 'right_elbow',
            'left_wrist', 'right_wrist', 'left_hip', 'right_hip',
            'left_knee', 'right_knee'
        ]

        # Trackers for the 10 joints: left_shoulder, right_shoulder, etc.
        self.joint_trackers = [None for _ in range(10)]
        self.lost_counts = [0 for _ in range(10)]
        self.max_lost_frames = 5
        self.velocity_threshold = 0.15

        # Debug visualization parameters
        self.declare_parameter('debug_viz', True)
        self.bridge = CvBridge()
        self.window_open = False

        self.is_person = False
        self.last_time = None

    def callback_moving(self, msg):
        if self.is_person is False:
            return

        self.check_movement(msg)

    def callback_person(self, msg):
        self.is_person = msg.data
        if not self.is_person:
            # Reset trackers when there is no person detected
            self.joint_trackers = [None for _ in range(10)]
            self.lost_counts = [0 for _ in range(10)]
            self.last_time = None
            if self.window_open:
                cv2.destroyAllWindows()
                self.window_open = False

    def check_movement(self, msg):
        currently_moving = False

        # Read debug visualization parameter
        debug_viz = self.get_parameter(
            'debug_viz'
        ).get_parameter_value().bool_value

        cv_image = None
        if debug_viz and msg.image is not None:
            try:
                cv_image = self.bridge.imgmsg_to_cv2(
                    msg.image, desired_encoding='bgr8'
                )
            except Exception as e:
                self.get_logger().error(f'Failed to convert image: {e}')

        # Dynamic dt calculation
        current_time = self.get_clock().now()
        if self.last_time is None:
            dt = 1.0 / self.Hz
        else:
            dt = (current_time - self.last_time).nanoseconds / 1e9
            if dt <= 0.0 or dt > 1.0:
                dt = 1.0 / self.Hz
        self.last_time = current_time

        for i in range(0, 17):
            if i >= 5 and i <= 14:
                idx = i - 5
                x, y = msg.coordinates[i].x, msg.coordinates[i].y

                if x == 0.0 and y == 0.0:
                    # Point not detected in this frame
                    if self.joint_trackers[idx] is not None:
                        # Only predict state
                        self.joint_trackers[idx].predict(dt=dt)
                        self.lost_counts[idx] += 1
                        if self.lost_counts[idx] > self.max_lost_frames:
                            self.joint_trackers[idx] = None
                    continue

                # Point is detected
                if self.joint_trackers[idx] is None:
                    # Initialize Kalman Filter
                    self.joint_trackers[idx] = KalmanFilterKeypoint(
                        x, y, dt=dt
                    )
                    self.lost_counts[idx] = 0
                else:
                    # Predict and Update
                    self.joint_trackers[idx].predict(dt=dt)
                    self.joint_trackers[idx].update(
                        np.array([[x], [y]], dtype=np.float32)
                    )
                    self.lost_counts[idx] = 0

                # Get estimated velocity components
                vx = self.joint_trackers[idx].x[2, 0]
                vy = self.joint_trackers[idx].x[3, 0]
                speed = np.sqrt(vx**2 + vy**2)

                # Check speed against threshold
                is_moving = speed > self.velocity_threshold
                if is_moving:
                    self.get_logger().info(
                        f'{self.name_joints[idx]} is moving '
                        f'(speed: {speed:.4f})'
                    )
                    currently_moving = True

                # Draw debug information on image if active
                if cv_image is not None:
                    h, w, _ = cv_image.shape
                    # Convert normalized position to pixel coordinates
                    px = int(x * w)
                    py = int(y * h)

                    # Draw keypoint circle
                    cv2.circle(cv_image, (px, py), 4, (0, 255, 0), -1)

                    # Draw velocity arrow (scale factor 150 pixels per unit/sec)
                    arrow_scale = 150.0
                    ex = int(px + vx * arrow_scale)
                    ey = int(py + vy * arrow_scale)
                    color = (0, 0, 255) if is_moving else (255, 0, 0)
                    thickness = 2 if is_moving else 1
                    cv2.arrowedLine(
                        cv_image, (px, py), (ex, ey), color, thickness,
                        tipLength=0.4
                    )

        if cv_image is not None:
            cv2.imshow('Moving Debug Visualization', cv_image)
            cv2.waitKey(1)
            self.window_open = True
        elif self.window_open:
            cv2.destroyAllWindows()
            self.window_open = False

        if currently_moving != self.msg.data:
            self.msg.data = currently_moving
            self.publisher_.publish(self.msg)

    def destroy_node(self):
        if self.window_open:
            cv2.destroyAllWindows()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = Moving()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()