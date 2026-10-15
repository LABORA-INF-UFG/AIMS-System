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

from there_is_person.presence import is_person

NOT_DETECTED = (0.0, 0.0)


def frame(body_points):
    """Build 17 keypoints with the given body points (indices 5..14) detected."""
    keypoints = [NOT_DETECTED] * 17
    confidence = [0.0] * 17
    for i, point in enumerate(body_points):
        keypoints[5 + i] = point
        confidence[5 + i] = 0.9
    return keypoints, confidence


def test_spread_body_is_person():
    points = [(0.4 + 0.1 * (i % 2), 0.2 + 0.07 * i) for i in range(10)]
    assert is_person(*frame(points))


def test_too_few_points_is_not_person():
    points = [(0.4 + 0.1 * (i % 2), 0.2 + 0.07 * i) for i in range(5)]
    assert not is_person(*frame(points))


def test_clustered_points_are_not_person():
    points = [(0.5 + 0.001 * i, 0.5 + 0.001 * i) for i in range(10)]
    assert not is_person(*frame(points))


def test_spread_on_one_axis_only_is_not_person():
    points = [(0.5, 0.1 * i) for i in range(10)]
    assert not is_person(*frame(points))


def test_face_and_ankles_are_ignored():
    keypoints, confidence = frame([])
    for i in (0, 1, 2, 3, 4, 15, 16):
        keypoints[i] = (0.1 * i / 2, 0.06 * i)
        confidence[i] = 0.9
    assert not is_person(keypoints, confidence)


def test_thresholds_are_configurable():
    points = [(0.4 + 0.1 * (i % 2), 0.2 + 0.07 * i) for i in range(4)]
    assert not is_person(*frame(points))
    assert is_person(*frame(points), min_points=4, min_std=0.02)
