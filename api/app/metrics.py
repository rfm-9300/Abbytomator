from __future__ import annotations

from decimal import Decimal, InvalidOperation


def parse_money(value: object) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    text = str(value).strip()
    if not text or text in {"-", "—"}:
        return Decimal("0")
    text = text.replace("£", "").replace("$", "").replace("€", "").replace(",", "").replace(" ", "")
    if text.endswith("%"):
        text = text[:-1]
    try:
        return Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(f"Cannot parse money: {value!r}") from exc


def parse_percent(value: object) -> Decimal | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text in {"-", "—"}:
        return None
    text = text.replace("%", "").replace(",", "").strip()
    try:
        number = Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(f"Cannot parse percent: {value!r}") from exc
    if number > 1:
        number = number / Decimal("100")
    return number


def parse_int(value: object) -> int:
    if value is None or str(value).strip() in {"", "-", "—"}:
        return 0
    text = str(value).strip().replace(",", "").replace(" ", "")
    return int(Decimal(text))


def cpc(amount_spent: Decimal, clicks: int) -> Decimal | None:
    if clicks <= 0:
        return None
    return (amount_spent / Decimal(clicks)).quantize(Decimal("0.01"))


def cpp(amount_spent: Decimal, tix_sold: int) -> Decimal | None:
    if tix_sold <= 0:
        return None
    return (amount_spent / Decimal(tix_sold)).quantize(Decimal("0.01"))


def ctr(clicks: int, impressions: int | None, imported: Decimal | None = None) -> Decimal | None:
    if imported is not None:
        return imported
    if not impressions or impressions <= 0:
        return None
    return (Decimal(clicks) / Decimal(impressions)).quantize(Decimal("0.0001"))


def money_str(amount: Decimal | None, currency: str = "GBP") -> str:
    if amount is None:
        return "—"
    symbol = {"GBP": "£", "USD": "$", "EUR": "€"}.get(currency, "")
    quantized = amount.quantize(Decimal("0.01"))
    return f"{symbol}{quantized:,.2f}"


def percent_str(value: Decimal | None) -> str:
    if value is None:
        return "—"
    return f"{(value * Decimal('100')).quantize(Decimal('0.01'))}%"
