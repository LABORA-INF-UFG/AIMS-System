"""
AIMS Core Launch File — Minimal configuration.

Launches only the essential nodes: CSI publisher (real or mock)
and breath estimator. Use this for lightweight testing scenarios.

Usage:
    ros2 launch csi aims_core_launch.py [csi_source:=mock|picoscenes]
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition, UnlessCondition
from launch.substitutions import EnvironmentVariable, LaunchConfiguration, PythonExpression
from launch_ros.actions import Node


def generate_launch_description():
    use_picoscenes = PythonExpression(["'", LaunchConfiguration('csi_source'), "' == 'picoscenes'"])

    return LaunchDescription([
        DeclareLaunchArgument(
            'csi_source',
            default_value=EnvironmentVariable('CSI_SOURCE', default_value='mock'),
            description="CSI input: 'mock' (recorded frame) or 'picoscenes' (UDP from host)",
        ),

        # Mock CSI publisher (default)
        Node(
            package='csi',
            executable='mock_csi',
            name='mock_csi_publisher',
            output='screen',
            condition=UnlessCondition(use_picoscenes),
        ),

        # Real CSI publisher (CSI_SOURCE=picoscenes)
        Node(
            package='csi',
            executable='csi_publisher',
            name='csi_publisher',
            output='screen',
            condition=IfCondition(use_picoscenes),
        ),

        # Breath estimation from CSI data
        Node(
            package='csi',
            executable='breath_estimator',
            name='breath_estimator',
            output='screen',
        ),
    ])
