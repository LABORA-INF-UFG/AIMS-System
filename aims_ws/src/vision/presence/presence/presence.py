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

from .rule import Hysteresis, is_person

LATCHED = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)


class Presence(Node):

    def __init__(self):
        super().__init__('presence')
        self.min_points = self.declare_parameter('min_points', 6).value
        self.min_std = self.declare_parameter('min_std', 0.045).value
        # One frame with a low-confidence limb must not flip presence (and reset `moving`).
        self.hysteresis = Hysteresis(self.declare_parameter('min_frames', 4).value)

        self.publisher = self.create_publisher(Bool, '/person_present', LATCHED)
        self.create_subscription(PoseKeypoints, '/estimation_points', self.callback, 10)
        self.state = False
        self.publisher.publish(Bool(data=False))
        self.get_logger().info('presence node started')

    def callback(self, msg):
        keypoints = [(p.x, p.y) for p in msg.keypoints]
        detected = self.hysteresis.update(
            is_person(keypoints, msg.confidence, self.min_points, self.min_std))
        if detected != self.state:
            self.state = detected
            self.publisher.publish(Bool(data=detected))
            self.get_logger().info(f'Person detected: {detected}')


def main(args=None):
    rclpy.init(args=args)
    node = Presence()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
