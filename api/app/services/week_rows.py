from __future__ import annotations

from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.metrics import parse_int, parse_money, parse_percent
from app.models import Campaign, Client, Location, Week, WeekCampaignMetric, WeekLocationMetric
from app.services.csv_source import is_ignored_campaign
from app.services.import_week import rollup_city_spend


class WeekRowError(ValueError):
    pass


DEFAULT_CITY = "Default"


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


def _require_name(name: str | None) -> str:
    token = (name or "").strip()
    if is_ignored_campaign(token):
        raise WeekRowError("Campaign name is required")
    return token


def _status(value: str | None, default: str = "live") -> str:
    if value is None:
        return default
    token = value.strip().lower()
    if token not in {"live", "off"}:
        raise WeekRowError("status must be live or off")
    return token


def get_or_create_campaign(
    db: Session,
    client: Client,
    name: str,
    *,
    platform: str | None = None,
    status: str | None = None,
) -> Campaign:
    clean = _require_name(name)
    campaign = db.scalar(select(Campaign).where(Campaign.client_id == client.id, Campaign.name == clean))
    if campaign is None:
        campaign = Campaign(
            client_id=client.id,
            name=clean,
            platform=(platform or "META").strip() or "META",
            status=_status(status, "live"),
            event_label="",
        )
        db.add(campaign)
        db.flush()
        return campaign
    if platform is not None:
        campaign.platform = platform.strip() or campaign.platform
    if status is not None:
        campaign.status = _status(status, campaign.status)
    if campaign.archived_at is not None:
        campaign.archived_at = None
    return campaign


def apply_campaign_numbers(
    metric: WeekCampaignMetric,
    *,
    amount_spent: object | None = None,
    clicks: object | None = None,
    ctr: object | None = None,
    tix_sold: object | None = None,
) -> None:
    if amount_spent is not None:
        metric.amount_spent = parse_money(amount_spent)
    if clicks is not None:
        metric.clicks = max(0, parse_int(clicks))
    if ctr is not None:
        metric.ctr_imported = parse_percent(ctr)
    if tix_sold is not None:
        metric.tix_sold = max(0, parse_int(tix_sold))


def add_campaign_to_week(
    db: Session,
    client: Client,
    week: Week,
    *,
    name: str,
    platform: str | None = "META",
    status: str | None = "live",
    city: str | None = None,
    amount_spent: object = 0,
    clicks: object = 0,
    ctr: object | None = None,
    tix_sold: object = 0,
) -> Campaign:
    """Create the campaign and its first city. Spend/clicks/tix live on the city; the campaign row is the sum."""
    campaign = get_or_create_campaign(db, client, name, platform=platform, status=status)
    metric = _campaign_metric(db, week, campaign.id)
    apply_campaign_numbers(metric, ctr=ctr)
    add_location_to_week(
        db,
        week,
        campaign,
        name=(city or "").strip() or DEFAULT_CITY,
        amount_spent=amount_spent,
        clicks=clicks,
        tix_sold=tix_sold,
    )
    return campaign


def patch_week_campaign(
    db: Session,
    client: Client,
    week: Week,
    campaign: Campaign,
    *,
    name: str | None = None,
    platform: str | None = None,
    status: str | None = None,
    amount_spent: object | None = None,
    clicks: object | None = None,
    ctr: object | None = None,
    tix_sold: object | None = None,
) -> Campaign:
    if name is not None:
        clean = _require_name(name)
        clash = db.scalar(
            select(Campaign).where(
                Campaign.client_id == client.id,
                Campaign.name == clean,
                Campaign.id != campaign.id,
            )
        )
        if clash is not None:
            raise WeekRowError("A campaign with that name already exists")
        campaign.name = clean
    if platform is not None:
        campaign.platform = platform.strip() or campaign.platform
    if status is not None:
        campaign.status = _status(status, campaign.status)
    metric = _campaign_metric(db, week, campaign.id)
    has_cities = bool(campaign.locations)
    apply_campaign_numbers(
        metric,
        amount_spent=None if has_cities else amount_spent,
        clicks=None if has_cities else clicks,
        ctr=ctr,
        tix_sold=None if has_cities else tix_sold,
    )
    if has_cities:
        rollup_city_spend(db, week)
    return campaign


