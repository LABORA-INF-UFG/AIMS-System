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

import time

# How long read() waits for a frame before reporting a failed read.
READ_TIMEOUT_SEC = 1.0


class OakCamera:
    """RGB preview of the OAK color camera, as BGR frames of width x height."""

    def __init__(self, width, height, fps, log=print):
        import depthai as dai

        pipeline = dai.Pipeline()
        cam = pipeline.create(dai.node.ColorCamera)
        cam.setBoardSocket(dai.CameraBoardSocket.CAM_A)
        cam.setResolution(dai.ColorCameraProperties.SensorResolution.THE_1080_P)
        # The preview is center-cropped to the requested aspect ratio, not stretched.
        cam.setPreviewSize(width, height)
        cam.setInterleaved(False)
        cam.setColorOrder(dai.ColorCameraProperties.ColorOrder.BGR)
        cam.setFps(fps)
        xout = pipeline.create(dai.node.XLinkOut)
        xout.setStreamName('rgb')
        cam.preview.link(xout.input)

        self.device = None
        try:
            self.device = dai.Device(pipeline)
        except RuntimeError as e:
            log(f'Could not open the OAK camera: {e}')
            return
        self.queue = self.device.getOutputQueue('rgb', maxSize=1, blocking=False)
        log(f'OAK camera {self.device.getMxId()} on USB {self.device.getUsbSpeed().name}')

    def isOpened(self):  # noqa: N802 (cv2.VideoCapture name)
        return self.device is not None and not self.device.isClosed()

    def read(self):
        """Return (ok, frame) like cv2.VideoCapture.read; ok is False after a timeout."""
        if not self.isOpened():
            return False, None
        deadline = time.monotonic() + READ_TIMEOUT_SEC
        try:
            while time.monotonic() < deadline:
                msg = self.queue.tryGet()
                if msg is not None:
                    return True, msg.getCvFrame()
                time.sleep(0.005)
        except RuntimeError:
            # depthai raises once the device is gone (unplugged, USB error)
            pass
        return False, None

    def release(self):
        if self.device is not None:
            self.device.close()
