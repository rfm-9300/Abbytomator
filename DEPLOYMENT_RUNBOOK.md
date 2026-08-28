# Abbitomator Deployment Runbook

Production deploys of this repo are automated. A merge (or push) to `main`
triggers GitHub Actions: test → build/push the Docker image → SSH to
`extractor-vps` and recreate the app container.

Manual `./deploy.sh` + SSH remains an emergency fallback. The phrases
"make deploy" / "deploy to VPS" still mean "get this onto production",
but the default path is CI/CD, not a laptop SSH session.

This app deploys to **`extractor-vps`** (same box as Extractor). It does **not**
deploy to `hillsong-vps`. Extractor keeps port `80`. Abbitomator is served on
port `8081` through the same Caddy container.

## What this deploy covers

| Component | Runtime | Deployed by this pipeline? |
|-----------|---------|----------------------------|
| App | Docker image `ghcr.io/rfm-9300/abbitomator` — FastAPI + built Astro UI on port 8001 | Yes |
| Data | Docker volume `abbitomator_data` → `/data` (SQLite, generated PDFs) | Left mounted (not wiped) |
| Caddy | Extractor’s `docker-compose.caddy.yml` | **No** — only recreate Caddy when those files change |
| Extractor | `~/hillsong-aggregator` on `:80` | **No** — do not `down` that stack |

## Production Target

- SSH alias (manual fallback): `extractor-vps`
- Host: `172.233.116.75` (root)
- Production directory: `~/abbitomator`
- Compose file: `docker-compose.prod.yml`
- Caddy lives in Extractor’s `~/hillsong-aggregator` (`Caddyfile` + `docker-compose.caddy.yml`)
- Image: `ghcr.io/rfm-9300/abbitomator:${TAG:-latest}`
- Public URL: `http://172.233.116.75:8081`
- Health endpoint: `/health` (unauthenticated)

## Automated path (merge to main)

Workflow: [`.github/workflows/deploy.yml`](.github/workflows/deploy.yml)

```text
PR / merge to main (docs-only changes are skipped)
  → test (pytest in api/)
  → (main only) docker build linux/amd64, push SHA + latest tags to GHCR
  → (main only) scp compose + remote-deploy.sh, SSH pull + up -d
  → curl /health on the app container
```

Manual re-run: GitHub → Actions → **Deploy Abbitomator** → Run workflow.

### One-time GitHub secrets

Add these as repository secrets, or as secrets on the `production` environment:

| Secret | Purpose |
|--------|---------|
| `DEPLOY_HOST` | `172.233.116.75` (the host behind `ssh extractor-vps`) |
| `DEPLOY_USER` | `root` |
| `DEPLOY_SSH_KEY` | Private key whose public key is in that user's `authorized_keys` |
| `DEPLOY_SSH_KNOWN_HOSTS` | Optional. Output of `ssh-keyscan -H 172.233.116.75`. If unset, CI uses `ssh-keyscan` at deploy time. |

Do **not** put production `.env` values in GitHub. Secrets stay on the VPS.

The workflow authenticates to GHCR with `GITHUB_TOKEN` (no extra registry secret).
It forwards that short-lived token to the VPS only for `docker pull`, then logs out.

Until `DEPLOY_HOST` / `DEPLOY_USER` / `DEPLOY_SSH_KEY` are set, the **Test** and
**Build and push image** jobs can succeed and the **Deploy to VPS** job fails
with a missing-secret error.

### One-time VPS checks

```bash
ssh extractor-vps "mkdir -p ~/abbitomator && docker network create web_proxy || true"
ssh extractor-vps "test -f ~/abbitomator/.env && echo '.env present'"
ssh extractor-vps "curl -fsS --version >/dev/null && echo curl ok"
```

The public GitHub Actions runner must be able to SSH to `DEPLOY_HOST` (DigitalOcean
firewall / security group, TCP 22). Restrict the key to deploy commands if possible.

On first deploy, create `~/abbitomator/.env` with at least:

```text
DASHBOARD_USER=…
DASHBOARD_PASSWORD=…
OPENROUTER_API_KEY=…
OPENROUTER_MODEL=openai/gpt-4o
SEED_IF_EMPTY=0
```

