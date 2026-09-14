from datetime import date

import pytest

from job_hunter.freshness import age_hours, is_recent

TODAY = date(2026, 9, 14)


def test_datetime_attribute_wins_over_the_label():
    assert age_hours("2026-09-14", "5 gün önce", TODAY) == 0


def test_age_from_the_datetime_attribute():
    assert age_hours("2026-09-09", "", TODAY) == 120


@pytest.mark.parametrize(
    "label, expected",
    [
        ("18 dakika önce", 0.3),
        ("5 saat önce", 5),
        ("2 gün önce", 48),
        ("1 hafta önce", 168),
        ("3 ay önce", 2160),
        ("18 minutes ago", 0.3),
        ("2 days ago", 48),
        ("1 week ago", 168),
    ],
)
def test_age_from_turkish_and_english_labels(label, expected):
    assert age_hours("", label, TODAY) == pytest.approx(expected, rel=0.01)


def test_unknown_age_is_reported_as_none():
    assert age_hours("", "", TODAY) is None
    assert age_hours("bozuk-tarih", "belirsiz", TODAY) is None


def test_posting_from_five_days_ago_is_not_recent():
    # The posting that started this: LinkedIn returned it despite the 24h filter.
    assert is_recent("2026-09-09", "5 gün önce", 24, TODAY) is False


def test_todays_posting_is_recent():
    assert is_recent("2026-09-14", "18 dakika önce", 24, TODAY) is True


def test_yesterdays_posting_is_kept_because_the_date_has_no_time():
    # A posting made late yesterday reads as 24h old; dropping it would lose
    # genuinely fresh results.
    assert is_recent("2026-09-13", "20 saat önce", 24, TODAY) is True


def test_unknown_age_is_kept():
    assert is_recent("", "", 24, TODAY) is True
