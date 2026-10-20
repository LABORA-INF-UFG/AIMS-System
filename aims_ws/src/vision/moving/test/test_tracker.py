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

from moving.tracker import JOINT_NAMES, KalmanFilterKeypoint, MotionHold, MotionTracker
import numpy as np
import pytest

DT = 1.0 / 15.0


def body_frame(offset_x=0.0, missing=()):
    """Return 17 keypoints and confidences with the body joints (5..14) at a fixed pose."""
    keypoints = [(0.0, 0.0)] * 17
    confidence = [0.0] * 17
    for i in range(5, 15):
        if i not in missing:
            keypoints[i] = (0.3 + 0.02 * i + offset_x, 0.1 + 0.05 * i)
            confidence[i] = 0.9
    return keypoints, confidence


def test_kalman_estimates_constant_velocity():
    kf = KalmanFilterKeypoint(0.0, 0.0, dt=DT)
    for step in range(1, 60):
        kf.predict(dt=DT)
        kf.update(np.array([[0.3 * step * DT], [0.0]], dtype=np.float32))
    assert kf.x[2, 0] == pytest.approx(0.3, abs=0.02)
    assert kf.x[3, 0] == pytest.approx(0.0, abs=0.02)


def test_still_person_is_not_moving():
    tracker = MotionTracker()
    for _ in range(30):
        assert tracker.update(*body_frame(), DT) == {}


def test_walking_person_is_moving():
    tracker = MotionTracker(velocity_threshold=0.15)
    for step in range(30):
        moving = tracker.update(*body_frame(offset_x=0.5 * step * DT), DT)
    assert sorted(moving) == sorted(JOINT_NAMES)
    assert all(speed > 0.15 for speed in moving.values())


def test_lost_joint_is_dropped_after_max_lost_frames():
    tracker = MotionTracker(max_lost_frames=2)
    tracker.update(*body_frame(), DT)
    left_shoulder = 0
    for _ in range(2):
        tracker.update(*body_frame(missing=(5,)), DT)
        assert tracker.trackers[left_shoulder] is not None
    tracker.update(*body_frame(missing=(5,)), DT)
    assert tracker.trackers[left_shoulder] is None


def test_reset_clears_tracks():
    tracker = MotionTracker()
    tracker.update(*body_frame(), DT)
    tracker.reset()
    assert tracker.trackers == [None] * len(JOINT_NAMES)


def test_motion_hold_keeps_motion_for_hold_sec():
    hold = MotionHold(hold_sec=1.0)
    assert hold.update(True, 10.0)
    assert hold.update(False, 10.5)
    assert not hold.update(False, 11.0)


def test_motion_hold_is_false_before_any_motion():
    assert not MotionHold(hold_sec=1.0).update(False, 10.0)
