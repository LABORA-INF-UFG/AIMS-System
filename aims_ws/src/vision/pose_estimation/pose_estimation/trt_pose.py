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

import ctypes
import os

import cv2
import numpy as np

# ultralytics predict() defaults, so both backends pick the same main person.
BOX_CONF = 0.25
NMS_IOU = 0.7
NUM_KEYPOINTS = 17

_CUDA_MEMCPY_HOST_TO_DEVICE = 1
_CUDA_MEMCPY_DEVICE_TO_HOST = 2


def engine_path_for(model_path):
    """Return the Jetson engine path for a model (.pt or .onnx) path."""
    return os.path.splitext(model_path)[0] + '.jetson.engine'


def letterbox(frame, size):
    """Resize keeping the aspect ratio and pad to size x size, like ultralytics LetterBox."""
    h, w = frame.shape[:2]
    r = min(size / h, size / w)
    new_w, new_h = int(round(w * r)), int(round(h * r))
    pad_x, pad_y = (size - new_w) / 2, (size - new_h) / 2
    if (new_w, new_h) != (w, h):
        frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
    top, left = int(round(pad_y - 0.1)), int(round(pad_x - 0.1))
    bottom, right = size - new_h - top, size - new_w - left
    frame = cv2.copyMakeBorder(frame, top, bottom, left, right, cv2.BORDER_CONSTANT,
                               value=(114, 114, 114))
    return frame, r, left, top


def decode(output, r, pad_x, pad_y, width, height, box_conf=BOX_CONF, iou=NMS_IOU):
    """
    Return (xyn, conf) of the main person in one raw YOLOv8-pose output, or None.

    output is (56, N): cx, cy, w, h, score, then x, y, conf for each keypoint, in
    letterboxed input pixels. The main person is the largest box left after NMS.
    """
    scores = output[4]
    keep = scores >= box_conf
    if not np.any(keep):
        return None
    det = output[:, keep]
    cx, cy, bw, bh = det[0], det[1], det[2], det[3]
    boxes = np.stack([cx - bw / 2, cy - bh / 2, bw, bh], axis=1)
    idx = cv2.dnn.NMSBoxes(boxes.tolist(), det[4].tolist(), box_conf, iou)
    idx = np.array(idx).reshape(-1)
    if idx.size == 0:
        return None
    main = idx[int(np.argmax(bw[idx] * bh[idx]))]
    kpts = det[5:5 + 3 * NUM_KEYPOINTS, main].reshape(NUM_KEYPOINTS, 3)
    x = (kpts[:, 0] - pad_x) / r / width
    y = (kpts[:, 1] - pad_y) / r / height
    xyn = np.clip(np.stack([x, y], axis=1), 0.0, 1.0)
    return xyn, kpts[:, 2]


class _Cuda:
    """The few libcudart calls needed to feed a TensorRT execution context."""

    def __init__(self):
        try:
            self.lib = ctypes.CDLL('libcudart.so')
        except OSError:
            self.lib = ctypes.CDLL('/usr/local/cuda/lib64/libcudart.so')

    def check(self, err, what):
        if err != 0:
            self.lib.cudaGetErrorString.restype = ctypes.c_char_p
            raise RuntimeError(f'{what} failed: {self.lib.cudaGetErrorString(err).decode()}')

    def malloc(self, nbytes):
        ptr = ctypes.c_void_p()
        self.check(self.lib.cudaMalloc(ctypes.byref(ptr), ctypes.c_size_t(nbytes)), 'cudaMalloc')
        return ptr

    def to_device(self, dst, array):
        self.check(self.lib.cudaMemcpy(dst, array.ctypes.data_as(ctypes.c_void_p),
                                       ctypes.c_size_t(array.nbytes),
                                       _CUDA_MEMCPY_HOST_TO_DEVICE), 'cudaMemcpy H2D')

    def to_host(self, array, src):
        self.check(self.lib.cudaMemcpy(array.ctypes.data_as(ctypes.c_void_p), src,
                                       ctypes.c_size_t(array.nbytes),
                                       _CUDA_MEMCPY_DEVICE_TO_HOST), 'cudaMemcpy D2H')


