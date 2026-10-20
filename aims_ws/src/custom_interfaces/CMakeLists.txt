cmake_minimum_required(VERSION 3.8)
project(custom_interfaces)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# find dependencies
find_package(ament_cmake REQUIRED)
# uncomment the following section in order to fill in
# further dependencies manually.
# find_package(<dependency> REQUIRED)

#Find the package that generates message code from msg/srv files:
find_package(rosidl_default_generators REQUIRED)

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  # the following line skips the linter which checks for copyrights
  # comment the line when a copyright and license is added to all source files
  set(ament_cmake_copyright_FOUND TRUE)
  # the following line skips cpplint (only works in a git repo)
  # comment the line when this package is in a git repo and when
  # a copyright and license is added to all source files
  set(ament_cmake_cpplint_FOUND TRUE)
  ament_lint_auto_find_test_dependencies()
endif()

set(msg_files
  "msg/PktCSI.msg"
  "msg/PktCSIMeta.msg"
  "msg/PktCSISample.msg"
  "msg/PktCSISignal.msg"
  "msg/PktRxExtraInfo.msg"
  "msg/PktRxBasic.msg"
  "msg/PktTxExtraInfo.msg"
  "msg/BreathEstimate.msg"
  "msg/MmWVitalSignal.msg"
  "msg/HeartControl.msg"
  "msg/ApneaAI.msg"
  "msg/PersistenceRequest.msg"
  "msg/PersistenceFeedback.msg"
  "msg/BreathControl.msg"
  "msg/OctaveCardiofi.msg"
)
set(srv_files
  "srv/Persistence.srv"
)
set(action_files
  "action/Persistence.action"
)
#rosidl_generate_interfaces(${PROJECT_NAME}
#  ${msg_files}
#  ${srv_files}
#)
rosidl_generate_interfaces(${PROJECT_NAME}
  ${msg_files}
  ${srv_files}
  ${action_files}
)
ament_export_dependencies(rosidl_default_runtime)

ament_package()
