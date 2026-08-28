from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import require_user
from app.config import CLIENT_SLUG
from app.db import get_db
from app.models import Campaign, Location, Week, WeekCampaignMetric, WeekLocationMetric
from app.services.comments import generate_letter_comments
from app.services.csv_source import CsvInsightsSource
from app.services.import_week import import_from_source
from app.services.pdf import monthly_pdf_bytes, weekly_pdf_bytes
from app.services.queries import monthly_rollup, overview_for_week, require_client, week_payload

router = APIRouter(prefix="/api", dependencies=[Depends(require_user)])


class WeekCreate(BaseModel):
    period_end: date
    notes: str | None = None


class WeekPatch(BaseModel):
    notes: str | None = None
    updated_until: str | None = None


class TixPatch(BaseModel):
    tix_sold: int


class CampaignNotesIn(BaseModel):
    id: int
    note: str = ""
    performance_summary: str = ""
    next_steps: str = ""


class LocationNotesIn(BaseModel):
    id: int
    note: str = ""
    status: str | None = None


class WeekNotesPatch(BaseModel):
    updated_until: str | None = None
    campaigns: list[CampaignNotesIn] = []
    locations: list[LocationNotesIn] = []


def _campaign_metric(db: Session, week: Week, campaign_id: int) -> WeekCampaignMetric:
    metric = db.scalar(
        select(WeekCampaignMetric).where(
            WeekCampaignMetric.week_id == week.id,
            WeekCampaignMetric.campaign_id == campaign_id,
        )
    )
    if metric is None:
        metric = WeekCampaignMetric(week_id=week.id, campaign_id=campaign_id)
        db.add(metric)
        db.flush()
    return metric


def _location_metric(db: Session, week: Week, location_id: int) -> WeekLocationMetric:
    loc_metric = db.scalar(
        select(WeekLocationMetric).where(
            WeekLocationMetric.week_id == week.id,
            WeekLocationMetric.location_id == location_id,
        )
    )
    if loc_metric is None:
        loc_metric = WeekLocationMetric(week_id=week.id, location_id=location_id)
        db.add(loc_metric)
        db.flush()
    return loc_metric


def _week_or_404(db: Session, week_id: int) -> Week:
    week = db.get(Week, week_id)
    if week is None:
        raise HTTPException(404, "Week not found")
    return week


@router.get("/weeks")
def list_weeks(db: Session = Depends(get_db)) -> dict:
    client = require_client(db, CLIENT_SLUG)
    weeks = db.scalars(select(Week).where(Week.client_id == client.id).order_by(Week.period_end.desc())).all()
    return {"weeks": [week_payload(w) for w in weeks]}


@router.post("/weeks")
def create_week(body: WeekCreate, db: Session = Depends(get_db)) -> dict:
    client = require_client(db, CLIENT_SLUG)
    existing = db.scalar(select(Week).where(Week.client_id == client.id, Week.period_end == body.period_end))
    if existing is not None:
        if body.notes is not None:
            existing.notes = body.notes
        return week_payload(existing)
    week = Week(client_id=client.id, period_end=body.period_end, notes=body.notes or "")
    db.add(week)
    db.flush()
    return week_payload(week)


@router.get("/weeks/{week_id}")
def get_week(week_id: int, db: Session = Depends(get_db)) -> dict:
    return week_payload(_week_or_404(db, week_id))


@router.patch("/weeks/{week_id}")
def patch_week(week_id: int, body: WeekPatch, db: Session = Depends(get_db)) -> dict:
    week = _week_or_404(db, week_id)
    if body.notes is not None:
        week.notes = body.notes
    if body.updated_until is not None:
        week.updated_until = body.updated_until
    return week_payload(week)


def _apply_letter_notes(db: Session, week: Week, body: WeekNotesPatch) -> dict:
    if body.updated_until is not None:
        week.updated_until = body.updated_until
    for item in body.campaigns:
        campaign = db.get(Campaign, item.id)
        if campaign is None:
            raise HTTPException(404, f"Campaign {item.id} not found")
        metric = _campaign_metric(db, week, campaign.id)
        metric.note = item.note
        metric.performance_summary = item.performance_summary
        metric.next_steps = item.next_steps
    for item in body.locations:
        location = db.get(Location, item.id)
        if location is None:
            raise HTTPException(404, f"Location {item.id} not found")
        loc_metric = _location_metric(db, week, location.id)
        loc_metric.note = item.note
        if item.status is not None:
            if item.status not in {"live", "off"}:
                raise HTTPException(400, "status must be live or off")
            location.status = item.status
    return overview_for_week(db, week)


@router.patch("/weeks/{week_id}/notes")
def patch_week_notes(week_id: int, body: WeekNotesPatch, db: Session = Depends(get_db)) -> dict:
    return _apply_letter_notes(db, _week_or_404(db, week_id), body)


