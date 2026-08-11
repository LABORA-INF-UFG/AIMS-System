# ADR-0003: Host Networking para Serviços ROS2 no Docker

- **Status**: Accepted
- **Data**: 2026-06-17
- **Decisores**: Luiz Fernando de Freitas Oliveira
- **Contexto técnico**: Configuração de rede para comunicação DDS entre contêineres e host

---

## Contexto

O ROS2 utiliza o middleware **DDS (Data Distribution Service)** para a descoberta e comunicação entre nós. A descoberta de participantes DDS ocorre via **multicast UDP** na rede local, o que conflita com o funcionamento padrão de redes bridge do Docker (`docker0`).

Em uma topologia Docker bridge:
- Contêineres ficam isolados em uma rede virtual separada (`172.x.x.x`)
- O multicast UDP não atravessa a interface bridge por padrão
- Nós ROS2 dentro de contêineres não conseguem descobrir nós no host ou em outros contêineres sem configuração adicional complexa

Além disso, o PicoScenes — que roda **obrigatoriamente no host Linux** por precisar de acesso direto à placa de rede Wi-Fi — envia pacotes UDP via packet-forwarding para o endereço `127.0.0.1:1025`. Contêineres em bridge networking não podem receber pacotes enviados para `localhost` do host.

## Decisão

Configurar os serviços `ros2-nodes` e `rosbridge` com `network_mode: "host"` e `ipc: host` no `docker-compose.yml`.

```yaml
ros2-nodes:
  network_mode: "host"
  ipc: host

rosbridge:
  network_mode: "host"
  ipc: host
```

## Alternativas Consideradas

| Alternativa | Motivo de descarte |
|---|---|
| **Docker bridge + DDS multicast config** | Exige configuração avançada de rotas de multicast, mapeamento de interfaces e é instável com FastDDS em ambientes de laboratório. |
| **Cyclone DDS com unicast discovery** | Possível, mas exige conhecimento aprofundado de `CYCLONE_URI` XML e é incompatível com o perfil FastDDS (`fastdds_profile.xml`) já em uso no projeto. |
| **Docker Macvlan** | Requer privilégios de rede adicionais no host e configuração complexa de L2; inadequado para ambiente laboratorial compartilhado. |
| **ROS2 via socket proxy (zenoh-bridge)** | Introduz latência adicional e um componente de infraestrutura novo em um sistema já complexo. |

## Consequências

### Positivas
- Descoberta DDS entre o host (PicoScenes) e os contêineres funciona naticamente sem configuração adicional.
- Nós ROS2 no contêiner recebem pacotes UDP enviados ao `localhost` do host.
- Zero overhead de NAT ou proxy para tráfego de dados de CSI (alta frequência, ~1000 pacotes/s).
- Compatibilidade total com o arquivo `fastdds_profile.xml` existente.

### Negativas / Trade-offs
- **`network_mode: host` só funciona em Linux**. Em macOS e Windows, o Docker não suporta este modo, o que torna o desenvolvimento/teste fora de máquinas Linux impossível com a stack completa.
- Isolamento de rede reduzido: os contêineres ROS2 compartilham o namespace de rede do host, expondo todas as portas sem binding explícito.
- Potencial conflito de portas com outros serviços rodando no host na mesma porta (ex: 9090 do rosbridge).

### Mitigação
- O `ROS_DOMAIN_ID` (padrão: `5`) é configurável via `.env` para evitar colisões com outras instâncias ROS2 na rede local do laboratório.
- O `FastDDS` é configurado via `fastdds_profile.xml` para restringir interfaces de comunicação, reduzindo o risco de colisão de tráfego.

## Links Relacionados
- [ADR-0001](./ADR-0001-docker-compose-para-orquestracao.md) — Adoção do Docker Compose
- [ADR-0002](./ADR-0002-ros2-humble-como-versao-alvo.md) — ROS2 Humble como versão alvo
