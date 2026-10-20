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
from pose_estimation.trt_pose import decode, engine_path_for, letterbox, NUM_KEYPOINTS


def make_output(dets):
    """Build a raw (56, N) output from (cx, cy, w, h, score, keypoint x, y) tuples."""
    out = np.zeros((5 + 3 * NUM_KEYPOINTS, len(dets)), np.float32)
    for j, (cx, cy, w, h, score, kx, ky) in enumerate(dets):
        out[:5, j] = cx, cy, w, h, score
        out[5::3, j] = kx
        out[6::3, j] = ky
        out[7::3, j] = 0.9
    return out


def test_letterbox_pads_to_square():
    img, r, pad_x, pad_y = letterbox(np.zeros((288, 352, 3), np.uint8), 320)
    assert img.shape == (320, 320, 3)
    assert abs(r - 320 / 352) < 1e-6
    assert (pad_x, pad_y) == (0, 29)


def test_decode_picks_largest_box_and_normalizes():
    r, pad_x, pad_y = 320 / 352, 0, 29
    out = make_output([
        (100, 100, 40, 80, 0.9, 100, 100),
        (220, 160, 80, 160, 0.6, 176 * r + pad_x, 144 * r + pad_y),
        (50, 50, 300, 300, 0.1, 0, 0),  # below the box confidence: ignored
    ])
    xyn, conf = decode(out, r, pad_x, pad_y, 352, 288)
    assert xyn.shape == (NUM_KEYPOINTS, 2)
    np.testing.assert_allclose(xyn[0], [0.5, 0.5], atol=1e-4)
    np.testing.assert_allclose(conf, 0.9, atol=1e-6)


def test_decode_without_detections():
    out = make_output([(100, 100, 40, 80, 0.1, 0, 0)])
    assert decode(out, 1.0, 0, 0, 320, 320) is None


def test_engine_path_for():
    assert engine_path_for('/m/yolov8n-pose.pt') == '/m/yolov8n-pose.jetson.engine'
