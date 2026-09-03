from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.config import TEMPLATE_DIR  # noqa: F401 — sets Homebrew dylib path before WeasyPrint
from app.metrics import money_str
from app.services.queries import monthly_rollup, overview_for_week

try:
    from weasyprint import HTML
except Exception:  # pragma: no cover - optional system libs
    HTML = None


def _env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html"]),
    )


def _require_weasyprint() -> None:
    if HTML is None:
        raise RuntimeError(
            "WeasyPrint is not available. On macOS run: brew install pango libffi"
        )


def _to_dec(value):
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _whole(value) -> str:
    if value is None:
        return "–"
    return f"{int(value):,}"


def _bullets(text: str | None) -> list[str]:
    if not text:
        return []
    lines = []
    for raw in text.splitlines():
        line = raw.strip().lstrip("\u2022\u25cf*- ").strip()
        if line:
            lines.append(line)
    return lines


def _percent(value) -> str:
    if value is None:
        return "–"
    dec = _to_dec(value)
    pct = (dec * Decimal("100")).quantize(Decimal("0.01"))
    text = format(pct, "f").rstrip("0").rstrip(".")
    return f"{text}%"


def _status_phrase(status: str) -> str:
    return "Live" if status == "live" else "Off"


def _template_helpers(currency: str) -> dict:
    return {
        "money": lambda value: money_str(_to_dec(value), currency),
        "percent": _percent,
        "money_or_dash": lambda value: money_str(_to_dec(value), currency) if value is not None else "–",
        "whole": _whole,
        "bullets": _bullets,
        "status_phrase": _status_phrase,
    }


def _first_line(text: str | None) -> str | None:
    return next(iter(_bullets(text)), None)


def _rank_locations(locations: list[dict]) -> tuple[dict[int, str], int | None]:
    """Assign each location a short status tag for the "Key takeaways" cards, and pick the
    single best-performing (lowest CPP) location to highlight in the city table. This is a
    ranking of the CPP figure already shown in the table, not an editorial judgment call —
    with fewer than two comparable live locations there's nothing to rank, so everyone reads
    as "Stable support" instead of guessing at a best/worst.
    """
    live = [loc for loc in locations if loc["status"] == "live" and loc.get("cpp") is not None]
    best_id = worst_id = None
    if len(live) > 1:
        best_id = min(live, key=lambda loc: loc["cpp"])["id"]
        worst_id = max(live, key=lambda loc: loc["cpp"])["id"]
    tags: dict[int, str] = {}
    for loc in locations:
        if loc["status"] != "live":
            tags[loc["id"]] = "Off"
        elif loc["id"] == best_id:
            tags[loc["id"]] = "Best performer"
        elif loc["id"] == worst_id:
            tags[loc["id"]] = "Needs optimisation"
        else:
            tags[loc["id"]] = "Stable support"
    return tags, best_id


def _augment_overview_for_pdf(overview: dict) -> dict:
    """Adds the fields the card-based weekly template needs on top of what
    queries.overview_for_week returns: a flat campaign list for the Overview page, one-line
    summaries pulled from the existing note/performance_summary text, and the per-city
    ranking used by the city table and "Key takeaways" cards."""
    all_campaigns: list[dict] = []
    for group in overview["groups"]:
        for campaign in group["campaigns"]:
            all_campaigns.append(campaign)
            campaign["card_summary"] = _first_line(campaign["performance_summary"])
            campaign["one_liner"] = _first_line(campaign["note"])
            if campaign["locations"]:
                tags, best_id = _rank_locations(campaign["locations"])
                for loc in campaign["locations"]:
                    loc["takeaway_tag"] = tags[loc["id"]]
                campaign["best_location_id"] = best_id
            else:
                campaign["best_location_id"] = None
    overview["all_campaigns"] = all_campaigns
    return overview


def render_weekly_html(overview: dict, client_name: str, currency: str) -> str:
    template = _env().get_template("weekly.html")
    overview = _augment_overview_for_pdf(overview)
    return template.render(
        overview=overview,
        client_name=client_name,
        currency=currency,
        **_template_helpers(currency),
    )


def render_monthly_html(rollup: dict, client_name: str, currency: str) -> str:
    template = _env().get_template("monthly.html")
    month_name = _month_name(rollup["year"], rollup["month"])
    return template.render(
        rollup=rollup,
        client_name=client_name,
        currency=currency,
        month_name=month_name,
        **_template_helpers(currency),
    )


def weekly_pdf_bytes(db, week, client) -> bytes:
    _require_weasyprint()
    overview = overview_for_week(db, week)
    html = render_weekly_html(overview, client.name, client.currency)
    return HTML(string=html, base_url=str(TEMPLATE_DIR)).write_pdf()


def monthly_pdf_bytes(db, client, year: int, month: int) -> bytes:
    _require_weasyprint()
    rollup = monthly_rollup(db, client, year, month)
    html = render_monthly_html(rollup, client.name, client.currency)
    return HTML(string=html, base_url=str(TEMPLATE_DIR)).write_pdf()


def write_pdf(path: Path, data: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def _month_name(year: int, month: int) -> str:
    import calendar

    return f"{calendar.month_name[month]} {year}"
