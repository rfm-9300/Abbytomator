from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from app.metrics import cpp, parse_money, parse_percent
from app.services.csv_source import normalize_status, parse_csv

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_abby_overview_csv() -> None:
    insights, updated = parse_csv((FIXTURES / "overview.csv").read_bytes())
    assert updated == "10/8"
    assert len(insights) == 3
    edinburgh = insights[0]
    assert edinburgh.name == "[TA] EDINBURGH"
    assert edinburgh.status == "off"
    assert edinburgh.amount_spent == Decimal("5876.13")
    assert edinburgh.clicks == 246987
    assert edinburgh.tix_sold == 4448
    assert edinburgh.ctr == Decimal("0.1610")
    road = insights[1]
    assert road.status == "live"
    assert road.tix_sold == 10810


def test_status_normalisation() -> None:
    assert normalize_status("Live ") == "live"
    assert normalize_status("Off") == "off"
    assert normalize_status("paused") == "off"


def test_parse_money_and_percent() -> None:
    assert parse_money("£17,633.17") == Decimal("17633.17")
    assert parse_percent("14.71%") == Decimal("0.1471")
    assert parse_percent("13%") == Decimal("0.13")


def test_cpp_zero_tickets() -> None:
    assert cpp(Decimal("100"), 0) is None
    assert cpp(Decimal("100"), 4) == Decimal("25.00")


def test_city_csv() -> None:
    insights, _ = parse_csv((FIXTURES / "cities.csv").read_bytes())
    assert len(insights) == 2
    assert insights[0].city == "Edinburgh"
    assert insights[1].city == "Glasgow"
