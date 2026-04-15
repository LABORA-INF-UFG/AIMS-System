import os
import time

from keras.models import load_model

from csi.libs.ApneaDetectionAI import ApneaDetectionAI
from custom_interfaces.msg import ApneaAI
from custom_interfaces.msg import PktCSI
import rclpy
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node


class ApneaAIPublisher(Node):
    def __init__(self):
        super().__init__('apnea_ai_publisher')

        self.subscriber_callback_group = MutuallyExclusiveCallbackGroup()
        self.pkt_subscriber = self.create_subscription(
                PktCSI,
                'pktcsi',
                self.listener_callback,
                100,
                callback_group=self.subscriber_callback_group)

        self._publisher = self.create_publisher(
                ApneaAI,
                'apnea_ai',
                10)
        timer_period = 0.7
        self.publisher_callback_group = MutuallyExclusiveCallbackGroup()
        self.timer = self.create_timer(
                timer_period,
                self.publisher_callback,
                callback_group=self.publisher_callback_group)

        self.apnea_detection_ai = ApneaDetectionAI()
        self.model = load_model(os.getenv('KERAS_APNEA_MODEL'))

    def listener_callback(self, msg: PktCSI):
        self.get_logger().info(f'Reading pktcsi: {msg.pktid}')
        parsed_pkt = self.apnea_detection_ai.parse_pkt(msg)
        self.apnea_detection_ai.add_to_buffer(parsed_pkt)

    def publisher_callback(self):
        if self.apnea_detection_ai.is_buffer_full:
            is_apnea = self.apnea_detection_ai.pipeline(self.model)
            self.get_logger().info(f'Apnea prediction: {is_apnea}')

            if is_apnea:
                apnea_detection_msg = ApneaAI()
                apnea_detection_msg.timestamp = time.time_ns()
                self._publisher.publish(apnea_detection_msg)


def main(args=None):
    rclpy.init(args=args)

    apnea_ai_publisher = ApneaAIPublisher()
    executor = MultiThreadedExecutor()
    executor.add_node(apnea_ai_publisher)
    executor.spin()

    apnea_ai_publisher.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
