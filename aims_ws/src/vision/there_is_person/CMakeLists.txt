cmake_minimum_required(VERSION 3.5)
project(there_is_person)

# Encontre pacotes ROS 2 e ament
find_package(ament_cmake REQUIRED)

# Adicione a dependência do pacote.xml
ament_package()