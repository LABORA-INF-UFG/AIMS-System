from custom_interfaces.action import Persistence
from custom_interfaces.msg import PktCSI, HeartControl, BreathControl
import rclpy, os, time
from rclpy.node import Node
from rclpy.action import ActionServer
from csi.libs.CsiMsgToDict import CsiMsgToDict
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup
from rclpy.executors import MultiThreadedExecutor


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

        self.get_logger().info("Iniciando captura de {}".format(goal_handle.request.num_frames))

        self.listener_node.clear_buffers()

        data = time.strftime("%d_%m_%Y-%H:%M")

        feedback_msg = Persistence.Feedback()
        recv_frames = len(self.listener_node.frame_buffer)
        while recv_frames < goal_handle.request.num_frames:
            if recv_frames % 10 == 0:
                feedback_msg.captured_frames = recv_frames
                goal_handle.publish_feedback(feedback_msg)

            rclpy.spin_once(node=self.listener_node)
            recv_frames = len(self.listener_node.frame_buffer)

        current_dir = os.getenv('AIMS')
        if not os.path.exists(current_dir + '/Capturas'):
            os.mkdir(current_dir + '/Capturas')

        nome_captura_csi = f'{goal_handle.request.nome_coleta}-{goal_handle.request.nome_paciente}-{goal_handle.request.modelo_nic_rx}-{goal_handle.request.modelo_nic_tx}-{goal_handle.request.posicao_paciente}-{goal_handle.request.distancia_antenas_centimetros}cm-{data}.txt'
        with open(f"{os.getenv('AIMS')}/Capturas/{nome_captura_csi}", "w") as f:
            for item in self.listener_node.frame_buffer:
                f.write(str(CsiMsgToDict(item)) + "\n")
        
        if len(self.listener_node.heartbeat_buffer) > 0:
            nome_captura_heartbeat = f'Heartbeats-{goal_handle.request.nome_coleta}-{goal_handle.request.nome_paciente}-{goal_handle.request.modelo_nic_rx}-{goal_handle.request.modelo_nic_tx}-{goal_handle.request.posicao_paciente}-{goal_handle.request.distancia_antenas_centimetros}cm-{data}.txt'
            with open(f"{os.getenv('AIMS')}/Capturas/{nome_captura_heartbeat}", "w") as f:
                for item in self.listener_node.heartbeat_buffer:
                    f.write(str(item) + "\n")

        if len(self.listener_node.breath_buffer) > 0:
            nome_captura_breath = f'Breaths-{goal_handle.request.nome_coleta}-{goal_handle.request.nome_paciente}-{goal_handle.request.modelo_nic_rx}-{goal_handle.request.modelo_nic_tx}-{goal_handle.request.posicao_paciente}-{goal_handle.request.distancia_antenas_centimetros}cm-{data}.txt'
            with open(f"{os.getenv('AIMS')}/Capturas/{nome_captura_breath}", "w") as f:
                for item in self.listener_node.breath_buffer:
                    f.write(str(item) + "\n")

        self.get_logger().info("Request served.")

        goal_handle.succeed()
        result = Persistence.Result()
        result.response = f"Captura ({nome_captura_csi}) salva em '{os.getenv('AIMS')}/Capturas/'"
        return result
    


def main():
    rclpy.init()

    persistence_action_server_node = PersistenceAction()

    _multiThreadedExecutor = MultiThreadedExecutor()

    _multiThreadedExecutor.add_node(persistence_action_server_node)

    try:
        persistence_action_server_node.get_logger().info('PersistenceAction iniciado.')
        _multiThreadedExecutor.spin()
    except KeyboardInterrupt:
        persistence_action_server_node.get_logger().info('PersistenceAction: Keyboard interrupt, shutting down.\n')

    rclpy.shutdown()


if __name__ == '__main__':
    main()
