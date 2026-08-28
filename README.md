# Abbitomator

Internal dashboard for Abby’s **Stuart Mitchell** reporting: campaign tracker, weekly overview (spend + tickets + cost per ticket), weekly PDF, monthly presentation.

Meta data comes from an Ads Manager CSV/XLSX upload. Ticket sales stay manual. There is no Meta API in this version.

## Run locally

```bash
cp .env.example .env
make install
make dev
```

Open [http://127.0.0.1:4321](http://127.0.0.1:4321) and sign in with the credentials in `.env`.

Use Python 3.11 for the API venv (system 3.14 may lack `ensurepip`). On macOS, WeasyPrint needs `brew install pango`. The API listens on `:8001` (`GET /health` is unauthenticated) so it does not collide with Extractor on `:8000`.

GitHub: [rfm-9300/Abbytomator](https://github.com/rfm-9300/Abbytomator). Pushes to `main` run tests, publish `ghcr.io/rfm-9300/abbytomator`, and deploy to `extractor-vps`. See `DEPLOYMENT_RUNBOOK.md`.

## Layout

- `web/` — Astro 6 dashboard
- `api/` — FastAPI + SQLite
- `design-system/` — thebots compact shell (same tokens as Extractor)
