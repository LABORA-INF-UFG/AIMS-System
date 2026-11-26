# Thin wrapper around Docker Compose. Optional: `make` is not required.
# Mock mode needs nothing else than:  docker compose up -d --build
# (Windows users without make can run the commands below directly.)

.PHONY: up up-hardware up-vision up-vision-gpu up-vision-jetson down logs build host-setup

up:            ## Start in mock mode (no hardware)
	docker compose up -d --build

up-hardware:   ## Start with real CSI from PicoScenes on this host
	CSI_SOURCE=picoscenes docker compose up -d --build

up-vision:     ## Also start camera pose estimation (CPU)
	docker compose --profile vision up -d --build

up-vision-gpu: ## Same on an NVIDIA GPU (CUDA + TensorRT image)
	docker compose -f docker-compose.yml -f docker-compose.gpu.yml --profile vision up -d --build

up-vision-jetson: ## Same on a Jetson with JetPack 4.6 (plain TensorRT image)
	docker compose -f docker-compose.yml -f docker-compose.jetson.yml --profile vision up -d --build

down:
	docker compose --profile vision down

logs:
	docker compose logs -f

build:
	docker compose build

host-setup:    ## Install PicoScenes on this Linux host (reboot afterwards)
	scripts/host/install_picoscenes.sh
