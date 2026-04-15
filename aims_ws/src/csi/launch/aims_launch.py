from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, ExecuteProcess, RegisterEventHandler, LogInfo
from launch.conditions import IfCondition
from launch.launch_description_sources import AnyLaunchDescriptionSource
from ament_index_python import get_package_share_directory
from launch_ros.actions import Node
from launch.event_handlers import OnProcessExit
from launch.substitutions import EnvironmentVariable
import os, shutil


def generate_launch_description():
    csi_publisher = Node(
            package='csi',
            executable='csi_publisher',
            condition=IfCondition(
                [str(shutil.which('PicoScenes') is not None)]
            )
        )

    return LaunchDescription([
        IncludeLaunchDescription(
        AnyLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory('rosbridge_server'),
                'launch/rosbridge_websocket_launch.xml'))
        ),
        ExecuteProcess(
            cmd=[
                shutil.which('bash'),
                '-c',
                'sudo switch5300Firmware csi &> /dev/null; array_prepare_for_picoscenes 2 "5180 HT20"; PicoScenes -d debug -i wlp2s0 --mode logger --forward-to 127.0.0.1:1025'
            ],
            name='picoscenes'
        ),
        Node(
            package='csi',
            executable='mock_csi',
            condition=IfCondition(
                [str(shutil.which('PicoScenes') is None)]
            )
        ),
        csi_publisher,
        Node(
            package='csi',
            executable='breath_estimator'
        ),
        Node(
            package='csi',
            executable='persistence_action'
        ),
        Node(
            package='csi',
            executable='persistence_bridge'
        ),
        Node(
            package='csi',
            executable='csi_heatmap_publisher'
        ),
        ExecuteProcess(
            cmd=[
                shutil.which('bash'),
                '-c',
                'npm run dev'
            ],
            cwd=(os.getenv('AIMS') + '/web'),
            name='node'
        ),
        ExecuteProcess(
            cmd=[
                shutil.which('xdg-open'),
                'http://localhost:3001',
            ],
            name='browser'
        ),
        RegisterEventHandler(
            OnProcessExit(
                target_action=csi_publisher,
                on_exit=[
                    LogInfo(msg=(EnvironmentVariable(name='USER'),
                            ' closed the turtlesim window'))
                ]
            )
        )
    ])