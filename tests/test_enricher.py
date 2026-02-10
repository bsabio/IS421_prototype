"""Unit tests for the Attendee Directory Enricher.

Covers: CSV parsing, name normalisation, URL validation, dedup, and export.
"""

from __future__ import annotations

import csv
import json
import textwrap
from io import StringIO
from pathlib import Path

import pytest

# ---- Models ----------------------------------------------------------------
from enricher.models import (
    AttendeeEnriched,
    AttendeeRaw,
    EnricherConfig,
    SocialLink,
    SourceType,
)

# ---- Normalisation ---------------------------------------------------------
from enricher.normalize import normalize_company, normalize_name, normalize_url

# ---- Validation ------------------------------------------------------------
from enricher.validate import validate_attendee_urls, validate_url

# ---- Dedup -----------------------------------------------------------------
from enricher.dedupe import dedupe

# ---- Export ----------------------------------------------------------------
from enricher.export import compute_summary, export_csv, export_json

# ---- Ingest ----------------------------------------------------------------
from enricher.ingest import ingest_csv


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture()
def default_config() -> EnricherConfig:
    return EnricherConfig()


@pytest.fixture()
def sample_csv(tmp_path: Path) -> Path:
    """Write a minimal attendee CSV and return the path."""
    csv_path = tmp_path / "attendees.csv"
    csv_path.write_text(
        textwrap.dedent("""\
        Full Name,Company,Role,LinkedIn URL,Twitter URL,GitHub URL,Website
        Alice Johnson,Acme Corp,CTO,https://www.linkedin.com/in/alicej,https://twitter.com/alicej,,https://alice.dev
        Bob Smith,Widgets Inc,Engineer,https://linkedin.com/in/bobsmith,,,
        alice johnson,ACME Corp,CTO,https://www.linkedin.com/in/alicej,,,
        ,,,,,
        Charlie Brown,,Intern,,,,
        """),
        encoding="utf-8",
    )
    return csv_path


# ============================================================================
# Normalisation tests
# ============================================================================

class TestNormalizeName:
    def test_full_name(self):
        raw = AttendeeRaw(full_name="  jane   DOE  ")
        assert normalize_name(raw) == "Jane Doe"

    def test_first_last(self):
        raw = AttendeeRaw(first_name="john", last_name="mcnamara")
        assert normalize_name(raw) == "John Mcnamara"

    def test_hyphenated(self):
        raw = AttendeeRaw(full_name="mary-jane watson")
        assert normalize_name(raw) == "Mary-Jane Watson"

    def test_empty(self):
        raw = AttendeeRaw()
        assert normalize_name(raw) == ""

    def test_only_first(self):
        raw = AttendeeRaw(first_name="solo")
        assert normalize_name(raw) == "Solo"

    def test_mc_prefix(self):
        raw = AttendeeRaw(full_name="connor mcdonald")
        assert normalize_name(raw) == "Connor Mcdonald"


class TestNormalizeCompany:
    def test_whitespace(self):
        assert normalize_company("  Acme  Corp  ") == "Acme Corp"

    def test_none(self):
        assert normalize_company(None) is None

    def test_empty(self):
        assert normalize_company("   ") is None


class TestNormalizeUrl:
    def test_adds_scheme(self):
        assert normalize_url("linkedin.com/in/foo") == "https://linkedin.com/in/foo"

    def test_strips_whitespace(self):
        assert normalize_url("  https://x.com/bar  ") == "https://x.com/bar"

    def test_none(self):
        assert normalize_url(None) is None

    def test_empty(self):
        assert normalize_url("") is None

    def test_angle_brackets(self):
        assert normalize_url("<https://github.com/user>") == "https://github.com/user"


# ============================================================================
# URL validation tests
# ============================================================================

class TestValidateUrl:
    def test_valid_linkedin(self, default_config):
        link = validate_url(
            "https://www.linkedin.com/in/janedoe",
            config=default_config,
            source_field="linkedin_url",
            source_type=SourceType.CSV,
        )
        assert link is not None
        assert link.platform == "linkedin"
        assert link.provenance == "csv.linkedin_url"

    def test_valid_twitter(self, default_config):
        link = validate_url(
            "https://twitter.com/janedoe",
            config=default_config,
            source_field="twitter_url",
            source_type=SourceType.API,
        )
        assert link is not None
        assert link.platform == "twitter"
        assert link.provenance == "api.twitter_url"

    def test_valid_x_domain(self, default_config):
        link = validate_url(
            "https://x.com/janedoe",
            config=default_config,
            source_field="twitter_url",
            source_type=SourceType.CSV,
        )
        assert link is not None
        assert link.platform == "twitter"

    def test_invalid_scheme(self, default_config):
        link = validate_url(
            "ftp://linkedin.com/in/foo",
            config=default_config,
            source_field="linkedin_url",
            source_type=SourceType.CSV,
        )
        assert link is None

    def test_non_allowlisted_social(self, default_config):
        """A known social field pointing to a non-allowlisted domain is rejected."""
        link = validate_url(
            "https://evil-site.com/profile/foo",
            config=default_config,
            source_field="linkedin_url",
            source_type=SourceType.CSV,
        )
        assert link is None

    def test_website_field_any_domain(self, default_config):
        """The 'website_url' field accepts any domain (it's not a known social)."""
        link = validate_url(
            "https://my-personal-site.co",
            config=default_config,
            source_field="website_url",
            source_type=SourceType.CSV,
        )
        assert link is not None
        assert link.platform == "website"

    def test_none_url(self, default_config):
        assert validate_url(None, config=default_config, source_field="x", source_type=SourceType.CSV) is None

    def test_empty_url(self, default_config):
        assert validate_url("", config=default_config, source_field="x", source_type=SourceType.CSV) is None

    def test_malformed_url(self, default_config):
        link = validate_url(
            "not a url at all",
            config=default_config,
            source_field="linkedin_url",
            source_type=SourceType.CSV,
        )
        assert link is None


