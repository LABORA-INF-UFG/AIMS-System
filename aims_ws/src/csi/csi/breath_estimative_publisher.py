import rclpy
from rclpy.node import Node
from rclpy.executors import MultiThreadedExecutor
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup, ReentrantCallbackGroup

#from std_msgs.msg import String
from custom_interfaces.msg import PktCSI
from custom_interfaces.msg import EstimativeBreath
from csi.libs.BreathEstimation import BreathEstimation, processamento, Apneia



class BreathEstimativePublisher(Node):  # publica as estimativas de respiração e apneia no topico

    def __init__(self):

        super().__init__('estimative_publisher')  # criando o nó

        self._publisher = self.create_publisher(EstimativeBreath, 'estimativebreath', 10)  # criando o publisher

        self.subscriber_callback_group = MutuallyExclusiveCallbackGroup()
        self._pkt_subscriber = self.create_subscription(
            PktCSI,
            'pktcsi',
            self.listener_callback,
            10, callback_group=self.subscriber_callback_group)
        self._pkt_subscriber  # prevent unused variable warning
        
        self._estimator = BreathEstimation()
        self._apneia = Apneia(qtd_de_estimativas=20) # qtd minima de estimativas até começar a detectar apneia


        # self.pub_timer_callback_group = self.subscriber_callback_group
        # self.timer = self.create_timer(1.0, self.timer_callback, callback_group=self.pub_timer_callback_group)


        self.processamento_timer_callback_group = MutuallyExclusiveCallbackGroup()
        self.processamento_timer = self.create_timer(0.5, self.processamento_and_pub_callback, callback_group=self.processamento_timer_callback_group)

        self.breath_estimation = None
        self.apneia = None
        self.precision:float = 1.0

        self.i = 0
        self.pkts_received = 0
        self.pkts_received_before_process = 0


    def listener_callback(self, msg):
        #self.get_logger().info('I heard>>: "%s"' % msg.pktid)

        # TODO subplots (amp and phase), split amplitude/phase to plot
        #splitted_phase = [msg.csi.phase[i * self.r:self.r + (i * self.r)] for i in range(self.n)]

        self._estimator.recebe_pacote_csi(msg)

        self.pkts_received += 1


    def processamento_and_pub_callback(self):
        if self._estimator.buffer_preenchido and self.pkts_received - self.pkts_received_before_process >= self._estimator.fs:

            #self.get_logger().info('Chamando processamento()')

            self.pkts_received_before_process = self.pkts_received
            self.apneia, self.breath_estimation = processamento(self._estimator, self._apneia, self.pkts_received)

            estimativeBreath_msg = EstimativeBreath()
        
            estimativeBreath_msg.breath_estimative = self.breath_estimation  
            estimativeBreath_msg.precision = 1.0
            estimativeBreath_msg.apneia_detected = bool(self.apneia)  # possiveis valores: 0 ou 1

            self._publisher.publish(estimativeBreath_msg)
            #self.get_logger().info('Publishing breath estimative: "%s"' % self.i)

            self.i += 1


def main(args=None):
    rclpy.init(args=args)

    breath_estimator_publisher = BreathEstimativePublisher()

    executor = MultiThreadedExecutor()

    executor.add_node(breath_estimator_publisher)

    try:
        breath_estimator_publisher.get_logger().info('BreathEstimator iniciado.')
        executor.spin()
    except KeyboardInterrupt:
        breath_estimator_publisher.get_logger().info('BreathEstimator: Keyboard interrupt, shutting down.\n')

    
    breath_estimator_publisher.destroy_node()
    
    rclpy.shutdown()


if __name__ == '__main__':
    main()