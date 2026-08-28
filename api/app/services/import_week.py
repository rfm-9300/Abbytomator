from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Campaign, Client, Location, Week, WeekCampaignMetric, WeekLocationMetric
from app.services.csv_source import is_ignored_campaign
from app.services.insights import CampaignInsight, InsightsSource


@dataclass
class ImportResult:
    campaigns_upserted: int
    locations_upserted: int
    updated_until: str | None


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def apply_insights(
    db: Session,
    client: Client,
    week: Week,
    insights: list[CampaignInsight],
    updated_until: str | None,
) -> ImportResult:
    now = _utcnow()
    if updated_until:
        week.updated_until = updated_until

    campaign_count = 0
    location_count = 0
    seen_campaigns: set[str] = set()

    for row in insights:
        if is_ignored_campaign(row.name):
            continue
        campaign = db.scalar(
            select(Campaign).where(Campaign.client_id == client.id, Campaign.name == row.name)
        )
        if campaign is None:
            campaign = Campaign(
                client_id=client.id,
                name=row.name,
                platform=row.platform,
                status=row.status,
                event_label="",
            )
            db.add(campaign)
            db.flush()
        campaign.platform = row.platform
        campaign.status = row.status
        campaign.last_imported_at = now
        if (campaign.event_label or "").strip() == campaign.name.strip():
            campaign.event_label = ""
        if row.name not in seen_campaigns:
            campaign_count += 1
            seen_campaigns.add(row.name)

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

        if row.city:
            location = db.scalar(
                select(Location).where(Location.campaign_id == campaign.id, Location.name == row.city)
            )
            if location is None:
                location = Location(campaign_id=campaign.id, name=row.city)
                db.add(location)
                db.flush()
            location_count += 1
            loc_metric = db.scalar(
                select(WeekLocationMetric).where(
                    WeekLocationMetric.week_id == week.id,
                    WeekLocationMetric.location_id == location.id,
                )
            )
            if loc_metric is None:
                loc_metric = WeekLocationMetric(week_id=week.id, location_id=location.id)
                db.add(loc_metric)
            loc_metric.amount_spent = row.amount_spent
            loc_metric.clicks = row.clicks
            if not loc_metric.tix_sold and row.tix_sold:
                loc_metric.tix_sold = row.tix_sold
        else:
            metric.amount_spent = row.amount_spent
            metric.clicks = row.clicks
            metric.impressions = row.impressions
            metric.ctr_imported = row.ctr
            if not metric.tix_sold and row.tix_sold:
                metric.tix_sold = row.tix_sold

    for campaign in db.scalars(select(Campaign).where(Campaign.client_id == client.id)).all():
        if is_ignored_campaign(campaign.name) and campaign.archived_at is None:
            campaign.archived_at = now
        elif (campaign.event_label or "").strip() == campaign.name.strip():
            campaign.event_label = ""

    rollup_city_spend(db, week)
    return ImportResult(
        campaigns_upserted=campaign_count,
        locations_upserted=location_count,
        updated_until=week.updated_until,
    )


def import_from_source(
    db: Session,
    client: Client,
    week: Week,
    source: InsightsSource,
    raw: bytes | None = None,
) -> ImportResult:
    insights, updated_until = source.fetch(raw, until=week.period_end)
    return apply_insights(db, client, week, insights, updated_until)


def rollup_city_spend(db: Session, week: Week) -> None:
    """When city rows carry spend, campaign spend is the sum of those cities."""
    metrics = db.scalars(
        select(WeekCampaignMetric).where(WeekCampaignMetric.week_id == week.id)
    ).all()
    for metric in metrics:
        campaign = db.get(Campaign, metric.campaign_id)
        if campaign is None:
            continue
        loc_ids = list(
            db.scalars(select(Location.id).where(Location.campaign_id == campaign.id))
        )
        if not loc_ids:
            continue
        loc_metrics = db.scalars(
            select(WeekLocationMetric).where(
                WeekLocationMetric.week_id == week.id,
                WeekLocationMetric.location_id.in_(loc_ids),
            )
        ).all()
        spends = [m.amount_spent for m in loc_metrics if m.amount_spent is not None]
        if spends:
            metric.amount_spent = sum(spends, Decimal("0"))
        city_clicks = [m.clicks for m in loc_metrics if m.clicks]
        if city_clicks:
            metric.clicks = sum(city_clicks)
        tix = sum(m.tix_sold for m in loc_metrics)
        if tix:
            metric.tix_sold = tix
