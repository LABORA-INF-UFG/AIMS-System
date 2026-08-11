# ADR-0005: TailwindCSS v4 como Framework de Estilização da Interface Web

- **Status**: Accepted
- **Data**: 2026-06-17
- **Decisores**: Luiz Fernando de Freitas Oliveira
- **Contexto técnico**: Migração do sistema de design do frontend web

---

## Contexto

A interface web do AIMS-System foi construída originalmente sobre uma combinação de:
- **Bootstrap 5** (framework CSS de componentes)
- **jQuery** (manipulação DOM)
- Um template CSS customizado com múltiplos arquivos (`main.css`, `style.css`, 7 arquivos `variables*.css`)
- Bibliotecas de terceiros via `assets/vendor/` (AOS, GLightbox, Swiper, etc.)

Esta combinação resultava em:
- Imagem Docker com dependências de produção desnecessárias (Bootstrap e jQuery como `dependencies`, não `devDependencies`)
- Build do contêiner falhando devido à tentativa de compilar `rclnodejs` (que foi detectada e removida neste processo)
- Frontend de ~650KB apenas em CSS de vendor não utilizado
- Múltiplas fontes de verdade para estilos (Bootstrap utilities + CSS customizado + variáveis CSS)
- Dependência de jQuery para manipulação DOM já disponível nativamente no browser moderno

O projeto é de natureza **científica e laboratorial**, com a interface servindo como ferramenta de suporte ao uso do sistema de monitoramento. A interface deve ser funcional, legível e manutenível, sem necessidade de componentes de UI complexos.

## Decisão

Migrar a estilização da interface de **Bootstrap 5 + jQuery** para **TailwindCSS v4**, usando a abordagem **CSS-First com compilação no build do Docker**.

Configuração adotada:
- **Versão**: TailwindCSS v4 (última versão estável) com `@tailwindcss/cli`
- **Abordagem**: CSS-First — tokens de design definidos diretamente em `input.css` via diretiva `@theme`
- **Build**: compilação do `tailwind.css` minificado no estágio `builder` do Dockerfile, copiado para o `runtime` como arquivo estático
- **JS**: substituição do jQuery por JavaScript Vanilla para manipulação de DOM (abas, painel deslizante, buscas dinâmicas)

## Alternativas Consideradas

| Alternativa | Motivo de descarte |
|---|---|
| **Manter Bootstrap 5** | Dependência pesada de runtime (jQuery + bootstrap.js). Requer jQuery como peer dependency. Utilitários CSS verbosos e conflitantes com CSS customizado. |
| **TailwindCSS v3** | Requer `tailwind.config.js` em JavaScript, mais verboso. v4 adota CSS-First que é mais alinhado ao padrão moderno e elimina a necessidade do arquivo de configuração. |
| **Vanilla CSS customizado** | Alto custo de manutenção. Requer design system completo manual para manter consistência visual. |
| **Bulma CSS** | Framework de componentes sem utilitários; mesmos problemas de manutenção do Bootstrap para customizações. |
| **shadcn/ui ou DaisyUI** | Adequados para aplicações React/Vue; incompatíveis com a arquitetura atual de HTML estático + Express. |

## Motivos da Escolha do TailwindCSS v4

1. **CSS-First sem arquivo de configuração**: A diretiva `@theme` no `input.css` centraliza todos os tokens de design (cores, fontes), eliminando a necessidade de `tailwind.config.js` e simplificando a manutenção.
2. **Compilação Docker-only (offline-first)**: O CSS é compilado em tempo de build do contêiner, gerando um arquivo estático minificado sem dependência de CDN externo — requisito importante para laboratórios com restrições de acesso à internet.
3. **Remoção de dependências de runtime**: Bootstrap e jQuery são removidos de `dependencies` (runtime), reduzindo a imagem final do contêiner e eliminando a necessidade de servir arquivos de vendor do `node_modules`.
4. **Node.js 20 como efeito colateral positivo**: O compilador `@tailwindcss/oxide` (Rust-based) requer Node.js ≥ 20, o que forçou a atualização da imagem base do servidor web para `node:20-alpine` — versão LTS mais recente e com suporte a longo prazo.

## Consequências

### Positivas
- Redução significativa de CSS não utilizado no bundle final (PurgeCSS nativo no v4).
- Consistência de design garantida pelo sistema de tokens (`--color-primary`, `--color-primary-dark`, etc.).
- Eliminação do jQuery e de todos os arquivos de vendor desnecessários (~12MB removidos do repositório).
- Interface funcional sem dependência de conexão externa à internet no laboratório.
- Scripts de interação (tabs, drawer) reimplementados em ~30 linhas de JS Vanilla, sem dependências externas.

### Negativas / Trade-offs
- **Curva de aprendizado**: colaboradores familiarizados apenas com Bootstrap precisam aprender a sintaxe de utilitários do Tailwind.
- **HTML verboso**: classes utilitárias diretamente no HTML resultam em marcação mais extensa. Aceitável dado o escopo limitado das views.
- **Ausência de componentes pré-construídos**: tabs, modais e drawers precisam ser implementados manualmente (o que foi feito com JS Vanilla + transições CSS).
- **Atualização de Node.js**: a migração para `node:20-alpine` pode exigir revisão futura de compatibilidade de outros pacotes npm.

## Links Relacionados
- [CHANGELOG.md](../CHANGELOG.md) — Detalhes das mudanças da Fase 2
- [ADR-0001](./ADR-0001-docker-compose-para-orquestracao.md) — Adoção do Docker Compose
