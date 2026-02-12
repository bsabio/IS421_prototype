"""
Tests for the Newsletter JSON Builder.

Run:  python -m pytest tests/test_json_builder.py -v
"""
import json
import os
import tempfile
from pathlib import Path

import pytest

# Ensure the project root is importable
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from newsroom.schema import (
    Accelerator,
    Amount,
    Company,
    EntityRefs,
    Event,
    Investment,
    Location,
    Metadata,
    NewsletterData,
    NewsletterDraftPlan,
    Person,
    SectionPlan,
    Source,
    _slug,
)
from newsroom.json_builder import (
    EntityRegistry,
    _build_real_data,
    validate,
    write_json,
)


# ── Unit: slug helper ────────────────────────────────────────────────────────

class TestSlug:
    def test_simple(self):
        assert _slug("OpenAI") == "openai"

    def test_spaces_and_special(self):
        assert _slug("Flock AI") == "flock-ai"

    def test_mixed(self):
        assert _slug("Goldman Sachs Alternatives") == "goldman-sachs-alternatives"

    def test_leading_trailing(self):
        assert _slug("  Hello World! ") == "hello-world"


# ── Unit: Source ─────────────────────────────────────────────────────────────

class TestSource:
    def test_to_dict_without_confidence(self):
        s = Source(url="https://example.com", publisher="Ex", retrievedAt="2026-01-01T00:00:00+00:00")
        d = s.to_dict()
        assert "confidence" not in d
        assert d["publisher"] == "Ex"

    def test_to_dict_with_confidence(self):
        s = Source(url="https://example.com", publisher="Ex", retrievedAt="2026-01-01T00:00:00+00:00", confidence=0.9)
        d = s.to_dict()
        assert d["confidence"] == 0.9


# ── Unit: Company / Person auto-id ───────────────────────────────────────────

class TestEntityAutoId:
    def test_company_auto_id(self):
        c = Company(name="Startup X")
        assert c.id == "company:startup-x"

    def test_person_auto_id(self):
        p = Person(name="Jane Doe")
        assert p.id == "person:jane-doe"

    def test_explicit_id_preserved(self):
        c = Company(name="Foo", id="company:custom")
        assert c.id == "company:custom"


# ── Unit: EntityRegistry dedup ───────────────────────────────────────────────

class TestEntityRegistry:
    def test_add_company_dedup(self):
        reg = EntityRegistry()
        id1 = reg.add_company("Acme Corp", industry=["SaaS"])
        id2 = reg.add_company("Acme Corp", location="NYC")
        assert id1 == id2
        assert len(reg.companies) == 1
        # merged fields
        assert reg.companies[0].industry == ["SaaS"]
        assert reg.companies[0].location == "NYC"

    def test_add_person_dedup(self):
        reg = EntityRegistry()
        reg.add_person("John Doe", role="CEO")
        reg.add_person("John Doe", affiliations=["company:acme"])
        assert len(reg.people) == 1
        assert reg.people[0].role == "CEO"
        assert reg.people[0].affiliations == ["company:acme"]


# ── Unit: Investment serialisation ───────────────────────────────────────────

class TestInvestmentSerialisation:
    def test_round_trip(self):
        inv = Investment(
            title="Test raise",
            summary="Summary",
            date="2026-01-01",
            round="Seed",
            amount=Amount(5_000_000),
            sources=[Source(url="https://ex.com", publisher="Ex")],
            tags=["funding"],
        )
        d = inv.to_dict()
        assert d["id"] == "investment:test-raise"
        assert d["type"] == "investment"
        assert d["amount"]["value"] == 5_000_000
        assert len(d["sources"]) == 1


# ── Unit: NewsletterData envelope ────────────────────────────────────────────

class TestNewsletterData:
    def test_to_dict_structure(self):
        nd = NewsletterData()
        d = nd.to_dict()
        assert "metadata" in d
        assert "entities" in d
        assert "content" in d
        assert "newsletterDraftPlan" in d
        assert "companies" in d["entities"]
        assert "people" in d["entities"]
        assert "events" in d["content"]
        assert "investments" in d["content"]


# ── Integration: build real data ─────────────────────────────────────────────

class TestBuildRealData:
    @pytest.fixture(scope="class")
    def data(self):
        return _build_real_data()

    @pytest.fixture(scope="class")
    def payload(self, data):
        return data.to_dict()

    def test_has_8_investments(self, payload):
        assert len(payload["content"]["investments"]) == 8

    def test_has_8_events(self, payload):
        assert len(payload["content"]["events"]) == 8

    def test_has_5_accelerators(self, payload):
        assert len(payload["content"]["accelerators"]) == 5

    def test_companies_not_empty(self, payload):
        assert len(payload["entities"]["companies"]) > 0

    def test_people_not_empty(self, payload):
        assert len(payload["entities"]["people"]) > 0

    def test_all_investments_have_sources(self, payload):
        for inv in payload["content"]["investments"]:
            assert len(inv["sources"]) >= 1, f"{inv['id']} missing sources"

    def test_all_events_have_sources(self, payload):
        for ev in payload["content"]["events"]:
            assert len(ev["sources"]) >= 1, f"{ev['id']} missing sources"

    def test_investment_ids_unique(self, payload):
        ids = [i["id"] for i in payload["content"]["investments"]]
        assert len(ids) == len(set(ids))

    def test_company_ids_unique(self, payload):
        ids = [c["id"] for c in payload["entities"]["companies"]]
        assert len(ids) == len(set(ids))

    def test_entity_refs_resolve(self, payload):
        """Every id referenced in entityRefs should exist in entities."""
        company_ids = {c["id"] for c in payload["entities"]["companies"]}
        person_ids = {p["id"] for p in payload["entities"]["people"]}
        all_ids = company_ids | person_ids

        for section in ("investments", "events", "accelerators"):
            for item in payload["content"].get(section, []):
                refs = item.get("entityRefs", {})
                for ref_list in refs.values():
                    for ref_id in ref_list:
                        assert ref_id in all_ids, (
                            f"{item['id']} references '{ref_id}' which is not in entities"
                        )


# ── Integration: validation ──────────────────────────────────────────────────

class TestValidation:
    def test_valid_real_data(self):
        data = _build_real_data()
        errors = validate(data.to_dict())
        assert errors == [], f"Validation errors: {errors}"

    def test_missing_metadata(self):
        bad = {"entities": {"companies": [], "people": []}, "content": {"events": [], "investments": []}, "newsletterDraftPlan": {"audience": "", "tone": "", "sections": []}}
        errors = validate(bad)
        assert any("metadata" in e for e in errors)

    def test_missing_sources(self):
        bad = _build_real_data().to_dict()
        bad["content"]["investments"][0]["sources"] = []
        errors = validate(bad)
        assert len(errors) > 0


# ── Integration: write + read ────────────────────────────────────────────────

class TestWriter:
    def test_write_and_read(self):
        data = _build_real_data()
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "out.json")
            write_json(data, path)
            assert os.path.exists(path)
            with open(path) as f:
                loaded = json.load(f)
            assert loaded["metadata"]["version"] == "1.0.0"
            assert len(loaded["content"]["investments"]) == 8
