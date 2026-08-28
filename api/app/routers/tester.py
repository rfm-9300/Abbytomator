from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import require_user
from app.config import CLIENT_SLUG
from app.db import get_db
from app.services.demo import append_demo_week, clear_reporting, demo_status, load_demo

router = APIRouter(prefix="/api/tester", dependencies=[Depends(require_user)])


class DemoIn(BaseModel):
    replace: bool = False


@router.get("/status")
def status(db: Session = Depends(get_db)) -> dict:
    return demo_status(db, CLIENT_SLUG)


@router.post("/demo")
def demo(body: DemoIn, db: Session = Depends(get_db)) -> dict:
    return load_demo(db, CLIENT_SLUG, replace=body.replace)


@router.post("/week")
def extra_week(db: Session = Depends(get_db)) -> dict:
    return append_demo_week(db, CLIENT_SLUG)


@router.post("/clear")
def clear(db: Session = Depends(get_db)) -> dict:
    return clear_reporting(db, CLIENT_SLUG)
