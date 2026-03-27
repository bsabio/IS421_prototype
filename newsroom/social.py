"""Social media snippet generation for funding stories."""

from __future__ import annotations

import re
from typing import Dict, List

from .models import FundingItem


def _shorten(text: str, limit: int) -> str:
    compact = re.sub(r"\s+", " ", (text or "").strip())
    if len(compact) <= limit:
        return compact
    return compact[: max(0, limit - 1)].rstrip() + "…"


def _hashtags(item: FundingItem) -> str:
    base = ["#AI", "#Startups", "#VentureCapital"]
    extra = []
    for category in (item.categories or [])[:2]:
        tag = re.sub(r"[^a-zA-Z0-9]", "", category.title())
        if tag:
            extra.append(f"#{tag}")
    deduped = []
    for tag in base + extra:
        if tag not in deduped:
            deduped.append(tag)
    return " ".join(deduped[:5])


def generate_story_snippets(item: FundingItem) -> Dict[str, object]:
    """Generate a 3-part X thread + LinkedIn post for one funding item."""
    q = item.who_what_why_when_where_how
    headline = item.title or f"{item.startup_name} funding update"

    thread = [
        _shorten(
            f"{headline} — {item.startup_name} announced {item.amount} {item.round_type} funding in {item.location or 'the Tri-State ecosystem'}. {_hashtags(item)}",
            280,
        ),
        _shorten(
            f"Why it matters: {q.why or 'The raise gives the team runway to execute product and go-to-market milestones over the next 12-18 months.'}",
            280,
        ),
        _shorten(
            f"What to watch: {q.how or 'Track hiring, enterprise pilots, and follow-on customer traction.'} Founders/students: what question would you ask this team next?",
            280,
        ),
    ]

    linkedin_post = _shorten(
        (
            f"Funding signal: {headline}. "
            f"{q.who or item.startup_name} secured {item.amount} ({item.round_type}). "
            f"The strategic angle is {q.why or 'scaling product execution with disciplined capital deployment'}. "
            f"For operators and investors, this is a useful indicator for category momentum in {item.location or 'the region'}. "
            f"{_hashtags(item)}"
        ),
        1200,
    )

    return {
        "x_thread": thread,
        "linkedin_post": linkedin_post,
    }


def generate_social_snippets(funding_items: List[FundingItem]) -> Dict[str, Dict[str, object]]:
    """Generate snippets keyed by normalized startup name."""
    snippets: Dict[str, Dict[str, object]] = {}
    for item in funding_items:
        key = re.sub(r"[^a-z0-9]+", "-", (item.startup_name or "story").strip().lower()).strip("-")
        if not key:
            key = "story"
        if key in snippets:
            key = f"{key}-{len(snippets) + 1}"
        snippets[key] = generate_story_snippets(item)
    return snippets
