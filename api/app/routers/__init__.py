from __future__ import annotations

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import require_user
from app.config import CLIENT_SLUG
from app.db import get_db
from app.services.pdf import PDF_TEMPLATES
from app.services.queries import require_client

router = APIRouter(prefix="/api", dependencies=[Depends(require_user)])


class ClientPatch(BaseModel):
    name: str | None = None
    currency: str | None = None
    report_email: str | None = None
    auto_email_enabled: bool | None = None
    pdf_template: str | None = None
    gmail_address: str | None = None
    gmail_app_password: str | None = None
    report_email_weekday: int | None = None
    report_email_hour: int | None = None
    report_email_minute: int | None = None
    report_email_tz: str | None = None
    openrouter_api_key: str | None = None
    openrouter_model: str | None = None


@router.get("/me")
def me(user: str = Depends(require_user)) -> dict:
    return {"user": user}


def _client_payload(client) -> dict:
    return {
        "id": client.id,
        "name": client.name,
        "slug": client.slug,
        "currency": client.currency,
        "report_email": client.report_email or "",
        "auto_email_enabled": client.auto_email_enabled,
        "pdf_template": client.pdf_template or "modern",
        "gmail_address": client.gmail_address or "",
        "gmail_app_password": client.gmail_app_password or "",
        "report_email_weekday": client.report_email_weekday,
        "report_email_hour": client.report_email_hour,
        "report_email_minute": client.report_email_minute,
        "report_email_tz": client.report_email_tz or "Europe/London",
        "openrouter_api_key": client.openrouter_api_key or "",
        "openrouter_model": client.openrouter_model or "openai/gpt-4o",
    }


@router.get("/client")
def get_client(db: Session = Depends(get_db)) -> dict:
    return _client_payload(require_client(db, CLIENT_SLUG))


@router.patch("/client")
def patch_client(body: ClientPatch, db: Session = Depends(get_db)) -> dict:
    client = require_client(db, CLIENT_SLUG)
    if body.name is not None:
        client.name = body.name.strip() or client.name
    if body.currency is not None:
        client.currency = body.currency.strip().upper() or client.currency
    if body.report_email is not None:
        client.report_email = body.report_email.strip()
    if body.auto_email_enabled is not None:
        client.auto_email_enabled = body.auto_email_enabled
    if body.pdf_template is not None:
        if body.pdf_template not in PDF_TEMPLATES:
            raise HTTPException(400, f"pdf_template must be one of {sorted(PDF_TEMPLATES)}")
        client.pdf_template = body.pdf_template
    if body.gmail_address is not None:
        client.gmail_address = body.gmail_address.strip()
    if body.gmail_app_password is not None:
        client.gmail_app_password = body.gmail_app_password.strip().replace(" ", "")
    if body.report_email_weekday is not None:
        if not 0 <= body.report_email_weekday <= 6:
            raise HTTPException(400, "report_email_weekday must be 0 (Monday) through 6 (Sunday)")
        client.report_email_weekday = body.report_email_weekday
    if body.report_email_hour is not None:
        if not 0 <= body.report_email_hour <= 23:
            raise HTTPException(400, "report_email_hour must be 0 through 23")
        client.report_email_hour = body.report_email_hour
    if body.report_email_minute is not None:
        if not 0 <= body.report_email_minute <= 59:
            raise HTTPException(400, "report_email_minute must be 0 through 59")
        client.report_email_minute = body.report_email_minute
    if body.report_email_tz is not None:
        tz_name = body.report_email_tz.strip() or "Europe/London"
        try:
            ZoneInfo(tz_name)
        except ZoneInfoNotFoundError as exc:
            raise HTTPException(400, f"Unknown timezone: {tz_name}") from exc
        client.report_email_tz = tz_name
    if body.openrouter_api_key is not None:
        client.openrouter_api_key = body.openrouter_api_key.strip()
    if body.openrouter_model is not None:
        client.openrouter_model = body.openrouter_model.strip() or "openai/gpt-4o"
    return _client_payload(client)
