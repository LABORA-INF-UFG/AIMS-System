# Documentação — AIMS-System

Este diretório centraliza a documentação técnica do projeto AIMS-System.

## Estrutura

```
docs/
├── README.md          # Este arquivo
├── CHANGELOG.md       # Histórico de alterações do projeto
└── adrs/              # Architectural Decision Records
    ├── README.md      # Índice dos ADRs
    ├── ADR-0001-...   # Adoção do Docker Compose
    ├── ADR-0002-...   # ROS2 Humble como versão alvo
    ├── ADR-0003-...   # Host Networking para ROS2 DDS
    ├── ADR-0004-...   # Rosbridge como camada de integração
    └── ADR-0005-...   # TailwindCSS v4 como framework de estilização
```

## O que é cada documento?

### [CHANGELOG.md](./CHANGELOG.md)
Registro cronológico de todas as alterações significativas do projeto, seguindo o padrão [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/).

### [adrs/](./adrs/README.md)
**Architectural Decision Records (ADRs)** documentam as decisões arquiteturais tomadas durante o desenvolvimento, incluindo o contexto, as alternativas consideradas e as consequências de cada decisão. O formato adotado é o **MADR (Markdown Any Decision Records)**.
