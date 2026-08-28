from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.models import Base, Campaign, Client, Week, WeekCampaignMetric, WeekLocationMetric
from app.services.queries import overview_for_week
from app.services.week_rows import (
    WeekRowError,
    add_campaign_to_week,
    add_location_to_week,
    delete_location,
    delete_week,
    patch_week_campaign,
    patch_week_location,
    remove_campaign_from_week,
)


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


def test_add_campaign_creates_overview_row() -> None:
    db = _session()
    client, week = _client_week(db)
    add_campaign_to_week(
        db,
        client,
        week,
        name="[TA] EDINBURGH",
        platform="META",
        status="live",
        amount_spent="120.50",
        clicks=80,
        ctr="13.5",
        tix_sold=12,
    )
    db.flush()
    overview = overview_for_week(db, week)
    row = overview["groups"][0]["campaigns"][0]
    assert row["name"] == "[TA] EDINBURGH"
    assert row["platform"] == "META"
    assert row["status"] == "live"
    assert row["amount_spent"] == 120.5
    assert row["clicks"] == 80
    assert row["tix_sold"] == 12
    assert row["ctr"] == pytest.approx(0.135)
    assert [loc["name"] for loc in row["locations"]] == ["Default"]
    assert row["locations"][0]["amount_spent"] == 120.5
    assert overview["totals"]["tix_sold"] == 12


def test_add_same_name_updates_this_week() -> None:
    db = _session()
    client, week = _client_week(db)
    add_campaign_to_week(db, client, week, name="OTR", amount_spent=10, clicks=4, tix_sold=1)
    add_campaign_to_week(db, client, week, name="OTR", amount_spent=25, clicks=9, tix_sold=3)
    db.flush()
    campaigns = db.scalars(select(Campaign).where(Campaign.client_id == client.id)).all()
    assert len(campaigns) == 1
    metric = db.scalar(select(WeekCampaignMetric))
    assert metric.amount_spent == Decimal("25")
    assert metric.tix_sold == 3


def test_empty_name_is_rejected() -> None:
    db = _session()
    client, week = _client_week(db)
    with pytest.raises(WeekRowError):
        add_campaign_to_week(db, client, week, name="  ")


def test_patch_campaign_numbers_and_name() -> None:
    db = _session()
    client, week = _client_week(db)
    campaign = add_campaign_to_week(db, client, week, name="Old", amount_spent=10, clicks=2)
    db.flush()
    patch_week_campaign(
        db,
        client,
        week,
        campaign,
        name="New",
        status="off",
        ctr=0.2,
    )
    patch_week_location(db, week, campaign.locations[0], amount_spent=40, clicks=8, tix_sold=5)
    db.flush()
    overview = overview_for_week(db, week)
    row = overview["groups"][0]["campaigns"][0]
    assert row["name"] == "New"
    assert row["status"] == "off"
    assert row["amount_spent"] == 40
    assert row["clicks"] == 8
    assert row["tix_sold"] == 5
    assert row["ctr"] == pytest.approx(0.2)


def test_add_campaign_with_named_city() -> None:
    db = _session()
    client, week = _client_week(db)
    add_campaign_to_week(db, client, week, name="OTR", city="Edinburgh", amount_spent=150, tix_sold=80)
    db.flush()
    row = overview_for_week(db, week)["groups"][0]["campaigns"][0]
    assert [loc["name"] for loc in row["locations"]] == ["Edinburgh"]
    assert row["amount_spent"] == 150
    assert row["tix_sold"] == 80


def test_blank_city_becomes_default() -> None:
    db = _session()
    client, week = _client_week(db)
    add_campaign_to_week(db, client, week, name="OTR", city="  ", amount_spent=10)
    db.flush()
    row = overview_for_week(db, week)["groups"][0]["campaigns"][0]
    assert [loc["name"] for loc in row["locations"]] == ["Default"]
    assert row["amount_spent"] == 10


