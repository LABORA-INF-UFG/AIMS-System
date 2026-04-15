import os

from oct2py import Oct2Py

from csi.libs.OctaveCardiofi import OctaveCardiofiWindow
from custom_interfaces.msg import PktCSI
from custom_interfaces.msg import OctaveCardiofi
import rclpy
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node


class OctaveCardiofiPublisher(Node):
    def __init__(self) -> None:
        super().__init__('octave_cardiofi_publisher')

        self.subscriber_callback_group = MutuallyExclusiveCallbackGroup()
        self.pkt_subscriber = self.create_subscription(
            PktCSI,
            'pktcsi',
            self.listener_callback,
            100,
            callback_group=self.subscriber_callback_group)

        self.publisher_callback_group = MutuallyExclusiveCallbackGroup()
        self.publisher = self.create_publisher(
            OctaveCardiofi,
            'octave_cardiofi',
            10)
        timer_period = 1
        self.timer = self.create_timer(
            timer_period,
            self.publisher_callback,
            callback_group=self.publisher_callback_group)

        self.cardiofi_windows = OctaveCardiofiWindow()
        self.oc = Oct2Py()
        self.oc.addpath(f'{os.getenv("AIMS")}/aims_ws/src/csi/csi/libs')
        self.previous_breath = [0] * 6
        self.previous_heart = [0] * 6
        self.counter = 0
        self.window_size = 15 * 100  # 15 seconds * 100 hertz

    def listener_callback(self, msg: PktCSI) -> None:
        self.get_logger().info(f'Reading pktcsi: {msg.pktid}')
        self.cardiofi_windows.insert(msg)

    def publisher_callback(self) -> None:
        if self.counter == 0:
            window = self.cardiofi_windows.amplitude_windows[0].get()
        elif self.counter == 1:
            window = self.cardiofi_windows.amplitude_windows[1].get()
        elif self.counter == 2:
            window = self.cardiofi_windows.amplitude_windows[2].get()
        elif self.counter == 3:
            window = (self.cardiofi_windows.phase_windows[0].get()
                      - self.cardiofi_windows.phase_windows[1].get())
        elif self.counter == 4:
            window = (self.cardiofi_windows.phase_windows[1].get()
                      - self.cardiofi_windows.phase_windows[2].get())
        elif self.counter == 5:
            window = (self.cardiofi_windows.phase_windows[2].get()
                      - self.cardiofi_windows.phase_windows[0].get())
        else:
            raise RuntimeError(f'Unexpected value for self.counter: '
                               f'{self.counter}')

        breath_rate, heart_rate = self.oc.slidingEstimateVital(
            self.window_size,
            window,
            self.counter + 1,
            self.previous_breath,
            self.previous_heart,
            nout=2
        )

        octave_cardiofi_msg = OctaveCardiofi()
        octave_cardiofi_msg.breath = breath_rate
        octave_cardiofi_msg.heart = heart_rate
        self.get_logger().info(f'Breath: {breath_rate} \\ Heart: {heart_rate}')
        self.publisher.publish(octave_cardiofi_msg)

        self.previous_breath[self.counter] = breath_rate
        self.previous_heart[self.counter] = heart_rate
        self.counter = (self.counter + 1) % 6


def main(args=None) -> None:
    rclpy.init(args=args)

    octave_cardiofi_publisher = OctaveCardiofiPublisher()
    executor = MultiThreadedExecutor()
    executor.add_node(octave_cardiofi_publisher)
    executor.spin()

    octave_cardiofi_publisher.oc.exit()
    octave_cardiofi_publisher.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
