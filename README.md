
# AIMS System

**A**dvanced **M**ult**I**Modal **S**ensing — Sistema de monitoramento contactless de sinais vitais baseado em Wi-Fi CSI, ROS2 e interface web.

## Arquitetura

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  HOST (Linux)                                                                │
│  ┌──────────────────┐          UDP (packet-forward)                          │
│  │   PicoScenes      │────────────────────────────────────┐                  │
│  │   (IWL5300 NIC)   │         127.0.0.1:1025             │                  │
│  └──────────────────┘                                     │                  │
├───────────────────────────────────────────────────────────┼──────────────────┤
│  DOCKER (network_mode: host)                              ▼                  │
│  ┌──────────────────────────────────────────────────────────────────────┐    │
│  │  ros2-nodes                                                          │    │
│  │  ├─ csi_publisher (recebe UDP, faz parse, publica /pktcsi)           │    │
│  │  ├─ breath_estimator (estima respiração, publica /estimativebreath)  │    │
│  │  ├─ csi_heatmap_publisher (publica /heatmap)                         │    │
│  │  ├─ persistence_action (salva capturas em disco)                     │    │
│  │  └─ persistence_bridge                                               │    │
│  └──────────────────────────────────────────────────────────────────────┘    │
│  ┌──────────────────────────────────────────────────────────────────────┐    │
│  │  rosbridge (WebSocket :9090 ↔ DDS)                                   │    │
│  └──────────────────────────────────────────────────────────────────────┘    │
├──────────────────────────────────────────────────────────────────────────────┤
│  DOCKER (bridge network)                                                     │
│  ┌───────────────────────┐    ┌──────────────────┐                           │
│  │  web (:3001)           │    │  mongo (:27017)   │                          │
│  │  Express.js            │───▶│  MongoDB 7        │                          │
│  │  Patient management    │    │  Volume persist.  │                          │
│  └───────────────────────┘    └──────────────────┘                           │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Início Rápido (Docker)

### Pré-requisitos

- [Docker](https://docs.docker.com/get-docker/) e [Docker Compose](https://docs.docker.com/compose/install/)
- PicoScenes instalado no host (apenas se usar hardware real — ver [picoscenes/README.md](picoscenes/README.md))

### 1. Configurar variáveis de ambiente

```bash
cp .env.example .env
# Edite .env conforme necessário
```

### 2. Subir a stack

```bash
# Build e start de todos os serviços
docker compose up -d --build

# Acompanhar logs
docker compose logs -f
```

### 3. Acessar

- **Interface web**: http://localhost:3001
- **Rosbridge WebSocket**: ws://localhost:9090

### 4. Parar

```bash
docker compose down
```

## Serviços

| Serviço | Descrição | Rede | Porta |
|---------|-----------|------|-------|
| `ros2-nodes` | Nós ROS2 de processamento CSI | host | — |
| `rosbridge` | Ponte WebSocket ↔ DDS | host | 9090 |
| `web` | Express.js (pacientes + monitoramento) | bridge | 3001 |
| `mongo` | MongoDB (dados de pacientes) | bridge | 27017 |

## Nós ROS2 e Tópicos

| Nó | Função | Tópicos |
|---|---|---|
| `csi_publisher` | Recebe frame CSI do PicoScenes via UDP, faz parse e publica | `/pktcsi` |
| `mock_csi` | Simula envio de pacotes CSI a partir de arquivo | `/pktcsi` |
| `breath_estimator` | Estimativa de respiração e detecção de apneia | `/estimativebreath` |
| `csi_heatmap_publisher` | Publica heatmap para feedback visual | `/heatmap` |
| `persistence_action` | Action server para persistir capturas CSI | `/persist_csi` |
| `persistence_bridge` | Ponte de persistência para interação web | — |

## Variáveis de Ambiente

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `ROS_DOMAIN_ID` | `5` | Domínio DDS para isolamento de rede ROS2 |
| `RMW_IMPLEMENTATION` | `rmw_fastrtps_cpp` | Middleware ROS2 |
| `CSI_UDP_PORT` | `1025` | Porta UDP para receber frames do PicoScenes |
| `WEB_PORT` | `3001` | Porta do servidor web |
| `MONGO_URI` | `mongodb://mongo:27017/mycaredb` | String de conexão MongoDB |
| `ROSBRIDGE_PORT` | `9090` | Porta WebSocket do rosbridge |
| `KERAS_APNEA_MODEL` | `/app/models/...` | Caminho para modelo de IA (volume) |

## Modos de Operação

### Com hardware PicoScenes (produção)

1. No host Linux: executar `./picoscenes_routine_rx.bash`
2. Docker: `docker compose up -d`
3. O `csi_publisher` recebe frames via UDP automaticamente

### Sem hardware (desenvolvimento)

O sistema detecta automaticamente que PicoScenes não está disponível e lança o `mock_csi` que reproduz frames do arquivo `single_csi_frame.txt`.

```bash
docker compose up -d
```

### Sistema Distribuído

Para executar nós em máquinas diferentes, mantenha o mesmo `ROS_DOMAIN_ID` em todas as máquinas e garanta conectividade de rede entre elas. O `network_mode: host` permite DDS discovery via multicast.

## Desenvolvimento Local (sem Docker)

### Dependências

- [ROS2 Humble](https://docs.ros.org/en/humble/Installation.html)
- [Node.js 18](https://nodejs.org/)
- [MongoDB 7](https://www.mongodb.com/docs/manual/installation/)
- Python 3.10+

### Build do workspace ROS2

```bash
source /opt/ros/humble/setup.bash
cd aims_ws
colcon build --symlink-install
source install/local_setup.bash
```

### Web server

```bash
cd web
cp .env.example .env
npm install
npm run dev
```

## Repositório Oficial

```
https://github.com/LABORA-INF-UFG/AIMS-System
```
