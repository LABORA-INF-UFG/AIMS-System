import rclpy
from rclpy.node import Node
import random

from custom_interfaces.msg import BreathEstimate

class MockedBreathingRateAndApneaPublisher(Node):

    def __init__(self):
        super().__init__('mocked_breathing_and_apnea_publisher')
        self.publisher_ = self.create_publisher(BreathEstimate, 'breath_estimate', 10)
        self.timer_period = 2  # seconds
        self.timer = self.create_timer(self.timer_period, self.timer_callback)

        self.i = 0
        self.breathing_rate: float = 8.0
        self.precision : float = 0.8
        self.apnea_detected = False
        self.br_zero_counter = 0

    def timer_callback(self):
        msg = BreathEstimate()

        # Mock the precision
        
        self.precision = random.uniform(0.75, 1)

        # ==========================

        # Mock the breathing rate and apnea
        self.breathing_rate += random.randrange(-2, 2, 1)

        if self.breathing_rate < 0:
            self.breathing_rate = 0

        if self.breathing_rate > 20:
            self.breathing_rate = 20

        if self.breathing_rate == 0:

                self.apnea_detected = True

                self.br_zero_counter += 1

                if self.br_zero_counter > (5/self.timer_period):
                    self.br_zero_counter = 0
                    self.breathing_rate = 11
                    self.apnea_detected = False
 
        else:
            self.apnea_detected = False

        # ==========================

        # Populate the msg file
        msg.breath_rate = float(self.breathing_rate)
        msg.apnea_detected = self.apnea_detected
        msg.precision = self.precision

        # ==========================
        self.publisher_.publish(msg)
        self.get_logger().info('Publishing breathing estimate msg: "%s"' % self.i)
        self.i += 1


def main(args=None):

    rclpy.init(args=args)

    minimal_publisher = MockedBreathingRateAndApneaPublisher()

    rclpy.spin(minimal_publisher)

    # Destroy the node explicitly
    # (optional - otherwise it will be done automatically
    # when the garbage collector destroys the node object)
    minimal_publisher.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
