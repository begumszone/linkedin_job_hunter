"""Optional push channel via ntfy.

Off by default: on the public ntfy.sh server a topic is unauthenticated, so
anyone who knows the topic name can read it. Pick an unguessable topic (or
self-host) before turning this on.
"""

from __future__ import annotations

import logging

import requests

from ..config import NtfyConfig
from ..linkedin import Job
from . import render

log = logging.getLogger(__name__)


def send_ntfy(config: NtfyConfig, jobs: list[Job]) -> None:
    if not jobs or not config.enabled:
        return

    url = f"{config.server}/{config.topic}"
    headers = {
        "Title": render.subject(jobs, "").strip().encode("utf-8"),
        "Priority": config.priority,
        "Tags": "briefcase",
    }
    if len(jobs) == 1:
        headers["Click"] = jobs[0].url

    response = requests.post(
        url, data=render.as_text(jobs).encode("utf-8"), headers=headers, timeout=20
    )
    response.raise_for_status()
    log.info("%d ilan ntfy konusuna gönderildi", len(jobs))
