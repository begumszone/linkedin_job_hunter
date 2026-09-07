"""Decide whether a job posting matches a search's keywords."""

from __future__ import annotations

from typing import Iterable, Sequence

from .text import tokenize


def _haystack(*parts: str) -> str:
    return tokenize(" ".join(part for part in parts if part))


def _contains(haystack: str, term: str) -> bool:
    """True when ``term`` starts a word in ``haystack``.

    The match must begin at a word boundary but may run into a suffix, so
    ``finans`` finds "Finansal Raporlama" while ``IFRS`` does not fire on an
    unrelated word that merely contains those letters.
    """
    needle = tokenize(term).strip()
    return bool(needle) and f" {needle}" in haystack


def matched_keywords(text: str, keywords: Sequence[str]) -> list[str]:
    """Return the keywords that occur in ``text``, in config order."""
    haystack = _haystack(text)
    return [keyword for keyword in keywords if _contains(haystack, keyword)]


def matches(
    text: str,
    keywords: Sequence[str],
    mode: str = "any",
    exclude: Iterable[str] = (),
) -> list[str]:
    """Return matched keywords, or an empty list when the posting is rejected.

    ``mode`` is ``any`` (at least one keyword) or ``all`` (every keyword).
    Anything in ``exclude`` vetoes the posting regardless of the mode.
    """
    haystack = _haystack(text)
    if any(_contains(haystack, term) for term in exclude):
        return []

    hits = matched_keywords(text, keywords)
    if mode == "all":
        return hits if len(hits) == len(keywords) else []
    return hits
