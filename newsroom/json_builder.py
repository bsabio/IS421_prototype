"""
Newsletter JSON Builder – mapper, normaliser, validator, writer.

Usage:
    python -m newsroom.json_builder          # build from real newsletter data
    python -m newsroom.json_builder --validate data/newsletter_data.json
"""
from __future__ import annotations

import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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
    _now_iso,
    _slug,
)


# ── Validator ────────────────────────────────────────────────────────────────

def _load_json_schema() -> Dict[str, Any]:
    schema_path = Path(__file__).parent / "newsletter_schema.json"
    with open(schema_path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate(data: Dict[str, Any]) -> List[str]:
    """
    Validate *data* against newsletter_schema.json.
    Returns a list of error strings (empty == valid).
    Uses jsonschema if installed, otherwise falls back to structural checks.
    """
    errors: List[str] = []
    try:
        import jsonschema  # type: ignore
        schema = _load_json_schema()
        v = jsonschema.Draft7Validator(schema)
        for err in sorted(v.iter_errors(data), key=lambda e: list(e.absolute_path)):
            path = ".".join(str(p) for p in err.absolute_path) or "(root)"
            errors.append(f"{path}: {err.message}")
    except ImportError:
        errors.extend(_structural_validate(data))
    return errors


def _structural_validate(data: Dict[str, Any]) -> List[str]:
    """Lightweight fallback when jsonschema is not installed."""
    errors: List[str] = []

    for key in ("metadata", "entities", "content", "newsletterDraftPlan"):
        if key not in data:
            errors.append(f"(root): missing required key '{key}'")

    meta = data.get("metadata", {})
    for mk in ("generatedAt", "timeWindow", "version"):
        if mk not in meta:
            errors.append(f"metadata: missing '{mk}'")

    entities = data.get("entities", {})
    for ek in ("companies", "people"):
        if ek not in entities:
            errors.append(f"entities: missing '{ek}'")

    content = data.get("content", {})
    for ck in ("events", "investments"):
        if ck not in content:
            errors.append(f"content: missing '{ck}'")

    # Check every content item has id, type, title, summary, sources
    for section_name in ("events", "investments", "articles", "resources", "accelerators"):
        for idx, item in enumerate(content.get(section_name, [])):
            prefix = f"content.{section_name}[{idx}]"
            for rk in ("id", "type", "title", "summary", "sources"):
                if rk not in item:
                    errors.append(f"{prefix}: missing '{rk}'")
            if "sources" in item and len(item["sources"]) == 0:
                errors.append(f"{prefix}.sources: must have at least 1 source")

    # Check entity ids
    for idx, c in enumerate(entities.get("companies", [])):
        if "id" not in c or not c["id"].startswith("company:"):
            errors.append(f"entities.companies[{idx}]: id must start with 'company:'")
    for idx, p in enumerate(entities.get("people", [])):
        if "id" not in p or not p["id"].startswith("person:"):
            errors.append(f"entities.people[{idx}]: id must start with 'person:'")

    plan = data.get("newsletterDraftPlan", {})
    for pk in ("audience", "tone", "sections"):
        if pk not in plan:
            errors.append(f"newsletterDraftPlan: missing '{pk}'")

    return errors


# ── Entity registry (deduplication) ──────────────────────────────────────────

class EntityRegistry:
    """Collects and deduplicates companies and people by slug."""

    def __init__(self) -> None:
        self._companies: Dict[str, Company] = {}
        self._people: Dict[str, Person] = {}

    # -- companies --
    def add_company(self, name: str, **kwargs: Any) -> str:
        cid = f"company:{_slug(name)}"
        if cid not in self._companies:
            self._companies[cid] = Company(name=name, id=cid, **kwargs)
        else:
            # merge non-empty fields
            existing = self._companies[cid]
            for k, v in kwargs.items():
                if v and not getattr(existing, k, None):
                    setattr(existing, k, v)
        return cid

    # -- people --
    def add_person(self, name: str, **kwargs: Any) -> str:
        pid = f"person:{_slug(name)}"
        if pid not in self._people:
            self._people[pid] = Person(name=name, id=pid, **kwargs)
        else:
            existing = self._people[pid]
            for k, v in kwargs.items():
                if v and not getattr(existing, k, None):
                    setattr(existing, k, v)
        return pid

    @property
    def companies(self) -> List[Company]:
        return list(self._companies.values())

    @property
    def people(self) -> List[Person]:
        return list(self._people.values())


# ── Real data builder ────────────────────────────────────────────────────────

def _build_real_data() -> NewsletterData:
    """
    Build the canonical JSON from the real, verified newsletter data
    (AlleyWatch funding, Gary's Guide events, verified accelerators).
    """
    reg = EntityRegistry()
    retrieved = "2026-02-10T12:00:00+00:00"

    # ── Companies (startups) ───────────────────────────────────────────────
    reg.add_company("Cubby", industry=["PropTech", "AI"], location="New York, NY")
    reg.add_company("ORION Security", industry=["Cybersecurity", "AI"], location="New York, NY")
    reg.add_company("BoldVoice", industry=["EdTech", "AI"], location="New York, NY")
    reg.add_company("Concourse", industry=["FinTech", "AI"], location="New York, NY")
    reg.add_company("Limy", industry=["AI", "Commerce"], location="New York, NY")
    reg.add_company("Flock AI", industry=["AI", "E-Commerce"], location="New York, NY")
    reg.add_company("Nerd Apply", industry=["EdTech"], location="New York, NY")
    reg.add_company("ALCOVE", industry=["Workspace", "Hospitality"], location="Brooklyn, NY")

    # ── Companies (investors / accelerators) ───────────────────────────────
    reg.add_company("Goldman Sachs Alternatives", industry=["Finance"])
    reg.add_company("Norwest", industry=["Venture Capital"])
    reg.add_company("Matrix", industry=["Venture Capital"])
    reg.add_company("Standard Capital", industry=["Venture Capital"])
    reg.add_company("Flybridge", industry=["Venture Capital"])
    reg.add_company("Work-Bench", industry=["Venture Capital"])
    reg.add_company("Riverpark Ventures", industry=["Venture Capital"])
    reg.add_company("Techstars", industry=["Accelerator"], location="New York, NY")
    reg.add_company("ERA", aliases=["Entrepreneurs Roundtable Accelerator"], industry=["Accelerator"], location="New York, NY")
    reg.add_company("Entrepreneur First", aliases=["EF"], industry=["Accelerator"], location="London / New York / Bangalore / SF")
    reg.add_company("NYU Tandon Future Labs", industry=["Incubator"], location="Brooklyn, NY")
    reg.add_company("Blueprint Health", industry=["Accelerator"], location="New York, NY")

    # ── People ─────────────────────────────────────────────────────────────
    reg.add_person("Matt Engfer", role="CEO", affiliations=["company:cubby"])
    reg.add_person("Nitay Milner", role="CEO", affiliations=["company:orion-security"])
    reg.add_person("Anada Lakra", role="CEO", affiliations=["company:boldvoice"])
    reg.add_person("Matthieu Hafemeister", role="CEO", affiliations=["company:concourse"])
    reg.add_person("Aviv Shamny", role="CEO", affiliations=["company:limy"])
    reg.add_person("Manvitha Mallela", role="CEO", affiliations=["company:flock-ai"])
    reg.add_person("Braden Weissman", role="Cofounder", affiliations=["company:nerd-apply"])
    reg.add_person("Cooper Weissman", role="Cofounder", affiliations=["company:nerd-apply"])
    reg.add_person("Helen Knight", role="CEO", affiliations=["company:alcove"])
    reg.add_person("Andres Barreto", role="Managing Director", affiliations=["company:techstars"])

    # ── Investments ────────────────────────────────────────────────────────
    _aw = lambda slug: Source(
        url=f"https://www.alleywatch.com/2026/{slug}",
        publisher="AlleyWatch",
        retrievedAt=retrieved,
        confidence=0.95,
    )

    investments = [
        Investment(
            title="Cubby raises $63M Series A",
            summary="AI-native platform for self-storage operators integrating facility management, revenue optimization, and Voice AI. Serves 400+ operators managing 450,000 units across North America.",
            date="2026-02-04",
            round="Series A",
            amount=Amount(63_000_000),
            entityRefs=EntityRefs(
                companies=["company:cubby"],
                people=["person:matt-engfer"],
                investors=["company:goldman-sachs-alternatives"],
            ),
            sources=[_aw("02/cubby-storage-self-storage-software-ai-facility-management-revenue-management-platform-operating-system-matt-engfer/")],
            tags=["funding", "proptech", "ai"],
        ),
        Investment(
            title="ORION Security raises $32M Series A",
            summary="Uses 5 proprietary AI agents to prevent data leaks without security policies. 96% reduction in false positives. Fortune 500 customers within first 5 months.",
            date="2026-02-06",
            round="Series A",
            amount=Amount(32_000_000),
            entityRefs=EntityRefs(
                companies=["company:orion-security"],
                people=["person:nitay-milner"],
                investors=["company:norwest"],
            ),
            sources=[_aw("02/orion-security-ata-loss-prevention-autonomous-dlp-contextual-security-policy-free-nitay-milner/")],
            tags=["funding", "cybersecurity", "ai"],
        ),
        Investment(
            title="BoldVoice raises $21M Series A",
            summary="AI-powered voice coaching for non-native English speakers. 5M+ downloads, $10M+ ARR, professionals in 150+ countries. Team of just 7 employees.",
            date="2026-01-29",
            round="Series A",
            amount=Amount(21_000_000),
            entityRefs=EntityRefs(
                companies=["company:boldvoice"],
                people=["person:anada-lakra"],
                investors=["company:matrix"],
            ),
            sources=[_aw("01/boldvoice-ai-accent-non-native-english-coaching-pronunciation-training-platform-anada-lakra/")],
            tags=["funding", "edtech", "ai"],
        ),
        Investment(
            title="Concourse raises $12M Series A",
            summary="Enterprise AI agents for finance teams. Connects to ERPs, billing, and data warehouses. 19x revenue growth in past year.",
            date="2026-02-05",
            round="Series A",
            amount=Amount(12_000_000),
            entityRefs=EntityRefs(
                companies=["company:concourse"],
                people=["person:matthieu-hafemeister"],
                investors=["company:standard-capital"],
            ),
            sources=[_aw("02/concourse-finance-automation-platform-enterprise-ai-erp-software-integration-analysis-agentic-matthieu-hafemeister/")],
            tags=["funding", "fintech", "ai"],
        ),
        Investment(
            title="Limy raises $10M Seed",
            summary="Agentic web infrastructure helping brands control visibility in AI-driven commerce. Fortune 100 customers including AstraZeneca, Samsung, KIA.",
            date="2026-01-30",
            round="Seed",
            amount=Amount(10_000_000),
            entityRefs=EntityRefs(
                companies=["company:limy"],
                people=["person:aviv-shamny"],
                investors=["company:flybridge"],
            ),
            sources=[_aw("01/limy-agentic-web-infrastructure-attribution-seo-product-commerce-platform-aviv-shamny/")],
            tags=["funding", "ai", "commerce"],
        ),
        Investment(
            title="Flock AI raises $6M Seed",
            summary="AI visual commerce platform generating diverse product imagery across every body type. 90% cost savings vs photoshoots, 30%+ conversion lift.",
            date="2026-02-10",
            round="Seed",
            amount=Amount(6_000_000),
            entityRefs=EntityRefs(
                companies=["company:flock-ai"],
                people=["person:manvitha-mallela"],
                investors=["company:work-bench"],
            ),
            sources=[_aw("02/flock-ai-ai-visual-commerce-personalized-product-imagery-conversion-optimization-manvitha-mallela/")],
            tags=["funding", "ai", "ecommerce"],
        ),
        Investment(
            title="Nerd Apply raises $3.2M Seed",
            summary="Privacy-first data platform for college counselors. Aggregates 100,000+ de-identified admissions outcomes across 500+ organizations.",
            date="2026-01-27",
            round="Seed",
            amount=Amount(3_200_000),
            entityRefs=EntityRefs(
                companies=["company:nerd-apply"],
                people=["person:braden-weissman", "person:cooper-weissman"],
                investors=["company:riverpark-ventures"],
            ),
            sources=[_aw("01/nerd-apply-college-counseling-platform-admissions-outcomes-data-braden-weissman-cooper-weissman/")],
            tags=["funding", "edtech"],
        ),
        Investment(
            title="ALCOVE raises $1M Pre-Seed",
            summary="Premium soundproofed Pods in hotels and neighborhoods. $18/hr, no membership. 1,200+ guests, 10,000+ hours. Partnerships with Hilton, Hyatt, Fairmont.",
            date="2026-02-09",
            round="Pre-Seed",
            amount=Amount(1_000_000),
            entityRefs=EntityRefs(
                companies=["company:alcove"],
                people=["person:helen-knight"],
                investors=[],
            ),
            sources=[_aw("02/alcove-private-workspace-pods-on-demand-soundproof-remote-work-helen-knight/")],
            tags=["funding", "workspace", "hospitality"],
        ),
    ]

    # ── Events ─────────────────────────────────────────────────────────────
    _gg = lambda url: Source(url=url, publisher="Gary's Guide", retrievedAt=retrieved, confidence=0.9)

    events = [
        Event(
            title="AI Interfaces Hackathon w/ Claude",
            summary="Build AI interfaces with Anthropic's Claude. Co-hosted by Anthropic and AI Tinkerers. Hackathon format with prizes.",
            startDate="2026-02-21T09:00:00-05:00",
            location=Location(city="New York", state="NY", country="US"),
            topics=["AI", "Hackathon"],
            cost="Free",
            registrationUrl="http://gary.to/hie5lxh",
            sources=[_gg("http://gary.to/hie5lxh")],
            tags=["hackathon", "ai"],
        ),
        Event(
            title="Startup Fundraising Summit — By Investors, For Founders",
            summary="With Dorothy Chang (Flybridge Capital), Will McKelvey (Lerer Hippeau), Marina Girgis (Precursor Ventures), and more. A Gary's Guide featured event.",
            startDate="2026-02-19T13:00:00-05:00",
            location=Location(city="New York", state="NY", country="US"),
            topics=["Fundraising", "VC"],
            cost="Free",
            sources=[_gg("https://www.garysguide.com/events?region=nyc")],
            tags=["summit", "fundraising"],
        ),
        Event(
            title="AI Engineers Presents — Devs & Drinks",
            summary="Networking with hiring teams from Suno, Graphite, Tennr, FLORA, Metropolis, OpenRouter, and more.",
            startDate="2026-02-26T18:00:00-05:00",
            location=Location(city="New York", state="NY", country="US"),
            topics=["AI", "Networking"],
            cost="Free",
            registrationUrl="http://gary.to/gzulxix",
            sources=[_gg("http://gary.to/gzulxix")],
            tags=["networking", "ai"],
        ),
        Event(
            title="Female Founders Forum",
            summary="With Elizabeth Cutler (SoulCycle & Peoplehood), Melissa Mash (Dagne Dover), Caroline Huber (Jones), and investor panelists from Upfront, Type Capital, Antler VC, NY Ventures.",
            startDate="2026-02-13T13:00:00-05:00",
            location=Location(city="New York", state="NY", country="US"),
            topics=["Founders", "Diversity"],
            cost="Free",
            sources=[_gg("https://www.garysguide.com/events?region=nyc")],
            tags=["forum", "founders"],
        ),
        Event(
            title="Cybersecurity Summit",
            summary="With Deidre Diamond (CyberSN), Stephen Craig (NY Presbyterian), Igor Lasic (ReversingLabs), Jeff Steadman (The Identity At The Center).",
            startDate="2026-02-25T08:00:00-05:00",
            location=Location(city="New York", state="NY", country="US", venue="Sheraton Times Sq, 811 7th Ave"),
            topics=["Cybersecurity"],
            cost="Paid",
            sources=[_gg("https://www.garysguide.com/events?region=nyc")],
            tags=["summit", "cybersecurity"],
        ),
        Event(
            title="AI Trivia Night",
            summary="Trivia night co-hosted by OpenAI and SignalFire. A fun way to network with the AI community in NYC.",
            startDate="2026-02-19T19:30:00-05:00",
            location=Location(city="New York", state="NY", country="US"),
            topics=["AI", "Social"],
            cost="Free",
            sources=[_gg("https://www.garysguide.com/events?region=nyc")],
            tags=["social", "ai"],
        ),
        Event(
            title="NYC Coffee Club — Early-Stage B2B Founders & Funders",
            summary="Morning coffee networking with Forum Ventures & Zeal Capital Partners. For early-stage B2B founders and funders.",
            startDate="2026-02-20T10:00:00-05:00",
            location=Location(city="New York", state="NY", country="US"),
            topics=["Networking", "B2B"],
            cost="Free",
            registrationUrl="http://gary.to/m6utxzp",
            sources=[_gg("http://gary.to/m6utxzp")],
            tags=["networking", "b2b"],
        ),
        Event(
            title="AI Hot 100 Summit",
            summary="The who's who of enterprise AI. 150+ AI execs, 100+ AI founders, 100+ VC partners & AI labs. Themes: voice AI, financial services, healthcare, retail, agentic infrastructure.",
            startDate="2026-05-07T09:00:00-04:00",
            location=Location(city="New York", state="NY", country="US", venue="Civic Hall, 124 E 14th St"),
            topics=["AI", "Enterprise"],
            cost="Paid",
            registrationUrl="http://gary.to/w06u04e",
            sources=[_gg("http://gary.to/w06u04e")],
            tags=["summit", "ai", "enterprise"],
        ),
    ]

    # ── Accelerators ───────────────────────────────────────────────────────
    accelerators = [
        Accelerator(
            title="Techstars NYC",
            summary="$220K investment ($200K uncapped MFN SAFE + $20K CEA for 5% common stock). Hybrid 3-month program with $2M+ in partner perks. MD: Andres Barreto. Next cohort starts March 9, 2026; Demo Day June 4, 2026. Notable alumni: ClassPass, GlossGenius, Bluecore, Gorgias.",
            location=Location(city="New York", state="NY", country="US"),
            focus=["AI/ML", "FinTech", "HealthTech", "Climate", "Enterprise SaaS"],
            terms="$220K for 5% common stock + uncapped MFN SAFE",
            entityRefs=EntityRefs(companies=["company:techstars"], people=["person:andres-barreto"]),
            sources=[Source(url="https://www.techstars.com/accelerators/nyc", publisher="Techstars", retrievedAt=retrieved, confidence=1.0)],
            tags=["accelerator"],
        ),
        Accelerator(
            title="Entrepreneurs Roundtable Accelerator (ERA)",
            summary="$150K on a post-money SAFE for 6% equity. 4-month program, now in its 30th cohort (Winter 2026 with 15 companies). 400+ startups invested, alumni have raised $2B+ with $10B+ in market cap. 500+ mentors.",
            location=Location(city="New York", state="NY", country="US"),
            focus=["B2B SaaS", "AI", "FinTech", "Enterprise"],
            terms="$150K for 6% equity (post-money SAFE)",
            entityRefs=EntityRefs(companies=["company:era"]),
            sources=[Source(url="https://www.eranyc.com/2026/01/12/nycs-era-entrepreneurs-roundtable-accelerator-announces-participants-winter-2026-program-companies-receive-150000-investments-post-money-safe/", publisher="ERA NYC", retrievedAt=retrieved, confidence=1.0)],
            tags=["accelerator"],
        ),
        Accelerator(
            title="Entrepreneur First (EF)",
            summary="Pre-team accelerator: equity-free grant while ideating, up to $250K investment when you form a company, up to $5M follow-on through Series B. $600K+ in credits (Azure, OpenAI, Anthropic). Portfolio worth $13B+.",
            location=Location(city="London / New York / Bangalore / SF", state="", country="Global"),
            focus=["Deep Tech", "AI/ML", "Hard Tech"],
            terms="Equity-free grant + up to $250K investment + up to $5M follow-on",
            entityRefs=EntityRefs(companies=["company:entrepreneur-first"]),
            sources=[Source(url="https://www.joinef.com/", publisher="Entrepreneur First", retrievedAt=retrieved, confidence=1.0)],
            tags=["accelerator"],
        ),
        Accelerator(
            title="NYU Tandon Future Labs",
            summary="Public-private partnership with NYC & NYSERDA. Free incubator space across 3 labs: Data Future Lab, Urban Future Lab, Veterans Future Lab. Programs include Catalyst NYC (6-month mentorship), ACRE (cleantech), Keystone (8-week crash course). 200+ graduates, $4.1B economic impact, 3,200+ jobs created.",
            location=Location(city="Brooklyn", state="NY", country="US", venue="370 Jay St & 87 35th St"),
            focus=["AI", "Clean Energy", "Smart Cities", "Cybersecurity", "HealthTech"],
            terms="Free (no equity taken)",
            entityRefs=EntityRefs(companies=["company:nyu-tandon-future-labs"]),
            sources=[Source(url="https://futurelabs.nyc/", publisher="NYU Tandon Future Labs", retrievedAt=retrieved, confidence=1.0)],
            tags=["incubator"],
        ),
        Accelerator(
            title="Blueprint Health",
            summary="3-month healthcare-focused accelerator for 6% equity. Strong clinical mentor network with 1,000+ companies vetted annually. Alumni include Healthie, AdhereTech, Health Recovery Solutions, Touch Surgery. Also runs Junto Health consortium.",
            location=Location(city="New York", state="NY", country="US"),
            focus=["Healthcare IT", "Digital Health"],
            terms="6% equity",
            entityRefs=EntityRefs(companies=["company:blueprint-health"]),
            sources=[Source(url="https://www.blueprinthealth.org/", publisher="Blueprint Health", retrievedAt=retrieved, confidence=0.85)],
            tags=["accelerator", "healthcare"],
        ),
    ]

    # ── Draft plan ─────────────────────────────────────────────────────────
    plan = NewsletterDraftPlan(
        audience="builders + students + founders in NYC tech",
        tone="concise, practical, hype-free",
        format="web newsletter + optional multi-page PDF",
        sections=[
            SectionPlan("Funding Headlines", "Rank investments by amount descending; show company, amount, round, lead investor, and 2-sentence summary."),
            SectionPlan("Trend Brief", "Count investments by primary industry tag; render as category tiles with deal counts."),
            SectionPlan("Events & Rooms to Be In", "Chronological list of upcoming events with date, venue, cost, and 1-2 line why-attend."),
            SectionPlan("Accelerators Watch", "List active accelerators with terms, focus, and application deadlines."),
            SectionPlan("People to Follow", "Highlight founders and investors from high-confidence sources."),
            SectionPlan("Sources & Bibliography", "Numbered footnotes linking every claim to its source URL."),
        ],
        aiWriterInstructions=[
            "Use metadata.timeWindow for the intro line.",
            "For each item, cite sources as footnotes/links.",
            "Prefer concrete numbers and dates; avoid speculation.",
            "End with 2-3 calls-to-action (subscribe, submit a deal/event).",
            "Group funding by round type (Series A, Seed, Pre-Seed) in descending order.",
            "For events, bold the date and include registration links where available.",
        ],
    )

    # ── Assemble ───────────────────────────────────────────────────────────
    return NewsletterData(
        metadata=Metadata(
            generatedAt=_now_iso(),
            timeWindow_start="2026-01-27T00:00:00-05:00",
            timeWindow_end="2026-02-12T23:59:59-05:00",
            region=["US", "NYC"],
            version="1.0.0",
            description="Canonical dataset for IS421 NYC tech newsletter – Feb 2026 edition",
            pipeline="offline-aggregator",
            notes="Built from verified AlleyWatch, Gary's Guide, and accelerator program websites.",
        ),
        companies=reg.companies,
        people=reg.people,
        events=events,
        investments=investments,
        accelerators=accelerators,
        draftPlan=plan,
    )


# ── Writer ───────────────────────────────────────────────────────────────────

def write_json(data: NewsletterData, output_path: str) -> str:
    """Serialise *data* to pretty-printed JSON at *output_path*. Returns path."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = data.to_dict()
    with open(out, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    return str(out.resolve())


# ── CLI ──────────────────────────────────────────────────────────────────────

def main() -> None:
    root = Path(__file__).resolve().parent.parent
    output = root / "data" / "newsletter_data.json"

    if len(sys.argv) > 1 and sys.argv[1] == "--validate":
        # Validate an existing file
        target = sys.argv[2] if len(sys.argv) > 2 else str(output)
        print(f"Validating {target} …")
        with open(target, "r", encoding="utf-8") as f:
            payload = json.load(f)
        errors = validate(payload)
        if errors:
            print(f"INVALID – {len(errors)} error(s):")
            for e in errors:
                print(f"  ✗ {e}")
            sys.exit(1)
        else:
            print("✓ Valid")
            sys.exit(0)

    # Build
    print("Building newsletter JSON …")
    data = _build_real_data()
    path = write_json(data, str(output))
    print(f"Wrote {path}")

    # Validate
    with open(path, "r", encoding="utf-8") as f:
        payload = json.load(f)
    errors = validate(payload)
    if errors:
        print(f"WARNING – {len(errors)} validation error(s):")
        for e in errors:
            print(f"  ✗ {e}")
        sys.exit(1)
    else:
        # Summary stats
        ent = payload["entities"]
        con = payload["content"]
        print(f"✓ Valid  |  {len(ent['companies'])} companies  |  {len(ent['people'])} people  |  "
              f"{len(con['investments'])} investments  |  {len(con['events'])} events  |  "
              f"{len(con.get('accelerators', []))} accelerators")


if __name__ == "__main__":
    main()
