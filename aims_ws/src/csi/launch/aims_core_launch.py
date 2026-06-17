"""
AIMS Core Launch File — Minimal configuration.

Launches only the essential nodes: CSI publisher (real or mock)
and breath estimator. Use this for lightweight testing scenarios.

Usage:
    ros2 launch csi aims_core_launch.py
"""

from launch import LaunchDescription
from launch.conditions import IfCondition
from launch_ros.actions import Node
import shutil


def generate_launch_description():
    has_picoscenes = str(shutil.which('PicoScenes') is not None)
    no_picoscenes = str(shutil.which('PicoScenes') is None)

    return LaunchDescription([
        # Mock CSI publisher (when PicoScenes is NOT available)
        Node(
            package='csi',
            executable='mock_csi',
            name='mock_csi_publisher',
            output='screen',
            condition=IfCondition([no_picoscenes]),
        ),

        # Real CSI publisher (when PicoScenes IS available)
        Node(
            package='csi',
            executable='csi_publisher',
            name='csi_publisher',
            output='screen',
            condition=IfCondition([has_picoscenes]),
        ),

        # Breath estimation from CSI data
        Node(
            package='csi',
            executable='breath_estimator',
            name='breath_estimator',
            output='screen',
        ),
    ])
