"""Work out how old a posting is, from the card's own date fields.

LinkedIn does not always honour the "last 24 hours" filter: when a query has
few results it pads the list with older, unrelated postings. So the age is
checked again locally instead of trusting the search filter.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timezone

# "5 gün önce", "18 dakika önce", "2 weeks ago", "1 month ago"
_RELATIVE = re.compile(
    r"(\d+)\s*(dakika|saat|gün|hafta|ay|yıl|minute|hour|day|week|month|year)",
    re.IGNORECASE,
)

_UNIT_HOURS = {
    "dakika": 1 / 60,
    "minute": 1 / 60,
    "saat": 1,
    "hour": 1,
    "gün": 24,
    "day": 24,
    "hafta": 24 * 7,
    "week": 24 * 7,
    "ay": 24 * 30,
    "month": 24 * 30,
    "yıl": 24 * 365,
    "year": 24 * 365,
}


def age_hours(posted_at: str = "", posted_label: str = "", today: date | None = None):
    """Approximate posting age in hours, or None when it cannot be told.

    ``posted_at`` is the card's ``<time datetime="...">`` value — a plain date,
    so a posting from today reads as 0 hours old. ``posted_label`` ("5 gün
    önce") is the fallback when the attribute is missing.
    """
    if posted_at:
        try:
            posted = datetime.fromisoformat(posted_at.strip()).date()
        except ValueError:
            posted = None
        if posted is not None:
            reference = today or datetime.now(timezone.utc).date()
            return max((reference - posted).days, 0) * 24

    match = _RELATIVE.search(posted_label or "")
    if match:
        amount = int(match.group(1))
        unit = match.group(2).lower()
        return amount * _UNIT_HOURS[unit]

    return None


def is_recent(posted_at: str, posted_label: str, hours: int, today: date | None = None) -> bool:
    """True when the posting is within the window, or its age is unknown.

    An unknown age is kept: dropping it would silently hide real postings if
    LinkedIn ever stops publishing the date.
    """
    age = age_hours(posted_at, posted_label, today)
    if age is None:
        return True
    # The datetime attribute carries a date, not a time, so a posting made late
    # yesterday reads as 24h old at midnight. One day of slack avoids dropping
    # genuinely fresh postings.
    return age <= hours + 24