def test_remove_campaign_from_week_keeps_other_weeks() -> None:
    db = _session()
    client, week = _client_week(db)
    other = Week(client_id=client.id, period_end=date(2026, 8, 17))
    db.add(other)
    db.flush()
    campaign = add_campaign_to_week(db, client, week, name="OTR", amount_spent=50, tix_sold=5)
    add_campaign_to_week(db, client, other, name="OTR", amount_spent=70, tix_sold=9)
    db.flush()
    remove_campaign_from_week(db, week, campaign)
    db.flush()
    assert overview_for_week(db, week)["groups"] == []
    kept = overview_for_week(db, other)["groups"][0]["campaigns"][0]
    assert kept["amount_spent"] == 70
    # The campaign definition survives for other weeks.
    assert db.scalar(select(Campaign).where(Campaign.name == "OTR")) is not None


def test_delete_week_drops_that_week_only() -> None:
    db = _session()
    client, week = _client_week(db)
    other = Week(client_id=client.id, period_end=date(2026, 8, 17))
    db.add(other)
    db.flush()
    campaign = add_campaign_to_week(db, client, week, name="OTR", amount_spent=50, tix_sold=5)
    add_campaign_to_week(db, client, other, name="OTR", amount_spent=70, tix_sold=9)
    db.flush()
    delete_week(db, week)
    db.flush()
    assert db.get(Week, week.id) is None
    kept = overview_for_week(db, other)["groups"][0]["campaigns"][0]
    assert kept["amount_spent"] == 70
    assert db.scalar(select(Campaign).where(Campaign.name == "OTR")) is not None
    assert db.scalar(select(WeekCampaignMetric).where(WeekCampaignMetric.campaign_id == campaign.id)) is not None


def test_delete_city_resums_campaign_spend() -> None:
    db = _session()
    client, week = _client_week(db)
    campaign = add_campaign_to_week(db, client, week, name="OTR", city="Edinburgh", amount_spent=100, tix_sold=80)
    glasgow = add_location_to_week(db, week, campaign, name="Glasgow", amount_spent=50, tix_sold=40)
    db.flush()
    assert overview_for_week(db, week)["groups"][0]["campaigns"][0]["amount_spent"] == 150
    delete_location(db, glasgow)
    db.flush()
    row = overview_for_week(db, week)["groups"][0]["campaigns"][0]
    assert row["amount_spent"] == 100
    assert row["tix_sold"] == 80
    assert [loc["name"] for loc in row["locations"]] == ["Edinburgh"]


def test_previous_week_totals_for_kpi_deltas() -> None:
    db = _session()
    client, week = _client_week(db)
    later = Week(client_id=client.id, period_end=date(2026, 8, 17), updated_until="17/8")
    db.add(later)
    db.flush()
    add_campaign_to_week(db, client, week, name="OTR", amount_spent=100, clicks=10, tix_sold=10)
    add_campaign_to_week(db, client, later, name="OTR", amount_spent=150, clicks=20, tix_sold=15)
    db.flush()
    assert overview_for_week(db, week)["previous"] is None
    current = overview_for_week(db, later)
    assert current["previous"]["label"] == "10/8"
    assert current["previous"]["totals"]["amount_spent"] == 100
    assert current["totals"]["amount_spent"] == 150


def test_patch_city_rollups_spend_and_tix() -> None:
    db = _session()
    client, week = _client_week(db)
    campaign = add_campaign_to_week(
        db, client, week, name="OTR", city="Edinburgh", amount_spent=100, clicks=400, tix_sold=80
    )
    glasgow = add_location_to_week(
        db, week, campaign, name="Glasgow", amount_spent=50, clicks=200, tix_sold=40
    )
    db.flush()
    patch_week_location(db, week, glasgow, amount_spent=75, tix_sold=55)
    db.flush()
    overview = overview_for_week(db, week)
    row = overview["groups"][0]["campaigns"][0]
    assert row["amount_spent"] == 175
    assert row["tix_sold"] == 135
    assert {loc["name"] for loc in row["locations"]} == {"Edinburgh", "Glasgow"}
