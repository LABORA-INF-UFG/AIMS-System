# ADR-0005: TailwindCSS v4 as the Styling Framework of the Web Interface

- **Status**: Accepted
- **Date**: 2026-06-17
- **Deciders**: Luiz Fernando de Freitas Oliveira
- **Technical context**: Migration of the frontend design system

---

## Context

The AIMS-System web interface was originally built on a combination of:
- **Bootstrap 5** (component CSS framework)
- **jQuery** (DOM manipulation)
- A custom CSS template with several files (`main.css`, `style.css`, 7 `variables*.css` files)
- Third-party libraries under `assets/vendor/` (AOS, GLightbox, Swiper, etc.)

This combination resulted in:
- A Docker image with unnecessary production dependencies (Bootstrap and jQuery as `dependencies`, not `devDependencies`)
- Container builds failing while trying to compile `rclnodejs` (found and removed during this process)
- A frontend carrying ~650 KB of unused vendor CSS
- Multiple sources of truth for styles (Bootstrap utilities + custom CSS + CSS variables)
- A jQuery dependency for DOM manipulation already available natively in modern browsers

The project is **scientific and laboratory** in nature, and the interface is a support tool for the monitoring system. It must be functional, readable and maintainable, with no need for complex UI components.

## Decision

Migrate the interface styling from **Bootstrap 5 + jQuery** to **TailwindCSS v4**, using the **CSS-First approach with compilation during the Docker build**.

Adopted configuration:
- **Version**: TailwindCSS v4 (latest stable) with `@tailwindcss/cli`
- **Approach**: CSS-First, with design tokens defined directly in `input.css` through the `@theme` directive
- **Build**: the minified `tailwind.css` is compiled in the `builder` stage of the Dockerfile and copied to `runtime` as a static file
- **JS**: jQuery replaced by Vanilla JavaScript for DOM manipulation (tabs, sliding panel, dynamic search)

## Alternatives Considered

| Alternative | Why it was rejected |
|---|---|
| **Keep Bootstrap 5** | Heavy runtime dependency (jQuery + bootstrap.js). Requires jQuery as a peer dependency. Verbose CSS utilities that conflict with custom CSS. |
| **TailwindCSS v3** | Requires a JavaScript `tailwind.config.js`, more verbose. v4 is CSS-First, closer to modern practice, and removes the need for a config file. |
| **Custom vanilla CSS** | High maintenance cost. Needs a full manual design system to stay visually consistent. |
| **Bulma CSS** | Component framework without utilities; same maintenance problems as Bootstrap for customization. |
| **shadcn/ui or DaisyUI** | Suited to React/Vue applications; incompatible with the current static HTML + Express architecture. |

## Why TailwindCSS v4

1. **CSS-First, no config file**: the `@theme` directive in `input.css` centralizes all design tokens (colors, fonts), removing `tailwind.config.js` and simplifying maintenance.
2. **Docker-only compilation (offline-first)**: CSS is compiled at container build time, producing a minified static file with no external CDN dependency, which matters for labs with restricted internet access.
3. **No runtime dependencies**: Bootstrap and jQuery are removed from `dependencies` (runtime), shrinking the final image and removing the need to serve vendor files from `node_modules`.
4. **Node.js 20 as a positive side effect**: the Rust-based `@tailwindcss/oxide` compiler requires Node.js >= 20, which forced the web base image up to `node:20-alpine`, the latest LTS at the time.

## Consequences

### Positive
- Significant reduction of unused CSS in the final bundle (native purging in v4).
- Design consistency guaranteed by the token system (`--color-primary`, `--color-primary-dark`, etc.).
- jQuery and all unnecessary vendor files removed (~12 MB less in the repository).
- Interface works with no external internet connection in the lab.
- Interaction scripts (tabs, drawer) reimplemented in ~30 lines of Vanilla JS, without external dependencies.

### Negative / Trade-offs
- **Learning curve**: contributors who only know Bootstrap must learn Tailwind's utility syntax.
- **Verbose HTML**: utility classes directly in the HTML make markup longer. Acceptable given the limited scope of the views.
- **No prebuilt components**: tabs, modals and drawers must be implemented by hand (done with Vanilla JS + CSS transitions).
- **Node.js upgrade**: moving to `node:20-alpine` may require reviewing the compatibility of other npm packages in the future.

## Related Links
- [CHANGELOG.md](../CHANGELOG.md) — Details of the Phase 2 changes
- [ADR-0001](./ADR-0001-docker-compose-for-orchestration.md) — Docker Compose for orchestration
