from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models import Base, Campaign, Client, Location, Week, WeekCampaignMetric, WeekLocationMetric
from app.services.pdf import HTML, render_monthly_html, render_weekly_html
from app.services.queries import monthly_rollup, overview_for_week


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, future=True)()


def _client(db: Session) -> Client:
    client = Client(name="Stuart Mitchell", slug="stuart-mitchell", currency="GBP")
    db.add(client)
    db.flush()
    return client


def test_weekly_html_is_bots_lab_report() -> None:
    db = _session()
    client = _client(db)
    prior = Week(client_id=client.id, period_end=date(2026, 8, 3), updated_until="3/8")
    week = Week(client_id=client.id, period_end=date(2026, 8, 10), updated_until="10/8")
    db.add_all([prior, week])
    db.flush()
    road = Campaign(
        client_id=client.id,
        name="[TA] ON THE ROAD",
        platform="META",
        status="live",
        event_label="On the Road",
    )
    fringe = Campaign(
        client_id=client.id,
        name="[TA] EDINBURGH SHOWS",
        platform="META",
        status="live",
        event_label="Edinburgh Shows",
    )
    db.add_all([road, fringe])
    db.flush()
    dundee = Location(campaign_id=road.id, name="Dundee", status="live")
    aberdeen = Location(campaign_id=road.id, name="Aberdeen", status="off")
    db.add_all([dundee, aberdeen])
    db.flush()
    db.add_all(
        [
            WeekCampaignMetric(
                week_id=prior.id,
                campaign_id=road.id,
                amount_spent=Decimal("3000"),
                clicks=100000,
                tix_sold=2000,
            ),
            WeekCampaignMetric(
                week_id=week.id,
                campaign_id=road.id,
                amount_spent=Decimal("3886.57"),
                clicks=153063,
                ctr_imported=Decimal("0.13"),
                tix_sold=3087,
                note="Dundee is the only city still live.",
                performance_summary="Ticket sales across the tour continue to climb.",
                next_steps="Monitor Dundee as the show date nears.",
            ),
            WeekCampaignMetric(
                week_id=week.id,
                campaign_id=fringe.id,
                amount_spent=Decimal("2874"),
                clicks=167961,
                ctr_imported=Decimal("0.16"),
                tix_sold=11018,
                performance_summary="CPC and CTR holding steady at scale.",
                next_steps="Continue current targeting and creative.",
            ),
            WeekLocationMetric(
                week_id=prior.id, location_id=dundee.id, amount_spent=Decimal("700"), clicks=30000, tix_sold=700
            ),
            WeekLocationMetric(
                week_id=prior.id, location_id=aberdeen.id, amount_spent=Decimal("700"), clicks=20000, tix_sold=500
            ),
            WeekLocationMetric(
                week_id=week.id,
                location_id=dundee.id,
                amount_spent=Decimal("765.57"),
                clicks=33783,
                tix_sold=809,
                note="Dundee remains the top-performing location by volume.",
            ),
            WeekLocationMetric(
                week_id=week.id,
                location_id=aberdeen.id,
                amount_spent=Decimal("788"),
                clicks=24447,
                tix_sold=644,
                note="Aberdeen closed out with a healthy final tally.",
            ),
        ]
    )
    db.flush()

    html = render_weekly_html(overview_for_week(db, week), client.name, client.currency)
    assert "Space Grotesk" in html
    assert "Manrope" in html
    assert "fonts/Manrope-Regular.ttf" in html
    assert "fonts/SpaceGrotesk-SemiBold.ttf" in html
    assert "Meta Ads Weekly Report" in html
    assert "Account manager: Abby" in html
    assert "Updated to 10/8" in html
    assert "Overview" in html
    assert "On the Road" in html
    assert "Edinburgh Shows" in html
    assert "Dundee is the only city still live." in html
    assert "Next moves" in html
    assert "Monitor Dundee as the show date nears." in html
    assert "3/8" in html
    assert "Performance notes" not in html  # single-line summaries surface as the campaign card summary, no extra card
    assert "Ticket sales across the tour continue to climb." in html
    assert "CPC and CTR holding steady at scale." in html
    assert "Dundee remains the top-performing location by volume." in html
    assert "Aberdeen closed out with a healthy final tally." in html
    assert "Powered by" in html
    assert "tb." in html
    assert "punchline-logo.png" not in html


@pytest.mark.skipif(HTML is None, reason="WeasyPrint not installed")
def test_weekly_pdf_bytes() -> None:
    db = _session()
    client = _client(db)
    week = Week(client_id=client.id, period_end=date(2026, 8, 10), updated_until="10/8")
    db.add(week)
    db.flush()
    campaign = Campaign(client_id=client.id, name="[TA] Demo", platform="META", status="live")
    db.add(campaign)
    db.flush()
    db.add(WeekCampaignMetric(week_id=week.id, campaign_id=campaign.id, amount_spent=Decimal("10"), clicks=100))
    db.flush()
    html = render_weekly_html(overview_for_week(db, week), client.name, client.currency)
    pdf = HTML(string=html, base_url=str(__import__("app.config", fromlist=["TEMPLATE_DIR"]).TEMPLATE_DIR)).write_pdf()
    assert pdf[:4] == b"%PDF"


def test_monthly_html_cover() -> None:
    db = _session()
    client = _client(db)
    week = Week(client_id=client.id, period_end=date(2026, 8, 10), updated_until="10/8")
    db.add(week)
    db.flush()
    html = render_monthly_html(monthly_rollup(db, client, 2026, 8), client.name, client.currency)
    assert "August 2026" in html
    assert "monthly presentation" in html
