"""
Canonical data types for the newsletter JSON contract.

These dataclasses mirror the JSON Schema in newsletter_schema.json.
All fields use plain Python types so the objects serialise with json.dumps().
"""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# ── helpers ──────────────────────────────────────────────────────────────────

def _slug(text: str) -> str:
    """Turn arbitrary text into a URL-safe slug."""
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Source ───────────────────────────────────────────────────────────────────

@dataclass
class Source:
    url: str
    publisher: str
    retrievedAt: str = ""          # ISO-8601
    confidence: Optional[float] = None  # 0.0 – 1.0

    def __post_init__(self):
        if not self.retrievedAt:
            self.retrievedAt = _now_iso()

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "url": self.url,
            "publisher": self.publisher,
            "retrievedAt": self.retrievedAt,
        }
        if self.confidence is not None:
            d["confidence"] = self.confidence
        return d


# ── Entities ─────────────────────────────────────────────────────────────────

@dataclass
class Company:
    name: str
    id: str = ""
    aliases: List[str] = field(default_factory=list)
    industry: List[str] = field(default_factory=list)
    location: str = ""
    links: List[str] = field(default_factory=list)
    sources: List[Source] = field(default_factory=list)

    def __post_init__(self):
        if not self.id:
            self.id = f"company:{_slug(self.name)}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "aliases": self.aliases,
            "industry": self.industry,
            "location": self.location,
            "links": self.links,
            "sources": [s.to_dict() for s in self.sources],
        }


@dataclass
class Person:
    name: str
    id: str = ""
    role: str = ""
    affiliations: List[str] = field(default_factory=list)
    socials: Dict[str, str] = field(default_factory=dict)
    sources: List[Source] = field(default_factory=list)

    def __post_init__(self):
        if not self.id:
            self.id = f"person:{_slug(self.name)}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role,
            "affiliations": self.affiliations,
            "socials": self.socials,
            "sources": [s.to_dict() for s in self.sources],
        }


# ── Entity refs ──────────────────────────────────────────────────────────────

@dataclass
class EntityRefs:
    companies: List[str] = field(default_factory=list)
    people: List[str] = field(default_factory=list)
    investors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"companies": self.companies, "people": self.people}
        if self.investors:
            d["investors"] = self.investors
        return d


# ── Location ─────────────────────────────────────────────────────────────────

@dataclass
class Location:
    city: str = ""
    state: str = ""
    country: str = "US"
    venue: str = ""
    isOnline: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ── Amount ───────────────────────────────────────────────────────────────────

@dataclass
class Amount:
    value: float
    currency: str = "USD"
    approximate: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ── Content items ────────────────────────────────────────────────────────────

@dataclass
class Event:
    title: str
    summary: str
    sources: List[Source]
    id: str = ""
    type: str = "event"
    startDate: str = ""
    endDate: Optional[str] = None
    location: Location = field(default_factory=Location)
    topics: List[str] = field(default_factory=list)
    cost: str = "Free"
    registrationUrl: Optional[str] = None
    entityRefs: EntityRefs = field(default_factory=EntityRefs)
    tags: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.id:
            self.id = f"event:{_slug(self.title)}"

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "id": self.id,
            "type": self.type,
            "title": self.title,
            "summary": self.summary,
            "startDate": self.startDate,
            "endDate": self.endDate,
            "location": self.location.to_dict(),
            "topics": self.topics,
            "cost": self.cost,
            "entityRefs": self.entityRefs.to_dict(),
            "sources": [s.to_dict() for s in self.sources],
            "tags": self.tags,
        }
        if self.registrationUrl:
            d["registrationUrl"] = self.registrationUrl
        return d


@dataclass
class Investment:
    title: str
    summary: str
    sources: List[Source]
    id: str = ""
    type: str = "investment"
    date: str = ""
    round: str = ""
    amount: Amount = field(default_factory=lambda: Amount(0))
    entityRefs: EntityRefs = field(default_factory=EntityRefs)
    tags: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.id:
            self.id = f"investment:{_slug(self.title)}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "title": self.title,
            "summary": self.summary,
            "date": self.date,
            "round": self.round,
            "amount": self.amount.to_dict(),
            "entityRefs": self.entityRefs.to_dict(),
            "sources": [s.to_dict() for s in self.sources],
            "tags": self.tags,
        }


