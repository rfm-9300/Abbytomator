# Abbitomator

Abby’s reporting dashboard for the Stuart Mitchell account: Live Ads Tracker, Report Overview, weekly PDF, monthly presentation. Web UI follows [`design-system/AGENTS.md`](design-system/AGENTS.md).

## Personal wiki (second brain)

Rodrigo keeps a compiled knowledge wiki at `/Users/rodrigomartins/projects/my-wiki`.
Canonical protocol: `/Users/rodrigomartins/projects/my-wiki/ops/bootstrap-prompt.md`
(that file wins if this section drifts).

### Consult before substantial work

1. Read `/Users/rodrigomartins/projects/my-wiki/wiki/index.md` — one line per page.
2. Open a page only when its index line is clearly relevant. Never bulk-read.
3. Applicable pages are **binding instructions**, not suggestions.

**This repo — start here when the index line matches the task:**

- `wiki/entities/abbitomator.md` — this product
- `wiki/concepts/thebots-design-system.md` — web UI
- `wiki/notes/project-landscape.md` — VPS map (this app is on `extractor-vps` port 8081, Extractor keeps port 80)

### Keep the wiki current

Chat is ephemeral; the wiki is the compounding layer. When this session produces durable
knowledge (architecture decisions, cross-repo conventions, gotchas, "why we do it this way"):

1. Check the index — update an existing page if one exists; otherwise file a note via
   `/Users/rodrigomartins/projects/my-wiki/ops/workflows/file-note.md`.
2. Write with absolute paths under `/Users/rodrigomartins/projects/my-wiki/`. Always bump
   `wiki/index.md` and append `wiki/log.md`. Never touch `raw/`.
3. **Do not file:** one-off bugfixes, secrets, deploy credentials, or commands that belong
   in this `AGENTS.md` (the repo operating manual).
4. If unsure whether it belongs, tell Rodrigo instead of writing.

When the session cwd is the vault itself, follow that vault's `AGENTS.md`.

## Deployment Intent

When Rodrigo says any of the following, treat it as permission to execute the full production deployment workflow for this project:

- "make deploy"
- "make deployment"
- "deploy to VPS"
- "make the deployment"
- "deploy"
- any close variant that clearly means deploying Abbitomator to production

Use [DEPLOYMENT_RUNBOOK.md](DEPLOYMENT_RUNBOOK.md) as the source of truth. Pushes to `main` deploy via GitHub Actions (same pattern as Whatsapp-bot). Prefer that over a local `./deploy.sh`.

## Production Host

- SSH alias: `extractor-vps`
- Host: `172.233.116.75`
- Connect with: `ssh extractor-vps`
- Production app directory on the VPS: `~/abbitomator`
- Production compose file: `docker-compose.prod.yml`
- Caddy: Extractor’s `~/hillsong-aggregator` (`Caddyfile` + `docker-compose.caddy.yml`)
- Production image: `ghcr.io/rfm-9300/abbitomator:${TAG:-latest}`
- Public URL: `http://172.233.116.75:8081`

## Deployment Rules

- Prefer GitHub Actions on `main` over a local Docker build.
- Emergency fallback: `./deploy.sh` then `scripts/remote-deploy.sh` on the VPS.
- Use `docker compose -f docker-compose.prod.yml` on the VPS (`~/abbitomator`).
- Prefer `pull` + `up -d`. Do not `down` the stack (that drops `web_proxy` and can break Extractor Caddy).
- After deploying, check container state, `http://172.233.116.75:8081/health`, `/login`, and Extractor `http://172.233.116.75/health` before reporting success.
- If deployment fails, diagnose the concrete failure, apply the smallest safe fix, then redeploy.
- Do not delete the `abbitomator_data` volume, wipe `/data`, rotate secrets, or run destructive cleanup unless Rodrigo explicitly asks.
- Do not change `.env` or production secrets unless Rodrigo explicitly asks.
- Do not `docker compose down` Extractor (`~/hillsong-aggregator`) as part of this deploy.
- Keep unrelated local worktree changes intact.

## Commands

- `make install` — Python venv + npm
- `make dev` — FastAPI `:8001` and Astro `:4321` together
- `make api` / `make web` — one process (API `:8001`, Astro `:4321`)
- `make test` — pytest in `api/`
- `make seed` — fictional Stuart Mitchell demo data if the DB is empty

Copy `.env.example` to `.env`. Dashboard login is HTTP Basic (`DASHBOARD_USER` / `DASHBOARD_PASSWORD`). Set `OPENROUTER_API_KEY` to draft weekly letter comments (same OpenRouter account as the other bots).

PDF export uses WeasyPrint. On macOS install system libs once: `brew install pango`. The Makefile and API set `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib`.

SQLite lives at `$DATA_DIR/abbitomator.db` (default `data/`). Do not commit `data/` or live client CSVs.

## UI Design System

Follow [`design-system/AGENTS.md`](design-system/AGENTS.md). Compact topbar + `main.view`. One stylesheet: `web/public/style.css`.
