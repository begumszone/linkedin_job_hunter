"""Fetch recent job postings from LinkedIn's public (guest) job search.

LinkedIn has no public jobs API, so this reads the same endpoint the logged-out
job search page uses to paginate results. It is deliberately slow and polite:
one page at a time, a delay between requests, and a hard stop on 429.
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from urllib.parse import urlencode, urlsplit, urlunsplit

import requests
from bs4 import BeautifulSoup

log = logging.getLogger(__name__)

SEARCH_URL = (
    "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
)
PAGE_SIZE = 25
_JOB_ID_FROM_URL = re.compile(r"-(\d{6,})(?:\?|$)")
_JOB_ID_FROM_URN = re.compile(r"(\d{6,})")


class RateLimited(Exception):
    """LinkedIn asked us to slow down (HTTP 429 or a block page)."""


@dataclass
class Job:
    id: str
    title: str
    company: str
    location: str
    url: str
    posted_at: str = ""
    posted_label: str = ""
    search_name: str = ""
    matched_keywords: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "company": self.company,
            "location": self.location,
            "url": self.url,
            "posted_at": self.posted_at,
            "posted_label": self.posted_label,
            "search_name": self.search_name,
            "matched_keywords": list(self.matched_keywords),
        }


def _clean_url(href: str) -> str:
    """Drop LinkedIn's tracking query string so the same job yields one URL."""
    parts = urlsplit(href.strip())
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def _text(node) -> str:
    return node.get_text(strip=True) if node else ""


def _job_id(card, url: str) -> str:
    urn = card.get("data-entity-urn") or card.get("data-id") or ""
    match = _JOB_ID_FROM_URN.search(urn)
    if match:
        return match.group(1)
    match = _JOB_ID_FROM_URL.search(url)
    if match:
        return match.group(1)
    return url


def parse_jobs(html: str) -> list[Job]:
    """Parse the job cards out of one guest-search response."""
    soup = BeautifulSoup(html, "html.parser")
    jobs: list[Job] = []

    for card in soup.select("div.base-card, div.base-search-card, li div[data-entity-urn]"):
        link = card.select_one("a.base-card__full-link, a.base-search-card--link, a[href*='/jobs/view/']")
        href = link.get("href", "") if link else ""
        if not href:
            continue
        url = _clean_url(href)

        title = _text(card.select_one("h3.base-search-card__title"))
        if not title and link:
            title = _text(link.select_one("span.sr-only")) or link.get("aria-label", "")

        time_node = card.select_one("time")
        jobs.append(
            Job(
                id=_job_id(card, url),
                title=title,
                company=_text(card.select_one("h4.base-search-card__subtitle")),
                location=_text(card.select_one(".job-search-card__location")),
                url=url,
                posted_at=(time_node.get("datetime", "") if time_node else ""),
                posted_label=_text(time_node),
            )
        )

    return jobs


class LinkedInClient:
    def __init__(self, user_agent: str, delay_seconds: float = 3.0, timeout: int = 20):
        self.delay_seconds = delay_seconds
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": user_agent,
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "tr,en;q=0.8",
            }
        )
        self._last_request = 0.0

    def _wait(self) -> None:
        elapsed = time.monotonic() - self._last_request
        if elapsed < self.delay_seconds:
            time.sleep(self.delay_seconds - elapsed)

    def _get(self, params: dict) -> str:
        for attempt in range(3):
            self._wait()
            response = self.session.get(SEARCH_URL, params=params, timeout=self.timeout)
            self._last_request = time.monotonic()

            if response.status_code == 429:
                if attempt == 2:
                    raise RateLimited("LinkedIn 429 döndü, tarama durduruldu.")
                backoff = self.delay_seconds * (2 ** (attempt + 1))
                log.warning("429 alındı, %.0f sn bekleniyor", backoff)
                time.sleep(backoff)
                continue
            if response.status_code in (400, 404):
                # The guest endpoint answers 400 for "no more pages".
                return ""
            response.raise_for_status()
            return response.text
        return ""

    def search(
        self,
        keywords: str,
        location: str = "",
        hours: int = 24,
        max_results: int = 50,
        remote_only: bool = False,
    ) -> list[Job]:
        """Return postings for one query, newest first."""
        found: dict[str, Job] = {}
        start = 0

        while start < max_results:
            params = {
                "keywords": keywords,
                "location": location,
                "f_TPR": f"r{int(hours) * 3600}",
                "sortBy": "DD",  # date descending
                "start": start,
            }
            if remote_only:
                params["f_WT"] = "2"  # LinkedIn's "Remote" workplace filter

            html = self._get(params)
            if not html.strip():
                break

            page = parse_jobs(html)
            if not page:
                if start == 0:
                    # A non-empty body with no cards means LinkedIn served a
                    # login wall or changed its markup — not "no jobs today".
                    log.warning(
                        "'%s' için yanıt geldi ama hiç ilan kartı ayrıştırılamadı. "
                        "LinkedIn giriş duvarı göstermiş veya sayfa yapısı değişmiş olabilir.",
                        keywords,
                    )
                break

            new_on_page = 0
            for job in page:
                if job.id not in found:
                    found[job.id] = job
                    new_on_page += 1

            if new_on_page == 0 or len(page) < PAGE_SIZE:
                break
            start += PAGE_SIZE

        log.info(
            "'%s' (%s) için %d ilan bulundu",
            keywords,
            location or "tüm konumlar",
            len(found),
        )
        return list(found.values())[:max_results]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def build_query(keywords: list[str], mode: str) -> list[str]:
    """Turn the configured keywords into LinkedIn search queries.

    ``any`` searches each keyword on its own so a match on one term is enough;
    ``all`` sends a single AND query and the result is filtered locally too.
    """
    if mode == "all":
        return [" AND ".join(f'"{kw}"' if " " in kw else kw for kw in keywords)]
    return list(keywords)
