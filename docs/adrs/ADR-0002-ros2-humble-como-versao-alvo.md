# ADR-0002: ROS2 Humble como Versão Alvo do Sistema

- **Status**: Accepted
- **Data**: 2026-06-17
- **Decisores**: Luiz Fernando de Freitas Oliveira
- **Contexto técnico**: Migração da versão base do ROS2 utilizada no projeto

---

## Contexto

O projeto foi originalmente desenvolvido com **ROS2 Foxy** (EOL: Junho 2023). A versão Foxy não recebe mais patches de segurança ou atualizações de pacotes. Além disso, os pacotes essenciais do projeto (como `rosbridge_suite` e `ros-dev-tools`) possuem suporte oficial aprimorado nas versões mais recentes do ROS2.

A equipe precisava decidir qual versão LTS do ROS2 adotar para a base do contêiner Docker, equilibrando estabilidade com suporte a longo prazo.

## Decisão

Migrar a imagem base dos contêineres ROS2 de `ros:foxy` para **`ros:humble-ros-base`** (ROS2 Humble Hawksbill).

## Alternativas Consideradas

| Alternativa | Motivo de descarte |
|---|---|
| **Foxy** (manter) | EOL desde Junho 2023. Sem patches de segurança. Pacotes com suporte reduzido nos repositórios apt. |
| **Galactic** | EOL desde Dezembro 2022. Descartado pelo mesmo motivo. |
| **Iron** (LTS) | Versão LTS mais recente, mas lançada em Maio 2024 — muito recente para garantir estabilidade dos pacotes do ecossistema Python/CSI utilizados no projeto à época da decisão. |
| **Jazzy Jalisco** | Versão de desenvolvimento ativa; menor estabilidade e compatibilidade garantida com a `PicoscenesToolbox`. |

## Motivos da Escolha do Humble

1. **LTS com suporte estendido**: Humble tem suporte até Maio de 2027, garantindo estabilidade para o período de pesquisa do projeto.
2. **Compatibilidade com Ubuntu 22.04 (Jammy)**: a imagem base oficial `ros:humble-ros-base` é construída sobre Ubuntu 22.04, a plataforma de laboratório utilizada.
3. **Suporte completo ao `rosbridge_suite`**: o pacote `ros-humble-rosbridge-server` está disponível nos repositórios apt oficiais.
4. **Compatibilidade com a `PicoscenesToolbox`**: a biblioteca oficial de desserialização do PicoScenes é instalada do repositório pip e foi validada neste ambiente.

## Consequências

### Positivas
- Imagens Docker menores e mais eficientes (~1.5GB vs ~2.5GB com Foxy).
- Pacotes apt disponíveis e atualizados nos repositórios oficiais do ROS2.
- Suporte LTS garantido até 2027, alinhado com o horizonte do projeto de pesquisa.

### Negativas / Trade-offs
- A migração exigiu revisão e ajuste dos arquivos de launch (`aims_launch.py`, `aims_core_launch.py`) para remover integrações que dependiam de comportamentos específicos da versão Foxy.
- Eventuais colaboradores com equipamentos mais antigos (ex: Jetson Nano com ROS2 Foxy) precisam manter compatibilidade de interface via DDS, o que é gerenciado pelo `ROS_DOMAIN_ID` e pela configuração do `FastDDS`.

## Links Relacionados
- [ADR-0001](./ADR-0001-docker-compose-para-orquestracao.md) — Adoção do Docker Compose
- [ADR-0003](./ADR-0003-host-networking-para-ros2-dds.md) — Host Networking para ROS2 DDS
