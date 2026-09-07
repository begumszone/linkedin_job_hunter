"""Configuration loading and validation."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

MAX_KEYWORDS = 10
VALID_MODES = {"any", "all"}


class ConfigError(Exception):
    """Raised when config.yaml is missing something or asks for the impossible."""


@dataclass
class Search:
    name: str
    keywords: list[str]
    location: str = ""
    match_mode: str = "any"
    exclude: list[str] = field(default_factory=list)
    remote_only: bool = False
    recipients: list[str] = field(default_factory=list)
    max_results: int = 25
    enabled: bool = True


@dataclass
class EmailConfig:
    enabled: bool = True
    recipients: list[str] = field(default_factory=list)
    subject_prefix: str = "[İlan]"
    host: str = ""
    port: int = 587
    username: str = ""
    password: str = ""
    sender: str = ""
    use_ssl: bool = False


@dataclass
class NtfyConfig:
    enabled: bool = False
    server: str = "https://ntfy.sh"
    topic: str = ""
    priority: str = "default"


@dataclass
class Settings:
    hours: int = 24
    request_delay_seconds: float = 3.0
    state_file: str = "state/seen_jobs.json"
    forget_after_days: int = 30
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )


@dataclass
class Config:
    searches: list[Search]
    email: EmailConfig
    ntfy: NtfyConfig
    settings: Settings

    def active_searches(self) -> list[Search]:
        return [search for search in self.searches if search.enabled]

    def recipients_for(self, search: Search) -> list[str]:
        """Who gets this search's results.

        A search with its own recipients goes only to them — so one person's
        alerts never land in another's inbox. Searches without their own list
        fall back to the global recipients.
        """
        return search.recipients or self.email.recipients


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return [str(item) for item in value]


def _load_search(raw: dict[str, Any], index: int) -> Search:
    name = str(raw.get("name") or f"Arama {index + 1}")
    keywords = [kw.strip() for kw in _as_list(raw.get("keywords")) if kw.strip()]
    if not keywords:
        raise ConfigError(f"'{name}' aramasında en az bir anahtar kelime olmalı.")
    if len(keywords) > MAX_KEYWORDS:
        raise ConfigError(
            f"'{name}' aramasında {len(keywords)} anahtar kelime var; "
            f"en fazla {MAX_KEYWORDS} olabilir."
        )

    mode = str(raw.get("match_mode", "any")).lower()
    if mode not in VALID_MODES:
        raise ConfigError(
            f"'{name}' aramasının match_mode değeri {sorted(VALID_MODES)} "
            f"içinden biri olmalı, '{mode}' değil."
        )

    # A search can name a secret holding its recipients, so a public repo
    # never has to carry anyone's address.
    recipients = _as_list(raw.get("recipients"))
    secret_name = str(raw.get("recipients_secret") or "").strip()
    if secret_name:
        for address in _env_list(secret_name):
            if address not in recipients:
                recipients.append(address)

    return Search(
        name=name,
        keywords=keywords,
        location=str(raw.get("location") or "").strip(),
        match_mode=mode,
        exclude=[term.strip() for term in _as_list(raw.get("exclude")) if term.strip()],
        remote_only=bool(raw.get("remote_only", False)),
        recipients=recipients,
        max_results=int(raw.get("max_results", 25)),
        enabled=bool(raw.get("enabled", True)),
    )


def _env(name: str, fallback: str = "") -> str:
    """Read an env var, treating an empty value as absent.

    A workflow passes every declared secret through, so an unset secret still
    arrives as an empty string; without this the config-file default would be
    overwritten by "".
    """
    return os.environ.get(name, "").strip() or fallback


def _env_list(name: str) -> list[str]:
    """Read a comma-separated env var, e.g. EMAIL_RECIPIENTS."""
    raw = os.environ.get(name, "")
    return [item.strip() for item in raw.split(",") if item.strip()]


def load_config(path: str | Path) -> Config:
    path = Path(path)
    if not path.exists():
        raise ConfigError(f"Config dosyası bulunamadı: {path}")

    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    raw_searches = raw.get("searches") or []
    if not raw_searches:
        raise ConfigError("config.yaml içinde en az bir 'searches' girdisi olmalı.")
    searches = [_load_search(item or {}, i) for i, item in enumerate(raw_searches)]

    raw_notify = raw.get("notifications") or {}
    raw_email = raw_notify.get("email") or {}
    # Credentials come from the environment (GitHub Actions secrets), never
    # from the committed config file.
    # Recipients may live in EMAIL_RECIPIENTS so a public repo need not carry
    # anyone's address; both sources are merged, config order first.
    recipients = _as_list(raw_email.get("recipients"))
    for address in _env_list("EMAIL_RECIPIENTS"):
        if address not in recipients:
            recipients.append(address)

    email = EmailConfig(
        enabled=bool(raw_email.get("enabled", True)),
        recipients=recipients,
        subject_prefix=str(raw_email.get("subject_prefix", "[İlan]")),
        host=_env("SMTP_HOST", str(raw_email.get("host", "smtp.gmail.com"))),
        port=int(_env("SMTP_PORT", str(raw_email.get("port", 587)))),
        username=_env("SMTP_USERNAME"),
        password=_env("SMTP_PASSWORD"),
        sender=_env("SMTP_FROM") or _env("SMTP_USERNAME"),
        use_ssl=bool(raw_email.get("use_ssl", False)),
    )

    raw_ntfy = raw_notify.get("ntfy") or {}
    ntfy = NtfyConfig(
        enabled=bool(raw_ntfy.get("enabled", False)),
        server=str(raw_ntfy.get("server", "https://ntfy.sh")).rstrip("/"),
        topic=_env("NTFY_TOPIC", str(raw_ntfy.get("topic", ""))),
        priority=str(raw_ntfy.get("priority", "default")),
    )

    raw_settings = raw.get("settings") or {}
    settings = Settings(
        hours=int(raw_settings.get("hours", 24)),
        request_delay_seconds=float(raw_settings.get("request_delay_seconds", 3.0)),
        state_file=str(raw_settings.get("state_file", "state/seen_jobs.json")),
        forget_after_days=int(raw_settings.get("forget_after_days", 30)),
    )

    config = Config(searches=searches, email=email, ntfy=ntfy, settings=settings)

    if email.enabled:
        orphans = [s.name for s in config.active_searches() if not config.recipients_for(s)]
        if orphans:
            raise ConfigError(
                "Şu aramaların alıcısı yok: "
                + ", ".join(orphans)
                + ". Aramaya 'recipients' (ya da 'recipients_secret') ekle, "
                "veya notifications.email.recipients altına genel bir adres yaz."
            )
    if ntfy.enabled and not ntfy.topic:
        raise ConfigError("ntfy açık ama 'topic' boş.")

    return config
