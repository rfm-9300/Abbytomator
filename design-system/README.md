# thebots.lab UI Design System (Abbitomator)

Same visual system as Extractor and the WhatsApp-bot dashboards. Agents must follow this folder when adding or changing HTML, CSS, or Astro pages.

**Implemented CSS lives in** [`web/public/style.css`](../web/public/style.css). This folder documents it. Do not invent a parallel visual language.

## Read this first

| File | When to open it |
|---|---|
| [AGENTS.md](AGENTS.md) | **Always** — hard rules, do/don't, checklist |
| [tokens.md](tokens.md) | Colors, type, radius, elevation, motion |
| [components.md](components.md) | Class catalog + copy-paste HTML |
| [patterns.md](patterns.md) | Page recipes (compact shell, form, table) |
| [i18n.md](i18n.md) | User-facing copy |

## Surfaces

| Surface | Files | Stylesheet |
|---|---|---|
| Dashboard | `web/src/layouts/Dashboard.astro`, `web/src/pages/` | `/style.css` |
| Weekly / monthly PDF | `api/app/templates/` | print CSS in those templates (client-facing, not the dashboard theme) |

Auth is a small login page that stores HTTP Basic credentials in `sessionStorage`. There is no cookie session.

## Visual identity

Copied from Extractor: compact shell (topbar + centered `.view`, no sidebar). Light default, dark via `html[data-theme]` and `web/public/theme.js`.
