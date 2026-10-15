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

import time

import cv2
from cv_bridge import CvBridge
import message_filters
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import CompressedImage, Image
from vision_interfaces.msg import PoseKeypoints

# Skeleton edges between COCO body keypoints (shoulders, elbows, wrists, hips, knees).
EDGES = [
    (5, 7), (7, 9), (6, 8), (8, 10),  # arms
    (5, 11), (6, 12), (11, 13), (12, 14),  # torso sides and thighs
    (5, 6), (11, 12),  # shoulders and hips
]
GREEN = (0, 255, 0)


def draw_keypoints(frame, msg):
    """Draw the detected body keypoints of msg and the skeleton lines on frame."""
    height, width = frame.shape[:2]
    points = {
        i: (int(msg.keypoints[i].x * width), int(msg.keypoints[i].y * height))
        for i in range(5, 15) if msg.confidence[i] > 0.0
    }
    for point in points.values():
        cv2.circle(frame, point, 8, GREEN, -1)
    for a, b in EDGES:
        if a in points and b in points:
            cv2.line(frame, points[a], points[b], GREEN, 2)
    return frame


class Visualization(Node):

    def __init__(self):
        super().__init__('visualization')
        self.period = 1.0 / self.declare_parameter('image_rate_hz', 5.0).value
        self.jpeg_quality = self.declare_parameter('jpeg_quality', 70).value
        self.show_window = self.declare_parameter('show_window', False).value

        self.bridge = CvBridge()
        self.last_publish = 0.0
        self.publisher = self.create_publisher(CompressedImage, '/vision_image', 1)
        points_sub = message_filters.Subscriber(self, PoseKeypoints, '/estimation_points')
        image_sub = message_filters.Subscriber(
            self, Image, '/vision/image_raw',
            qos_profile=QoSProfile(depth=1, reliability=ReliabilityPolicy.BEST_EFFORT))
        # Frames and keypoints share the exact same header.stamp.
        self.sync = message_filters.TimeSynchronizer([points_sub, image_sub], 10)
        self.sync.registerCallback(self.callback)
        self.get_logger().info('visualization node started')

    def callback(self, points_msg, image_msg):
        now = time.monotonic()
        due = now - self.last_publish >= self.period
        if not (due or self.show_window):
            return

        frame = draw_keypoints(
            self.bridge.imgmsg_to_cv2(image_msg, desired_encoding='bgr8'), points_msg)

        if due:
            self.last_publish = now
            ok, jpeg = cv2.imencode(
                '.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality])
            if ok:
                msg = CompressedImage(header=image_msg.header, format='jpeg')
                msg.data = jpeg.tobytes()
                self.publisher.publish(msg)

        if self.show_window:
            cv2.imshow('Pose Detection', frame)
            cv2.waitKey(1)


def main(args=None):
    rclpy.init(args=args)
    node = Visualization()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
