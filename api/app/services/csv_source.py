from __future__ import annotations

import csv
import io
import re
from datetime import date

from app.metrics import parse_int, parse_money, parse_percent
from app.services.insights import CampaignInsight

STATUS_LIVE = {"live", "active", "on", "enabled"}
STATUS_OFF = {"off", "paused", "disabled", "inactive", "archived"}

NAME_KEYS = ("campaign", "campaign name", "campaign_name", "name")
STATUS_KEYS = ("campaign status", "status", "delivery", "campaign_status")
SPEND_KEYS = ("amount spent", "amount_spent", "spend", "amount spent ")
CLICKS_KEYS = ("clicks", "link clicks", "unique clicks")
IMPR_KEYS = ("impressions", "impr.")
CTR_KEYS = ("ctr", "ctr (all)")
TIX_KEYS = ("tix sold", "tickets sold", "tix", "tickets")
CITY_KEYS = ("city", "region", "location", "dma", "ad set name", "adset_name")
PLATFORM_KEYS = ("platform", "column 1", "publisher platform")

UPDATED_RE = re.compile(r"updated until(?: the)?\s+(.+)", re.I)
IGNORED_NAME_RE = re.compile(
    r"^(merge\b|total\b|totals\b|results?\b|grand total\b)|merge venue",
    re.I,
)


def _norm(header: str) -> str:
    return re.sub(r"\s+", " ", header.strip().lower())


def _pick(row: dict[str, str], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        if key in row and row[key].strip():
            return row[key].strip()
    return None


def is_ignored_campaign(name: str | None) -> bool:
    token = (name or "").strip()
    if not token:
        return True
    if token.lower() in {"campaign", "total", "totals", "results", "result"}:
        return True
    return bool(IGNORED_NAME_RE.search(token))


def normalize_status(value: str | None) -> str:
    if not value:
        return "off"
    token = value.strip().lower()
    if token in STATUS_LIVE:
        return "live"
    if token in STATUS_OFF:
        return "off"
    if "live" in token or "active" in token:
        return "live"
    return "off"


def _is_meta_header_row(values: list[str]) -> bool:
    joined = " ".join(_norm(v) for v in values if v)
    return "campaign" in joined and ("spend" in joined or "amount" in joined or "status" in joined)


class CsvInsightsSource:
    def fetch(
        self,
        raw: bytes | None = None,
        *,
        since: date | None = None,
        until: date | None = None,
    ) -> tuple[list[CampaignInsight], str | None]:
        if raw is None:
            raise ValueError("CSV source requires file bytes")
        return parse_csv(raw)


def parse_csv(raw: bytes) -> tuple[list[CampaignInsight], str | None]:
    text = _decode(raw)
    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        return [], None

    header_index = 0
    updated_until: str | None = None
    for index, row in enumerate(rows):
        blob = " ".join(cell.strip() for cell in row if cell and cell.strip())
        match = UPDATED_RE.search(blob)
        if match:
            updated_until = match.group(1).strip().rstrip(",")
        if _is_meta_header_row(row):
            header_index = index

    headers = [_norm(cell) for cell in rows[header_index]]
    insights: list[CampaignInsight] = []
    for raw_row in rows[header_index + 1 :]:
        if not any(cell.strip() for cell in raw_row):
            continue
        mapped = {
            headers[i]: raw_row[i].strip() if i < len(raw_row) else ""
            for i in range(len(headers))
            if headers[i]
        }
        blob = " ".join(mapped.values())
        if UPDATED_RE.search(blob):
            continue
        name = _pick(mapped, NAME_KEYS)
        if not name or is_ignored_campaign(name):
            continue

        platform = (_pick(mapped, PLATFORM_KEYS) or "META").strip().upper() or "META"
        if platform in {"COLUMN 1"}:
            platform = "META"

        city = _pick(mapped, CITY_KEYS)
        tix_raw = _pick(mapped, TIX_KEYS)
        impressions_raw = _pick(mapped, IMPR_KEYS)
        insights.append(
            CampaignInsight(
                name=name.strip(),
                platform=platform,
                status=normalize_status(_pick(mapped, STATUS_KEYS)),
                amount_spent=parse_money(_pick(mapped, SPEND_KEYS) or "0"),
                clicks=parse_int(_pick(mapped, CLICKS_KEYS) or "0"),
                impressions=parse_int(impressions_raw) if impressions_raw else None,
                ctr=parse_percent(_pick(mapped, CTR_KEYS)) if _pick(mapped, CTR_KEYS) else None,
                city=city.strip() if city else None,
                tix_sold=parse_int(tix_raw) if tix_raw else None,
            )
        )
    return insights, updated_until


def _decode(raw: bytes) -> str:
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        return raw.decode("utf-16")
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("latin-1")
