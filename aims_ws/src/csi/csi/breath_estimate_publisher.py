import rclpy
from rclpy.node import Node
from rclpy.executors import MultiThreadedExecutor
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup, ReentrantCallbackGroup

#from std_msgs.msg import String
from custom_interfaces.msg import PktCSI
from custom_interfaces.msg import BreathEstimate
from csi.libs.BreathEstimation import BreathEstimation, process, Apnea



class BreathEstimatePublisher(Node):  # publishes the breathing and apnea estimates on the topic

    def __init__(self):

        super().__init__('breath_estimate_publisher')  # creating the node

        self._publisher = self.create_publisher(BreathEstimate, 'breath_estimate', 10)  # creating the publisher

        self.subscriber_callback_group = MutuallyExclusiveCallbackGroup()
        self._pkt_subscriber = self.create_subscription(
            PktCSI,
            'pktcsi',
            self.listener_callback,
            10, callback_group=self.subscriber_callback_group)
        self._pkt_subscriber  # prevent unused variable warning
        
        self._estimator = BreathEstimation()
        self._apnea = Apnea(num_estimates=20) # minimum number of estimates before apnea detection starts


        # self.pub_timer_callback_group = self.subscriber_callback_group
        # self.timer = self.create_timer(1.0, self.timer_callback, callback_group=self.pub_timer_callback_group)


        self.process_timer_callback_group = MutuallyExclusiveCallbackGroup()
        self.process_timer = self.create_timer(0.5, self.process_and_pub_callback, callback_group=self.process_timer_callback_group)

        self.breath_estimation = None
        self.apnea = None
        self.precision:float = 1.0

        self.i = 0
        self.pkts_received = 0
        self.pkts_received_before_process = 0


    def listener_callback(self, msg):
        #self.get_logger().info('I heard>>: "%s"' % msg.pktid)

        # TODO subplots (amp and phase), split amplitude/phase to plot
        #splitted_phase = [msg.csi.phase[i * self.r:self.r + (i * self.r)] for i in range(self.n)]

        self._estimator.receive_csi_packet(msg)

        self.pkts_received += 1


    def process_and_pub_callback(self):
        if self._estimator.buffer_filled and self.pkts_received - self.pkts_received_before_process >= self._estimator.fs:

            #self.get_logger().info('Calling process()')

            self.pkts_received_before_process = self.pkts_received
            self.apnea, self.breath_estimation = process(self._estimator, self._apnea, self.pkts_received)

            breath_estimate_msg = BreathEstimate()
        
            breath_estimate_msg.breath_rate = self.breath_estimation  
            breath_estimate_msg.precision = 1.0
            breath_estimate_msg.apnea_detected = bool(self.apnea)  # possible values: 0 or 1

            self._publisher.publish(breath_estimate_msg)
            #self.get_logger().info('Publishing breath estimate: "%s"' % self.i)

            self.i += 1


def main(args=None):
    rclpy.init(args=args)

    breath_estimator_publisher = BreathEstimatePublisher()

    executor = MultiThreadedExecutor()

    executor.add_node(breath_estimator_publisher)

    try:
        breath_estimator_publisher.get_logger().info('BreathEstimator started.')
        executor.spin()
    except KeyboardInterrupt:
        breath_estimator_publisher.get_logger().info('BreathEstimator: Keyboard interrupt, shutting down.\n')

    
    breath_estimator_publisher.destroy_node()
    
    rclpy.shutdown()


if __name__ == '__main__':
    main()