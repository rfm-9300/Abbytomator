from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(80), unique=True)
    currency: Mapped[str] = mapped_column(String(8), default="GBP")
    date_format: Mapped[str] = mapped_column(String(32), default="d/m/Y")

    campaigns: Mapped[list[Campaign]] = relationship(back_populates="client")
    weeks: Mapped[list[Week]] = relationship(back_populates="client")


class Campaign(Base):
    __tablename__ = "campaigns"
    __table_args__ = (UniqueConstraint("client_id", "name", name="uq_campaign_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), index=True)
    name: Mapped[str] = mapped_column(String(300))
    platform: Mapped[str] = mapped_column(String(32), default="META")
    status: Mapped[str] = mapped_column(String(16), default="off")
    event_label: Mapped[str] = mapped_column(String(300), default="")
    external_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_imported_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    client: Mapped[Client] = relationship(back_populates="campaigns")
    locations: Mapped[list[Location]] = relationship(back_populates="campaign", cascade="all, delete-orphan")
    metrics: Mapped[list[WeekCampaignMetric]] = relationship(back_populates="campaign")


class Location(Base):
    __tablename__ = "locations"
    __table_args__ = (UniqueConstraint("campaign_id", "name", name="uq_location_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(16), default="live")

    campaign: Mapped[Campaign] = relationship(back_populates="locations")
    metrics: Mapped[list[WeekLocationMetric]] = relationship(back_populates="location")


class Week(Base):
    __tablename__ = "weeks"
    __table_args__ = (UniqueConstraint("client_id", "period_end", name="uq_week"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), index=True)
    period_end: Mapped[date] = mapped_column(Date)
    updated_until: Mapped[str | None] = mapped_column(String(80), nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    client: Mapped[Client] = relationship(back_populates="weeks")
    campaign_metrics: Mapped[list[WeekCampaignMetric]] = relationship(
        back_populates="week", cascade="all, delete-orphan"
    )
    location_metrics: Mapped[list[WeekLocationMetric]] = relationship(
        back_populates="week", cascade="all, delete-orphan"
    )


class WeekCampaignMetric(Base):
    __tablename__ = "week_campaign_metrics"
    __table_args__ = (UniqueConstraint("week_id", "campaign_id", name="uq_week_campaign"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    week_id: Mapped[int] = mapped_column(ForeignKey("weeks.id"), index=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id"), index=True)
    amount_spent: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    clicks: Mapped[int] = mapped_column(default=0)
    impressions: Mapped[int | None] = mapped_column(nullable=True)
    ctr_imported: Mapped[Decimal | None] = mapped_column(Numeric(8, 6), nullable=True)
    tix_sold: Mapped[int] = mapped_column(default=0)
    note: Mapped[str] = mapped_column(Text, default="")
    performance_summary: Mapped[str] = mapped_column(Text, default="")
    next_steps: Mapped[str] = mapped_column(Text, default="")

    week: Mapped[Week] = relationship(back_populates="campaign_metrics")
    campaign: Mapped[Campaign] = relationship(back_populates="metrics")


class WeekLocationMetric(Base):
    __tablename__ = "week_location_metrics"
    __table_args__ = (UniqueConstraint("week_id", "location_id", name="uq_week_location"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    week_id: Mapped[int] = mapped_column(ForeignKey("weeks.id"), index=True)
    location_id: Mapped[int] = mapped_column(ForeignKey("locations.id"), index=True)
    amount_spent: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    clicks: Mapped[int] = mapped_column(default=0)
    tix_sold: Mapped[int] = mapped_column(default=0)
    note: Mapped[str] = mapped_column(Text, default="")

    week: Mapped[Week] = relationship(back_populates="location_metrics")
    location: Mapped[Location] = relationship(back_populates="metrics")
