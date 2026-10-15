# Copyright 2026 Lucas Reis
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Launch the AIMS vision pipeline.

Usage:
    ros2 launch vision_bringup vision.launch.py [device:=cpu|cuda:0] [camera:=0|/path/video.mp4]

device defaults to $VISION_DEVICE, else 'cpu'; camera defaults to $VISION_CAMERA, else '0'.
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import EnvironmentVariable, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    config = PathJoinSubstitution([FindPackageShare('vision_bringup'), 'config', 'vision.yaml'])
    # value_type=str keeps camera '0' a string instead of a YAML integer.
    overrides = {
        'device': ParameterValue(LaunchConfiguration('device'), value_type=str),
        'camera': ParameterValue(LaunchConfiguration('camera'), value_type=str),
    }
    return LaunchDescription([
        DeclareLaunchArgument(
            'device', default_value=EnvironmentVariable('VISION_DEVICE', default_value='cpu')),
        DeclareLaunchArgument(
            'camera', default_value=EnvironmentVariable('VISION_CAMERA', default_value='0')),
        Node(package='pose_estimation', executable='pose_estimation', name='pose_estimation',
             parameters=[config, overrides], output='screen'),
        Node(package='there_is_person', executable='there_is_person', name='there_is_person',
             parameters=[config], output='screen'),
        Node(package='moving', executable='moving', name='moving',
             parameters=[config], output='screen'),
        Node(package='visualization', executable='visualization', name='visualization',
             parameters=[config], output='screen'),
    ])
