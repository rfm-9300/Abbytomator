# UI Design System — agent rules

Parent repo `AGENTS.md` has the personal-wiki section. This file is UI-only; still read
`/Users/rodrigomartins/projects/my-wiki/wiki/index.md` before substantial design work
(`wiki/concepts/thebots-design-system.md`).

Follow these rules for any change under `web/src/` or `web/public/`.

## Must

- Use existing classes from [components.md](components.md). Prefer composition over new CSS.
- Style with tokens from [tokens.md](tokens.md) (`var(--accent)`, `var(--ink)`, `var(--r-lg)`, …).
- Keep the compact shell: `header.topbar` (brand + theme) + `main.view`.
- Load `/style.css` and `/theme.js` from `Dashboard.astro` only.
- Keep BEM-style names (`block__elem--mod`).
- Map campaign status to pills: live → `pill--ok`, off → `pill` (default).
- After adding a token, class, or pattern, update this `design-system/` folder.

## Must not

- Do not add a second stylesheet for the dashboard.
- Do not hardcode hex, `oklch()`, or `rgb()` in component rules. Add a token on `:root` (and `html[data-theme="dark"]` if the dark value differs).
- Do not introduce a new font family. Stack is Outfit + Nunito + JetBrains Mono.
- Do not revive Extractor-only classes (`.badge`, `.button`, `.panel-head`, `.shell`, `.upload`).
- Do not use inline `style=""` for colors, type, or spacing that tokens already cover.
- Do not invent a new button / pill / modal primitive when `.btn`, `.pill`, `.banner` exist.
- Do not skip the dark-theme check.
- Do not copy a WhatsApp-bot sidebar into this app.

## Decision tree

```
Need a control?
  exists in components.md? → use it
  close variant (size/tone)? → existing modifier (--sm, --ghost, --danger, --primary)
  genuinely new? → add to web/public/style.css with tokens, then document in components.md

Need a color?
  semantic token exists (--accent, --ok, --bad, …)? → use it
  else → add --name on :root AND html[data-theme="dark"], then use var(--name)
```

## Checklist before finishing a UI change

- [ ] Reused shared classes; no one-off palette
- [ ] Light and dark both readable
- [ ] `max-width: 920px` does not overflow; Overview/Monthly use `.view--wide` (`1280px`)
- [ ] Focus states use `border-color: var(--accent)` + `box-shadow: 0 0 0 4px var(--accent-soft)`
- [ ] `design-system/` updated if tokens/classes/patterns changed
