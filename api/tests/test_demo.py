from __future__ import annotations

from datetime import date

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.models import Base, Campaign, Client, Week
from app.services.demo import append_demo_week, clear_reporting, demo_status, load_demo
from app.services.queries import monthly_rollup, overview_for_week


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, future=True)()


def test_load_demo_covers_weeks_campaigns_and_cities() -> None:
    db = _session()
    status = load_demo(db)
    db.flush()
    assert status["weeks"] == 5
    assert status["campaigns"] == 6
    assert status["locations"] == 5
    assert status["latest_week"]["updated_until"] == "17/8"
    names = {row["name"] for row in status["campaign_rows"]}
    assert "[TA] ON THE ROAD Campaign" in names
    assert "[TA] BLACKFRIARS" in names
    otr = next(row for row in status["campaign_rows"] if "ON THE ROAD" in row["name"])
    assert set(otr["cities"]) == {"Edinburgh", "Glasgow", "Manchester", "Leeds", "Newcastle"}


def test_demo_overview_has_cities_and_letter_notes() -> None:
    db = _session()
    load_demo(db)
    db.flush()
    week = db.scalar(select(Week).where(Week.period_end == date(2026, 8, 17)))
    overview = overview_for_week(db, week)
    names = [
        campaign["name"]
        for group in overview["groups"]
        for campaign in group["campaigns"]
    ]
    assert "[TA] EDINBURGH SHOWS// FRINGE" in names
    assert "[TA] EDINBURGH" in names
    assert all(len(group["campaigns"]) == 1 for group in overview["groups"])
    otr = next(
        campaign
        for group in overview["groups"]
        for campaign in group["campaigns"]
        if "ON THE ROAD" in campaign["name"]
    )
    assert len(otr["locations"]) == 5
    assert otr["note"]
    assert overview["has_structured_notes"] is True
    assert overview["totals"]["tix_sold"] > 0


def test_monthly_has_july_and_august() -> None:
    db = _session()
    load_demo(db)
    db.flush()
    client = db.scalar(select(Client))
    july = monthly_rollup(db, client, 2026, 7)
    august = monthly_rollup(db, client, 2026, 8)
    assert len(july["weeks"]) == 2
    assert len(august["weeks"]) == 3


def test_replace_and_clear() -> None:
    db = _session()
    load_demo(db)
    db.flush()
    extra = Campaign(client_id=db.scalar(select(Client)).id, name="Custom leftover")
    db.add(extra)
    db.flush()
    assert demo_status(db)["campaigns"] == 7
    replaced = load_demo(db, replace=True)
    db.flush()
    assert replaced["campaigns"] == 6
    assert "Custom leftover" not in {row["name"] for row in replaced["campaign_rows"]}
    cleared = clear_reporting(db)
    db.flush()
    assert cleared["weeks"] == 0
    assert cleared["campaigns"] == 0
    assert db.scalar(select(Client)) is not None


def test_append_demo_week() -> None:
    db = _session()
    load_demo(db)
    db.flush()
    status = append_demo_week(db)
    db.flush()
    assert status["weeks"] == 6
    assert status["latest_week"]["period_end"] == "2026-08-24"
