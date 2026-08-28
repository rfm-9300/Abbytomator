from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, selectinload

from app.config import CLIENT_SLUG
from app.models import Campaign, Client, Location, Week, WeekCampaignMetric, WeekLocationMetric
from app.services.queries import require_client, week_label, week_payload

DEMO_WEEKS: list[tuple[date, str]] = [
    (date(2026, 7, 20), "20/7"),
    (date(2026, 7, 27), "27/7"),
    (date(2026, 8, 3), "3/8"),
    (date(2026, 8, 10), "10/8"),
    (date(2026, 8, 17), "17/8"),
]


def _dec(value: float | int | str) -> Decimal:
    return Decimal(str(value))


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _scale(base: float, factor: float) -> Decimal:
    return _dec(round(base * factor, 2))


def _iscale(base: int, factor: float) -> int:
    return max(0, int(round(base * factor)))


# Per-week multipliers so July → August reads as a real run, not a copy-paste.
_WEEK_FACTORS = {
    date(2026, 7, 20): 0.82,
    date(2026, 7, 27): 0.90,
    date(2026, 8, 3): 0.96,
    date(2026, 8, 10): 1.00,
    date(2026, 8, 17): 1.08,
}


def _campaign_specs() -> list[dict]:
    return [
        {
            "name": "[TA] EDINBURGH SHOWS// FRINGE",
            "status": "live",
            "event_label": "",
            "spent": 4070,
            "clicks": 252934,
            "ctr": "0.16",
            "tix": 11156,
            "note": "Fringe week is still live. Spend is concentrated on the remaining Edinburgh dates.",
            "performance_summary": (
                "Ticket sales stepped up again this week while CPC and CTR stayed efficient.\n"
                "CPP remains the strongest of the Edinburgh pair."
            ),
            "next_steps": (
                "Hold the current live set through the last Fringe shows.\n"
                "Review frequency before the final weekend."
            ),
        },
        {
            "name": "[TA] EDINBURGH",
            "status": "off",
            "event_label": "",
            "spent": 5876.13,
            "clicks": 246987,
            "ctr": "0.161",
            "tix": 4448,
            "note": "This line is off. The live Edinburgh volume now sits on the Fringe campaign.",
            "performance_summary": "Closed out at a stable CPP. No spend this week.",
            "next_steps": "Leave off unless a new Edinburgh on-sale is confirmed.",
            "off_from": date(2026, 8, 3),
        },
        {
            "name": "[TA] BLACKFRIARS",
            "status": "live",
            "event_label": "",
            "spent": 2195,
            "clicks": 172179,
            "ctr": "0.16",
            "tix": 9242,
            "note": "Blackfriars is still live and converting at a low CPP.",
            "performance_summary": (
                "Clicks and ticket volume both rose this week.\n"
                "CPC remains the cheapest live campaign."
            ),
            "next_steps": "Keep live. Watch saturation on the warm audience.",
        },
        {
            "name": "[TA] ON THE ROAD Campaign",
            "status": "live",
            "event_label": "",
            "spent": 4425,
            "clicks": 157924,
            "ctr": "0.13",
            "tix": 10810,
            "note": "Manchester is now off. Leeds and Newcastle are still live; Edinburgh and Glasgow stay as volume cities.",
            "performance_summary": "On the Road ticket sales keep climbing even after Manchester closed.",
            "next_steps": (
                "Monitor Leeds and Newcastle as remaining budget concentrates.\n"
                "Use Manchester's close-out as the baseline for the next on-sale."
            ),
            "locations": [
                {
                    "name": "Edinburgh",
                    "status": "live",
                    "spent": 1320,
                    "clicks": 48000,
                    "tix": 3100,
                    "note": "Edinburgh remains the volume driver and is converting efficiently at scale.",
                },
                {
                    "name": "Glasgow",
                    "status": "live",
                    "spent": 980,
                    "clicks": 36000,
                    "tix": 2500,
                    "note": "Glasgow is still live and holding a stable CPP.",
                },
                {
                    "name": "Manchester",
                    "status": "off",
                    "spent": 900,
                    "clicks": 32000,
                    "tix": 2200,
                    "note": "Manchester closed out strongly in its final stretch.",
                    "off_from": date(2026, 8, 10),
                },
                {
                    "name": "Leeds",
                    "status": "live",
                    "spent": 720,
                    "clicks": 24000,
                    "tix": 1600,
                    "note": "Leeds is carrying more of the live budget this week.",
                },
                {
                    "name": "Newcastle",
                    "status": "live",
                    "spent": 505,
                    "clicks": 17924,
                    "tix": 1410,
                    "note": "Newcastle is the newest live city and is still ramping.",
                    "from": date(2026, 8, 3),
                },
            ],
        },
        {
            "name": "[TA] BANTER TICKET SALES",
            "status": "off",
            "event_label": "",
            "spent": 2118,
            "clicks": 156340,
            "ctr": "0.15",
            "tix": 4640,
            "note": "Banter is off pending the next on-sale date.",
            "performance_summary": "No spend this week.",
            "next_steps": "Hold off until the next on-sale date is confirmed.",
            "off_from": date(2026, 7, 27),
        },
        {
            "name": "[TA] Glesga da - Farewell Tour",
            "status": "off",
            "event_label": "",
            "spent": 2244.92,
            "clicks": 77501,
            "ctr": "0.13",
            "tix": 1846,
            "note": "Farewell tour is closed.",
            "performance_summary": "Final week of spend already passed.",
            "next_steps": "Leave archived unless a late date is added.",
            "off_from": date(2026, 7, 27),
        },
    ]


