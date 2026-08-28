from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.models import Base, Campaign, Client, Week, WeekCampaignMetric, WeekLocationMetric
from app.services.csv_source import CsvInsightsSource, parse_csv
from app.services.import_week import apply_insights, import_from_source
from app.services.queries import monthly_rollup, overview_for_week

FIXTURES = Path(__file__).parent / "fixtures"


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, future=True)()


def _client_week(db: Session) -> tuple[Client, Week]:
    client = Client(name="Stuart Mitchell", slug="stuart-mitchell", currency="GBP")
    db.add(client)
    db.flush()
    week = Week(client_id=client.id, period_end=date(2026, 8, 10))
    db.add(week)
    db.flush()
    return client, week


def test_abby_overview_skips_merge_and_does_not_group_by_name() -> None:
    db = _session()
    client, week = _client_week(db)
    insights, updated = parse_csv((FIXTURES / "abby-overview.csv").read_bytes())
    assert updated == "10/8"
    names = [row.name for row in insights]
    assert "MERGE VENUE CAMPAIGNS 2.0" not in names
    assert names == [
        "[TA] EDINBURGH",
        "[TA] Glesga da - Farewell Tour",
        "[TA] ON THE ROAD Campaign",
        "[TA] BANTER TICKET SALES",
        "[TA] EDINBURGH SHOWS// FRINGE",
        "[TA] BLACKFRIARS",
    ]
    result = apply_insights(db, client, week, insights, updated)
    db.flush()
    assert result.campaigns_upserted == 6
    overview = overview_for_week(db, week)
    assert [g["event_label"] for g in overview["groups"]] == [
        c["name"] for g in overview["groups"] for c in g["campaigns"]
    ]
    assert all(len(g["campaigns"]) == 1 for g in overview["groups"])
    stored = db.scalars(select(Campaign).where(Campaign.client_id == client.id)).all()
    assert all(not campaign.event_label for campaign in stored if not campaign.archived_at)


def test_import_creates_campaigns_and_metrics() -> None:
    db = _session()
    client, week = _client_week(db)
    result = import_from_source(db, client, week, CsvInsightsSource(), (FIXTURES / "overview.csv").read_bytes())
    db.commit()
    assert result.campaigns_upserted == 3
    assert week.updated_until == "10/8"
    overview = overview_for_week(db, week)
    assert overview["totals"]["tix_sold"] == 4448 + 10810 + 9242
    names = [c["name"] for g in overview["groups"] for c in g["campaigns"]]
    assert "[TA] BLACKFRIARS" in names


def test_reimport_preserves_tix_sold() -> None:
    db = _session()
    client, week = _client_week(db)
    insights, updated = parse_csv((FIXTURES / "overview.csv").read_bytes())
    apply_insights(db, client, week, insights, updated)
    db.flush()
    campaign = db.scalar(select(Campaign).where(Campaign.name == "[TA] EDINBURGH"))
    metric = db.scalar(
        select(WeekCampaignMetric).where(
            WeekCampaignMetric.week_id == week.id, WeekCampaignMetric.campaign_id == campaign.id
        )
    )
    metric.tix_sold = 99
    db.flush()
    apply_insights(db, client, week, insights, updated)
    db.flush()
    metric = db.scalar(
        select(WeekCampaignMetric).where(
            WeekCampaignMetric.week_id == week.id, WeekCampaignMetric.campaign_id == campaign.id
        )
    )
    assert metric.tix_sold == 99
    assert metric.amount_spent == Decimal("5876.13")


def test_city_import_rollups_spend_and_tix() -> None:
    db = _session()
    client, week = _client_week(db)
    import_from_source(db, client, week, CsvInsightsSource(), (FIXTURES / "cities.csv").read_bytes())
    db.flush()
    overview = overview_for_week(db, week)
    campaign = overview["groups"][0]["campaigns"][0]
    assert campaign["amount_spent"] == 150.0
    assert campaign["tix_sold"] == 120
    assert campaign["clicks"] == 700
    assert len(campaign["locations"]) == 2
    assert campaign["locations"][0]["clicks"] in {500, 200}


def test_monthly_rollup() -> None:
    db = _session()
    client, week = _client_week(db)
    import_from_source(db, client, week, CsvInsightsSource(), (FIXTURES / "overview.csv").read_bytes())
    db.flush()
    rollup = monthly_rollup(db, client, 2026, 8)
    assert len(rollup["weeks"]) == 1
    assert rollup["totals"]["tix_sold"] == overview_for_week(db, week)["totals"]["tix_sold"]
    empty = monthly_rollup(db, client, 2026, 1)
    assert empty["weeks"] == []
    assert empty["totals"]["amount_spent"] == 0


def test_overview_letter_fields_and_history() -> None:
    db = _session()
    client, week = _client_week(db)
    earlier = Week(client_id=client.id, period_end=date(2026, 8, 3), updated_until="3/8")
    db.add(earlier)
    db.flush()
    import_from_source(db, client, week, CsvInsightsSource(), (FIXTURES / "cities.csv").read_bytes())
    db.flush()
    campaign = db.scalar(select(Campaign).where(Campaign.name == "[TA] FRINGE"))
    metric = db.scalar(
        select(WeekCampaignMetric).where(
            WeekCampaignMetric.week_id == week.id, WeekCampaignMetric.campaign_id == campaign.id
        )
    )
    metric.note = "Glasgow is now off."
    metric.next_steps = "Hold spend on Edinburgh."
    loc = campaign.locations[0]
    loc.status = "off"
    loc_metric = db.scalar(
        select(WeekLocationMetric).where(
            WeekLocationMetric.week_id == week.id, WeekLocationMetric.location_id == loc.id
        )
    )
    loc_metric.note = "Closed out this week."
    db.flush()
    overview = overview_for_week(db, week)
    row = overview["groups"][0]["campaigns"][0]
    assert row["note"] == "Glasgow is now off."
    assert row["next_steps"] == "Hold spend on Edinburgh."
    assert overview["has_structured_notes"] is True
    assert [h["label"] for h in overview["history"]] == ["3/8", "10/8"]
    city = next(item for item in row["locations"] if item["id"] == loc.id)
    assert city["status"] == "off"
    assert city["note"] == "Closed out this week."
    assert len(city["tix_history"]) == 2
