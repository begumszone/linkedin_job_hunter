"""Send the new-postings digest over SMTP."""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage
from email.utils import formataddr

from ..config import EmailConfig
from ..linkedin import Job
from . import render

log = logging.getLogger(__name__)


class EmailError(Exception):
    pass


def _validate(config: EmailConfig, recipients: list[str]) -> None:
    missing = [
        name
        for name, value in (
            ("SMTP_HOST", config.host),
            ("SMTP_USERNAME", config.username),
            ("SMTP_PASSWORD", config.password),
        )
        if not value
    ]
    if missing:
        raise EmailError(
            "E-posta gönderilemedi, eksik ayar: "
            + ", ".join(missing)
            + ". Bunları GitHub Actions secrets olarak (ya da lokalde .env ile) tanımla."
        )
    if not recipients:
        raise EmailError("E-posta gönderilemedi: alıcı listesi boş.")


def send_email(config: EmailConfig, recipients: list[str], jobs: list[Job]) -> None:
    if not jobs:
        return
    _validate(config, recipients)

    message = EmailMessage()
    message["Subject"] = render.subject(jobs, config.subject_prefix)
    message["From"] = formataddr(("LinkedIn Job Hunter", config.sender or config.username))
    message["To"] = ", ".join(recipients)
    message.set_content(render.as_text(jobs))
    message.add_alternative(render.as_html(jobs), subtype="html")

    try:
        if config.use_ssl or config.port == 465:
            server = smtplib.SMTP_SSL(config.host, config.port, timeout=30)
        else:
            server = smtplib.SMTP(config.host, config.port, timeout=30)
        with server:
            if not (config.use_ssl or config.port == 465):
                server.starttls()
            server.login(config.username, config.password)
            server.send_message(message)
    except smtplib.SMTPAuthenticationError as exc:
        raise EmailError(
            "SMTP girişi reddedildi. Gmail kullanıyorsan normal şifreni değil, "
            "iki adımlı doğrulama açıkken oluşturulan 'uygulama şifresi'ni kullan."
        ) from exc
    except (smtplib.SMTPException, OSError) as exc:
        raise EmailError(f"SMTP hatası: {exc}") from exc

    log.info("%d ilan %s adresine e-postalandı", len(jobs), ", ".join(recipients))
