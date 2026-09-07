from __future__ import annotations

from datetime import date

import pytest

from app.models import Client, Week
from app.services import email as email_service


def _client(**overrides) -> Client:
    defaults = dict(
        id=1,
        name="Stuart Mitchell",
        slug="stuart-mitchell",
        currency="GBP",
        report_email="a@x.com, b@x.com",
        gmail_address="abby@gmail.com",
        gmail_app_password="app-password",
    )
    defaults.update(overrides)
    return Client(**defaults)


def _week() -> Week:
    return Week(id=1, client_id=1, period_end=date(2026, 8, 10), updated_until="10/8")


def test_send_weekly_report_email_requires_gmail_credentials() -> None:
    with pytest.raises(email_service.EmailNotConfigured):
        email_service.send_weekly_report_email(
            _client(gmail_address="", gmail_app_password=""), _week(), b"%PDF-1.4"
        )


def test_send_weekly_report_email_requires_a_recipient() -> None:
    client = _client(report_email="  ")
    with pytest.raises(email_service.EmailNotConfigured):
        email_service.send_weekly_report_email(client, _week(), b"%PDF-1.4")


class _FakeSMTP:
    instances: list["_FakeSMTP"] = []

    def __init__(self, *_args, **_kwargs) -> None:
        self.logged_in: tuple[str, str] | None = None
        self.sent = None
        _FakeSMTP.instances.append(self)

    def __enter__(self) -> "_FakeSMTP":
        return self

    def __exit__(self, *_exc) -> None:
        return None

    def login(self, address: str, password: str) -> None:
        self.logged_in = (address, password)

    def send_message(self, message) -> None:
        self.sent = message


def test_send_weekly_report_email_sends_via_gmail_smtp(monkeypatch: pytest.MonkeyPatch) -> None:
    _FakeSMTP.instances = []
    monkeypatch.setattr(email_service.smtplib, "SMTP_SSL", _FakeSMTP)

    client = _client(gmail_app_password="app password")  # spaces should be stripped
    recipients = email_service.send_weekly_report_email(client, _week(), b"%PDF-1.4")

    assert recipients == ["a@x.com", "b@x.com"]
    smtp = _FakeSMTP.instances[0]
    assert smtp.logged_in == ("abby@gmail.com", "apppassword")
    assert smtp.sent["To"] == "a@x.com, b@x.com"
    assert smtp.sent["From"] == "abby@gmail.com"
    assert "Stuart Mitchell" in smtp.sent["Subject"]
    attachments = list(smtp.sent.iter_attachments())
    assert len(attachments) == 1
    assert attachments[0].get_content_type() == "application/pdf"
    assert attachments[0].get_content() == b"%PDF-1.4"


def test_send_weekly_report_email_wraps_smtp_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    class _BoomSMTP(_FakeSMTP):
        def login(self, address: str, password: str) -> None:
            import smtplib

            raise smtplib.SMTPAuthenticationError(535, b"bad credentials")

    monkeypatch.setattr(email_service.smtplib, "SMTP_SSL", _BoomSMTP)

    with pytest.raises(email_service.EmailSendError):
        email_service.send_weekly_report_email(_client(), _week(), b"%PDF-1.4")


def test_send_weekly_report_email_honors_to_override(monkeypatch: pytest.MonkeyPatch) -> None:
    _FakeSMTP.instances = []
    monkeypatch.setattr(email_service.smtplib, "SMTP_SSL", _FakeSMTP)

    recipients = email_service.send_weekly_report_email(_client(), _week(), b"%PDF-1.4", to="override@x.com")

    assert recipients == ["override@x.com"]
