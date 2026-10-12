# Thin wrapper around Docker Compose. Optional: `make` is not required.
# Mock mode needs nothing else than:  docker compose up -d --build
# (Windows users without make can run the commands below directly.)

.PHONY: up up-hardware down logs build host-setup

up:            ## Start in mock mode (no hardware)
	docker compose up -d --build

up-hardware:   ## Start with real CSI from PicoScenes on this host
	CSI_SOURCE=picoscenes docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f

build:
	docker compose build

host-setup:    ## Install PicoScenes on this Linux host (reboot afterwards)
	scripts/host/install_picoscenes.sh
