## there_is_person

No de deteccao de pessoa baseado em TensorFlow Lite.

## Build

```bash
cd aims_ws
source /opt/ros/foxy/setup.bash
colcon build
source install/setup.bash
```

## Run

```bash
ros2 run there_is_person is_person
```

## Requisitos

- Variavel `AIMS` apontando para a raiz do repositorio.
- Arquivo do modelo em `resources/lite-model_movenet_singlepose_thunder_tflite_float16_4.tflite`.
- Webcam conectada para captura de video.