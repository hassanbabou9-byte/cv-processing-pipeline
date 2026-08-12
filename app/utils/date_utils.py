"""
Date parsing utilities for normalizing free-text dates extracted from CVs.

CVs express dates in wildly inconsistent formats — ISO dates, "MM/YYYY",
bare years, French month names, date ranges collapsed into a single
string, and "ongoing" markers like "Présent". This module makes a
best-effort attempt to extract a single date from whatever string
arrives.

Honest limitation: this does NOT guarantee correctness for every
possible format a CV might use — CVs are free text written by humans,
not a structured data entry form. When a date range is collapsed into
one field (e.g. "JUILLET - DÉCEMBRE 2023"), the FIRST recognizable date
is returned; this is a pragmatic choice, not a claim of correctness.
"""

import re
from datetime import date

_ONGOING_MARKERS = {
    "présent", "present", "actuel", "actuelle", "aujourd'hui",
    "aujourdhui", "en cours", "now", "current", "ongoing",
}

_FRENCH_MONTHS = {
    "janvier": 1, "février": 2, "fevrier": 2, "mars": 3, "avril": 4,
    "mai": 5, "juin": 6, "juillet": 7, "août": 8, "aout": 8,
    "septembre": 9, "octobre": 10, "novembre": 11,
    "décembre": 12, "decembre": 12,
}

_ISO_DATE_RE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
_ISO_YEAR_MONTH_RE = re.compile(r"\b(\d{4})-(\d{2})\b")
_MONTH_YEAR_SLASH_RE = re.compile(r"\b(\d{1,2})/(\d{4})\b")
_YEAR_ONLY_RE = re.compile(r"\b(?:19|20)\d{2}\b")
_FRENCH_MONTH_YEAR_RE = re.compile(
    r"\b(" + "|".join(_FRENCH_MONTHS.keys()) + r")\.?\s+(\d{4})\b",
    re.IGNORECASE,
)


def is_ongoing_marker(raw: str) -> bool:
    """True if the whole string represents an unfinished/ongoing date (e.g. "Présent")."""
    return raw.strip().lower() in _ONGOING_MARKERS


def parse_date_field(raw: str | None) -> date | None:
    """
    Best-effort parse of a free-text date string extracted from a CV.

    Tries, in order: ISO YYYY-MM-DD, ISO YYYY-MM (day=1), MM/YYYY,
    French "Mois YYYY", then a bare year (YYYY, month/day=1). Returns
    None if nothing recognizable is found, or if the text is an
    "ongoing" marker like "Présent" (no fixed end date — appropriate
    for an optional date_fin field).

    Args:
        raw: Free-text date string as extracted by the LLM (may be None
            or empty).

    Returns:
        A parsed date, or None if nothing could be recognized.

    Known limitation: when a field contains a full date RANGE with two
    month names (e.g. "JUILLET - DÉCEMBRE 2023" — a known LLM extraction
    quirk where a range gets collapsed into a single "debut" field
    instead of being split across debut/fin), this returns whichever
    month is directly adjacent to the year, which may be the range's
    END month rather than its start. The year itself is still correct.
    This is a data-ambiguity issue, not something a parser can resolve
    perfectly — the real fix is prompt-level (see cv_extraction_prompt.py's
    instructions to keep debut/fin as separate fields).
    """
    if not raw:
        return None

    text = raw.strip()
    if not text or is_ongoing_marker(text):
        return None

    if match := _ISO_DATE_RE.search(text):
        year, month, day = (int(g) for g in match.groups())
        try:
            return date(year, month, day)
        except ValueError:
            pass

    if match := _ISO_YEAR_MONTH_RE.search(text):
        year, month = (int(g) for g in match.groups())
        try:
            return date(year, month, 1)
        except ValueError:
            pass

    if match := _MONTH_YEAR_SLASH_RE.search(text):
        month, year = (int(g) for g in match.groups())
        try:
            return date(year, month, 1)
        except ValueError:
            pass

    if match := _FRENCH_MONTH_YEAR_RE.search(text):
        month_name, year_str = match.group(1).lower(), match.group(2)
        month = _FRENCH_MONTHS.get(month_name)
        if month:
            try:
                return date(int(year_str), month, 1)
            except ValueError:
                pass

    if match := _YEAR_ONLY_RE.search(text):
        try:
            return date(int(match.group(0)), 1, 1)
        except ValueError:
            pass

    return None