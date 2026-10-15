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

import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile
from std_msgs.msg import Bool
from vision_interfaces.msg import PoseKeypoints

from .tracker import MotionHold, MotionTracker

LATCHED = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
DEFAULT_DT = 1.0 / 15.0


class Moving(Node):

    def __init__(self):
        super().__init__('moving')
        self.tracker = MotionTracker(
            velocity_threshold=self.declare_parameter('velocity_threshold', 0.15).value,
            max_lost_frames=self.declare_parameter('max_lost_frames', 5).value)
        # Limb speed crosses the threshold back and forth within one movement.
        self.hold = MotionHold(self.declare_parameter('hold_sec', 1.0).value)

        self.publisher = self.create_publisher(Bool, '/is_moving', LATCHED)
        self.create_subscription(PoseKeypoints, '/estimation_points', self.callback_points, 10)
        self.create_subscription(Bool, '/there_is_person', self.callback_person, LATCHED)
        self.is_person = False
        self.is_moving = False
        self.last_stamp = None
        self.publisher.publish(Bool(data=False))
        self.get_logger().info('moving node started')

    def set_moving(self, moving):
        if moving != self.is_moving:
            self.is_moving = moving
            self.publisher.publish(Bool(data=moving))

    def callback_person(self, msg):
        self.is_person = msg.data
        if not self.is_person:
            # Restart tracking from scratch when the person leaves the frame.
            self.tracker.reset()
            self.hold.reset()
            self.last_stamp = None
            self.set_moving(False)

    def callback_points(self, msg):
        if not self.is_person:
            return

        stamp = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
        dt = DEFAULT_DT if self.last_stamp is None else stamp - self.last_stamp
        if dt <= 0.0 or dt > 1.0:
            dt = DEFAULT_DT
        self.last_stamp = stamp

        keypoints = [(p.x, p.y) for p in msg.keypoints]
        moving = self.tracker.update(keypoints, msg.confidence, dt)
        for name, speed in moving.items():
            self.get_logger().debug(f'{name} is moving (speed: {speed:.4f})')
        self.set_moving(self.hold.update(bool(moving), stamp))


def main(args=None):
    rclpy.init(args=args)
    node = Moving()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
