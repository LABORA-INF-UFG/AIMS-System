# 2D human pose keypoints of the main person in a camera frame.
# header.stamp matches the frame published on /vision/image_raw.
std_msgs/Header header
string[] names
geometry_msgs/Point[] keypoints   # x, y normalized to [0, 1]; z unused
float32[] confidence              # one value per keypoint, 0 when not detected
