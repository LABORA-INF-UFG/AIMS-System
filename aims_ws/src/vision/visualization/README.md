# visualization

Node `visualization`: pairs `/estimation_points` with `/vision/image_raw` by exact header
stamp (`message_filters.TimeSynchronizer`), draws the detected body keypoints and the
skeleton lines in green, and publishes the result on `/vision_image`
(`sensor_msgs/msg/CompressedImage`, jpeg) at most `image_rate_hz` times per second with
`jpeg_quality`. Set `show_window` to true to also show an OpenCV window.
