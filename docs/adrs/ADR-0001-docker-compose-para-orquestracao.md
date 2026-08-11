# ADR-0001: Adoção de Docker Compose para Orquestração da Stack

- **Status**: Accepted
- **Data**: 2026-06-17
- **Decisores**: Luiz Fernando de Freitas Oliveira
- **Contexto técnico**: Containerização da infraestrutura AIMS-System

---

## Contexto

O AIMS-System era executado manualmente por meio de múltiplos scripts Bash e comandos individuais (`docker run`, `ros2 launch`, `npm start`), exigindo que cada membro do laboratório seguisse uma sequência de inicialização frágil e documentada informalmente. O ambiente combinava:

- Um nó de hardware real (PicoScenes, no host Linux)
- Nós de processamento ROS2 em Python
- Um servidor Web Express.js
- Um banco de dados MongoDB

Cada componente precisava de configuração manual de variáveis de ambiente, portas e endereços IP.

## Decisão

Adotar o **Docker Compose** como ferramenta de orquestração da stack de desenvolvimento e produção do AIMS-System, com todos os serviços (exceto o PicoScenes, que exige acesso direto ao hardware) definidos no arquivo `docker-compose.yml`.

## Alternativas Consideradas

| Alternativa | Motivo de descarte |
|---|---|
| Manter scripts Bash manuais | Frágil, difícil de reproduzir, sem garantia de isolamento de ambiente. |
| Kubernetes (k8s) | Overkill para o contexto acadêmico/laboratorial com uma única máquina. Curva de aprendizado desnecessariamente alta para o time. |
| Podman Compose | Menor ecossistema de suporte, equipe mais familiarizada com Docker. |
| Docker Swarm | Maior complexidade sem benefício claro para single-node deployment. |

## Consequências

### Positivas
- Inicialização de toda a stack com um único comando: `docker compose up -d --build`.
- Variáveis de ambiente centralizadas em `.env` e `.env.example`.
- Isolamento de dependências entre os serviços.
- Volumes nomeados para persistência de dados do MongoDB e capturas de CSI.
- Healthchecks declarativos para verificação de prontidão dos serviços.

### Negativas / Trade-offs
- `network_mode: host` é necessário para os serviços ROS2 (DDS discovery por multicast UDP), o que reduz o isolamento de rede nesses contêineres.
- O Docker Compose não é suportado diretamente no macOS/Windows com `network_mode: host`; o desenvolvimento local na máquina Linux de produção permanece sendo o fluxo primário.

## Links Relacionados
- [ADR-0002](./ADR-0002-ros2-humble-como-versao-alvo.md) — ROS2 Humble como versão alvo
- [ADR-0003](./ADR-0003-host-networking-para-ros2-dds.md) — Host Networking para ROS2 DDS
