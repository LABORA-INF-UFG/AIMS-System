import rclpy
from rclpy.node import Node
from rclpy.executors import MultiThreadedExecutor
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup, ReentrantCallbackGroup

import time
from custom_interfaces.msg import PktCSI
from custom_interfaces.msg import BreathEstimate
from csi.libs.BreathEstimationCardiofi import BreathEstimationCardioFI, processamento
from std_msgs.msg import Float32
import warnings
warnings.filterwarnings("ignore")


class BreathEstimateCardiofiPublisher(Node):  # publica as estimativas de respiração e apneia no topico

    def __init__(self):

        super().__init__('cardiofi_estimate_publisher')  # criando o nó

        self._publisher_breath = self.create_publisher(Float32, 'breath_estimate_cardiofi', 10)  # criando o publisher
        self._publisher_heart  = self.create_publisher(Float32, 'heart_estimate_cardiofi', 10)  # criando o publisher

        self.subscriber_callback_group = MutuallyExclusiveCallbackGroup()
        self._pkt_subscriber = self.create_subscription(
            PktCSI,
            'pktcsi',
            self.listener_callback,
            10, callback_group=self.subscriber_callback_group)
        self._pkt_subscriber  # prevent unused variable warning
        
        self._estimator = BreathEstimationCardioFI()

        # self.pub_timer_callback_group = self.subscriber_callback_group
        # self.timer = self.create_timer(1.0, self.timer_callback, callback_group=self.pub_timer_callback_group)


        self.processamento_timer_callback_group = MutuallyExclusiveCallbackGroup()
        self.processamento_timer = self.create_timer(0.5, self.processamento_and_pub_callback, callback_group=self.processamento_timer_callback_group)

        self.breath_estimation = None
        self.heart_estimation = None
        self.precision:float = 1.0

        self.i = 0
        self.pkts_received = 0
        self.pkts_received_before_process = 0


    def listener_callback(self, msg):
        
        #self.get_logger().info('Pacote recebido '+str(self.pkts_received))
        self._estimator.recebe_pacote_csi(msg)
        self.pkts_received += 1


    def processamento_and_pub_callback(self):
        if self._estimator.buffer_preenchido and self.pkts_received - self.pkts_received_before_process >= self._estimator.fs:

            self.get_logger().info('Chamando processamento()')
            start_time = time.time()
            
            self.pkts_received_before_process = self.pkts_received
            self.breath_estimation, self.heart_estimation = processamento(self._estimator)
            end_time = time.time()
            self.get_logger().info("Execution time: {:.4f} seconds".format(end_time - start_time))
            breath_estimate_msg = BreathEstimate()
                        
            msg_br = Float32()
            msg_br.data = float(self.breath_estimation)
            msg_hr = Float32()
            msg_hr.data = float(self.heart_estimation)
        
            breath_estimate_msg.precision = 1.0
            self._publisher_breath.publish(msg_br)
            self._publisher_heart.publish(msg_hr)
            self.get_logger().info('Publishing estimates: "%s"' % self.i)

            self.i += 1


def main(args=None):
    rclpy.init(args=args)

    breath_estimator_publisher = BreathEstimateCardiofiPublisher()

    executor = MultiThreadedExecutor()

    executor.add_node(breath_estimator_publisher)

    try:
        breath_estimator_publisher.get_logger().info('Beginning client, shut down with CTRL-C')
        executor.spin()
    except KeyboardInterrupt:
        breath_estimator_publisher.get_logger().info('Keyboard interrupt, shutting down.\n')

    
    breath_estimator_publisher.destroy_node()
    
    rclpy.shutdown()


if __name__ == '__main__':
    main()