Ask Rodrigo before writing secrets. Reuse the OpenRouter key from the other bots if he agrees. Do not seed fictional demo data in production (`SEED_IF_EMPTY=0`).

## Manual fallback

Use only when CI is down or a hotfix must ship from a laptop.

### Preflight

Run from the repo root (`~/projects/abbitomator`):

```bash
git status --short
docker info
ssh extractor-vps "echo ok"
```

Do not require a clean worktree, but do not overwrite unrelated local changes.

Confirm Extractor Caddy is running (Abby’s UI is routed through it):

```bash
ssh extractor-vps "cd ~/hillsong-aggregator && docker compose -f docker-compose.caddy.yml ps"
```

### Build and push image

```bash
./deploy.sh
```

By default this builds and pushes `ghcr.io/rfm-9300/abbitomator:latest`.

### Sync deploy files and restart

```bash
ssh extractor-vps "mkdir -p ~/abbitomator"
scp docker-compose.prod.yml scripts/remote-deploy.sh extractor-vps:~/abbitomator/
ssh extractor-vps "chmod +x ~/abbitomator/remote-deploy.sh && TAG=latest ~/abbitomator/remote-deploy.sh"
```

Do not copy `.env` unless Rodrigo explicitly asks, or this is the **first** deploy and `~/abbitomator/.env` is missing.

Do **not** `docker compose down` Abbitomator as a habit — that removes the compose network and can drop Caddy’s route to `abbitomator-web`. Prefer `pull` + `up -d`.

### Keep Caddy routing (Extractor repo)

Abby’s hostname is wired in **Extractor’s** Caddy files so a later Extractor deploy does not drop it. From `~/projects/Extractor`:

```bash
scp Caddyfile docker-compose.caddy.yml extractor-vps:~/hillsong-aggregator/
ssh extractor-vps "cd ~/hillsong-aggregator && docker compose -f docker-compose.caddy.yml up -d"
```

Caddyfile contract:

- `:80` → `hillsong-aggregator-web-1:8000` (Extractor, 4GB body limit)
- `:8081` → `abbitomator-web:8001` (Abbitomator)

Only recreate Caddy when those two files changed.

Leave Extractor’s web/worker containers running. Do not `down` `~/hillsong-aggregator` as part of an Abbitomator deploy.

### Verify

```bash
ssh extractor-vps "cd ~/abbitomator && docker compose -f docker-compose.prod.yml ps"
curl -sS -m 15 http://172.233.116.75:8081/health
curl -sS -m 15 -o /dev/null -w "%{http_code}\n" http://172.233.116.75:8081/login
curl -sS -m 15 http://172.233.116.75/health
```

Report success only after the Abbitomator container is up, `/health` returns `{"ok":true}` on `:8081`, `/login` is reachable, and Extractor `/health` on `:80` still passes.

## Public Routing

| URL | App |
|-----|-----|
| `http://172.233.116.75` | Extractor |
| `http://172.233.116.75:8081` | Abbitomator |

Do not point this app at `hillsong-vps` or `/root/websites-thebots/Caddyfile`. Do not change DNS unless Rodrigo explicitly asks.

## Failure Rules

- If the image pull fails, check GHCR login (`docker login ghcr.io`) and the image name/tag.
- If SSH deploy fails with missing secrets, add `DEPLOY_HOST`, `DEPLOY_USER`, and `DEPLOY_SSH_KEY`.
- If the web container fails to start, inspect `abbitomator-web` logs. Missing `DASHBOARD_USER` / `DASHBOARD_PASSWORD` returns HTTP 503 on API calls.
- If PDF export fails, the image is missing Pango/Cairo system libs — rebuild, do not install packages on the live container as the fix.
- If Generate comments fails, confirm `OPENROUTER_API_KEY` is in `~/abbitomator/.env`.
- If `:8081` times out but in-container `/health` works, Caddy is not routing — sync Extractor `Caddyfile` / `docker-compose.caddy.yml` and `up -d` Caddy. Confirm DigitalOcean firewall allows TCP 8081.
- If Extractor on `:80` breaks after this deploy, revert Extractor `Caddyfile` to proxy-only `:80` and leave Abbitomator compose running.
- Do not delete the `abbitomator_data` volume, wipe `/data`, or rotate secrets unless Rodrigo explicitly asks.
- Do not `docker compose down` Extractor as part of this deploy.
