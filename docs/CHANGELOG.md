# Changelog

Todas as alterações relevantes do projeto AIMS-System são documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/),
e este projeto adere ao [Versionamento Semântico](https://semver.org/lang/pt-BR/).

---

## [Unreleased]

### Planned
- Fase 3: Refatoração dos nós ROS2 (type hints, logging estruturado, separação de responsabilidades)
- Fase 4: Pipeline de CI/CD

---

## [0.2.0] — 2026-06-17

### Fase 2 — Migração de Bootstrap para TailwindCSS v4

#### Added
- `web/public/assets/css/input.css`: ponto de entrada do TailwindCSS v4 com tokens de design customizados via diretiva `@theme` (cores primárias, fontes e utilitários da identidade visual AIMS).
- `web/package.json`: script `build:css` para compilar o CSS com `@tailwindcss/cli`.

#### Changed
- **`docker/web/Dockerfile`**: imagem base atualizada de `node:18-alpine` para `node:20-alpine` (requisito do compilador Rust-based do Tailwind v4). Adicionado estágio de `builder` para compilação do `tailwind.css` estático, copiado para o estágio de `runtime`.
- **`web/app.js`**: removidos os mapeamentos estáticos das pastas `node_modules/bootstrap/` e `node_modules/jquery/`, que não são mais necessários.
- **`web/public/index.html`**: refatorado para TailwindCSS v4. Novo layout em grid de cards com hover animado, substituindo a estrutura baseada em Bootstrap.
- **`web/views/registration.html`**: refatorado para TailwindCSS v4. Formulário com inputs com foco customizado e transições suaves.
- **`web/views/patients.html`**: refatorado para TailwindCSS v4. O JavaScript que gera dinamicamente os resultados de busca agora injeta classes utilitárias do Tailwind nos elementos criados.
- **`web/views/monitoring.html`**: refatorado para TailwindCSS v4. A navegação de abas (Tabs) dos gráficos e o painel deslizante de persistência (Drawer) foram reimplementados com JavaScript Vanilla + transições CSS nativas do Tailwind, removendo a dependência do `bootstrap.min.js` e do jQuery.

#### Removed
- Dependências `bootstrap` e `jquery` de `web/package.json`.
- Arquivos CSS legados: `main.css`, `style.css` e todos os arquivos `variables*.css`.
- Diretórios de vendor não utilizados: `assets/vendor/aos`, `assets/vendor/bootstrap`, `assets/vendor/boxicons`, `assets/vendor/glightbox`, `assets/vendor/isotope-layout`, `assets/vendor/php-email-form`, `assets/vendor/purecounter`, `assets/vendor/remixicon`, `assets/vendor/swiper`.

---

## [0.1.0] — 2026-06-17

### Fase 1 — Containerização e Migração para ROS2 Humble

#### Added
- **`docker-compose.yml`**: orquestração multi-serviço com 4 serviços (`ros2-nodes`, `rosbridge`, `web`, `mongo`), substituindo o processo de execução manual com `docker run`.
- **`docker/ros2/Dockerfile`**: Dockerfile multi-stage para os nós ROS2 (`builder` + `runtime`), baseado na imagem oficial `ros:humble-ros-base`. Inclui instalação da `PicoscenesToolbox` do repositório oficial.
- **`docker/ros2/entrypoint.sh`**: script de entrypoint que realiza o `source` do ambiente ROS2 e do workspace compilado antes de executar o CMD.
- **`docker/web/Dockerfile`**: Dockerfile multi-stage para o servidor web (`builder` + `runtime`), baseado em `node:20-alpine`.
- **`.env`** e **`.env.example`**: centralização de todas as variáveis de ambiente da stack (portas, URIs, configurações ROS2).
- **`web/.env.example`**: template de variáveis de ambiente para execução local sem Docker.
- **`aims_ws/src/csi/launch/aims_mock_launch.py`**: arquivo de launch dedicado para testes com dados mockados, sem depender do hardware PicoScenes.
- **`picoscenes/README.md`**: documentação da instalação e uso do PicoScenes no host Linux.
- **`models/README.md`**: placeholder documentando o diretório de modelos de ML montado como volume externo.

#### Changed
- **`aims_ws/src/csi/launch/aims_launch.py`**: removidos `ExecuteProcess` de inicialização do PicoScenes, `npm start` e `xdg-open`. O launch agora é responsável exclusivamente pelos nós ROS2.
- **`aims_ws/src/csi/launch/aims_core_launch.py`**: removida a inicialização embutida do rosbridge. Corrigido o executável `talker` → `csi_publisher`.
- **`web/app.js`**: substituição de `process.argv[2]` por variável de ambiente `MONGO_URI`. Adicionada lógica `async/await` com retry automático e graceful shutdown via `SIGTERM`/`SIGINT`.
- **`web/package.json`**: adicionado script `start` compatível com Docker.
- **`aims_ws/src/requirements.txt`**: removida dependência `oct2py` (experimental). Adicionados comentários.
- **`aims_ws/src/csi/package.xml`**: removida dependência `<depend>octave</depend>`.
- **`.gitignore`**: adicionadas entradas para `.env`, `web/node_modules/` e `*.pyc`.
- **`.dockerignore`**: expandido com exclusões completas para reduzir o contexto de build.
- **`picoscenes_routine_rx.bash`**: parametrizado via variáveis de ambiente, removendo valores hardcoded de IP/porta/interface.
- **`README.md`**: reescrito completamente com diagrama de arquitetura, instruções Docker-first e tabela de variáveis de ambiente.

#### Removed
- `docker/Dockerfile`: substituído por `docker/ros2/Dockerfile` (multi-stage).
- `docker/entrypoint.sh`: substituído por `docker/ros2/entrypoint.sh`.
- `docker/README.md`: conteúdo migrado para o README principal.
- Dependência `rclnodejs` de `web/package.json`: não era utilizada no backend; a comunicação com ROS2 ocorre no cliente via `roslib.js` + WebSocket para o rosbridge.

#### Fixed
- **Build Docker do serviço `web`**: erro de compilação de native addons (`int64-napi`) causado pela presença da dependência `rclnodejs`, incompatível com Alpine sem build tools.
- **Conflito de exportação de imagem**: os serviços `ros2-nodes` e `rosbridge` compartilham o mesmo Dockerfile, o que gerava race condition na exportação paralela de imagens (`image already exists`). Corrigido adicionando `image: aims-system-ros2:latest` explicitamente em ambos os serviços.