@router.post("/weeks/{week_id}/generate-notes")
def generate_week_notes(week_id: int, db: Session = Depends(get_db)) -> dict:
    week = _week_or_404(db, week_id)
    client = require_client(db, CLIENT_SLUG)
    overview = overview_for_week(db, week)
    draft = generate_letter_comments(overview, client.currency)
    body = WeekNotesPatch(campaigns=draft["campaigns"], locations=draft["locations"])
    return _apply_letter_notes(db, week, body)


@router.post("/weeks/{week_id}/import")
async def import_week(week_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)) -> dict:
    week = _week_or_404(db, week_id)
    client = require_client(db, CLIENT_SLUG)
    raw = await file.read()
    if not raw:
        raise HTTPException(400, "Empty file")
    result = import_from_source(db, client, week, CsvInsightsSource(), raw)
    return {
        "campaigns_upserted": result.campaigns_upserted,
        "locations_upserted": result.locations_upserted,
        "updated_until": result.updated_until,
        "week": week_payload(week),
    }


@router.patch("/weeks/{week_id}/campaigns/{campaign_id}")
def patch_week_campaign(
    week_id: int, campaign_id: int, body: TixPatch, db: Session = Depends(get_db)
) -> dict:
    week = _week_or_404(db, week_id)
    campaign = db.get(Campaign, campaign_id)
    if campaign is None:
        raise HTTPException(404, "Campaign not found")
    metric = _campaign_metric(db, week, campaign.id)
    metric.tix_sold = max(0, body.tix_sold)
    return {"campaign_id": campaign.id, "tix_sold": metric.tix_sold}


@router.patch("/weeks/{week_id}/locations/{location_id}")
def patch_week_location(
    week_id: int, location_id: int, body: TixPatch, db: Session = Depends(get_db)
) -> dict:
    week = _week_or_404(db, week_id)
    location = db.get(Location, location_id)
    if location is None:
        raise HTTPException(404, "Location not found")
    loc_metric = _location_metric(db, week, location.id)
    loc_metric.tix_sold = max(0, body.tix_sold)
    loc_ids = [loc.id for loc in location.campaign.locations]
    loc_metrics = db.scalars(
        select(WeekLocationMetric).where(
            WeekLocationMetric.week_id == week.id,
            WeekLocationMetric.location_id.in_(loc_ids),
        )
    ).all()
    total_tix = sum(m.tix_sold for m in loc_metrics)
    campaign_metric = db.scalar(
        select(WeekCampaignMetric).where(
            WeekCampaignMetric.week_id == week.id,
            WeekCampaignMetric.campaign_id == location.campaign_id,
        )
    )
    if campaign_metric is None:
        campaign_metric = WeekCampaignMetric(week_id=week.id, campaign_id=location.campaign_id)
        db.add(campaign_metric)
    campaign_metric.tix_sold = total_tix
    return {"location_id": location.id, "tix_sold": loc_metric.tix_sold, "campaign_tix_sold": total_tix}


@router.get("/overview")
def overview(week_id: int | None = None, db: Session = Depends(get_db)) -> dict:
    client = require_client(db, CLIENT_SLUG)
    if week_id is not None:
        week = _week_or_404(db, week_id)
    else:
        week = db.scalar(select(Week).where(Week.client_id == client.id).order_by(Week.period_end.desc()))
        if week is None:
            return {"week": None, "groups": [], "totals": {"amount_spent": 0, "clicks": 0, "tix_sold": 0, "cpc": None, "cpp": None}}
    return overview_for_week(db, week)


@router.get("/weeks/{week_id}/pdf")
def weekly_pdf(week_id: int, db: Session = Depends(get_db)) -> Response:
    week = _week_or_404(db, week_id)
    client = require_client(db, CLIENT_SLUG)
    try:
        data = weekly_pdf_bytes(db, week, client)
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
    filename = f"weekly-{client.slug}-{week.period_end.isoformat()}.pdf"
    return Response(content=data, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/monthly")
def monthly(year: int = Query(...), month: int = Query(..., ge=1, le=12), db: Session = Depends(get_db)) -> dict:
    client = require_client(db, CLIENT_SLUG)
    return monthly_rollup(db, client, year, month)


@router.get("/monthly/pdf")
def monthly_pdf(year: int = Query(...), month: int = Query(..., ge=1, le=12), db: Session = Depends(get_db)) -> Response:
    client = require_client(db, CLIENT_SLUG)
    try:
        data = monthly_pdf_bytes(db, client, year, month)
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
    filename = f"monthly-{client.slug}-{year:04d}-{month:02d}.pdf"
    return Response(content=data, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{filename}"'})
