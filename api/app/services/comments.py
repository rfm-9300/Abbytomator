from __future__ import annotations

import json
import re

import httpx
from fastapi import HTTPException

from app.config import openrouter_api_key, openrouter_model
from app.metrics import money_str, percent_str

SYSTEM_PROMPT = """You write Abby’s weekly Meta ads client letter for Punchline Promotions / Stuart Mitchell.

Voice: British English, account-manager to promoter. Calm, specific, no hype, no emojis, no exclamation marks.
The PDF already prints spend, clicks, CPC, CTR, tickets and CPP as bullets. Do not repeat those figures in the prose. Interpret them.

Good (city):
"Dundee remains the top-performing OTR location by volume and is now carrying the campaign as the sole active location. CPP has softened slightly as spend has been concentrated here, but it remains within an efficient range for the show approaching."

Good (campaign):
"Ticket sales have grown substantially, with CPC and CTR holding perfectly steady. CPP remains low despite the increase in volume, a strong sign the audience is continuing to convert efficiently at scale."

The examples above show tone only. Do not copy their sentences. Write about the campaigns in this snapshot.

Rules:
- Never invent numbers. Only use the snapshot. You may refer to direction (up, down, holding, concentrating) from tickets_by_week.
- Do not mention Meta, Punchline, Abby, AI, or that this was generated.
- note: 1-2 sentences on what is live vs paused this week. Empty only when the campaign has no cities.
- performance_summary: 2-3 short lines (newline separated, no bullets). Read efficiency, conversion vs reach, and whether CPP is healthy for this show. For city tours this is the overall tour read.
- next_steps: 2-3 concrete actions naming campaigns or cities (newline separated, no bullets). Not "monitor performance".
- city note: 1-2 sentences. Volume vs efficiency, CPP direction if prior-week tickets exist. Do not assign Live/Off to a city — that is the campaign's status.
- Off campaign: still write the full set. Past tense. note says it is off this week; performance_summary is a 2-line close-out (including when spend is £0.00 this week); next_steps is hold / leave off until the next on-sale. Never return empty strings for an Off campaign.

Return JSON only:
{"campaigns":[{"id":1,"note":"","performance_summary":"","next_steps":""}],"locations":[{"id":1,"note":""}]}
Use the ids from the snapshot. Include every campaign and location. Every campaign must have non-empty performance_summary and next_steps.
"""


def _fmt_money(value, currency: str) -> str | None:
    if value is None:
        return None
    return money_str(_dec(value), currency)


def _dec(value):
    from decimal import Decimal

    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _fmt_pct(value) -> str | None:
    if value is None:
        return None
    return percent_str(_dec(value))


def letter_snapshot(overview: dict, currency: str) -> dict:
    history = overview.get("history") or []
    labels = [col["label"] for col in history]
    campaigns = []
    for group in overview.get("groups") or []:
        for campaign in group.get("campaigns") or []:
            locations = []
            for loc in campaign.get("locations") or []:
                series = {}
                for label, tix in zip(labels, loc.get("tix_history") or []):
                    if tix is not None:
                        series[label] = tix
                locations.append(
                    {
                        "id": loc["id"],
                        "name": loc["name"],
                        "spend": _fmt_money(loc.get("amount_spent"), currency),
                        "clicks": loc.get("clicks") or 0,
                        "cpc": _fmt_money(loc.get("cpc"), currency),
                        "tickets": loc.get("tix_sold") or 0,
                        "cpp": _fmt_money(loc.get("cpp"), currency),
                        "tickets_by_week": series,
                    }
                )
            campaigns.append(
                {
                    "id": campaign["id"],
                    "name": campaign["name"],
                    "status": campaign.get("status") or "off",
                    "has_cities": bool(locations),
                    "spend": _fmt_money(campaign.get("amount_spent"), currency),
                    "clicks": campaign.get("clicks") or 0,
                    "cpc": _fmt_money(campaign.get("cpc"), currency),
                    "ctr": _fmt_pct(campaign.get("ctr")),
                    "tickets": campaign.get("tix_sold") or 0,
                    "cpp": _fmt_money(campaign.get("cpp"), currency),
                    "locations": locations,
                }
            )
    week = overview.get("week") or {}
    return {
        "client_date": week.get("label") or week.get("updated_until") or week.get("period_end"),
        "campaigns": campaigns,
    }


