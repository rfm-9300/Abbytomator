from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import require_user
from app.config import CLIENT_SLUG
from app.db import get_db
from app.services.queries import require_client

router = APIRouter(prefix="/api", dependencies=[Depends(require_user)])


class ClientPatch(BaseModel):
    name: str | None = None
    currency: str | None = None


@router.get("/me")
def me(user: str = Depends(require_user)) -> dict:
    return {"user": user}


@router.get("/client")
def get_client(db: Session = Depends(get_db)) -> dict:
    client = require_client(db, CLIENT_SLUG)
    return {"id": client.id, "name": client.name, "slug": client.slug, "currency": client.currency}


@router.patch("/client")
def patch_client(body: ClientPatch, db: Session = Depends(get_db)) -> dict:
    client = require_client(db, CLIENT_SLUG)
    if body.name is not None:
        client.name = body.name.strip() or client.name
    if body.currency is not None:
        client.currency = body.currency.strip().upper() or client.currency
    return {"id": client.id, "name": client.name, "slug": client.slug, "currency": client.currency}
