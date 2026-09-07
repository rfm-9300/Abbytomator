from __future__ import annotations

import smtplib
from email.message import EmailMessage

from app.config import ACCOUNT_MANAGER
from app.models import Client, Week
from app.services.queries import week_label

GMAIL_SMTP_HOST = "smtp.gmail.com"
GMAIL_SMTP_PORT = 465


class EmailNotConfigured(RuntimeError):
    """Gmail credentials or a recipient are missing — a 400, not a delivery failure."""


class EmailSendError(RuntimeError):
    """SMTP rejected the send — a 502, the caller can retry."""


def _recipients(raw: str) -> list[str]:
    return [addr.strip() for addr in raw.split(",") if addr.strip()]


def build_weekly_report_email(client: Client, week: Week, pdf_bytes: bytes, sender: str, recipients: list[str]) -> EmailMessage:
    label = week_label(week)
    message = EmailMessage()
    message["Subject"] = f"{client.name} — Weekly Meta Ads Report ({label})"
    message["From"] = sender
    message["To"] = ", ".join(recipients)
    message.set_content(
        f"Hi,\n\nAttached is the {client.name} weekly Meta ads report, updated to {label}.\n\nBest,\n{ACCOUNT_MANAGER}"
    )
    filename = f"weekly-{client.slug}-{week.period_end.isoformat()}.pdf"
    message.add_attachment(pdf_bytes, maintype="application", subtype="pdf", filename=filename)
    return message


def send_weekly_report_email(client: Client, week: Week, pdf_bytes: bytes, *, to: str | None = None) -> list[str]:
    """Emails the weekly PDF via Gmail SMTP. `to` overrides the client's saved
    `report_email` (comma-separated) for a one-off recipient; omit to use it."""
    address = (client.gmail_address or "").strip()
    app_password = (client.gmail_app_password or "").strip().replace(" ", "")
    if not address or not app_password:
        raise EmailNotConfigured(
            "Gmail is not configured. Add a Gmail address and App Password under Settings."
        )
    recipients = _recipients(client.report_email if to is None else to)
    if not recipients:
        raise EmailNotConfigured("No recipient email set. Add one under Settings.")

    message = build_weekly_report_email(client, week, pdf_bytes, address, recipients)
    try:
        with smtplib.SMTP_SSL(GMAIL_SMTP_HOST, GMAIL_SMTP_PORT, timeout=20) as smtp:
            smtp.login(address, app_password)
            smtp.send_message(message)
    except (smtplib.SMTPException, OSError) as exc:
        raise EmailSendError(str(exc)) from exc

    return recipients
