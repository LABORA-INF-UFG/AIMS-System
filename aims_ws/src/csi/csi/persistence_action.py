"""Action server that records every configured source topic to a folder."""

import os
import threading
import time

from ament_index_python.packages import get_package_share_directory
from custom_interfaces.action import Persistence
import rclpy
from rclpy.action import ActionServer, GoalResponse
from rclpy.callback_groups import (MutuallyExclusiveCallbackGroup,
                                   ReentrantCallbackGroup)
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile
from rosidl_runtime_py.utilities import get_message

from .capture_writers import Capture, load_sources

LATCHED = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
# Deep queue so CSI bursts are not dropped while a part is written.
STREAM = QoSProfile(depth=100)


class PersistenceAction(Node):

    def __init__(self):
        super().__init__('persistence_action')
        default = os.path.join(get_package_share_directory('csi'),
                               'config', 'capture_sources.yaml')
        self.sources_file = self.declare_parameter(
            'sources_file', default).value
        self._busy = False
        self._busy_lock = threading.Lock()
        self._sub_group = ReentrantCallbackGroup()
        self._action_server = ActionServer(
            self,
            Persistence,
            'persist_csi',
            execute_callback=self.execute,
            goal_callback=self.on_goal,
            callback_group=MutuallyExclusiveCallbackGroup())

    def on_goal(self, goal_request):
        with self._busy_lock:
            if self._busy:
                self.get_logger().warn('Capture running; goal rejected.')
                return GoalResponse.REJECT
            self._busy = True
            return GoalResponse.ACCEPT

    def execute(self, goal_handle):
        try:
            return self._capture(goal_handle)
        finally:
            with self._busy_lock:
                self._busy = False

    def _capture(self, goal_handle):
        req = goal_handle.request
        request = {f: getattr(req, f)
                   for f in req.get_fields_and_field_types()}
        result = Persistence.Result()
        try:
            sources = load_sources(self.sources_file)
            capture = Capture(os.environ['AIMS'], request, sources,
                              log=self.get_logger().error)
        except Exception as e:
            self.get_logger().error(f'Capture not started: {e!r}')
            goal_handle.abort()
            result.response = f'error: {e!r}'
            return result

        subs = []
        for name, cfg in sources.items():
            try:
                subs.append(self.create_subscription(
                    get_message(cfg['type']), cfg['topic'],
                    lambda msg, n=name: capture.write(n, msg, time.time_ns()),
                    LATCHED if cfg.get('qos') == 'latched' else STREAM,
                    callback_group=self._sub_group))
            except Exception as e:
                capture.fail(name, e)
        capture.write_meta('recording')
        self.get_logger().info(
            f'Recording {req.duration_s} s to {capture.folder}')

        csi_sources = [n for n, c in sources.items()
                       if c['writer'] == 'csi_npz']
        feedback = Persistence.Feedback()
        start = time.monotonic()
        try:
            while (elapsed := time.monotonic() - start) < req.duration_s:
                feedback.elapsed_s = int(elapsed)
                feedback.csi_frames = sum(capture.rows(n) for n in csi_sources)
                goal_handle.publish_feedback(feedback)
                time.sleep(min(1.0, req.duration_s - elapsed))
        finally:
            for sub in subs:
                self.destroy_subscription(sub)
            capture.close()

        self.get_logger().info(f'Capture saved to {capture.folder}')
        goal_handle.succeed()
        result.response = capture.folder
        return result


def main():
    rclpy.init()

    persistence_action_server_node = PersistenceAction()

    # At least 2 threads: the goal sleeps in one while subscriptions run.
    _multiThreadedExecutor = MultiThreadedExecutor(num_threads=4)

    _multiThreadedExecutor.add_node(persistence_action_server_node)

    try:
        persistence_action_server_node.get_logger().info(
            'PersistenceAction started.')
        _multiThreadedExecutor.spin()
    except KeyboardInterrupt:
        persistence_action_server_node.get_logger().info(
            'PersistenceAction: Keyboard interrupt, shutting down.\n')

    persistence_action_server_node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
