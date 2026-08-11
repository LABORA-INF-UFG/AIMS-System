# Architectural Decision Records (ADRs)

Este diretório contém os **Architectural Decision Records** do projeto AIMS-System.

ADRs documentam decisões arquiteturais significativas — o contexto que as motivou, as alternativas consideradas e as consequências esperadas. O formato adotado é o [MADR (Markdown Any Decision Records)](https://adr.github.io/madr/).

## Status possíveis

| Status | Significado |
|--------|-------------|
| `Proposed` | Decisão proposta, aguardando revisão |
| `Accepted` | Decisão aprovada e em vigor |
| `Deprecated` | Decisão substituída por outra mais recente |
| `Superseded by ADR-XXXX` | Substituída por um ADR específico |

## Índice

| ADR | Título | Status | Data |
|-----|--------|--------|------|
| [ADR-0001](./ADR-0001-docker-compose-para-orquestracao.md) | Adoção de Docker Compose para Orquestração da Stack | Accepted | 2026-06-17 |
| [ADR-0002](./ADR-0002-ros2-humble-como-versao-alvo.md) | ROS2 Humble como Versão Alvo do Sistema | Accepted | 2026-06-17 |
| [ADR-0003](./ADR-0003-host-networking-para-ros2-dds.md) | Host Networking para Serviços ROS2 no Docker | Accepted | 2026-06-17 |
| [ADR-0004](./ADR-0004-rosbridge-como-camada-de-integracao-web-ros2.md) | Rosbridge como Camada de Integração entre ROS2 e Web | Accepted | 2026-06-17 |
| [ADR-0005](./ADR-0005-tailwindcss-v4-como-framework-de-estilizacao.md) | TailwindCSS v4 como Framework de Estilização da Interface Web | Accepted | 2026-06-17 |

## Como criar um novo ADR

1. Crie um arquivo seguindo o padrão `ADR-XXXX-titulo-em-kebab-case.md`
2. Use o template abaixo como base
3. Atualize este índice

### Template

```markdown
# ADR-XXXX: Título da Decisão

- **Status**: Proposed | Accepted | Deprecated | Superseded by ADR-XXXX
- **Data**: YYYY-MM-DD
- **Decisores**: [nomes ou times envolvidos]
- **Contexto técnico**: [breve descrição do contexto]

---

## Contexto

[Descreva o problema ou necessidade que motivou a decisão.]

## Decisão

[Descreva a decisão tomada de forma clara e objetiva.]

## Alternativas Consideradas

| Alternativa | Motivo de descarte |
|---|---|
| Alternativa A | ... |
| Alternativa B | ... |

## Consequências

### Positivas
- ...

### Negativas / Trade-offs
- ...

## Links Relacionados
- [ADR-XXXX](./ADR-XXXX-...) — Título
```
