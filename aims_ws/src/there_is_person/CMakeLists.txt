cmake_minimum_required(VERSION 3.5)
project(there_is_person)

# Find ROS 2 and ament packages
find_package(ament_cmake REQUIRED)

# Add the dependency from package.xml
ament_package()