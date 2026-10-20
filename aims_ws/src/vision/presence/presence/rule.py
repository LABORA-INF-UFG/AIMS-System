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

import numpy as np

# Body keypoints used for the decision: shoulders, elbows, wrists, hips and knees.
BODY = slice(5, 15)


def is_person(keypoints, confidence, min_points=6, min_std=0.045):
    """
    Decide whether the keypoints of a frame belong to a person.

    keypoints is a sequence of 17 (x, y) pairs normalized to [0, 1] and confidence holds
    one value per keypoint (0 when not detected). A person is present when at least
    min_points body keypoints are detected and they are spread by at least min_std on
    both axes (a tight cluster of points is a false positive).
    """
    points = np.array([p for p, c in zip(keypoints[BODY], confidence[BODY]) if c > 0.0])
    if len(points) < min_points:
        return False
    std_x, std_y = points.std(axis=0)
    return bool(std_x >= min_std and std_y >= min_std)


class Hysteresis:
    """Change the reported state only after min_frames consecutive frames disagree with it."""

    def __init__(self, min_frames, state=False):
        self.min_frames = min_frames
        self.state = state
        self.count = 0

    def update(self, value):
        if value == self.state:
            self.count = 0
        else:
            self.count += 1
            if self.count >= self.min_frames:
                self.state = value
                self.count = 0
        return self.state