def build_engine(onnx_path, engine_path, trt, logger, workspace_mb=256):
    """Build an FP16 TensorRT engine from an ONNX file and save it next to it."""
    builder = trt.Builder(logger)
    network = builder.create_network(
        1 << int(trt.NetworkDefinitionCreationFlag.EXPLICIT_BATCH))
    parser = trt.OnnxParser(network, logger)
    with open(onnx_path, 'rb') as f:
        if not parser.parse(f.read()):
            errors = [str(parser.get_error(i)) for i in range(parser.num_errors)]
            raise RuntimeError(f'Could not parse {onnx_path}: ' + '; '.join(errors))
    config = builder.create_builder_config()
    config.max_workspace_size = workspace_mb << 20
    if builder.platform_has_fast_fp16:
        config.set_flag(trt.BuilderFlag.FP16)
    serialized = builder.build_serialized_network(network, config)
    if serialized is None:
        raise RuntimeError(f'TensorRT could not build an engine from {onnx_path}')
    # Write then rename, so an interrupted build never leaves a broken engine behind.
    tmp = engine_path + '.tmp'
    with open(tmp, 'wb') as f:
        f.write(serialized)
    os.replace(tmp, engine_path)


class TrtPose:
    """YOLOv8-pose TensorRT engine with a fixed 1x3xSxS input."""

    def __init__(self, model_path, log=print):
        import tensorrt as trt

        logger = trt.Logger(trt.Logger.WARNING)
        trt.init_libnvinfer_plugins(logger, '')
        self.engine_path = engine_path_for(model_path)
        if not os.path.exists(self.engine_path):
            onnx_path = os.path.splitext(model_path)[0] + '.onnx'
            if not os.path.exists(onnx_path):
                raise FileNotFoundError(
                    f'Neither {self.engine_path} nor {onnx_path} exists')
            log(f'Building {self.engine_path} from {onnx_path} (FP16), '
                'this takes several minutes the first time...')
            build_engine(onnx_path, self.engine_path, trt, logger)

        with open(self.engine_path, 'rb') as f:
            self.engine = trt.Runtime(logger).deserialize_cuda_engine(f.read())
        if self.engine is None:
            raise RuntimeError(
                f'Could not load {self.engine_path}; delete it to rebuild it from the ONNX')
        self.context = self.engine.create_execution_context()

        self.cuda = _Cuda()
        self.inputs, self.outputs, self.bindings = [], [], []
        for i in range(self.engine.num_bindings):
            shape = tuple(self.engine.get_binding_shape(i))
            dtype = trt.nptype(self.engine.get_binding_dtype(i))
            host = np.empty(shape, dtype=dtype)
            device = self.cuda.malloc(host.nbytes)
            self.bindings.append(device.value)
            (self.inputs if self.engine.binding_is_input(i) else self.outputs).append(
                (host, device))
        self.imgsz = self.inputs[0][0].shape[-1]

    def __call__(self, frame):
        """Return (xyn, conf) of the main person in a BGR frame, or None."""
        h, w = frame.shape[:2]
        img, r, pad_x, pad_y = letterbox(frame, self.imgsz)
        blob = img[:, :, ::-1].transpose(2, 0, 1)[np.newaxis].astype(np.float32) / 255.0
        host_in, device_in = self.inputs[0]
        host_in[...] = blob
        self.cuda.to_device(device_in, host_in)
        if not self.context.execute_v2(self.bindings):
            raise RuntimeError('TensorRT inference failed')
        host_out, device_out = self.outputs[0]
        self.cuda.to_host(host_out, device_out)
        return decode(host_out[0], r, pad_x, pad_y, w, h)
