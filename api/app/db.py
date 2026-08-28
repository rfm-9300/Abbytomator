from __future__ import annotations

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
)


def migrate_schema(bind=engine) -> None:
    with bind.begin() as conn:
        existing = {row[0] for row in conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))}
        for table, column, ddl in _COLUMN_MIGRATIONS:
            if table not in existing:
                continue
            cols = {row[1] for row in conn.execute(text(f"PRAGMA table_info({table})"))}
            if column not in cols:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {ddl}"))


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
