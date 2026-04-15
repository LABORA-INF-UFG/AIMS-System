from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, ExecuteProcess
from launch.conditions import IfCondition
from launch.launch_description_sources import AnyLaunchDescriptionSource
from ament_index_python import get_package_share_directory
from launch_ros.actions import Node
import os, shutil


def generate_launch_description():
    return LaunchDescription([
        IncludeLaunchDescription(
        AnyLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory('rosbridge_server'),
                'launch/rosbridge_websocket_launch.xml'))
        ),
        Node(
            package='csi',
            executable='mock_csi',
            condition=IfCondition(
                [str(shutil.which('PicoScenes') is None)]
            )
        ),
        Node(
            package='csi',
            executable='talker',
            condition=IfCondition(
                [str(shutil.which('PicoScenes') is not None)]
            )
        ),
        Node(
            package='csi',
            executable='breath_estimator'
        )
    ])
