import os
from glob import glob
from setuptools import setup

package_name = 'csi'
libs = 'csi/libs'

setup(
    name=package_name,
    version='0.0.0',
    packages=[package_name, libs],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name), glob('launch/*launch.[pxy][yma]*'))
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Victor Hugo',
    maintainer_email='victorhullopes@gmail.com',
    description='AIMS CSI controller',
    license='Apache License 2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'persistence_action = csi.persistence_action:main',
            'persistence_bridge = csi.persistence_bridge:main',
            'csi_publisher = csi.publisher_pkt_csi:main',
            'mock_csi = csi.mocked_pkt_csi_publisher:main',
            'mock_breathing = csi.mocked_breathing_apnea_publisher:main',
            'breath_estimator = csi.breath_estimate_publisher:main',
            'breath_estimator_cardiofi = csi.breath_estimate_cardiofi_publisher:main',
            'breath_plotter = csi.breath_plotter:main',
            'csi_heatmap_plotter = csi.csi_heatmap_node:main',
            'mmw_talker = csi.publisher_mmw:main',
            'csi_heatmap_publisher = csi.csi_heatmap_fig_publisher:main',
            'mock_heart_beat = csi.mock_heart_beat:main',
            'octave_cardiofi = csi.octave_cardiofi_publisher:main',
        ],
    },
)
