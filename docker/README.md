# Docker (AIMS)

Este Dockerfile e voltado principalmente para testes e onboarding rapido do ambiente.

## Build

Execute a partir da raiz do repositorio:

```bash
docker build -f ./docker/Dockerfile . -t <USUARIO>/aims-system
```

## Execucao

Se precisar de GUI, webcam e descoberta DDS em rede local, use host network/ipc/pid e mapeie os dispositivos:

```bash
docker run --rm -it \
	--device=/dev/dri:/dev/dri \
	--device=/dev/video0:/dev/video0 \
	--volume=/tmp/.X11-unix:/tmp/.X11-unix \
	--env="DISPLAY=$DISPLAY" \
	--network=host \
	--ipc=host \
	--pid=host \
	<USUARIO>/aims-system
```

O container ja define como comando padrao:

```bash
ros2 launch csi aims_core_launch.py
```

Para abrir shell interativo em vez do comando padrao:

```bash
docker run --rm -it <USUARIO>/aims-system bash
```

## Observacoes

- Em Linux desktop, pode ser necessario liberar X server com `xhost +local:`.
- Ajuste os devices conforme seu hardware (GPU, webcam, NIC etc.).
- Para cenarios distribuidos ROS2, manter `--network=host` ajuda na descoberta DDS.

Referencias:

- http://wiki.ros.org/docker/Tutorials/GUI
- https://old.reddit.com/r/ROS/comments/s2qtkl/any_luck_running_gui_applications_through_ros2/