@dataclass
class Article:
    title: str
    summary: str
    sources: List[Source]
    id: str = ""
    type: str = "article"
    publishedAt: str = ""
    entityRefs: EntityRefs = field(default_factory=EntityRefs)
    tags: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.id:
            self.id = f"article:{_slug(self.title)}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "title": self.title,
            "summary": self.summary,
            "publishedAt": self.publishedAt,
            "entityRefs": self.entityRefs.to_dict(),
            "sources": [s.to_dict() for s in self.sources],
            "tags": self.tags,
        }


@dataclass
class Resource:
    title: str
    summary: str
    sources: List[Source]
    id: str = ""
    type: str = "resource"
    url: str = ""
    entityRefs: EntityRefs = field(default_factory=EntityRefs)
    tags: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.id:
            self.id = f"resource:{_slug(self.title)}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "title": self.title,
            "summary": self.summary,
            "url": self.url,
            "entityRefs": self.entityRefs.to_dict(),
            "sources": [s.to_dict() for s in self.sources],
            "tags": self.tags,
        }


@dataclass
class Accelerator:
    title: str
    summary: str
    sources: List[Source]
    id: str = ""
    type: str = "accelerator"
    location: Location = field(default_factory=Location)
    focus: List[str] = field(default_factory=list)
    terms: str = ""
    entityRefs: EntityRefs = field(default_factory=EntityRefs)
    tags: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.id:
            self.id = f"accelerator:{_slug(self.title)}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "title": self.title,
            "summary": self.summary,
            "location": self.location.to_dict(),
            "focus": self.focus,
            "terms": self.terms,
            "entityRefs": self.entityRefs.to_dict(),
            "sources": [s.to_dict() for s in self.sources],
            "tags": self.tags,
        }


# ── Draft plan ───────────────────────────────────────────────────────────────

@dataclass
class SectionPlan:
    title: str
    logic: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class NewsletterDraftPlan:
    audience: str = "builders + students + founders"
    tone: str = "concise, practical, hype-free"
    format: str = "web newsletter + optional multi-page PDF"
    sections: List[SectionPlan] = field(default_factory=list)
    aiWriterInstructions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "audience": self.audience,
            "tone": self.tone,
            "format": self.format,
            "sections": [s.to_dict() for s in self.sections],
            "aiWriterInstructions": self.aiWriterInstructions,
        }


# ── Top-level envelope ──────────────────────────────────────────────────────

@dataclass
class Metadata:
    generatedAt: str = ""
    timeWindow_start: str = ""
    timeWindow_end: str = ""
    region: List[str] = field(default_factory=lambda: ["US"])
    version: str = "1.0.0"
    description: str = "Canonical dataset for newsletter generation"
    pipeline: str = "offline-aggregator"
    runId: str = ""
    notes: str = ""

    def __post_init__(self):
        if not self.generatedAt:
            self.generatedAt = _now_iso()
        if not self.runId:
            self.runId = str(uuid.uuid4())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "generatedAt": self.generatedAt,
            "timeWindow": {
                "start": self.timeWindow_start,
                "end": self.timeWindow_end,
            },
            "region": self.region,
            "version": self.version,
            "description": self.description,
            "provenance": {
                "pipeline": self.pipeline,
                "runId": self.runId,
                "notes": self.notes,
            },
        }


@dataclass
class NewsletterData:
    """Root object – serialises to the canonical JSON contract."""
    metadata: Metadata = field(default_factory=Metadata)
    companies: List[Company] = field(default_factory=list)
    people: List[Person] = field(default_factory=list)
    events: List[Event] = field(default_factory=list)
    investments: List[Investment] = field(default_factory=list)
    articles: List[Article] = field(default_factory=list)
    resources: List[Resource] = field(default_factory=list)
    accelerators: List[Accelerator] = field(default_factory=list)
    draftPlan: NewsletterDraftPlan = field(default_factory=NewsletterDraftPlan)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metadata": self.metadata.to_dict(),
            "entities": {
                "companies": [c.to_dict() for c in self.companies],
                "people":    [p.to_dict() for p in self.people],
            },
            "content": {
                "events":       [e.to_dict() for e in self.events],
                "investments":  [i.to_dict() for i in self.investments],
                "articles":     [a.to_dict() for a in self.articles],
                "resources":    [r.to_dict() for r in self.resources],
                "accelerators": [a.to_dict() for a in self.accelerators],
            },
            "newsletterDraftPlan": self.draftPlan.to_dict(),
        }
