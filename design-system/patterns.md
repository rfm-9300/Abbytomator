# Patterns

## Compact shell

Abbitomator has five dashboard pages (Overview, Weeks, Monthly, Settings, Tester) plus login. Do not add a sidebar. Overview is the landing page (`/` redirects there) because it is the daily workspace. Tester is a dev tool and sits behind a `.topbar__sep` after the report pages.

```
body
  a.skip
  header.topbar
    a.brand
    .topbar__actions
      nav.topbar__nav  (Overview, Weeks, Monthly, Settings | Tester)
      #btn-theme
  main.view#content
    .view__hero
    section.panel …
```

Head assets in `Dashboard.astro` (order matters):

1. Favicon `/favicon.svg`
2. Google Fonts (Outfit, Nunito, JetBrains Mono) + preconnect
3. `/style.css`
4. `/theme.js` (synchronous, in `<head>`)

`theme.js` also: file-name labels, tabs, `form[data-busy]`, `tr[data-href]`, `time[data-time]`, `[data-copy]`. First visit follows `prefers-color-scheme`; override is `localStorage.uiTheme`.


## List + create (index)

1. `.view__hero` with title + description
2. `.panel` “Source” containing `.form` with `.tabs` (YouTube | Google Drive | Upload). Drive tab uses `.tabs__list--3`. Advanced options in `<details class="details">`
3. Errors as `.banner.banner--bad` inside the form panel
4. `.panel` “Sermons” with `.tbl` (friendly status pills, relative `<time data-time>`, row `data-href`, Download in `.tbl__actions`) or `.empty.empty--sermons`

Create stays **on the list page**, not in a drawer. Primary CTA: **Extract sermon**.

Running rows may show the current `progress.headline` under the title.

## Channels (Watch)

1. `.view__hero` explaining automatic queuing
2. Success/error as `.banner.banner--ok` / `.banner.banner--bad` above the panels
3. `.panel` “Add a channel” with channel URL, Advanced details (transcript, language, ignore-shorter-than in minutes, pads), short hint + “How watching works” disclosure
4. `.panel` “Watching” with `.tbl` (status pills: watching `pill--ok`, paused default, error `pill--bad`) or `.empty.empty--channels`. Head includes **Check now**. Last queued title under the channel name. Row actions: **Queue latest**, **Remove**, then `.menu` for Check / Pause
5. `.panel` “Recently queued” as `.queue-list` (not a third full table)

Defaults for new channels come from Settings.

## Branding (Edit package)

1. `.view__hero` explaining intro → sermon → ending
2. `.panel` “Package” with `.timeline` (intro slot, sermon placeholder, ending slot)
3. `.panel` “Intro library” + `.panel` “Ending library”: upload form, then `.asset-list` of `.asset` cards (preview `.player.player--asset`, select / clear / delete)

Selected branding is applied automatically when a job finishes. Sermon detail can rebuild with **Rebuild with current intro & ending**.

## Sermon detail

1. `.crumb` back to `/`
2. `.panel` with title, friendly status pill (`Waiting` / `Working` / `Ready` / `Failed`), `.progress` (bar + `.steps`), optional player, then **Social kit** (`.kit` with This week / Shorts / Posts / Quotes tabs), then “What we found”
3. Social kit is review-only: 7-day plan, 9:16 clips with burned-in captions, quote cards, copy. **Regenerate kit** (`POST /jobs/{id}/social`) rebuilds from the saved transcript. While it runs, `data-social="building"` keeps live poll on so the page reloads when ready. Nothing is published from the dashboard.
4. Low confidence → `.banner.banner--warn` plus **Adjust the cut** (`POST /jobs/{id}/recut`)
5. Failed jobs: **Retry extraction** (`POST /jobs/{id}/retry`)
6. Job options live under `.details` (“More details”)
7. Raw worker output under `<details class="panel details-panel">` (“Technical log”)

Active jobs poll `GET /jobs/{id}/live` every 2.5s and patch progress/log in place. When status becomes `done` or `failed`, reload once. A `data-social="building"` job keeps polling after the sermon is ready so regenerate can refresh the kit. Do not use `<meta http-equiv="refresh">`.

When `status == done` and the output exists, show `.player` pointing at `/jobs/{id}/media` (inline) plus download / rebuild actions. Packaging uses the active intro & ending from `/edit`.

## Settings

1. `.view__hero`
2. Provider pills
3. **YouTube cookies** panel (upload Netscape `cookies.txt`, status pill, optional Remove). Separate form from the settings save.
4. Groups from `form_groups()`, including **Extraction defaults** first
5. Sticky `.form__sticky` **Save settings**

Field kinds: `text`, `secret`, `number`, `select`, `check`. Cookies are a file on the data volume (`cookies.txt`), not a settings.json field.

## Week-scoped report page (Overview)

Order matters — scope, then summary, then detail:

1. `.scopebar` — week stepper + "Write the letter" link. Everything below is scoped by it.
2. `.banner--ok` / `.banner--bad` for feedback (success auto-hides after ~2.6s)
3. `.kpis` with `.kpi__delta` week-over-week movement
4. One `.panel` — head holds the title plus **+ Add campaign**; body is the `.tbl.tbl--overview` with click-to-edit `.cellv` cells and nested city blocks, then `.empty.empty--overview` when there are no rows. Spend / clicks / tickets are typed on cities; the campaign line is their total. Adding a campaign already includes a city row (placeholder Default).

Do not stack a create form above the data. The table is what the user came for; the create affordance is a button in the panel head that reveals `.tbl__row--add` inside the table. Weeks (`+ New week`) follows the same shape.

Destructive actions confirm and say what they affect: removing a campaign drops **this week's line only** (it stays available for other weeks); deleting a city removes it from **every week**; deleting a week drops **that week's numbers and letter notes only** (campaigns stay).

**Editing must not fight the typist.** A numeric edit refreshes only the calculated cells (CPC, CPP, city sums and grand totals, KPIs) via `data-row` / `data-cell` hooks, so focus and tab order survive. Only structural edits (name, platform, status) and add/delete redraw the table, because those can reorder rows.

## Week letter (Weeks → detail)

Same `.scopebar` as Overview (prev / week select / next, plus All weeks and Overview). Then one `.panel` with Generate comments / Download PDF. Switching week reloads the letter fields.

## Monthly

Same scope-then-summary order as Overview: `.scopebar` (prev / month **name** select / year / next, plus Download presentation) → `.kpis` → one `.panel` with the week table and `.empty.empty--weeks`. Never ask for a month as a bare number input.

## New page

1. Use `Dashboard.astro`
2. Content in the slot — never a second topbar
3. Use hero + panel
4. Add copy per [i18n.md](i18n.md)
5. Do not create a second stylesheet

## Feedback

Every write tells the user it happened. Inline cell edits flash `.is-saved`; row-level actions post a `.banner--ok` that clears itself after ~2.6s; failures set `.is-invalid` on the offending control **and** show `.banner--bad`. No page in this app may save silently or swallow a rejected promise — every `load()` chain ends in a `.catch` that renders the message.

## Responsive

At `max-width: 920px`: tighter topbar/view padding; hide `.brand__sub`; `.form__grid` becomes one column. Keep the primary CTA visible. Honor `prefers-reduced-motion`.

## Auth

HTTP Basic on the API. The Astro `/login` page stores credentials in `sessionStorage` and sends `Authorization` on `/api` calls.

