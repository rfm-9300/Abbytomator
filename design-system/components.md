# Components

Class names as implemented in `web/public/style.css`. Copy these. Strings in examples are placeholders.

## Brand + topbar

```html
<header class="topbar">
  <a class="brand" href="/">
    <span class="brand__mark" aria-hidden="true">SE</span>
    <span class="brand__text">
        <span class="brand__name">Sermon extractor</span>
        <span class="brand__sub">Sermon to social</span>
    </span>
  </a>
  <div class="topbar__actions">
    <nav class="topbar__nav" aria-label="Main">
      <a class="btn btn--ghost btn--sm" href="/" aria-current="page">Sermons</a>
      <a class="btn btn--ghost btn--sm" href="/watch">Channels</a>
      <a class="btn btn--ghost btn--sm" href="/edit">Branding</a>
      <a class="btn btn--ghost btn--sm" href="/settings">Settings</a>
    </nav>
    <button class="iconbtn iconbtn--theme" id="btn-theme" type="button" aria-label="Dark theme">…</button>
  </div>
</header>
```

Theme button **must** keep `id="btn-theme"` — `theme.js` binds to it. It contains sun/moon SVGs (`.theme-icon--sun` / `.theme-icon--moon`); do not set `textContent` on the button.

Mark the current page with `aria-current="page"` on the matching topbar link. `.topbar__actions .btn[aria-current="page"]` gives it a surface fill so Sermons / Channels / Branding / Settings stay distinct.

Action rows that may wrap: `.row.row--wrap`. Overflow actions: `.menu` (`<details>` + `.menu__list`).

Skip link: `a.skip` as the first body child, pointing at `#content` on `main.view`.

## Social kit (sermon detail)

Shorts, posts, quotes, and the week plan live under `.kit` on the sermon page. Tabs reuse `.tabs` (This week / Shorts / Posts / Quotes). Copy buttons use `[data-copy="#id"]` (`theme.js` writes the target’s text to the clipboard and flashes “Copied”).

```html
<div class="kit">
  <div class="kit__head">
    <div>
      <h2 class="section-title">Social kit</h2>
      <p class="hint">Review before you post.</p>
    </div>
    <form action="/jobs/id/social" method="post" data-busy="Making shorts…">
      <button class="btn btn--ghost" type="submit">Regenerate kit</button>
    </form>
  </div>
  <article class="clip">
    <video class="player player--short" controls playsinline preload="metadata" src="/jobs/id/clips/0/media"></video>
    <div class="clip__meta">
      <p class="clip__title"><span class="pill pill--info">Hook</span></p>
      <p class="clip__hook">The line that stops the scroll.</p>
      <div class="copybox">
        <div class="copybox__head">
          <span class="copybox__label">Instagram Reel</span>
          <button class="btn btn--ghost btn--sm" type="button" data-copy="#ig-0">Copy</button>
        </div>
        <pre class="copybox__body" id="ig-0">Caption…</pre>
      </div>
    </div>
  </article>
</div>
```

`.player--short` is 9:16. Clip kind pills: hook `pill--info`, quote/application `pill--ok`, scripture `pill--warn`. Captions-on uses `pill--ok`.

Quote / Stories images: `.card-img` / `.card-img--stories`.

Week checklist:

```html
<ol class="plan">
  <li class="plan__item">
    <p class="plan__day">Monday</p>
    <div>
      <p class="plan__title">Hook Short / Reel</p>
      <p class="muted">The line that stops the scroll.</p>
      <p class="row row--wrap">…download / copy…</p>
    </div>
  </li>
</ol>
```

## Asset cards (Branding)

```html
<article class="asset asset--active">
  <video class="player player--asset" controls playsinline preload="metadata" src="/assets/id/media"></video>
  <div class="asset__meta">
    <p class="asset__title">Church intro</p>
    <p class="muted">intro.mp4</p>
    <div class="row">…</div>
  </div>
</article>
```

## Buttons

```html
<button class="btn btn--primary" type="submit">Extract sermon</button>
<a class="btn btn--primary" href="/jobs/id/download">Download final video</a>
<button class="btn btn--ghost" type="button">Cancel</button>
<button class="iconbtn iconbtn--theme" id="btn-theme" type="button">🌙</button>
```

- `.btn--primary` / `.btn--accent` — gradient CTA
- `.btn--ghost` — secondary
- `.btn--danger` — irreversible
- `.btn--sm` — compact
- Do not use a raw `<button>` or `.button` without `.btn`

