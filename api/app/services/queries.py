from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.config import ACCOUNT_MANAGER, CLIENT_SLUG
from app.metrics import cpc, cpp, ctr
from app.models import Campaign, Client, Location, Week, WeekCampaignMetric, WeekLocationMetric
from app.services.csv_source import is_ignored_campaign


def require_client(db: Session, slug: str = CLIENT_SLUG) -> Client:
    client = db.scalar(select(Client).where(Client.slug == slug))
    if client is None:
        client = Client(name="Stuart Mitchell", slug=slug, currency="GBP")
        db.add(client)
        db.flush()
    return client


def _event_group_label(campaign: Campaign) -> str:
    label = (campaign.event_label or "").strip()
    name = (campaign.name or "").strip()
    if label and label != name:
        return label
    return ""


def week_label(week: Week) -> str:
    if week.updated_until and week.updated_until.strip():
        return week.updated_until.strip()
    return f"{week.period_end.day}/{week.period_end.month}"


def week_payload(week: Week) -> dict:
    return {
        "id": week.id,
        "period_end": week.period_end.isoformat(),
        "updated_until": week.updated_until,
        "label": week_label(week),
        "notes": week.notes or "",
    }


def _dec(value) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def campaign_metric_payload(
    campaign: Campaign,
    metric: WeekCampaignMetric | None,
    locations: list[dict],
) -> dict:
    spent = _dec(metric.amount_spent) if metric else Decimal("0")
    clicks = metric.clicks if metric else 0
    impressions = metric.impressions if metric else None
    imported_ctr = _dec(metric.ctr_imported) if metric and metric.ctr_imported is not None else None
    loc_tix = sum(int(loc["tix_sold"]) for loc in locations)
    tix = loc_tix if locations else (metric.tix_sold if metric else 0)
    rate = ctr(clicks, impressions, imported_ctr)
    return {
        "id": campaign.id,
        "name": campaign.name,
        "platform": campaign.platform,
        "status": campaign.status,
        "event_label": _event_group_label(campaign) or campaign.name,
        "external_id": campaign.external_id,
        "last_imported_at": campaign.last_imported_at.isoformat() if campaign.last_imported_at else None,
        "amount_spent": float(spent),
        "clicks": clicks,
        "impressions": impressions,
        "ctr": float(rate) if rate is not None else None,
        "cpc": float(cpc(spent, clicks)) if cpc(spent, clicks) is not None else None,
        "tix_sold": tix,
        "cpp": float(cpp(spent, tix)) if cpp(spent, tix) is not None else None,
        "note": (metric.note if metric else "") or "",
        "performance_summary": (metric.performance_summary if metric else "") or "",
        "next_steps": (metric.next_steps if metric else "") or "",
        "show_city_clicks": any(int(loc.get("clicks") or 0) for loc in locations),
        "locations": locations,
    }


def location_payload(
    location: Location,
    loc_metric: WeekLocationMetric | None,
    tix_history: list[int | None],
) -> dict:
    spent = _dec(loc_metric.amount_spent) if loc_metric and loc_metric.amount_spent is not None else None
    tix = loc_metric.tix_sold if loc_metric else 0
    clicks = loc_metric.clicks if loc_metric else 0
    loc_cpc = cpc(spent, clicks) if spent is not None else None
    return {
        "id": location.id,
        "name": location.name,
        "status": location.status or "live",
        "amount_spent": float(spent) if spent is not None else None,
        "clicks": clicks,
        "tix_sold": tix,
        "cpc": float(loc_cpc) if loc_cpc is not None else None,
        "cpp": float(cpp(spent, tix)) if spent is not None and cpp(spent, tix) is not None else None,
        "note": (loc_metric.note if loc_metric else "") or "",
        "tix_history": tix_history,
    }


def _history_weeks(db: Session, client_id: int, week: Week) -> list[Week]:
    return list(
        db.scalars(
            select(Week)
            .where(Week.client_id == client_id, Week.period_end <= week.period_end)
            .order_by(Week.period_end)
        ).all()
    )


def _unique_history(weeks: list[Week]) -> list[dict]:
    seen: set[str] = set()
    rows = []
    for item in weeks:
        label = week_label(item)
        if label in seen:
            label = f"{item.period_end.day}/{item.period_end.month}"
        if label in seen:
            label = item.period_end.isoformat()
        seen.add(label)
        rows.append({"id": item.id, "label": label, "period_end": item.period_end.isoformat()})
    return rows


