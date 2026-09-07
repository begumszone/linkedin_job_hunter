"""Text helpers shared by search and matching.

Keyword matching has to survive Turkish casing (``İSTANBUL`` vs ``istanbul``)
and punctuation inside terms such as ``FP&A``, so everything is folded to a
plain ASCII lowercase form before comparison.
"""

from __future__ import annotations

import re
import unicodedata

_TURKISH_MAP = str.maketrans(
    {
        "İ": "i",
        "I": "i",
        "ı": "i",
        "Ş": "s",
        "ş": "s",
        "Ğ": "g",
        "ğ": "g",
        "Ü": "u",
        "ü": "u",
        "Ö": "o",
        "ö": "o",
        "Ç": "c",
        "ç": "c",
        "Â": "a",
        "â": "a",
        "Î": "i",
        "î": "i",
        "Û": "u",
        "û": "u",
    }
)

_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def fold(value: str) -> str:
    """Lowercase ``value`` and strip accents, Turkish letters included."""
    if not value:
        return ""
    folded = value.translate(_TURKISH_MAP).lower()
    folded = unicodedata.normalize("NFKD", folded)
    return "".join(ch for ch in folded if not unicodedata.combining(ch))


def tokenize(value: str) -> str:
    """Fold ``value`` and collapse every non-alphanumeric run to a space.

    ``FP&A`` and ``FP & A`` both become ``fp a``, so a keyword written either
    way still matches a job title written the other.
    """
    return " " + _NON_ALNUM.sub(" ", fold(value)).strip() + " "
