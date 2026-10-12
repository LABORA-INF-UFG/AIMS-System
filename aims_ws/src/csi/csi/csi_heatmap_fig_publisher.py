import time
import rclpy
from rclpy.node import Node
from rclpy.executors import MultiThreadedExecutor
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup, ReentrantCallbackGroup

#from std_msgs.msg import String
from custom_interfaces.msg import PktCSI
from csi.libs.BreathEstimation import BreathEstimation
from csi.libs.new_plotter import Plotter
import cv2
from sensor_msgs.msg import Image # Image is the message type
from cv_bridge import CvBridge # Package to convert between ROS and OpenCV Images
import numpy as np
import base64


class CsiHeatmapFigPublisher(Node):

    def __init__(self):

        super().__init__('csi_heatmap_fig_publisher')  # creating the node

        self.subscriber_callback_group = MutuallyExclusiveCallbackGroup()
        self._pkt_subscriber = self.create_subscription(
            PktCSI,
            'pktcsi',
            self.listener_callback,10)
        
        self.num_packets_to_plot = 1000

        self._estimator = BreathEstimation()
        self._plotter = Plotter(window_size=self.num_packets_to_plot, num_subcarriers=57)

        self.i = 0
        self.pkts_received = 0
        self.pkts_received_before_process = 0
        self.heatmap = None
        
        self.publisher_ = self.create_publisher(Image, 'heatmap', 10)
        # Used to convert between ROS and OpenCV images
        self.br = CvBridge()


    def listener_callback(self, msg):
        self._estimator.receive_csi_packet(msg)
        self.pkts_received += 1
        self.process_and_plot_callback()


    def process_and_plot_callback(self):
        if self._estimator.buffer_filled and (self.pkts_received - self.pkts_received_before_process >= 20):

            self.pkts_received_before_process = self.pkts_received
            
            phase_diff = self._estimator.phase_difference(self._estimator.get_csi()[:, -1*self.num_packets_to_plot:])
            self.heatmap = self._plotter.update(phase_diff, invariant=False)

            # Encode the image as PNG and publish it to the topic
            success, encoded_image = cv2.imencode('.png', self.heatmap)
            if success:
                image_msg = Image()
                image_msg.header.frame_id = 'my_frame'
                image_msg.encoding = 'bgr8'
                image_msg.height = 400
                image_msg.width = 100
                image_msg.data = encoded_image.tobytes()
                self.publisher_.publish(image_msg)
                #self.get_logger().info('CSI heatmap published.')
            else:
                self.get_logger().error('Failed to encode image.')


def main(args=None):

    rclpy.init()
    breath_estimator_publisher = CsiHeatmapFigPublisher()
    rclpy.spin(breath_estimator_publisher)
    # Destroy the node explicitly
    # (optional - otherwise it will be done automatically
    # when the garbage collector destroys the node object)
    breath_estimator_publisher.destroy_node()
    rclpy.shutdown()
    

if __name__ == '__main__':
    main()
