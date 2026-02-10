"""Pydantic models for attendee data validation and schema enforcement."""

from __future__ import annotations

import enum
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl, field_validator


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class SourceType(str, enum.Enum):
    CSV = "csv"
    API = "api"


# ---------------------------------------------------------------------------
# Social-link model
# ---------------------------------------------------------------------------

class SocialLink(BaseModel):
    """A single validated social URL together with its provenance."""

    platform: str = Field(
        ..., description="Normalised platform name (linkedin, twitter, github, website)"
    )
    url: str = Field(..., description="Validated URL string")
    provenance: str = Field(
        ...,
        description="Origin field, e.g. 'csv.linkedin_url' or 'api.twitter'",
    )


# ---------------------------------------------------------------------------
# Attendee record
# ---------------------------------------------------------------------------

class AttendeeRaw(BaseModel):
    """Loosely-typed attendee as it arrives from the ingestion layer."""

    full_name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company: Optional[str] = None
    role: Optional[str] = None
    email: Optional[str] = None
    event: Optional[str] = None

    linkedin_url: Optional[str] = None
    twitter_url: Optional[str] = None
    github_url: Optional[str] = None
    website_url: Optional[str] = None

    # Catch-all for extra columns the CSV/API might include
    extra: dict = Field(default_factory=dict)


class AttendeeEnriched(BaseModel):
    """Validated, normalised, deduplicated attendee record."""

    full_name: str
    company: Optional[str] = None
    role: Optional[str] = None
    event: Optional[str] = None
    social_links: list[SocialLink] = Field(default_factory=list)
    provenance_summary: str = Field(
        default="",
        description="Comma-separated list of provenance tags for all social links",
    )
    source_type: SourceType

    @field_validator("full_name")
    @classmethod
    def name_must_not_be_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("full_name must not be blank")
        return v.strip()


# ---------------------------------------------------------------------------
# Enrichment run summary
# ---------------------------------------------------------------------------

class EnrichmentSummary(BaseModel):
    total_ingested: int = 0
    total_after_dedup: int = 0
    duplicates_removed: int = 0
    pct_with_any_social: float = 0.0
    pct_with_linkedin: float = 0.0
    pct_with_twitter: float = 0.0
    pct_with_github: float = 0.0
    pct_with_website: float = 0.0


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

class AllowedFields(BaseModel):
    """Which attendee fields should be kept in the output."""

    full_name: bool = True
    company: bool = True
    role: bool = True
    linkedin: bool = True
    twitter: bool = True
    github: bool = True
    website: bool = True


class APIConfig(BaseModel):
    """Credentials and settings for the event-platform API."""

    base_url: str = ""
    api_key: str = ""
    event_id: str = ""
    timeout: int = 30
    max_retries: int = 3
    backoff_factor: float = 0.5
    user_agent: str = "AttendeeDirectoryEnricher/0.1 (contact: admin@example.com)"


class EnricherConfig(BaseModel):
    allowed_fields: AllowedFields = Field(default_factory=AllowedFields)
    api: APIConfig = Field(default_factory=APIConfig)
    output_dir: str = "output"
    output_formats: list[str] = Field(default_factory=lambda: ["json", "csv"])
    domain_allowlist: list[str] = Field(
        default_factory=lambda: [
            "linkedin.com",
            "www.linkedin.com",
            "twitter.com",
            "x.com",
            "github.com",
            "www.github.com",
        ]
    )
