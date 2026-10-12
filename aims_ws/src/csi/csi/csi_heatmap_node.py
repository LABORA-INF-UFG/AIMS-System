import time
import rclpy
from rclpy.node import Node
from rclpy.executors import MultiThreadedExecutor
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup, ReentrantCallbackGroup

#from std_msgs.msg import String
from custom_interfaces.msg import PktCSI
from csi.libs.BreathEstimation import BreathEstimation
from csi.libs.new_plotter import Plotter
import cv2, threading

class CsiHeatmapNode(Node):

    def __init__(self):

        super().__init__('heatmap_plotter')  # creating the node

        self.subscriber_callback_group = MutuallyExclusiveCallbackGroup()
        self._pkt_subscriber = self.create_subscription(
            PktCSI,
            'pktcsi',
            self.listener_callback,
            10, callback_group=self.subscriber_callback_group)
        self._pkt_subscriber  # prevent unused variable warning
        
        self.num_packets_to_plot = 1000

        self._estimator = BreathEstimation()
        self._plotter = Plotter(window_size=self.num_packets_to_plot, num_subcarriers=57)

        self.process_timer_callback_group = MutuallyExclusiveCallbackGroup()
        self.process_timer = self.create_timer(0.1, self.process_and_plot_callback, callback_group=self.process_timer_callback_group)

        self.i = 0
        self.pkts_received = 0
        self.pkts_received_before_process = 0
        self.heatmap = True

    def listener_callback(self, msg):
        #self.get_logger().info('I heard>>: "%s"' % msg.pktid)

        self._estimator.receive_csi_packet(msg)

        self.pkts_received += 1


    def process_and_plot_callback(self):
        if self._estimator.buffer_filled and (self.pkts_received - self.pkts_received_before_process >= 20):

            self.pkts_received_before_process = self.pkts_received
            
            phase_diff = self._estimator.phase_difference(self._estimator.get_csi()[:, -1*self.num_packets_to_plot:])
            self.heatmap = self._plotter.update(phase_diff, invariant=False)


def main(args=None):

    rclpy.init()

    breath_estimator_publisher = CsiHeatmapNode()
    executor = MultiThreadedExecutor()
    executor.add_node(breath_estimator_publisher)


    def ros_context():
            breath_estimator_publisher.get_logger().info('Node initialized, loading buffer.')
            executor.spin()


    node_thread = threading.Thread(target=ros_context)

    try:
        node_thread.start()
        while rclpy.ok():
            time.sleep(0.1)
            if breath_estimator_publisher._estimator.buffer_filled:
                cv2.imshow('Heatmap', breath_estimator_publisher.heatmap)
                cv2.waitKey(1)
            else:
                print(f'{breath_estimator_publisher._estimator.pkt_count/(breath_estimator_publisher._estimator.buffer_seconds ): .2f}%')
    
    except (KeyboardInterrupt, SystemExit):
        breath_estimator_publisher.destroy_node()
        rclpy.shutdown()
        cv2.destroyAllWindows()
    

if __name__ == '__main__':
    main()