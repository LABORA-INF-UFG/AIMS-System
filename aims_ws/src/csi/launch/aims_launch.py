"""
AIMS Full Launch File.

Launches all ROS2 processing nodes for the AIMS system.
PicoScenes and the web server are NOT started here — they run
as separate containers (or on the host for PicoScenes).

The CSI source comes from the csi_source argument (default: $CSI_SOURCE,
else 'mock'): 'picoscenes' runs the UDP publisher fed by PicoScenes on the
host; anything else runs the mock publisher.

Usage:
    ros2 launch csi aims_launch.py [csi_source:=mock|picoscenes]
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

        # CSI Publisher (real — CSI_SOURCE=picoscenes)
        Node(
            package='csi',
            executable='csi_publisher',
            name='csi_publisher',
            output='screen',
            condition=IfCondition(use_picoscenes),
        ),

        # CSI Publisher (mock — default)
        Node(
            package='csi',
            executable='mock_csi',
            name='mock_csi_publisher',
            output='screen',
            condition=UnlessCondition(use_picoscenes),
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