Inline action groups: `.row`. If they may wrap on narrow tables, add `.row--wrap`.

## View + crumb

```html
<main class="view">
  <p class="crumb"><a href="/">Sermons</a></p>
  <div class="view__hero">
    <h1 class="view__title">New extraction</h1>
    <p class="view__desc">One-line description.</p>
  </div>
</main>
```

Reporting tables (Overview, Monthly): `main.view.view--wide` so the 9-column campaign table fits (`--content-wide`). Weeks / Settings stay at `--content`.

## Panel + table

```html
<section class="panel">
  <div class="panel__head">
    <h2 class="panel__title">Sermons</h2>
  </div>
  <div class="tbl-wrap">
    <table class="tbl">
      <thead><tr><th>Status</th><th>Title</th></tr></thead>
      <tbody>
        <tr>
          <td><span class="pill pill--ok">done</span></td>
          <td class="name"><a href="/jobs/…">Title</a></td>
        </tr>
      </tbody>
    </table>
  </div>
</section>
```

Form panels wrap fields in `.panel__body`. Job-detail heads that stack title + pill use `.panel__head--stack`.

Cell helpers: `.name` `.muted` `.mono`. Clickable rows: `tr[data-href]`. Row download: `.tbl__actions`. Compact recents: `.queue-list` / `.queue-list__item`.

Empty modifiers: `.empty--sermons` `.empty--channels` `.empty--brand`.

## Empty

```html
<div class="empty">
  <p class="empty__title">No jobs yet</p>
  <p class="empty__desc">Paste a YouTube or Google Drive link to get started.</p>
</div>
```

## Pills (job status)

| Status | Class | Friendly label (job detail) |
|---|---|---|
| queued | `pill pill--info` | Waiting |
| running | `pill pill--warn` | Working |
| done | `pill pill--ok` | Ready |
| failed | `pill pill--bad` | Failed |

Jobs list **and** job detail use the friendly map in `app/progress.py` (`Waiting` / `Working` / `Ready` / `Failed`). Visual tone is still the CSS pill class.

Pills for watch-channel status: watching → `pill--ok`, paused → `pill` (default), error → `pill--bad`. Job rows from watch still use the job-status map above.

Low-confidence cut warning: `.banner.banner--warn`.

## Progress (job detail)

```html
<div class="progress">
  <div class="progress__head">
    <div>
      <p class="progress__headline">Finding the sermon</p>
      <p class="progress__detail">Figuring out where the sermon starts and ends.</p>
    </div>
    <p class="progress__pct mono">50%</p>
  </div>
  <div class="progress__bar progress__bar--live" role="progressbar" aria-valuenow="50">
    <span class="progress__fill" style="--progress: 50%"></span>
  </div>
  <ol class="steps">
    <li class="steps__item steps__item--done">…</li>
    <li class="steps__item steps__item--current">…</li>
    <li class="steps__item steps__item--todo">…</li>
  </ol>
</div>
```

Modifiers: `.progress__bar--live` (active job), `--ok`, `--bad`. Step states: `--done`, `--current`, `--todo`, `--failed`.

## Player (job detail)

```html
<video class="player" controls playsinline preload="metadata" src="/jobs/id/media"></video>
<div class="player-placeholder">
  <p class="player-placeholder__title">Video will appear here</p>
  <p class="player-placeholder__desc">When the cut finishes, you can watch it on this page.</p>
</div>
```

## Details disclosure

```html
<details class="details">
  <summary class="details__summary">More details</summary>
  …
</details>
<details class="panel details-panel">
  <summary class="panel__head details-panel__summary">…</summary>
  <div class="panel__body">…</div>
</details>
```

## Forms

```html
<form class="form">
  <div class="tabs" data-tabs>
    <div class="tabs__list tabs__list--3" role="tablist" aria-label="Source">
      <button class="tabs__tab" type="button" role="tab" aria-selected="true">YouTube</button>
      <button class="tabs__tab" type="button" role="tab" aria-selected="false">Google Drive</button>
      <button class="tabs__tab" type="button" role="tab" aria-selected="false">Upload</button>
    </div>
    <div class="tabs__panel" role="tabpanel">…</div>
    <div class="tabs__panel" role="tabpanel" hidden>…</div>
  </div>
  <div class="form__grid">
    <div class="form__row">
      <label class="lbl" for="language">Language</label>
      <input class="inp" id="language" name="language">
    </div>
  </div>
  <label class="check">
    <input type="checkbox" name="reencode" value="true">
    <span>Re-encode for a frame-accurate cut (slower)</span>
  </label>
  <button class="btn btn--primary" type="submit">Extract sermon</button>
</form>
```