def add_location_to_week(
    db: Session,
    week: Week,
    campaign: Campaign,
    *,
    name: str,
    amount_spent: object | None = None,
    clicks: object | None = None,
    tix_sold: object | None = None,
) -> Location:
    city = (name or "").strip()
    if not city:
        raise WeekRowError("City name is required")
    first_city = len(campaign.locations) == 0
    location = next((item for item in campaign.locations if item.name == city), None)
    if location is None:
        location = Location(name=city)
        campaign.locations.append(location)
        db.flush()
    loc_metric = _location_metric(db, week, location.id)
    spent = parse_money(amount_spent) if amount_spent is not None else Decimal("0")
    click_n = max(0, parse_int(clicks)) if clicks is not None else 0
    tix_n = max(0, parse_int(tix_sold)) if tix_sold is not None else 0
    if first_city and spent == 0 and click_n == 0 and tix_n == 0:
        campaign_metric = _campaign_metric(db, week, campaign.id)
        loc_metric.amount_spent = campaign_metric.amount_spent
        loc_metric.clicks = campaign_metric.clicks
        loc_metric.tix_sold = campaign_metric.tix_sold
    else:
        loc_metric.amount_spent = spent
        loc_metric.clicks = click_n
        loc_metric.tix_sold = tix_n
    rollup_city_spend(db, week)
    return location


def remove_campaign_from_week(db: Session, week: Week, campaign: Campaign) -> None:
    """Drop this campaign's line from one week. The campaign itself stays for other weeks."""
    loc_ids = [loc.id for loc in campaign.locations]
    if loc_ids:
        db.execute(
            delete(WeekLocationMetric).where(
                WeekLocationMetric.week_id == week.id,
                WeekLocationMetric.location_id.in_(loc_ids),
            )
        )
    db.execute(
        delete(WeekCampaignMetric).where(
            WeekCampaignMetric.week_id == week.id,
            WeekCampaignMetric.campaign_id == campaign.id,
        )
    )
    db.flush()


def delete_week(db: Session, week: Week) -> None:
    """Drop one week's numbers and letter notes. Campaigns and cities stay for other weeks."""
    db.execute(delete(WeekLocationMetric).where(WeekLocationMetric.week_id == week.id))
    db.execute(delete(WeekCampaignMetric).where(WeekCampaignMetric.week_id == week.id))
    db.expire(week)
    db.delete(week)
    db.flush()


def delete_location(db: Session, location: Location) -> None:
    """Cities are structural, so removing one drops it from every week."""
    campaign = location.campaign
    client_id = campaign.client_id
    db.execute(delete(WeekLocationMetric).where(WeekLocationMetric.location_id == location.id))
    campaign.locations.remove(location)
    db.delete(location)
    db.flush()
    # Campaign spend is the sum of its cities, so every week has to be re-summed.
    for week in db.scalars(select(Week).where(Week.client_id == client_id)):
        rollup_city_spend(db, week)
    db.flush()


def patch_week_location(
    db: Session,
    week: Week,
    location: Location,
    *,
    name: str | None = None,
    amount_spent: object | None = None,
    clicks: object | None = None,
    tix_sold: object | None = None,
) -> Location:
    if name is not None:
        city = name.strip()
        if not city:
            raise WeekRowError("City name is required")
        clash = db.scalar(
            select(Location).where(
                Location.campaign_id == location.campaign_id,
                Location.name == city,
                Location.id != location.id,
            )
        )
        if clash is not None:
            raise WeekRowError("That city already exists on this campaign")
        location.name = city
    loc_metric = _location_metric(db, week, location.id)
    if amount_spent is not None:
        loc_metric.amount_spent = parse_money(amount_spent)
    if clicks is not None:
        loc_metric.clicks = max(0, parse_int(clicks))
    if tix_sold is not None:
        loc_metric.tix_sold = max(0, parse_int(tix_sold))
    rollup_city_spend(db, week)
    return location