def demo_status(db: Session, slug: str = CLIENT_SLUG) -> dict:
    client = require_client(db, slug)
    weeks = list(
        db.scalars(select(Week).where(Week.client_id == client.id).order_by(Week.period_end.desc()))
    )
    campaigns = list(
        db.scalars(
            select(Campaign)
            .where(Campaign.client_id == client.id, Campaign.archived_at.is_(None))
            .options(selectinload(Campaign.locations))
            .order_by(Campaign.name)
        )
    )
    location_count = 0
    if campaigns:
        location_count = db.scalar(
            select(func.count(Location.id)).where(Location.campaign_id.in_([c.id for c in campaigns]))
        )
    return {
        "client": {"id": client.id, "name": client.name, "currency": client.currency},
        "weeks": len(weeks),
        "campaigns": len(campaigns),
        "locations": int(location_count or 0),
        "latest_week": week_payload(weeks[0]) if weeks else None,
        "week_rows": [
            {"id": week.id, "period_end": week.period_end.isoformat(), "label": week_label(week)}
            for week in weeks
        ],
        "campaign_rows": [
            {
                "id": campaign.id,
                "name": campaign.name,
                "status": campaign.status,
                "event_label": campaign.event_label or "",
                "cities": [loc.name for loc in sorted(campaign.locations, key=lambda item: item.name.lower())],
            }
            for campaign in campaigns
        ],
    }


def clear_reporting(db: Session, slug: str = CLIENT_SLUG) -> dict:
    client = require_client(db, slug)
    weeks = list(db.scalars(select(Week).where(Week.client_id == client.id)))
    campaigns = list(db.scalars(select(Campaign).where(Campaign.client_id == client.id)))
    week_ids = [week.id for week in weeks]
    campaign_ids = [campaign.id for campaign in campaigns]
    if week_ids:
        db.execute(delete(WeekLocationMetric).where(WeekLocationMetric.week_id.in_(week_ids)))
        db.execute(delete(WeekCampaignMetric).where(WeekCampaignMetric.week_id.in_(week_ids)))
        db.execute(delete(Week).where(Week.id.in_(week_ids)))
    if campaign_ids:
        db.execute(delete(Location).where(Location.campaign_id.in_(campaign_ids)))
        db.execute(delete(Campaign).where(Campaign.id.in_(campaign_ids)))
    db.flush()
    return demo_status(db, slug)


def load_demo(db: Session, slug: str = CLIENT_SLUG, *, replace: bool = False) -> dict:
    if replace:
        clear_reporting(db, slug)
    client = require_client(db, slug)
    weeks = {
        period_end: _upsert_week(db, client, period_end, updated_until)
        for period_end, updated_until in DEMO_WEEKS
    }
    latest = DEMO_WEEKS[-1][0]
    now = _now()
    for spec in _campaign_specs():
        campaign = _upsert_campaign(db, client, spec, now)
        locations = {
            loc_spec["name"]: _upsert_location(db, campaign, loc_spec) for loc_spec in spec.get("locations", [])
        }
        for period_end, week in weeks.items():
            factor = _WEEK_FACTORS[period_end]
            off_from = spec.get("off_from")
            active = off_from is None or period_end < off_from
            metric = _upsert_campaign_metric(db, week, campaign)
            if spec.get("locations"):
                total_spend = Decimal("0")
                total_clicks = 0
                total_tix = 0
                for loc_spec in spec["locations"]:
                    loc_from = loc_spec.get("from")
                    if loc_from and period_end < loc_from:
                        continue
                    loc_off = loc_spec.get("off_from")
                    loc_active = loc_off is None or period_end < loc_off
                    loc_factor = factor if loc_active else factor * 0.15
                    loc_metric = _upsert_location_metric(db, week, locations[loc_spec["name"]])
                    loc_metric.amount_spent = _scale(loc_spec["spent"], loc_factor)
                    loc_metric.clicks = _iscale(loc_spec["clicks"], loc_factor)
                    loc_metric.tix_sold = _iscale(loc_spec["tix"], loc_factor)
                    loc_metric.note = loc_spec.get("note", "") if period_end == latest else ""
                    total_spend += loc_metric.amount_spent or Decimal("0")
                    total_clicks += loc_metric.clicks
                    total_tix += loc_metric.tix_sold
                metric.amount_spent = total_spend
                metric.clicks = total_clicks
                metric.tix_sold = total_tix
                metric.ctr_imported = _dec(spec["ctr"])
            elif active:
                metric.amount_spent = _scale(spec["spent"], factor)
                metric.clicks = _iscale(spec["clicks"], factor)
                metric.tix_sold = _iscale(spec["tix"], factor)
                metric.ctr_imported = _dec(spec["ctr"])
            else:
                metric.amount_spent = Decimal("0")
                metric.clicks = 0
                metric.tix_sold = 0
                metric.ctr_imported = None
            if period_end == latest:
                metric.note = spec.get("note", "")
                metric.performance_summary = spec.get("performance_summary", "")
                metric.next_steps = spec.get("next_steps", "")
            else:
                metric.note = ""
                metric.performance_summary = ""
                metric.next_steps = ""
    db.flush()
    return demo_status(db, slug)


