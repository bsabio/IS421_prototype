"""Normalize attendee names, companies, and profile URLs.

Only operates on data that was already present in the CSV / API response.
No external look-ups, no web searches, no guessing.
"""

from __future__ import annotations

import logging
import re
import unicodedata

from enricher.models import AttendeeRaw

logger = logging.getLogger(__name__)


def _strip_control_chars(text: str) -> str:
    """Remove Unicode control characters but keep normal whitespace."""
    return "".join(
        ch for ch in text
        if unicodedata.category(ch)[0] != "C" or ch in ("\n", "\r", "\t", " ")
    )


def _title_case(name: str) -> str:
    """Smart title-case that handles McX, O'X, hyphens."""
    parts: list[str] = []
    for token in name.split():
        if token.startswith("Mc") and len(token) > 2:
            parts.append("Mc" + token[2:].capitalize())
        elif "'" in token:
            segments = token.split("'")
            parts.append("'".join(s.capitalize() for s in segments))
        elif "-" in token:
            segments = token.split("-")
            parts.append("-".join(s.capitalize() for s in segments))
        else:
            parts.append(token.capitalize())
    return " ".join(parts)


def normalize_name(raw: AttendeeRaw) -> str:
    """Build a cleaned full name from the raw record.

    Priority:
    1. ``full_name`` if present.
    2. ``first_name`` + ``last_name``.
    3. ``first_name`` or ``last_name`` alone (partial).
    """
    if raw.full_name and raw.full_name.strip():
        name = raw.full_name.strip()
    elif raw.first_name or raw.last_name:
        parts = [p.strip() for p in (raw.first_name, raw.last_name) if p and p.strip()]
        name = " ".join(parts)
    else:
        return ""

    # Collapse whitespace, strip control chars, apply title-case
    name = _strip_control_chars(name)
    name = re.sub(r"\s+", " ", name).strip()
    name = _title_case(name)
    return name


def normalize_company(value: str | None) -> str | None:
    """Return a cleaned company name, or None."""
    if not value or not value.strip():
        return None
    company = _strip_control_chars(value).strip()
    company = re.sub(r"\s+", " ", company)
    return company


def normalize_url(url: str | None) -> str | None:
    """Minimal URL tidy-up: trim whitespace, ensure scheme prefix."""
    if not url or not url.strip():
        return None
    url = url.strip()
    # Remove surrounding angle-brackets or quotes
    url = url.strip("<>\"'")
    if not url:
        return None
    # Add https:// if no scheme
    if not re.match(r"https?://", url, re.IGNORECASE):
        url = "https://" + url
    return url
