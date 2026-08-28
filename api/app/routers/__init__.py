from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.auth import require_user
from app.config import CLIENT_SLUG
from app.db import get_db
from app.models import Campaign, Location
from app.services.csv_source import is_ignored_campaign
from app.services.queries import require_client

router = APIRouter(prefix="/api", dependencies=[Depends(require_user)])


class CampaignPatch(BaseModel):
    status: str | None = None
    event_label: str | None = None


class LocationCreate(BaseModel):
    name: str


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


@router.get("/campaigns")
def list_campaigns(status: str | None = None, db: Session = Depends(get_db)) -> dict:
    client = require_client(db, CLIENT_SLUG)
    query = (
        select(Campaign)
        .where(Campaign.client_id == client.id, Campaign.archived_at.is_(None))
        .options(selectinload(Campaign.locations))
        .order_by(Campaign.status.desc(), Campaign.name)
    )
    campaigns = [c for c in db.scalars(query).all() if not is_ignored_campaign(c.name)]
    campaigns = sorted(campaigns, key=lambda item: (item.status != "live", item.name.lower()))
    if status in {"live", "off"}:
        campaigns = [c for c in campaigns if c.status == status]
    last_import = max((c.last_imported_at for c in campaigns if c.last_imported_at), default=None)
    return {
        "last_imported_at": last_import.isoformat() if last_import else None,
        "campaigns": [
            {
                "id": c.id,
                "name": c.name,
                "platform": c.platform,
                "status": c.status,
                "event_label": c.event_label or c.name,
                "last_imported_at": c.last_imported_at.isoformat() if c.last_imported_at else None,
                "locations": [{"id": loc.id, "name": loc.name} for loc in c.locations],
            }
            for c in campaigns
        ],
    }


@router.patch("/campaigns/{campaign_id}")
def patch_campaign(campaign_id: int, body: CampaignPatch, db: Session = Depends(get_db)) -> dict:
    campaign = db.get(Campaign, campaign_id)
    if campaign is None:
        raise HTTPException(404, "Campaign not found")
    if body.status is not None:
        if body.status not in {"live", "off"}:
            raise HTTPException(400, "status must be live or off")
        campaign.status = body.status
    if body.event_label is not None:
        campaign.event_label = body.event_label.strip() or campaign.name
    return {"id": campaign.id, "status": campaign.status, "event_label": campaign.event_label}


@router.post("/campaigns/{campaign_id}/locations")
def add_location(campaign_id: int, body: LocationCreate, db: Session = Depends(get_db)) -> dict:
    campaign = db.get(Campaign, campaign_id)
    if campaign is None:
        raise HTTPException(404, "Campaign not found")
    name = body.name.strip()
    if not name:
        raise HTTPException(400, "name is required")
    existing = db.scalar(select(Location).where(Location.campaign_id == campaign.id, Location.name == name))
    if existing is not None:
        return {"id": existing.id, "name": existing.name}
    location = Location(campaign_id=campaign.id, name=name)
    db.add(location)
    db.flush()
    return {"id": location.id, "name": location.name}
