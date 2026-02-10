"""Deduplication logic for enriched attendee records."""

from __future__ import annotations

import logging
import re
import unicodedata

from enricher.models import AttendeeEnriched

logger = logging.getLogger(__name__)


def _normalise_key(name: str) -> str:
    """Produce a deterministic dedup key from a full name.

    • Lower-case
    • Strip accents
    • Collapse whitespace
    • Remove punctuation
    """
    # Strip accents
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_only = "".join(ch for ch in nfkd if not unicodedata.combining(ch))
    key = ascii_only.lower().strip()
    key = re.sub(r"[^a-z0-9 ]", "", key)
    key = re.sub(r"\s+", " ", key)
    return key


def dedupe(attendees: list[AttendeeEnriched]) -> list[AttendeeEnriched]:
    """Remove duplicate attendee records.

    Strategy:
    - Primary key: normalised ``full_name``.
    - When a duplicate is found, merge social links (keeping the union)
      and prefer the record with more fields filled.
    """
    seen: dict[str, AttendeeEnriched] = {}
    dupes = 0

    for att in attendees:
        key = _normalise_key(att.full_name)
        if not key:
            # Records with empty names are kept as-is (should have been
            # filtered earlier, but be defensive).
            seen[f"__empty_{id(att)}"] = att
            continue

        if key in seen:
            dupes += 1
            existing = seen[key]
            # Merge social links (union by url)
            existing_urls = {link.url for link in existing.social_links}
            for link in att.social_links:
                if link.url not in existing_urls:
                    existing.social_links.append(link)
                    existing_urls.add(link.url)
            # Prefer more-complete company/role
            if not existing.company and att.company:
                existing.company = att.company
            if not existing.role and att.role:
                existing.role = att.role
            # Refresh provenance summary
            existing.provenance_summary = ", ".join(
                lk.provenance for lk in existing.social_links
            )
        else:
            seen[key] = att

    logger.info("Deduplication: %d duplicates removed", dupes)
    return list(seen.values())
