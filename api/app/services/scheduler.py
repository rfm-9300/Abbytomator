"""In-process weekly-email scheduler — stdlib only, no extra dependency, no separate
cron process. `main.py`'s lifespan runs `run_scheduler` as a background asyncio task
for the life of the app; it wakes once a week and calls `send_due_weekly_reports`.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.config import CLIENT_SLUG
from app.db import SessionLocal
from app.models import Week
from app.services.email import EmailNotConfigured, EmailSendError, send_weekly_report_email
from app.services.pdf import weekly_pdf_bytes
from app.services.queries import require_client

logger = logging.getLogger("abbitomator.scheduler")


def next_run_at(now: datetime, weekday: int, hour: int, minute: int) -> datetime:
    """Next datetime at or after `now` (same tzinfo) matching weekday/hour/minute."""
    candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    candidate += timedelta(days=(weekday - now.weekday()) % 7)
    if candidate <= now:
        candidate += timedelta(days=7)
    return candidate


def read_email_schedule(session_factory=SessionLocal) -> tuple[int, int, int, str]:
    """The client's auto-send slot (weekday/hour/minute/tz), from Settings — not .env."""
    db = session_factory()
    try:
        client = require_client(db, CLIENT_SLUG)
        return (
            client.report_email_weekday,
            client.report_email_hour,
            client.report_email_minute,
            client.report_email_tz or "Europe/London",
        )
    finally:
        db.close()


def send_due_weekly_reports(session_factory=SessionLocal) -> None:
    """Emails the latest week's PDF if auto-send is on, a recipient is configured, and
    that week hasn't been emailed yet. `Week.emailed_at` makes this idempotent — safe to
    call on every wakeup (or a restart) without risking a duplicate send.
    `session_factory` is overridable so tests can point this at an in-memory engine."""
    db = session_factory()
    try:
        client = require_client(db, CLIENT_SLUG)
        if not client.auto_email_enabled or not client.report_email.strip():
            return
        week = db.scalar(
            select(Week).where(Week.client_id == client.id).order_by(Week.period_end.desc())
        )
        if week is None or week.emailed_at is not None:
            return
        try:
            pdf = weekly_pdf_bytes(db, week, client)
            send_weekly_report_email(client, week, pdf)
        except (RuntimeError, EmailNotConfigured, EmailSendError):
            logger.exception("Automatic weekly report email failed for week %s", week.id)
            return
        week.emailed_at = datetime.utcnow()
        db.commit()
        logger.info("Automatic weekly report emailed for week %s", week.id)
    finally:
        db.close()


_ERROR_RETRY_SECONDS = 3600  # back off an hour on a config/scheduling bug rather than spin


async def run_scheduler(stop_event: asyncio.Event) -> None:
    """Sleeps until the next configured slot, runs the send, repeats — until `stop_event`
    is set (app shutdown). Re-reads the schedule from the client row each loop so a
    change saved in Settings takes effect on the next wakeup, no restart needed.

    Any failure inside `send_due_weekly_reports` itself is already caught and logged
    there (so one bad send doesn't stop future ones); the broad except here is a second
    net around the scheduling math (e.g. a bad timezone) so a misconfiguration can't
    silently kill this background task for the rest of the process's life."""
    while not stop_event.is_set():
        try:
            weekday, hour, minute, tz_name = await asyncio.to_thread(read_email_schedule)
            tz = ZoneInfo(tz_name)
            now = datetime.now(tz)
            target = next_run_at(now, weekday, hour, minute)
            seconds = (target - now).total_seconds()
        except Exception:
            logger.exception("Weekly email scheduler misconfigured; retrying in an hour")
            seconds = _ERROR_RETRY_SECONDS
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=seconds)
            return  # stop_event was set
        except asyncio.TimeoutError:
            pass
        try:
            await asyncio.to_thread(send_due_weekly_reports)
        except Exception:
            logger.exception("Weekly email scheduler tick failed unexpectedly")
