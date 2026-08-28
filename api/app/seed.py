from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Client
from app.services.demo import load_demo


def seed_if_empty(db: Session | None = None) -> None:
    close = False
    if db is None:
        from app.db import SessionLocal

        db = SessionLocal()
        close = True
    try:
        existing = db.scalar(select(Client).limit(1))
        if existing is not None:
            return
        load_demo(db)
        db.commit()
    finally:
        if close:
            db.close()
