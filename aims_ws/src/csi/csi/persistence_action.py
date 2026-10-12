from custom_interfaces.action import Persistence
from custom_interfaces.msg import PktCSI, HeartControl, BreathControl
import rclpy, os, re, time
from rclpy.node import Node
from rclpy.action import ActionServer
from csi.libs.CsiMsgToDict import CsiMsgToDict
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup
from rclpy.executors import MultiThreadedExecutor

def _safe(value):
    # Values come from the web form; keep file names valid on Windows bind mounts.
    return re.sub(r'[^A-Za-z0-9_-]', '_', str(value))


def capture_file_name(req, date, prefix=''):
    parts = [req.capture_name, req.subject_id, req.rx_nic_model, req.tx_nic_model,
             req.subject_position, f'{req.antenna_distance_cm}cm']
    return prefix + '-'.join(_safe(p) for p in parts) + f'-{date}.txt'


class Listener(Node):

    def __init__(self):
        super().__init__('persistence_csi_subscriber')

        self.subscription = self.create_subscription(
            PktCSI,
            'pktcsi',
            self.csi_listener_callback,
            10,
            callback_group= MutuallyExclusiveCallbackGroup())
        self.subscription  # prevent unused variable warning
        self.frame_buffer = []

        self._heart_subscription = self.create_subscription(
            HeartControl,
            'heart_control',
            self.heartbeat_listener_callback,
            10,
            callback_group= MutuallyExclusiveCallbackGroup())
        self.subscription  # prevent unused variable warning
        self.heartbeat_buffer = []

        self._breath_subscription = self.create_subscription(
            BreathControl,
            'breath_control',
            self.breath_listener_callback,
            10,
            callback_group= MutuallyExclusiveCallbackGroup())
        self.breath_buffer = []


    def csi_listener_callback(self, msg):
        #self.get_logger().info('I heard CSI>>: "%s"' % msg.pktid)
        self.frame_buffer.append(msg)

    def heartbeat_listener_callback(self, msg):
        self.get_logger().info('I heard a heartbeat, you are alive :)')
        self.heartbeat_buffer.append(
            {
                'timestamp': msg.timestamp,
                'pktid': self.frame_buffer[-1].pktid
            }
        )

    def breath_listener_callback(self, msg):
        self.get_logger().info('I received a breath, you are alive :)')
        self.breath_buffer.append(
            {
                'timestamp': msg.timestamp,
                'pktid': self.frame_buffer[-1].pktid
            }
        )

    def clear_buffers(self):
        self.frame_buffer = []
        self.heartbeat_buffer = []
        self.breath_buffer = []



class PersistenceAction(Node):

    def __init__(self):
        super().__init__('persistence_action')
        self._action_server = ActionServer(
            self,
            Persistence,
            'persist_csi',
            self.callback)
        
        self.listener_node = Listener()


    def callback(self, goal_handle):

        self.get_logger().info("Starting capture of {} frames".format(goal_handle.request.num_frames))

        self.listener_node.clear_buffers()

        date = time.strftime("%d_%m_%Y-%H-%M")

        feedback_msg = Persistence.Feedback()
        recv_frames = len(self.listener_node.frame_buffer)
        while recv_frames < goal_handle.request.num_frames:
            if recv_frames % 10 == 0:
                feedback_msg.captured_frames = recv_frames
                goal_handle.publish_feedback(feedback_msg)

            rclpy.spin_once(node=self.listener_node)
            recv_frames = len(self.listener_node.frame_buffer)

        current_dir = os.getenv('AIMS')
        if not os.path.exists(current_dir + '/captures'):
            os.mkdir(current_dir + '/captures')

        capture_name_csi = capture_file_name(goal_handle.request, date)
        with open(f"{os.getenv('AIMS')}/captures/{capture_name_csi}", "w") as f:
            for item in self.listener_node.frame_buffer:
                f.write(str(CsiMsgToDict(item)) + "\n")
        
        if len(self.listener_node.heartbeat_buffer) > 0:
            capture_name_heartbeat = capture_file_name(goal_handle.request, date, 'Heartbeats-')
            with open(f"{os.getenv('AIMS')}/captures/{capture_name_heartbeat}", "w") as f:
                for item in self.listener_node.heartbeat_buffer:
                    f.write(str(item) + "\n")

        if len(self.listener_node.breath_buffer) > 0:
            capture_name_breath = capture_file_name(goal_handle.request, date, 'Breaths-')
            with open(f"{os.getenv('AIMS')}/captures/{capture_name_breath}", "w") as f:
                for item in self.listener_node.breath_buffer:
                    f.write(str(item) + "\n")

        self.get_logger().info("Request served.")

        goal_handle.succeed()
        result = Persistence.Result()
        result.response = f"Capture ({capture_name_csi}) saved to '{os.getenv('AIMS')}/captures/'"
        return result
    


def main():
    rclpy.init()

    persistence_action_server_node = PersistenceAction()

    _multiThreadedExecutor = MultiThreadedExecutor()

    _multiThreadedExecutor.add_node(persistence_action_server_node)

    try:
        persistence_action_server_node.get_logger().info('PersistenceAction started.')
        _multiThreadedExecutor.spin()
    except KeyboardInterrupt:
        persistence_action_server_node.get_logger().info('PersistenceAction: Keyboard interrupt, shutting down.\n')

    rclpy.shutdown()


if __name__ == '__main__':
    main()
