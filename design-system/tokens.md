# Tokens

All dashboard visuals come from CSS custom properties on `:root` (light) and `html[data-theme="dark"]` (dark). Defined in `web/public/style.css`. Same token names and class contracts as the WhatsApp-bot design system, but Abbitomator carries its own accent identity (see below) rather than the shared violet/yellow.

Theme persistence: `web/public/theme.js` writes `html[data-theme]` from `localStorage.uiTheme` (`"light"` | `"dark"`). Default is **light**. Load `theme.js` in `<head>` so the theme applies before first paint.

## Color — light (default)

| Token | Value | Role |
|---|---|---|
| `--bg` | `#fdfcfa` | Page canvas |
| `--bg-deep` | `#f1efe8` | Recessed surfaces, off-state pill |
| `--bg-elev` | `#ffffff` | Elevated |
| `--surface` | `#ffffff` | Panels, inputs |
| `--surface-2` | `#f7f5ef` | Table header, current-page nav pill |
| `--line` | `#e9e5d9` | Default border |
| `--line-soft` | `#f0ede3` | Hairline / row divider |
| `--hairline-strong` | `#d9d3c1` | Hover border, scrollbar, mark outline |
| `--ink` | `#1c1a15` | Primary text |
| `--ink-2` | `#54503f` | Secondary text |
| `--ink-mute` | `#8a8571` | Labels, captions |
| `--ink-faint` | `#b7b19c` | Placeholders, off-state dot |
| `--accent` | `#f5b400` | Gold accent — the studio's own black-and-yellow |
| `--accent-deep` | `#a97800` | Accent text on light |
| `--accent-soft` | `rgba(245, 180, 0, 0.16)` | Focus ring, soft fill, KPI icon chip |
| `--accent-ink` | `#1c1a15` | Text on accent / gradient |
| `--ok` / `--ok-soft` / `--ok-ink` | `#1f9d5c` / tint / `#166b3f` | Success (live) |
| `--warn` / `--warn-soft` / `--warn-ink` | `#c9721c` / tint / `#97530f` | Warning |
| `--bad` / `--bad-soft` / `--bad-ink` | `#d1453e` / tint / `#a3302a` | Danger |
| `--info` / `--info-soft` / `--info-ink` | `#2f6fbb` / tint / `#204f89` | Info |
| `--mix` | `#ffffff` | Mix base for `color-mix(...)` |
| `--grad` | `135deg, #ffd23f → #f5b400` | Primary CTA fill |
| `--grad-hover` | `135deg, #ffdd6a → #d69a00` | Primary CTA hover |
| `--brand-mark` | `#161512` | The "tb." stamp's fill — always near-black, not themed |

## Color — dark (`html[data-theme="dark"]`)

| Token | Value | Role |
|---|---|---|
| `--bg` | `#12100c` | Canvas (thebots.lab) |
| `--bg-deep` | `#0b0a08` | Recessed surfaces, off-state pill |
| `--bg-elev` | `#1a1712` | Elevated |
| `--surface` | `#1a1712` | Panels |
| `--surface-2` | `#201c15` | Table header, current-page nav pill |
| `--line` | `rgba(240,233,216,0.10)` | Border |
| `--line-soft` | `rgba(240,233,216,0.06)` | Divider / grid |
| `--hairline-strong` | `rgba(240,233,216,0.16)` | Strong border, mark outline |
| `--ink` | `#f0e9d8` | Primary text |
| `--ink-2` | `#c7bfa9` | Secondary |
| `--ink-mute` | `#8a8371` | Muted |
| `--ink-faint` | `#54503f` | Faint, off-state dot |
| `--accent` | `#ffd23f` | Gold accent — same hue as light |
| `--accent-deep` | `#f5b400` | Deep gold |
| `--accent-soft` | `rgba(255,210,63,0.16)` | Soft gold |
| `--accent-ink` | `#1c1a15` | Text on gold |
| `--ok` / `--ok-ink` | `#6fcf8e` / `#9ae0b2` | Success |
| `--warn` / `--warn-ink` | `#e0a655` / `#f0c988` | Warning |
| `--bad` / `--bad-ink` | `#e2726a` / `#f2a099` | Danger |
| `--info` / `--info-ink` | `#7aa8e0` / `#aecaf0` | Info |
| `--mix` | `#201c15` | Mix base |
| `--grad` | `135deg, #ffd23f → #f5b400` | Primary CTA — same stops as light |
| `--grad-hover` | `135deg, #ffe27a → #ffc11a` | Primary CTA hover |
| `--brand-mark` | `#000000` | The "tb." stamp's fill on dark — pure black, not `#161512` (that value nearly disappears against `--surface`/`--bg`) |

Status `*-soft` values on dark are `rgba(color, 0.13)`.

On dark, links and accent-on-tint text use `var(--accent)`, not `--accent-deep`.

`--brand-mark` is the one token that isn't a light/dark pair of the *same* color — it's near-black in both themes by design (the studio's ink stamp), but the exact value differs so it stays visible against each theme's darkest surface. Always pair a `--brand-mark` fill with a `1px solid var(--hairline-strong)` border for the same reason.

## Type

| Token | Value | Use |
|---|---|---|
| `--sans` | `"Nunito", ui-sans-serif, system-ui, sans-serif` | Body, labels, buttons, table |
| `--display` | `"Outfit", var(--sans)` | Page titles, brand, empty title |
| `--mono` | `"JetBrains Mono", ui-monospace, "SF Mono", Menlo, monospace` | Times, pads, log, IDs, the "tb." mark |

Google Fonts loaded in `Dashboard.astro`: Outfit 500–800, Nunito 400–800, JetBrains Mono 400–600.

Body: `14px / 1.5`, antialiased. Do not add a fourth family.

## Radius, elevation, motion, focus

| Token | Value |
|---|---|
| `--r-xs` / `--r-sm` / `--r-md` / `--r-lg` | 8 / 12 / 14 / 18px |
| Buttons, pills | `999px` |
| Brand mark | `9px`, 36×36 (topbar) · `16px`, 56×56 (login) · `6px`, 24×24 (footer stamp) |
| `--shadow-sm/md/lg` | light: ink alpha; dark: near-black |
| `--glow-accent` | CTA glow |
| Hover | 120ms, `translateY(-1px)` |
| Focus | `border-color: var(--accent); box-shadow: 0 0 0 4px var(--accent-soft)` |

## Layout

| Token | Value |
|---|---|
| `--content` | `920px` max width of `.view` |
| `--content-wide` | `1280px` max width of `.view--wide` (Overview + Monthly) |
| Breakpoint | `max-width: 920px` → single-column form grid, tighter padding |

No decorative background wash. Dark keeps a faint 32px hairline grid behind the content; light is plain paper.