def overview_for_week(db: Session, week: Week) -> dict:
    campaigns = db.scalars(
        select(Campaign)
        .where(Campaign.client_id == week.client_id, Campaign.archived_at.is_(None))
        .options(selectinload(Campaign.locations))
        .order_by(Campaign.event_label, Campaign.name)
    ).all()
    metrics = {
        m.campaign_id: m
        for m in db.scalars(select(WeekCampaignMetric).where(WeekCampaignMetric.week_id == week.id))
    }
    loc_metrics = {
        m.location_id: m
        for m in db.scalars(select(WeekLocationMetric).where(WeekLocationMetric.week_id == week.id))
    }
    history = _history_weeks(db, week.client_id, week)
    history_ids = [item.id for item in history]
    history_payload = _unique_history(history)
    hist_map: dict[tuple[int, int], int] = {}
    if history_ids:
        for row in db.scalars(select(WeekLocationMetric).where(WeekLocationMetric.week_id.in_(history_ids))):
            hist_map[(row.location_id, row.week_id)] = row.tix_sold

    campaigns = [
        campaign
        for campaign in campaigns
        if not is_ignored_campaign(campaign.name)
        and (campaign.id in metrics or any(loc.id in loc_metrics for loc in campaign.locations))
    ]

    groups: dict[str, list[dict]] = {}
    has_structured_notes = False
    for campaign in campaigns:
        locations = []
        for loc in sorted(campaign.locations, key=lambda item: item.name.lower()):
            tix_history = [hist_map.get((loc.id, item.id)) for item in history]
            payload_loc = location_payload(loc, loc_metrics.get(loc.id), tix_history)
            if payload_loc["note"]:
                has_structured_notes = True
            locations.append(payload_loc)
        payload = campaign_metric_payload(campaign, metrics.get(campaign.id), locations)
        if payload["note"] or payload["performance_summary"] or payload["next_steps"]:
            has_structured_notes = True
        group_key = _event_group_label(campaign) or f"__solo_{campaign.id}"
        groups.setdefault(group_key, []).append(payload)

    grouped = []
    grand_spend = Decimal("0")
    grand_clicks = 0
    grand_tix = 0
    for label, items in groups.items():
        spend = sum((_dec(item["amount_spent"]) for item in items), Decimal("0"))
        clicks = sum(item["clicks"] for item in items)
        tix = sum(item["tix_sold"] for item in items)
        grand_spend += spend
        grand_clicks += clicks
        grand_tix += tix
        grouped.append(
            {
                "event_label": items[0]["event_label"] if label.startswith("__solo_") else label,
                "campaigns": items,
                "totals": {
                    "amount_spent": float(spend),
                    "clicks": clicks,
                    "tix_sold": tix,
                    "cpc": float(cpc(spend, clicks)) if cpc(spend, clicks) is not None else None,
                    "cpp": float(cpp(spend, tix)) if cpp(spend, tix) is not None else None,
                },
            }
        )

    grouped.sort(key=lambda g: g["event_label"].lower())
    return {
        "week": week_payload(week),
        "account_manager": ACCOUNT_MANAGER,
        "history": history_payload,
        "has_structured_notes": has_structured_notes,
        "groups": grouped,
        "totals": {
            "amount_spent": float(grand_spend),
            "clicks": grand_clicks,
            "tix_sold": grand_tix,
            "cpc": float(cpc(grand_spend, grand_clicks)) if cpc(grand_spend, grand_clicks) is not None else None,
            "cpp": float(cpp(grand_spend, grand_tix)) if cpp(grand_spend, grand_tix) is not None else None,
        },
    }


def monthly_rollup(db: Session, client: Client, year: int, month: int) -> dict:
    weeks = db.scalars(
        select(Week)
        .where(Week.client_id == client.id)
        .order_by(Week.period_end)
    ).all()
    in_month = [w for w in weeks if w.period_end.year == year and w.period_end.month == month]
    overviews = [overview_for_week(db, week) for week in in_month]
    spend = sum((_dec(o["totals"]["amount_spent"]) for o in overviews), Decimal("0"))
    clicks = sum(o["totals"]["clicks"] for o in overviews)
    tix = sum(o["totals"]["tix_sold"] for o in overviews)
    return {
        "year": year,
        "month": month,
        "weeks": overviews,
        "totals": {
            "amount_spent": float(spend),
            "clicks": clicks,
            "tix_sold": tix,
            "cpc": float(cpc(spend, clicks)) if cpc(spend, clicks) is not None else None,
            "cpp": float(cpp(spend, tix)) if cpp(spend, tix) is not None else None,
        },
    }
