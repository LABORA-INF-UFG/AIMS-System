"""
AIMS Mock Launch File — Development/Testing.

Launches the mock CSI publisher (reads from single_csi_frame.txt)
and the breath estimator node. Use this when PicoScenes hardware
is not available.

Usage:
    ros2 launch csi aims_mock_launch.py
"""

from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package='csi',
            executable='mock_csi',
            name='mock_csi_publisher',
            output='screen',
        ),
        Node(
            package='csi',
            executable='breath_estimator',
            name='breath_estimator',
            output='screen',
        ),
    ])
