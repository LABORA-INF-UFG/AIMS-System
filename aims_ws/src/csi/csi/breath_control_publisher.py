import time

import pynput

from custom_interfaces.msg import BreathControl
import rclpy
from rclpy.node import Node

class BreathControlPublisher(Node):
    def __init__(self) -> None:
        super().__init__('breath_control_publisher')
        self._publisher = self.create_publisher(
                BreathControl,
                'breath_control',
                10)
        self.timer = self.create_timer(0, self.timer_callback)

    def timer_callback(self) -> None:
        self.get_logger().info('Starting mouse capture')
        with pynput.mouse.Listener(on_click=self.on_click) as listener:
            listener.join()

    def on_click(self, x, y, button, pressed) -> None:
        breath_control_msg = BreathControl()
        breath_control_msg.timestamp = time.time_ns()
        if not pressed:  # Register on relase
            self._publisher.publish(breath_control_msg)
            self.get_logger().info(f'Publishing BreathControl message: '
                                   f'{breath_control_msg.timestamp}')


def main(args=None):
    rclpy.init(args=args)
    breath_control_publisher = BreathControlPublisher()
    rclpy.spin_once(breath_control_publisher)
    rclpy.shutdown()
