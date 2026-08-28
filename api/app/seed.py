from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import CLIENT_SLUG
from app.models import Campaign, Client, Location, Week, WeekCampaignMetric, WeekLocationMetric


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
        _seed(db)
        db.commit()
    finally:
        if close:
            db.close()


def _seed(db: Session) -> None:
    client = Client(name="Stuart Mitchell", slug=CLIENT_SLUG, currency="GBP")
    db.add(client)
    db.flush()

    prior = Week(client_id=client.id, period_end=date(2026, 8, 3), updated_until="3/8")
    week = Week(client_id=client.id, period_end=date(2026, 8, 10), updated_until="10/8")
    db.add_all([prior, week])
    db.flush()

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    fringe = Campaign(
        client_id=client.id,
        name="[TA] Demo Fringe Shows",
        platform="META",
        status="live",
        event_label="Edinburgh Fringe",
        last_imported_at=now,
    )
    road = Campaign(
        client_id=client.id,
        name="[TA] Demo On the Road",
        platform="META",
        status="live",
        event_label="On the Road",
        last_imported_at=now,
    )
    banter = Campaign(
        client_id=client.id,
        name="[TA] Demo Banter Ticket Sales",
        platform="META",
        status="off",
        event_label="Banter",
        last_imported_at=now,
    )
    db.add_all([fringe, road, banter])
    db.flush()

    edinburgh = Location(campaign_id=fringe.id, name="Edinburgh", status="live")
    glasgow = Location(campaign_id=fringe.id, name="Glasgow", status="off")
    manchester = Location(campaign_id=road.id, name="Manchester", status="off")
    leeds = Location(campaign_id=road.id, name="Leeds", status="live")
    db.add_all([edinburgh, glasgow, manchester, leeds])
    db.flush()

    db.add_all(
        [
            WeekCampaignMetric(
                week_id=prior.id,
                campaign_id=fringe.id,
                amount_spent=Decimal("1980.00"),
                clicks=91000,
                ctr_imported=Decimal("0.16"),
                tix_sold=5400,
            ),
            WeekCampaignMetric(
                week_id=prior.id,
                campaign_id=road.id,
                amount_spent=Decimal("1620.00"),
                clicks=58000,
                ctr_imported=Decimal("0.13"),
                tix_sold=3600,
            ),
            WeekCampaignMetric(
                week_id=week.id,
                campaign_id=fringe.id,
                amount_spent=Decimal("2140.00"),
                clicks=98000,
                ctr_imported=Decimal("0.16"),
                tix_sold=6200,
                note="Glasgow is now paused; Edinburgh stays live into the festival period.",
                performance_summary=(
                    "Ticket sales have grown this week, with CPC and CTR holding steady.\n"
                    "CPP remains efficient as volume increases."
                ),
                next_steps=(
                    "Keep current targeting on Edinburgh.\n"
                    "Watch CPP as the festival dates approach."
                ),
            ),
            WeekCampaignMetric(
                week_id=week.id,
                campaign_id=road.id,
                amount_spent=Decimal("1875.50"),
                clicks=64000,
                ctr_imported=Decimal("0.13"),
                tix_sold=4100,
                note="Manchester is now off. Leeds is the only On the Road city still live.",
                performance_summary="Ticket sales across On the Road continue to climb, with both cities contributing before Manchester was paused.",
                next_steps=(
                    "Monitor Leeds as remaining budget concentrates on one city.\n"
                    "Use Manchester's close-out as a baseline for the next on-sale."
                ),
            ),
            WeekCampaignMetric(
                week_id=week.id,
                campaign_id=banter.id,
                amount_spent=Decimal("0"),
                clicks=0,
                tix_sold=0,
                next_steps="Hold off until the next on-sale date is confirmed.",
            ),
            WeekLocationMetric(
                week_id=prior.id,
                location_id=edinburgh.id,
                amount_spent=Decimal("1200.00"),
                clicks=54000,
                tix_sold=3600,
            ),
            WeekLocationMetric(
                week_id=prior.id,
                location_id=glasgow.id,
                amount_spent=Decimal("780.00"),
                clicks=37000,
                tix_sold=1800,
            ),
            WeekLocationMetric(
                week_id=prior.id,
                location_id=manchester.id,
                amount_spent=Decimal("900.00"),
                clicks=32000,
                tix_sold=2200,
            ),
            WeekLocationMetric(
                week_id=prior.id,
                location_id=leeds.id,
                amount_spent=Decimal("720.00"),
                clicks=26000,
                tix_sold=1400,
            ),
            WeekLocationMetric(
                week_id=week.id,
                location_id=edinburgh.id,
                amount_spent=Decimal("1320.00"),
                clicks=60000,
                tix_sold=4100,
                note="Edinburgh remains the volume driver and is converting efficiently at scale.",
            ),
            WeekLocationMetric(
                week_id=week.id,
                location_id=glasgow.id,
                amount_spent=Decimal("820.00"),
                clicks=38000,
                tix_sold=2100,
                note="Glasgow closed out at a stable CPP before being switched off.",
            ),
            WeekLocationMetric(
                week_id=week.id,
                location_id=manchester.id,
                amount_spent=Decimal("980.00"),
                clicks=34000,
                tix_sold=2500,
                note="Manchester closed out strongly in its final stretch.",
            ),
            WeekLocationMetric(
                week_id=week.id,
                location_id=leeds.id,
                amount_spent=Decimal("895.50"),
                clicks=30000,
                tix_sold=1600,
                note="Leeds is now carrying the campaign as the sole active city.",
            ),
        ]
    )