def append_demo_week(db: Session, slug: str = CLIENT_SLUG) -> dict:
    client = require_client(db, slug)
    latest = db.scalar(select(Week).where(Week.client_id == client.id).order_by(Week.period_end.desc()))
    if latest is None:
        return load_demo(db, slug)
    period_end = latest.period_end + timedelta(days=7)
    existing = db.scalar(select(Week).where(Week.client_id == client.id, Week.period_end == period_end))
    if existing is not None:
        return demo_status(db, slug)
    week = Week(
        client_id=client.id,
        period_end=period_end,
        updated_until=f"{period_end.day}/{period_end.month}",
    )
    db.add(week)
    db.flush()
    factor = Decimal("1.06")
    for old in db.scalars(select(WeekCampaignMetric).where(WeekCampaignMetric.week_id == latest.id)):
        metric = WeekCampaignMetric(
            week_id=week.id,
            campaign_id=old.campaign_id,
            amount_spent=_dec(old.amount_spent) * factor,
            clicks=int(round(old.clicks * 1.06)),
            impressions=old.impressions,
            ctr_imported=old.ctr_imported,
            tix_sold=int(round(old.tix_sold * 1.06)),
        )
        db.add(metric)
    for old in db.scalars(select(WeekLocationMetric).where(WeekLocationMetric.week_id == latest.id)):
        spent = _dec(old.amount_spent) * factor if old.amount_spent is not None else None
        db.add(
            WeekLocationMetric(
                week_id=week.id,
                location_id=old.location_id,
                amount_spent=spent,
                clicks=int(round(old.clicks * 1.06)),
                tix_sold=int(round(old.tix_sold * 1.06)),
            )
        )
    db.flush()
    return demo_status(db, slug)


def _upsert_week(db: Session, client: Client, period_end: date, updated_until: str) -> Week:
    week = db.scalar(select(Week).where(Week.client_id == client.id, Week.period_end == period_end))
    if week is None:
        week = Week(client_id=client.id, period_end=period_end, updated_until=updated_until)
        db.add(week)
        db.flush()
        return week
    week.updated_until = updated_until
    return week


def _upsert_campaign(db: Session, client: Client, spec: dict, now: datetime) -> Campaign:
    campaign = db.scalar(select(Campaign).where(Campaign.client_id == client.id, Campaign.name == spec["name"]))
    if campaign is None:
        campaign = Campaign(client_id=client.id, name=spec["name"])
        db.add(campaign)
        db.flush()
    campaign.platform = "META"
    campaign.status = spec["status"]
    campaign.event_label = spec.get("event_label") or ""
    campaign.archived_at = None
    campaign.last_imported_at = now
    return campaign


def _upsert_location(db: Session, campaign: Campaign, spec: dict) -> Location:
    location = next((item for item in campaign.locations if item.name == spec["name"]), None)
    if location is None:
        location = Location(name=spec["name"])
        campaign.locations.append(location)
        db.flush()
    location.status = spec.get("status") or "live"
    return location


def _upsert_campaign_metric(db: Session, week: Week, campaign: Campaign) -> WeekCampaignMetric:
    metric = db.scalar(
        select(WeekCampaignMetric).where(
            WeekCampaignMetric.week_id == week.id,
            WeekCampaignMetric.campaign_id == campaign.id,
        )
    )
    if metric is None:
        metric = WeekCampaignMetric(week_id=week.id, campaign_id=campaign.id)
        db.add(metric)
        db.flush()
    return metric


def _upsert_location_metric(db: Session, week: Week, location: Location) -> WeekLocationMetric:
    metric = db.scalar(
        select(WeekLocationMetric).where(
            WeekLocationMetric.week_id == week.id,
            WeekLocationMetric.location_id == location.id,
        )
    )
    if metric is None:
        metric = WeekLocationMetric(week_id=week.id, location_id=location.id)
        db.add(metric)
        db.flush()
    return metric