Source choice on the list page uses `.tabs` (YouTube / Google Drive / Upload), not a divider. Inactive tab fields are cleared before submit. Drive files must be shared “Anyone with the link”; folders pick the largest video.

Language, pads, transcript source, and re-encode live under `<details class="details">` (“Advanced”). Closed details still submit. Defaults come from Settings (`extraction_defaults()`).

Submit buttons that wait on the server use `form[data-busy="Working…"]`. `theme.js` disables the button.

Sticky save on long forms: `.form__sticky` wrapping the primary button.

## File picker

Do not put `type="file"` on `.inp` — the native Choose file control breaks alignment. Use `.file`:

```html
<div class="file">
  <input class="file__input" id="video" type="file" name="video" accept="video/*">
  <div class="file__ui" aria-hidden="true">
    <span class="file__btn">Choose file</span>
    <span class="file__name" data-file-name>No file chosen</span>
  </div>
</div>
```

`theme.js` updates `[data-file-name]` when a file is chosen. Height, border, radius, and focus ring match `.inp`.

## Tabs

```html
<div class="tabs" data-tabs>
  <div class="tabs__list tabs__list--3" role="tablist" aria-label="Source">
    <button class="tabs__tab" type="button" role="tab" aria-selected="true">YouTube</button>
    <button class="tabs__tab" type="button" role="tab" aria-selected="false">Google Drive</button>
    <button class="tabs__tab" type="button" role="tab" aria-selected="false">Upload</button>
  </div>
  <div class="tabs__panel" role="tabpanel">…</div>
</div>
```

Selected tab: `aria-selected="true"`. Hide inactive panels with the `hidden` attribute.

Default `.tabs__list` is two columns. Source form uses `.tabs__list--3`. Social kit uses `.tabs__list--kit` (2×2 on small screens, four columns from 721px).

## Key/value (job meta)

```html
<dl class="kv">
  <div><dt>Language</dt><dd>pt</dd></div>
  <div><dt>Pad</dt><dd class="mono">2s / 5s</dd></div>
</dl>
```

## Log + error banner

```html
<p class="banner banner--bad">Upload too large</p>
<p class="banner banner--warn">Low confidence — check the start and end.</p>
<p class="banner banner--ok">Saved.</p>
<pre class="log">worker output…</pre>
```

## Branding timeline

```html
<ol class="timeline">
  <li class="timeline__slot timeline__slot--set">…intro…</li>
  <li class="timeline__join" aria-hidden="true">→</li>
  <li class="timeline__slot timeline__slot--sermon">…sermon…</li>
  <li class="timeline__join" aria-hidden="true">→</li>
  <li class="timeline__slot">…ending…</li>
</ol>
```

Selected slot: `.timeline__slot--set`. Empty copy: `.timeline__empty`.

## Overflow menu + recently queued

```html
<details class="menu">
  <summary class="btn btn--ghost btn--sm">More</summary>
  <div class="menu__list">…forms…</div>
</details>

<ul class="queue-list">
  <li class="queue-list__item">
    <span class="pill pill--ok">Ready</span>
    <div>
      <p class="queue-list__title"><a href="/jobs/…">Title</a></p>
      <p class="muted">Channel · <time datetime="…" data-time>Today</time></p>
    </div>
  </li>
</ul>
```

Relative times: `<time datetime="ISO" data-time>`. `theme.js` rewrites the text in the local timezone.

## When you need something not on these pages yet

Use the shared vocabulary before inventing classes:

- Confirm overwrite/delete → `.confirm` (add the CSS from WhatsApp-bot `style.css` if missing, then document it here)
- Toast → `.toast`
- Drawer form → `.drawer`
- Auth card → `.login` wrapping a `.panel` on `/login`. `main.view:has(> .login)` centers it on
  a faint dot-grid background. `.login__brand` (`.login__mark` + `.login__name` +
  `.login__tagline`) sits above the panel; `.login__heading` / `.login__sub` open the form in
  place of a `.panel__head`; `.login__footer` is the closing tagline below the panel.

## Abbitomator reporting

