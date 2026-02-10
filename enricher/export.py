"""Export enriched attendee data to JSON and CSV, with summary stats."""

from __future__ import annotations

import csv
import json
import logging
from pathlib import Path

from enricher.models import AttendeeEnriched, EnrichmentSummary

logger = logging.getLogger(__name__)


def compute_summary(
    total_ingested: int,
    attendees: list[AttendeeEnriched],
) -> EnrichmentSummary:
    """Compute enrichment statistics."""
    n = len(attendees) or 1  # avoid ZeroDivisionError

    def _pct(predicate) -> float:
        return round(sum(1 for a in attendees if predicate(a)) / n * 100, 1)

    return EnrichmentSummary(
        total_ingested=total_ingested,
        total_after_dedup=len(attendees),
        duplicates_removed=total_ingested - len(attendees),
        pct_with_any_social=_pct(lambda a: len(a.social_links) > 0),
        pct_with_linkedin=_pct(
            lambda a: any(lk.platform == "linkedin" for lk in a.social_links)
        ),
        pct_with_twitter=_pct(
            lambda a: any(lk.platform == "twitter" for lk in a.social_links)
        ),
        pct_with_github=_pct(
            lambda a: any(lk.platform == "github" for lk in a.social_links)
        ),
        pct_with_website=_pct(
            lambda a: any(lk.platform == "website" for lk in a.social_links)
        ),
    )


# ---------------------------------------------------------------------------
# JSON export
# ---------------------------------------------------------------------------

def export_json(
    attendees: list[AttendeeEnriched],
    summary: EnrichmentSummary,
    output_dir: str | Path,
) -> Path:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / "attendees_enriched.json"

    payload = {
        "summary": summary.model_dump(),
        "attendees": [a.model_dump() for a in attendees],
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    logger.info("JSON export → %s  (%d attendees)", path, len(attendees))
    return path


# ---------------------------------------------------------------------------
# CSV export
# ---------------------------------------------------------------------------

_CSV_COLUMNS = [
    "full_name",
    "company",
    "role",
    "event",
    "linkedin",
    "twitter",
    "github",
    "website",
    "provenance",
]


def _social_by_platform(att: AttendeeEnriched, platform: str) -> str:
    for lk in att.social_links:
        if lk.platform == platform:
            return lk.url
    return ""


def export_csv(
    attendees: list[AttendeeEnriched],
    summary: EnrichmentSummary,
    output_dir: str | Path,
) -> Path:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / "attendees_enriched.csv"

    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=_CSV_COLUMNS)
        writer.writeheader()
        for att in attendees:
            writer.writerow({
                "full_name": att.full_name,
                "company": att.company or "",
                "role": att.role or "",
                "event": att.event or "",
                "linkedin": _social_by_platform(att, "linkedin"),
                "twitter": _social_by_platform(att, "twitter"),
                "github": _social_by_platform(att, "github"),
                "website": _social_by_platform(att, "website"),
                "provenance": att.provenance_summary,
            })

    logger.info("CSV export  → %s  (%d attendees)", path, len(attendees))
    return path


def print_summary(summary: EnrichmentSummary) -> str:
    """Return a human-readable summary string."""
    lines = [
        "╔══════════════════════════════════════╗",
        "║   Attendee Enrichment Summary        ║",
        "╠══════════════════════════════════════╣",
        f"  Total ingested:      {summary.total_ingested}",
        f"  After dedup:         {summary.total_after_dedup}",
        f"  Duplicates removed:  {summary.duplicates_removed}",
        f"  % with any social:   {summary.pct_with_any_social}%",
        f"  % with LinkedIn:     {summary.pct_with_linkedin}%",
        f"  % with Twitter/X:    {summary.pct_with_twitter}%",
        f"  % with GitHub:       {summary.pct_with_github}%",
        f"  % with website:      {summary.pct_with_website}%",
        "╚══════════════════════════════════════╝",
    ]
    return "\n".join(lines)
