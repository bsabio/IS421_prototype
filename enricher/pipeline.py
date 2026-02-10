"""Pipeline: ties ingestion → normalisation → validation → dedup → export."""

from __future__ import annotations

import logging
from typing import Optional

from enricher.config import load_config
from enricher.dedupe import dedupe
from enricher.export import compute_summary, export_csv, export_json, print_summary
from enricher.ingest import ingest_api, ingest_csv
from enricher.models import (
    AttendeeEnriched,
    AttendeeRaw,
    EnricherConfig,
    SocialLink,
    SourceType,
)
from enricher.normalize import normalize_company, normalize_name, normalize_url
from enricher.validate import validate_attendee_urls

logger = logging.getLogger(__name__)


def _enrich_one(
    raw: AttendeeRaw,
    config: EnricherConfig,
    source_type: SourceType,
) -> Optional[AttendeeEnriched]:
    """Transform a single raw attendee into an enriched record."""
    full_name = normalize_name(raw)
    if not full_name:
        logger.warning("Attendee skipped – no usable name: %r", raw)
        return None

    company = normalize_company(raw.company)
    role = raw.role.strip() if raw.role else None

    # Collect all social-link fields present in the source
    url_fields: dict[str, str | None] = {
        "linkedin_url": normalize_url(raw.linkedin_url),
        "twitter_url": normalize_url(raw.twitter_url),
        "github_url": normalize_url(raw.github_url),
        "website_url": normalize_url(raw.website_url),
    }

    social_links = validate_attendee_urls(
        url_fields, config=config, source_type=source_type
    )

    provenance_summary = ", ".join(lk.provenance for lk in social_links)

    event = raw.event.strip() if raw.event else None

    return AttendeeEnriched(
        full_name=full_name,
        company=company,
        role=role,
        event=event,
        social_links=social_links,
        provenance_summary=provenance_summary,
        source_type=source_type,
    )


def run_csv_pipeline(
    csv_path: str,
    config_path: str | None = None,
    output_formats: list[str] | None = None,
) -> None:
    """End-to-end enrichment from an organizer-export CSV."""
    config = load_config(config_path)
    if output_formats:
        config.output_formats = output_formats

    raw_attendees = ingest_csv(csv_path)
    enriched = [
        rec
        for raw in raw_attendees
        if (rec := _enrich_one(raw, config, SourceType.CSV)) is not None
    ]
    logger.info("Enriched %d / %d raw attendees", len(enriched), len(raw_attendees))

    deduped = dedupe(enriched)
    summary = compute_summary(len(raw_attendees), deduped)

    if "json" in config.output_formats:
        export_json(deduped, summary, config.output_dir)
    if "csv" in config.output_formats:
        export_csv(deduped, summary, config.output_dir)

    print(print_summary(summary))


def run_api_pipeline(
    event_id: str,
    config_path: str | None = None,
    output_formats: list[str] | None = None,
) -> None:
    """End-to-end enrichment from an official platform API."""
    config = load_config(config_path)
    if output_formats:
        config.output_formats = output_formats

    raw_attendees = ingest_api(config.api, event_id)
    enriched = [
        rec
        for raw in raw_attendees
        if (rec := _enrich_one(raw, config, SourceType.API)) is not None
    ]
    logger.info("Enriched %d / %d raw attendees", len(enriched), len(raw_attendees))

    deduped = dedupe(enriched)
    summary = compute_summary(len(raw_attendees), deduped)

    if "json" in config.output_formats:
        export_json(deduped, summary, config.output_dir)
    if "csv" in config.output_formats:
        export_csv(deduped, summary, config.output_dir)

    print(print_summary(summary))
