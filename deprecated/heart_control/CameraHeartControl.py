import time
from typing import Tuple

import cv2
import numpy as np


class CameraHeartControl:
    def __init__(self,
                 cam_id: int = 0,
                 target_fps: int = 30,
                 width: int = 1280,
                 height: int = 720,
                 fourcc: int = cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'),
                 focus: int = 900,
                 exposure: int = 300,
                 area_thickness: int = 3
                 ) -> None:
        self.cam_id = cam_id
        self.target_fps = target_fps
        self.width = width
        self.height = height
        self.fourcc = fourcc
        self.focus = focus
        self.exposure = exposure

        self.area_p1 = (0, 0)
        self.area_p2 = (0, 0)
        self.area_thickness = area_thickness

    def disable_auto_exposure(self, cap: cv2.VideoCapture) -> None:
        cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 3)
        cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)
        cap.set(cv2.CAP_PROP_EXPOSURE, self.exposure)

    def create_stream(self) -> cv2.VideoCapture:
        cap = cv2.VideoCapture(self.cam_id)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        cap.set(cv2.CAP_PROP_FOURCC, self.fourcc)
        cap.set(cv2.CAP_PROP_FPS, self.target_fps)
        cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)
        cap.set(cv2.CAP_PROP_FOCUS, self.focus)
        return cap

    def get_frame(self, cap: cv2.VideoCapture) -> np.ndarray:
        _, frame = cap.read()
        return frame

    def to_frame_black_white(self, frame: np.ndarray) -> np.ndarray:
        frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        frame_blur = cv2.GaussianBlur(frame_gray, (9, 9), 0)
        _, frame_black_white = cv2.threshold(frame_blur,
                                             0,
                                             255,
                                             cv2.THRESH_BINARY +
                                             cv2.THRESH_OTSU)
        return frame_black_white

    def detect_beat(self,
                    frame: np.ndarray,
                    detect_color: int = 0,
                    detect_thresh: float = 0.80) -> bool:
        if detect_thresh < 0. or detect_thresh > 1.:
            raise ValueError(f'Error: detect_thresh must be greater than 0 and'
                             f'smaller than 1. Received: {detect_thresh}')
        detection_zone = frame[self.area_p1[1] + self.area_thickness:
                               self.area_p2[1] - self.area_thickness,
                               self.area_p1[0] + self.area_thickness:
                               self.area_p2[0] - self.area_thickness].flatten()
        detected_hits = detection_zone[detection_zone == detect_color]

        detection_hit_percent = detected_hits.size / detection_zone.size
        if detection_hit_percent >= detect_thresh:
            return True
        else:
            return False

    def show_frame(self, frame: np.ndarray,
                   color: Tuple[int, int, int] = (0, 0, 0),
                   window_name: str = 'HeartRate') -> None:
        cv2.rectangle(frame, self.area_p1, self.area_p2,
                      color, self.area_thickness)
        cv2.imshow(window_name, frame)

    def select_area(self, window_name: str, drawing=[False]) -> None:
        cv2.namedWindow(window_name)
        def on_mouse(event, x, y, flags, param):
            if event == cv2.EVENT_LBUTTONDOWN:
                self.area_p1 = (x, y)
                self.area_p2 = (x, y)
                drawing[0] = True
            elif event == cv2.EVENT_MOUSEMOVE and drawing[0]:
                self.area_p2 = (x, y)
            if event == cv2.EVENT_LBUTTONUP:
                drawing[0] = False
                self.area_p2 = (x, y)
        cv2.setMouseCallback(window_name, on_mouse)


if __name__ == "__main__":
    heart_control = CameraHeartControl()
    video_stream = heart_control.create_stream()
    _ = heart_control.get_frame(video_stream)
    heart_control.disable_auto_exposure(video_stream)
    while True:
        start = time.time()

        frame = heart_control.get_frame(video_stream)
        frame = heart_control.to_frame_black_white(frame)
        heart_control.show_frame(frame)
        print(heart_control.detect_beat(frame))

        end = time.time()
        print(f'fps: {1 / (end - start)}')

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cv2.destroyAllWindows()
    video_stream.release()
