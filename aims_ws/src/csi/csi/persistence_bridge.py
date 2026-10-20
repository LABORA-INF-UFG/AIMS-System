import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node

from custom_interfaces.action import Persistence
from custom_interfaces.msg import PersistenceRequest
from custom_interfaces.msg import PersistenceFeedback
from std_msgs.msg import String

class PersistenceBridge(Node):

    def __init__(self):
        super().__init__('persistence_bridge')
        self._action_client = ActionClient(self, Persistence, 'persist_csi')
        self.listener_request = self.create_subscription(PersistenceRequest, 'persistence_bridge/request', self.handle_request_callback, 10)
        self.publisher_feedback = self.create_publisher(PersistenceFeedback, 'persistence_bridge/feedback', 10)
        self.publisher_response = self.create_publisher(String, 'persistence_bridge/response', 10)


    def handle_request_callback(self, msg):
        self.send_goal(msg)


    def send_goal(self, msg):
        goal_msg = Persistence.Goal()
        goal_msg.capture_name = msg.capture_name
        goal_msg.subject_id = msg.subject_id
        goal_msg.rx_nic_model = msg.rx_nic_model
        goal_msg.tx_nic_model = msg.tx_nic_model
        goal_msg.subject_position = msg.subject_position
        goal_msg.antenna_distance_cm = msg.antenna_distance_cm
        goal_msg.num_frames = msg.num_frames

        self._action_client.wait_for_server()

        self._send_goal_future = self._action_client.send_goal_async(goal_msg, feedback_callback=self.feedback_callback)

        self._send_goal_future.add_done_callback(self.goal_response_callback)


    def goal_response_callback(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().info('Goal rejected :(')
            return

        self.get_logger().info('Goal accepted :)')

        self._get_result_future = goal_handle.get_result_async()
        self._get_result_future.add_done_callback(self.get_result_callback)


    def get_result_callback(self, future):
        res = String()
        res.data = future.result().result.response
        self.publisher_response.publish(res)
        self.get_logger().info('Result: {0}'.format(future.result().result.response))


    def feedback_callback(self, feedback_msg):
        msg = PersistenceFeedback()
        msg.captured_frames = feedback_msg.feedback.captured_frames
        self.publisher_feedback.publish(msg)
        #self.get_logger().info('Received feedback: {0}'.format(feedback_msg.feedback.captured_frames))


def main(args=None):
    rclpy.init(args=args)

    action_client = PersistenceBridge()

    rclpy.spin(action_client)


if __name__ == '__main__':
    main()