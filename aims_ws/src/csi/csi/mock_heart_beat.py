import rclpy, time
from rclpy.node import Node
from custom_interfaces.msg import HeartControl

class MockHeartBeat(Node):
    def __init__(self):
        super().__init__('heart_beat_mock')
        self._publisher = self.create_publisher(
                HeartControl,
                'heart_control',
                10)
        timer_period = 1
        self.timer = self.create_timer(timer_period, self.timer_callback)

    def timer_callback(self):
        heart_control_msg = HeartControl()
        heart_control_msg.timestamp = time.time_ns()
        self._publisher.publish(heart_control_msg)
        self.get_logger().info(f'Publishing mocked heart beat: {heart_control_msg.timestamp}')

def main(args=None):
    rclpy.init(args=args)
    mock_heartbeat_node = MockHeartBeat()
    rclpy.spin(mock_heartbeat_node)
    mock_heartbeat_node.destroy_node()
    rclpy.shutdown()