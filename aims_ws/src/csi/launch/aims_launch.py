"""
AIMS Full Launch File.

Launches all ROS2 processing nodes for the AIMS system.
PicoScenes and the web server are NOT started here — they run
as separate containers (or on the host for PicoScenes).

If PicoScenes is installed on the system, the real CSI publisher is used.
Otherwise, the mock publisher is launched for development/testing.

Usage:
    ros2 launch csi aims_launch.py
"""

from launch import LaunchDescription
from launch.conditions import IfCondition
from launch_ros.actions import Node
import shutil


def generate_launch_description():
    has_picoscenes = str(shutil.which('PicoScenes') is not None)
    no_picoscenes = str(shutil.which('PicoScenes') is None)

    return LaunchDescription([
        # CSI Publisher (real — only when PicoScenes is available on this machine)
        Node(
            package='csi',
            executable='csi_publisher',
            name='csi_publisher',
            output='screen',
            condition=IfCondition([has_picoscenes]),
        ),

        # CSI Publisher (mock — when PicoScenes is NOT available)
        Node(
            package='csi',
            executable='mock_csi',
            name='mock_csi_publisher',
            output='screen',
            condition=IfCondition([no_picoscenes]),
        ),

        # Breath estimation from CSI data
        Node(
            package='csi',
            executable='breath_estimator',
            name='breath_estimator',
            output='screen',
        ),

        # CSI data persistence (action server)
        Node(
            package='csi',
            executable='persistence_action',
            name='persistence_action',
            output='screen',
        ),

        # Persistence bridge (for web interaction)
        Node(
            package='csi',
            executable='persistence_bridge',
            name='persistence_bridge',
            output='screen',
        ),

        # CSI heatmap image publisher
        Node(
            package='csi',
            executable='csi_heatmap_publisher',
            name='csi_heatmap_publisher',
            output='screen',
        ),
    ])