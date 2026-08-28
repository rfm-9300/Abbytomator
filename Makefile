.PHONY: install api web dev test seed

API_VENV := api/.venv/bin
export DYLD_FALLBACK_LIBRARY_PATH := /opt/homebrew/lib:$(DYLD_FALLBACK_LIBRARY_PATH)

install:
	(/Users/rodrigomartins/.local/bin/python3.11 -m venv api/.venv 2>/dev/null || python3.11 -m venv api/.venv || python3 -m venv api/.venv)
	$(API_VENV)/pip install -r api/requirements.txt
	cd web && npm install

api:
	cd api && .venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8001

web:
	cd web && npm run dev

dev:
	$(MAKE) -j2 api web

test:
	cd api && .venv/bin/pytest -q

seed:
	cd api && .venv/bin/python -c "from app.db import init_db; from app.seed import seed_if_empty; init_db(); seed_if_empty()"
