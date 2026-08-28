from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Protocol


@dataclass(frozen=True)
class CampaignInsight:
    name: str
    platform: str
    status: str
    amount_spent: Decimal
    clicks: int
    impressions: int | None = None
    ctr: Decimal | None = None
    city: str | None = None
    tix_sold: int | None = None


class InsightsSource(Protocol):
    """Campaign performance for a date range. CSV now; Meta API later."""

    def fetch(
        self,
        raw: bytes | None = None,
        *,
        since: date | None = None,
        until: date | None = None,
    ) -> tuple[list[CampaignInsight], str | None]:
        """Return insights and an optional 'updated until' label."""


class MetaApiInsightsSource:
    def fetch(
        self,
        raw: bytes | None = None,
        *,
        since: date | None = None,
        until: date | None = None,
    ) -> tuple[list[CampaignInsight], str | None]:
        raise NotImplementedError(
            "Meta Marketing API is not configured. Upload a CSV export instead."
        )
