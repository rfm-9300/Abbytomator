from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base, Client, Week
from app.services import scheduler


def _session_factory():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, future=True)


@pytest.mark.parametrize(
    "now,weekday,hour,minute,expected",
    [
        # Monday 07:00, target Monday 08:00 same day -> today at 08:00.
        (datetime(2026, 8, 10, 7, 0), 0, 8, 0, datetime(2026, 8, 10, 8, 0)),
        # Monday 09:00, target Monday 08:00 already passed -> next Monday.
        (datetime(2026, 8, 10, 9, 0), 0, 8, 0, datetime(2026, 8, 17, 8, 0)),
        # Wednesday, target Monday -> the coming Monday.
        (datetime(2026, 8, 12, 12, 0), 0, 8, 0, datetime(2026, 8, 17, 8, 0)),
    ],
)
def test_next_run_at(now, weekday, hour, minute, expected) -> None:
    assert scheduler.next_run_at(now, weekday, hour, minute) == expected


def test_next_run_at_preserves_tzinfo() -> None:
    tz = ZoneInfo("Europe/London")
    now = datetime(2026, 8, 10, 7, 0, tzinfo=tz)
    target = scheduler.next_run_at(now, 0, 8, 0)
    assert target.tzinfo == tz


def test_read_email_schedule_reads_client_settings() -> None:
    factory = _session_factory()
    db = factory()
    db.add(
        Client(
            name="Stuart Mitchell",
            slug="stuart-mitchell",
            currency="GBP",
            report_email_weekday=2,
            report_email_hour=17,
            report_email_minute=30,
            report_email_tz="America/New_York",
        )
    )
    db.commit()
    db.close()

    assert scheduler.read_email_schedule(session_factory=factory) == (2, 17, 30, "America/New_York")


def test_read_email_schedule_defaults() -> None:
    factory = _session_factory()
    db = factory()
    db.add(Client(name="Stuart Mitchell", slug="stuart-mitchell", currency="GBP"))
    db.commit()
    db.close()

    assert scheduler.read_email_schedule(session_factory=factory) == (0, 8, 0, "Europe/London")


def test_send_due_weekly_reports_skips_when_auto_send_off(monkeypatch: pytest.MonkeyPatch) -> None:
    factory = _session_factory()
    db = factory()
    db.add(Client(name="Stuart Mitchell", slug="stuart-mitchell", currency="GBP", report_email="a@x.com", auto_email_enabled=False))
    db.commit()
    db.close()

    calls: list[object] = []
    monkeypatch.setattr(scheduler, "send_weekly_report_email", lambda *a, **k: calls.append(a) or ["a@x.com"])

    scheduler.send_due_weekly_reports(session_factory=factory)

    assert calls == []


def test_send_due_weekly_reports_skips_without_recipient(monkeypatch: pytest.MonkeyPatch) -> None:
    factory = _session_factory()
    db = factory()
    db.add(Client(name="Stuart Mitchell", slug="stuart-mitchell", currency="GBP", report_email="", auto_email_enabled=True))
    db.commit()
    db.close()

    calls: list[object] = []
    monkeypatch.setattr(scheduler, "send_weekly_report_email", lambda *a, **k: calls.append(a) or ["a@x.com"])

    scheduler.send_due_weekly_reports(session_factory=factory)

    assert calls == []


def test_send_due_weekly_reports_sends_once_then_skips(monkeypatch: pytest.MonkeyPatch) -> None:
    factory = _session_factory()
    db = factory()
    client = Client(name="Stuart Mitchell", slug="stuart-mitchell", currency="GBP", report_email="a@x.com", auto_email_enabled=True)
    db.add(client)
    db.flush()
    week = Week(client_id=client.id, period_end=date(2026, 8, 10), updated_until="10/8")
    db.add(week)
    db.commit()
    week_id = week.id
    db.close()

    calls: list[object] = []
    monkeypatch.setattr(scheduler, "send_weekly_report_email", lambda *a, **k: calls.append(a) or ["a@x.com"])
    monkeypatch.setattr(scheduler, "weekly_pdf_bytes", lambda *a, **k: b"%PDF-1.4")

    scheduler.send_due_weekly_reports(session_factory=factory)
    assert len(calls) == 1

    db = factory()
    stored = db.get(Week, week_id)
    assert stored.emailed_at is not None
    db.close()

    # A second wakeup must not re-send the same week.
    scheduler.send_due_weekly_reports(session_factory=factory)
    assert len(calls) == 1


def test_send_due_weekly_reports_logs_and_continues_on_send_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    factory = _session_factory()
    db = factory()
    client = Client(name="Stuart Mitchell", slug="stuart-mitchell", currency="GBP", report_email="a@x.com", auto_email_enabled=True)
    db.add(client)
    db.flush()
    week = Week(client_id=client.id, period_end=date(2026, 8, 10), updated_until="10/8")
    db.add(week)
    db.commit()
    week_id = week.id
    db.close()

    def _boom(*_a, **_k):
        from app.services.email import EmailSendError

        raise EmailSendError("smtp exploded")

    monkeypatch.setattr(scheduler, "send_weekly_report_email", _boom)
    monkeypatch.setattr(scheduler, "weekly_pdf_bytes", lambda *a, **k: b"%PDF-1.4")

    scheduler.send_due_weekly_reports(session_factory=factory)  # must not raise

    db = factory()
    stored = db.get(Week, week_id)
    assert stored.emailed_at is None  # left un-sent so a later wakeup can retry
    db.close()
