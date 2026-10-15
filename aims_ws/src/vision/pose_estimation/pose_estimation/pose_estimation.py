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

import os

import cv2
from cv_bridge import CvBridge
from geometry_msgs.msg import Point
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import Image
from ultralytics import YOLO
from vision_interfaces.msg import PoseKeypoints

# COCO keypoint order used by YOLOv8-pose.
KEYPOINT_NAMES = [
    'nose', 'left_eye', 'right_eye', 'left_ear', 'right_ear',
    'left_shoulder', 'right_shoulder', 'left_elbow', 'right_elbow',
    'left_wrist', 'right_wrist', 'left_hip', 'right_hip',
    'left_knee', 'right_knee', 'left_ankle', 'right_ankle',
]

# Consecutive failed reads (about 3 s at 15 Hz) before the node gives up.
MAX_FAILED_READS = 50


def resolve_model_path(model_path, device):
    """Return the TensorRT engine next to model_path when running on GPU and it exists."""
    engine = os.path.splitext(model_path)[0] + '.engine'
    if device != 'cpu' and os.path.exists(engine):
        return engine
    return model_path


class PoseEstimation(Node):

    def __init__(self):
        super().__init__('pose_estimation')
        self.device = self.declare_parameter('device', 'cpu').value
        model_path = self.declare_parameter(
            'model_path', '/app/models/vision/yolov8n-pose.pt').value
        camera = self.declare_parameter('camera', '0').value
        width = self.declare_parameter('width', 352).value
        height = self.declare_parameter('height', 288).value
        fps = self.declare_parameter('fps', 30).value
        self.imgsz = self.declare_parameter('imgsz', 320).value
        self.conf_threshold = self.declare_parameter('conf_threshold', 0.4).value
        rate_hz = self.declare_parameter('rate_hz', 15.0).value
        self.publish_image = self.declare_parameter('publish_image', True).value

        model_path = resolve_model_path(model_path, self.device)
        if not os.path.exists(model_path):
            raise FileNotFoundError(f'Pose model not found: {model_path}')
        self.model = YOLO(model_path, task='pose')
        # Warm-up inference: fails fast on a bad device and tells which device is really used.
        self.model(np.zeros((height, width, 3), np.uint8), verbose=False,
                   imgsz=self.imgsz, device=self.device)
        self.get_logger().info(
            f'Model {model_path} running on device {self.model.predictor.device}')

        self.is_file = not camera.isdigit()
        if not self.is_file:
            self.cap = cv2.VideoCapture(int(camera), cv2.CAP_V4L2)
            self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            self.cap.set(cv2.CAP_PROP_FPS, fps)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        else:
            self.cap = cv2.VideoCapture(camera)
        if not self.cap.isOpened():
            self.get_logger().error(f'Could not open camera {camera}')
        else:
            self.get_logger().info(f'Reading frames from camera {camera}')

        self.bridge = CvBridge()
        self.points_pub = self.create_publisher(PoseKeypoints, '/estimation_points', 10)
        self.image_pub = self.create_publisher(
            Image, '/vision/image_raw',
            QoSProfile(depth=1, reliability=ReliabilityPolicy.BEST_EFFORT))
        self.failed_reads = 0
        self.timer = self.create_timer(1.0 / rate_hz, self.run_inference)

    def read_frame(self):
        ret, frame = self.cap.read()
        if not ret and self.is_file:
            # Loop video files so tests can run indefinitely.
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = self.cap.read()
        return frame if ret else None

    def run_inference(self):
        frame = self.read_frame()
        # Stamp at capture time (before inference); both messages share it.
        stamp = self.get_clock().now().to_msg()
        if frame is None:
            self.failed_reads += 1
            self.get_logger().warn('Failed to read a frame from the camera',
                                   throttle_duration_sec=5.0)
            if self.failed_reads >= MAX_FAILED_READS:
                self.get_logger().error(
                    f'{self.failed_reads} consecutive camera read failures, exiting')
                # rclpy.shutdown() from this callback left the process hanging in testing,
                # so leave hard; the launch then shuts down and Docker restarts the container.
                os._exit(1)
            return
        self.failed_reads = 0

        results = self.model(frame, verbose=False, imgsz=self.imgsz, device=self.device)

        msg = PoseKeypoints()
        msg.header.stamp = stamp
        msg.header.frame_id = 'camera'
        msg.names = KEYPOINT_NAMES
        msg.keypoints = [Point() for _ in KEYPOINT_NAMES]
        msg.confidence = [0.0] * len(KEYPOINT_NAMES)

        kpts = results[0].keypoints
        if kpts is not None and kpts.conf is not None and len(kpts.data) > 0:
            # Keep only the main person: the largest bounding box.
            boxes = results[0].boxes.xywh.cpu().numpy()
            main = int(np.argmax(boxes[:, 2] * boxes[:, 3]))
            xyn = kpts.xyn[main].cpu().numpy()
            conf = kpts.conf[main].cpu().numpy()
            for i, ((x, y), c) in enumerate(zip(xyn, conf)):
                if c >= self.conf_threshold:
                    msg.keypoints[i] = Point(x=float(x), y=float(y))
                    msg.confidence[i] = float(c)

        self.points_pub.publish(msg)
        if self.publish_image:
            image = self.bridge.cv2_to_imgmsg(frame, encoding='bgr8')
            image.header = msg.header
            self.image_pub.publish(image)

    def destroy_node(self):
        self.cap.release()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = PoseEstimation()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
