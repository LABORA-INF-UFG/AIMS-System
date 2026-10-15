import time

from csi.libs.CameraHeartControl import CameraHeartControl
from custom_interfaces.msg import HeartControl
import cv2
import rclpy
from rclpy.node import Node


class HeartControlPublisher(Node):
    def __init__(self):
        super().__init__('heart_control_publisher')
        self.publisher_ = self.create_publisher(
                HeartControl,
                'heart_control',
                10)
        timer_period = (1 / 30)
        self.timer = self.create_timer(timer_period, self.timer_callback)
        self.video_capture = CameraHeartControl()
        self.video_stream = self.video_capture.create_stream()
        self.repeated_beat = False

        self.capture_area()

    def capture_area(self):
        _ = self.video_capture.get_frame(self.video_stream)
        self.video_capture.disable_auto_exposure(self.video_stream)
        while (cv2.waitKey(1) & 0xFF) != ord('\r'):
            frame = self.video_capture.get_frame(self.video_stream)
            self.video_capture.select_area(window_name='SelectArea')
            self.video_capture.show_frame(frame, window_name='SelectArea')
        cv2.destroyAllWindows()

    def timer_callback(self):
        frame = self.video_capture.get_frame(self.video_stream)
        bw_frame = self.video_capture.to_frame_black_white(frame)
        self.video_capture.show_frame(bw_frame, window_name='HeartRate')
        cv2.waitKey(1)

        beat_detected = self.video_capture.detect_beat(bw_frame,
                                                       detect_color=255,
                                                       detect_thresh=0.7)

        if beat_detected and not self.repeated_beat:
            heart_control_msg = HeartControl()
            heart_control_msg.timestamp = time.time_ns()
            self.publisher_.publish(heart_control_msg)
            self.get_logger().info(f'Publishing HeartControl beat: '
                                   f'{heart_control_msg.timestamp}')
            self.repeated_beat = True

        if not beat_detected:
            self.repeated_beat = False


def main(args=None):
    rclpy.init(args=args)
    heart_control_publisher = HeartControlPublisher()
    rclpy.spin(heart_control_publisher)
    heart_control_publisher.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
