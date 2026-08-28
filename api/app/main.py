from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import SEED_IF_EMPTY, WEB_DIST, ensure_dirs
from app.db import init_db
from app.routers import router as core_router
from app.routers.weeks import router as weeks_router
from app.seed import seed_if_empty


@asynccontextmanager
async def lifespan(_app: FastAPI):
    ensure_dirs()
    init_db()
    if SEED_IF_EMPTY:
        seed_if_empty()
    yield


app = FastAPI(title="Abbitomator", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:4321", "http://localhost:4321"],
    allow_credentials=True,
    allow_headers=["*"],
    allow_methods=["*"],
)

app.include_router(core_router)
app.include_router(weeks_router)


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.get("/api/health")
def api_health() -> dict:
    return {"ok": True}


if WEB_DIST.is_dir():
    from fastapi.staticfiles import StaticFiles

    app.mount("/", StaticFiles(directory=str(WEB_DIST), html=True), name="web")