Campaign status: live → `pill pill--ok`, off → `pill`. Where status is editable, the pill *is* the control: add `.pill--btn` to a `<button>` that toggles it. The coloured pill is what makes the table scannable, so never downgrade it to a `<select>`.

### Editable report table

The Overview table is the product's main workspace, so it must read as a **report first and a form second**. Values render as plain text in a `.cellv` span and only become an input once clicked (or focused and Enter/Space pressed):

```html
<td class="num" data-cell="tix_sold">
  <span class="cellv" role="button" tabindex="0"
        data-campaign="12" data-field="tix_sold" data-kind="int" data-raw="1450">1,450</span>
</td>
```

- `data-kind` drives display and edit formatting: `money`, `int`, `pct`, `text`. `pct` displays `12.50%` but edits as `12.50`, because CTR is stored as a fraction and `parse_percent` divides anything above 1 by 100.
- `data-raw` holds the edit value, the text node the formatted one. Keep both in sync on save.
- Commit on blur or Enter, revert on Escape, and skip the request when the value is unchanged.
- A whole table of visible input boxes reads as a form and drowns out summary rows. Do not do it. Values start as `.cellv` text and become an input only when clicked.
- Save feedback is required: `.is-saved` for ~1s (green fade, `cell-saved` keyframes) on success, `.is-invalid` plus `.banner--bad` on failure. Silent saves are a bug.
- Calculated cells (CPC, CPP) stay plain `.num` text — never editable.

Row structure: one `tbody.tbl__block` per campaign (add `.tbl__block--split` when it has cities). City `.tbl__row--city`, parent `.tbl__row--parent`, totals `.tbl__row--total` in `tfoot` (below the add-campaign row), inline create `.tbl__row--add`. Cities keep every column so they line up with the campaign — do not colspan the name. Mark a city with `.tbl__city` + `.tbl__branch` in the Campaign column and a muted “City” label in Status.

A split campaign is a **block**, not extra campaigns: accent rail on the first cell, shared `.surface-2` wash, campaign spend / clicks / tix use `.tbl__rolled` (they are the city sum, never typed on the campaign) plus a `.tbl__count` (“5 cities”). CTR stays on the campaign. **Add city** is a `.tbl__addcity.tbl__addcity--row` text control on the campaign row, visible on hover/focus — never a permanent empty row under the cities. The extra-city form starts hidden; ✕ or Escape closes it. After a successful add, close the form.

Create rows live **inside the table**, revealed by a button in `.panel__head`. **+ Add campaign** opens two rows: campaign identity (platform, name, status, CTR) and a city row already underneath. City name placeholder is `Default` — leave it blank to store “Default” so numbers have a home before real cities exist. Spend / clicks / tix on that city row. Enter submits, Escape closes.

### Week scope bar

`.scopebar` is the pill-shaped control bar above the KPIs on week-scoped pages: `.scopebar__label`, a `.scopebar__step` (prev `.iconbtn--sm`, `.sel`, next `.iconbtn--sm`), `.scopebar__spacer`, then secondary links. Options are newest-first, so "previous" moves *down* the list.

### KPI strip

`.kpis` > `.kpi` > `.kpi__label` + `.kpi__value` + optional `.kpi__delta`. A bare number answers nothing, so show the week-over-week change: `.kpi__delta--good` / `--bad` by whether the movement is *desirable* (CPP falling is good), plain `.kpi__delta` when flat or on the first week. Stacked panels: `.stack`.

Empty states may carry one CTA in `.empty__action`.

Visually-obvious-but-unlabelled headers (the row-actions column) get `<span class="sr-only">Row actions</span>` rather than an empty `<th>`.

Weekly letter editor (week detail): same `.scopebar` as Overview so you can change week without going back to the list, then one `.panel` per campaign inside `#notes-fields`. Campaign note / performance summary / next steps are `.txt`. Live/Off is the campaign pill in `.panel__head` — never a per-city select. City rows are a comment `.txt` only. Ticket numbers stay on Overview. `#generate-notes` is a `.btn.btn--ghost.btn--sm` that drafts those fields from the week numbers. Off campaigns still get a close-out (note + summary + next steps), not blank fields.

Tester (`/tester`): snapshot KPIs + two `.tbl`s (weeks, campaigns). Load demo is `.btn.btn--primary`. Replace / Wipe everything are `.btn.btn--danger` and confirm in a dialog before they run. Warn with `.banner.banner--warn` that this writes to the same SQLite file.

