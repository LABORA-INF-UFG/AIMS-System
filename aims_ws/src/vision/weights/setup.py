from setuptools import setup
import os
from glob import glob

package_name = 'weights'

setup(
    name=package_name,
    version='0.0.1',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'models'), glob('weights/models/*.tflite') + glob('weights/models/*.pt') + glob('weights/models/*.engine')),
        (os.path.join('share', package_name), glob('*.sh')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Lucas Reis',
    maintainer_email='lucas234@discente.ufg.br',
    description='TFLite model weights for pose estimation.',
    license='MIT',
    tests_require=['pytest'],
    entry_points={},
)
