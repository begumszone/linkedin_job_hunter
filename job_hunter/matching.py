"""Decide whether a job posting matches a search's keywords."""

from __future__ import annotations

from typing import Iterable, Sequence

from .text import tokenize


def _haystack(*parts: str) -> str:
    return tokenize(" ".join(part for part in parts if part))


# Short keywords are acronyms in practice (IT, BT, AD). Matching them with a
# suffix allowed turns "IT" into a match for "İthalat" and "İtfaiye", so they
# have to line up with a whole word.
ACRONYM_LENGTH = 3


def _contains(haystack: str, term: str) -> bool:
    """True when ``term`` starts a word in ``haystack``.

    A longer keyword may run into a suffix, so ``finans`` finds "Finansal
    Raporlama". A keyword of at most ``ACRONYM_LENGTH`` characters must match a
    whole word instead.
    """
    needle = tokenize(term).strip()
    if not needle:
        return False
    if len(needle.replace(" ", "")) <= ACRONYM_LENGTH:
        return f" {needle} " in haystack
    return f" {needle}" in haystack


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