class TestValidateAttendeeUrls:
    def test_multiple(self, default_config):
        urls = {
            "linkedin_url": "https://linkedin.com/in/test",
            "twitter_url": "https://twitter.com/test",
            "github_url": None,
            "website_url": "https://example.com",
        }
        links = validate_attendee_urls(urls, config=default_config, source_type=SourceType.CSV)
        assert len(links) == 3
        platforms = {lk.platform for lk in links}
        assert platforms == {"linkedin", "twitter", "website"}


# ============================================================================
# Dedup tests
# ============================================================================

class TestDedupe:
    def _make(self, name, company=None, socials=None):
        return AttendeeEnriched(
            full_name=name,
            company=company,
            social_links=socials or [],
            source_type=SourceType.CSV,
        )

    def test_removes_exact_dupes(self):
        attendees = [self._make("Jane Doe"), self._make("Jane Doe")]
        result = dedupe(attendees)
        assert len(result) == 1

    def test_case_insensitive(self):
        attendees = [self._make("Jane Doe"), self._make("jane doe")]
        result = dedupe(attendees)
        assert len(result) == 1

    def test_merges_socials(self):
        a1 = self._make(
            "Jane Doe",
            socials=[SocialLink(platform="linkedin", url="https://linkedin.com/in/jane", provenance="csv.linkedin_url")],
        )
        a2 = self._make(
            "jane doe",
            socials=[SocialLink(platform="twitter", url="https://twitter.com/jane", provenance="csv.twitter_url")],
        )
        result = dedupe([a1, a2])
        assert len(result) == 1
        assert len(result[0].social_links) == 2

    def test_merges_company(self):
        a1 = self._make("Jane Doe", company=None)
        a2 = self._make("jane doe", company="Acme")
        result = dedupe([a1, a2])
        assert result[0].company == "Acme"

    def test_no_dupes(self):
        attendees = [self._make("Alice"), self._make("Bob")]
        result = dedupe(attendees)
        assert len(result) == 2


# ============================================================================
# CSV ingestion tests
# ============================================================================

class TestIngestCSV:
    def test_reads_rows(self, sample_csv):
        rows = ingest_csv(sample_csv)
        # 5 data rows in the fixture (including blank and duplicate)
        assert len(rows) == 5

    def test_maps_fields(self, sample_csv):
        rows = ingest_csv(sample_csv)
        alice = rows[0]
        assert alice.full_name == "Alice Johnson"
        assert alice.company == "Acme Corp"
        assert alice.linkedin_url == "https://www.linkedin.com/in/alicej"

    def test_missing_file(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            ingest_csv(tmp_path / "nope.csv")


# ============================================================================
# Export tests
# ============================================================================

class TestExport:
    def _attendees(self):
        return [
            AttendeeEnriched(
                full_name="Alice Johnson",
                company="Acme",
                role="CTO",
                social_links=[
                    SocialLink(platform="linkedin", url="https://linkedin.com/in/alice", provenance="csv.linkedin_url"),
                ],
                provenance_summary="csv.linkedin_url",
                source_type=SourceType.CSV,
            ),
            AttendeeEnriched(
                full_name="Bob Smith",
                company="Widgets",
                source_type=SourceType.CSV,
            ),
        ]

    def test_json_export(self, tmp_path):
        atts = self._attendees()
        summary = compute_summary(3, atts)
        path = export_json(atts, summary, tmp_path)
        assert path.exists()
        data = json.loads(path.read_text())
        assert len(data["attendees"]) == 2
        assert data["summary"]["total_ingested"] == 3

    def test_csv_export(self, tmp_path):
        atts = self._attendees()
        summary = compute_summary(3, atts)
        path = export_csv(atts, summary, tmp_path)
        assert path.exists()
        reader = csv.DictReader(open(path))
        rows = list(reader)
        assert len(rows) == 2
        assert rows[0]["full_name"] == "Alice Johnson"


# ============================================================================
# Summary tests
# ============================================================================

class TestSummary:
    def test_percentages(self):
        atts = [
            AttendeeEnriched(
                full_name="A",
                social_links=[SocialLink(platform="linkedin", url="https://linkedin.com/in/a", provenance="csv.linkedin_url")],
                source_type=SourceType.CSV,
            ),
            AttendeeEnriched(full_name="B", source_type=SourceType.CSV),
        ]
        s = compute_summary(3, atts)
        assert s.total_ingested == 3
        assert s.total_after_dedup == 2
        assert s.duplicates_removed == 1
        assert s.pct_with_any_social == 50.0
        assert s.pct_with_linkedin == 50.0