def generate_letter_comments(overview: dict, currency: str = "GBP") -> dict:
    key = openrouter_api_key()
    if not key:
        raise HTTPException(
            503,
            "Set OPENROUTER_API_KEY in .env to generate comments.",
        )
    snapshot = letter_snapshot(overview, currency)
    if not snapshot["campaigns"]:
        raise HTTPException(400, "Import a Meta report before generating comments.")

    payload = {
        "model": openrouter_model(),
        "temperature": 0.4,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": "Write this week's letter comments from the snapshot:\n"
                + json.dumps(snapshot, ensure_ascii=True),
            },
        ],
    }
    try:
        with httpx.Client(timeout=90.0) as client:
            response = client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "http://127.0.0.1:4321",
                    "X-Title": "Abbitomator",
                },
                json=payload,
            )
            response.raise_for_status()
            body = response.json()
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text[:400] if exc.response is not None else str(exc)
        raise HTTPException(502, f"OpenRouter error: {detail}") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(502, f"OpenRouter request failed: {exc}") from exc

    try:
        content = body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise HTTPException(502, "OpenRouter returned an empty reply.") from exc

    drafted = _parse_json(content)
    return _align_draft(snapshot, drafted)


def _parse_json(content: str) -> dict:
    text = (content or "").strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1)
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise HTTPException(502, "Model did not return JSON comments.") from exc
    if not isinstance(data, dict):
        raise HTTPException(502, "Model did not return JSON comments.")
    return data


def _zero_spend(campaign: dict) -> bool:
    spend = str(campaign.get("spend") or "")
    return spend in {"", "—", "£0.00", "$0.00", "€0.00"} and not campaign.get("clicks") and not campaign.get("tickets")


def _fallback_campaign(campaign: dict) -> dict:
    off = (campaign.get("status") or "") == "off"
    name = campaign.get("name") or "this campaign"
    if off:
        note = f"{name} is off this week."
        if _zero_spend(campaign):
            summary = "No spend this week.\nBanked totals stay on the letter as the close-out."
        else:
            summary = "The line is off. Totals on this row are the close-out for the week."
        next_steps = "Hold until the next on-sale is confirmed."
        if campaign.get("has_cities"):
            note = f"{name} is off this week. City totals below are the close-out."
        return {"note": note, "performance_summary": summary, "next_steps": next_steps}
    return {
        "note": "",
        "performance_summary": "",
        "next_steps": "",
    }


def _fallback_location(loc: dict) -> str:
    name = loc.get("name") or "This city"
    return f"{name} held its place on the tour this week."


def _align_draft(snapshot: dict, drafted: dict) -> dict:
    by_campaign = {int(row["id"]): row for row in drafted.get("campaigns") or [] if "id" in row}
    by_location = {int(row["id"]): row for row in drafted.get("locations") or [] if "id" in row}
    campaigns = []
    locations = []
    for campaign in snapshot["campaigns"]:
        row = by_campaign.get(int(campaign["id"]), {})
        fallback = _fallback_campaign(campaign)
        note = str(row.get("note") or "").strip()
        summary = str(row.get("performance_summary") or "").strip()
        next_steps = str(row.get("next_steps") or "").strip()
        if campaign.get("status") == "off":
            note = note or fallback["note"]
            summary = summary or fallback["performance_summary"]
            next_steps = next_steps or fallback["next_steps"]
        elif not summary:
            summary = fallback["performance_summary"]
        campaigns.append(
            {
                "id": campaign["id"],
                "note": note,
                "performance_summary": summary,
                "next_steps": next_steps or fallback["next_steps"],
            }
        )
        for loc in campaign["locations"]:
            loc_row = by_location.get(int(loc["id"]), {})
            loc_note = str(loc_row.get("note") or "").strip() or _fallback_location(loc)
            locations.append({"id": loc["id"], "note": loc_note})
    return {"campaigns": campaigns, "locations": locations}
