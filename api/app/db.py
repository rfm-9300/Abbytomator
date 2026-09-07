from __future__ import annotations

import os
from collections.abc import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from app.config import DB_PATH, ensure_dirs
from app.models import Base

ensure_dirs()

engine = create_engine(
    f"sqlite:///{DB_PATH}",
    connect_args={"check_same_thread": False},
    future=True,
)


@event.listens_for(engine, "connect")
def _fk_on(dbapi_connection, _connection_record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


_COLUMN_MIGRATIONS = (
    ("week_campaign_metrics", "note", "note TEXT DEFAULT ''"),
    ("week_campaign_metrics", "performance_summary", "performance_summary TEXT DEFAULT ''"),
    ("week_campaign_metrics", "next_steps", "next_steps TEXT DEFAULT ''"),
    ("week_location_metrics", "note", "note TEXT DEFAULT ''"),
    ("week_location_metrics", "clicks", "clicks INTEGER DEFAULT 0"),
    ("locations", "status", "status VARCHAR(16) DEFAULT 'live'"),
    ("clients", "report_email", "report_email TEXT DEFAULT ''"),
    ("clients", "auto_email_enabled", "auto_email_enabled BOOLEAN DEFAULT 0"),
    ("weeks", "emailed_at", "emailed_at DATETIME"),
    ("clients", "pdf_template", "pdf_template VARCHAR(16) DEFAULT 'modern'"),
    ("clients", "gmail_address", "gmail_address TEXT DEFAULT ''"),
    ("clients", "gmail_app_password", "gmail_app_password TEXT DEFAULT ''"),
    ("clients", "report_email_weekday", "report_email_weekday INTEGER DEFAULT 0"),
    ("clients", "report_email_hour", "report_email_hour INTEGER DEFAULT 8"),
    ("clients", "report_email_minute", "report_email_minute INTEGER DEFAULT 0"),
    ("clients", "report_email_tz", "report_email_tz TEXT DEFAULT 'Europe/London'"),
    ("clients", "openrouter_api_key", "openrouter_api_key TEXT DEFAULT ''"),
    ("clients", "openrouter_model", "openrouter_model TEXT DEFAULT 'openai/gpt-4o'"),
)

# These columns replace an old .env var. The first time each one is added to an
# existing clients table, seed it from that var (if set) so upgrading doesn't
# silently break email sending or AI comment drafting for anyone who already had
# it configured — after this, the var is dead and Settings is the only source.
_ENV_BACKFILL = {
    "gmail_address": "GMAIL_ADDRESS",
    "gmail_app_password": "GMAIL_APP_PASSWORD",
    "report_email_weekday": "REPORT_EMAIL_WEEKDAY",
    "report_email_hour": "REPORT_EMAIL_HOUR",
    "report_email_minute": "REPORT_EMAIL_MINUTE",
    "report_email_tz": "REPORT_EMAIL_TZ",
    "openrouter_api_key": "OPENROUTER_API_KEY",
    "openrouter_model": "OPENROUTER_MODEL",
}


def migrate_schema(bind=engine) -> None:
    with bind.begin() as conn:
        existing = {row[0] for row in conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))}
        for table, column, ddl in _COLUMN_MIGRATIONS:
            if table not in existing:
                continue
            cols = {row[1] for row in conn.execute(text(f"PRAGMA table_info({table})"))}
            if column in cols:
                continue
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {ddl}"))
            env_name = _ENV_BACKFILL.get(column)
            if not env_name:
                continue
            value = os.environ.get(env_name, "").strip()
            if column == "gmail_app_password":
                value = value.replace(" ", "")
            if value:
                conn.execute(text(f"UPDATE {table} SET {column} = :value"), {"value": value})


def init_db() -> None:
    ensure_dirs()
    Base.metadata.create_all(bind=engine)
    migrate_schema(engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
