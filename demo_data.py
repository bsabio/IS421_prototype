"""
Demo data generator - Creates sample data for testing the newsletter pipeline
Usage: python demo_data.py
"""
import json
from pathlib import Path
from datetime import datetime
from newsroom.models import FundingItem, EventItem, AcceleratorItem, WHOWHATWHYStructure


def create_demo_funding_items():
    """Create sample funding items"""
    items = [
        FundingItem(
            title="Acme AI raises $15M Series A to build autonomous agents",
            startup_name="Acme AI",
            round_type="series-a",
            amount="$15M",
            amount_numeric=15_000_000,
            investors=["Venture Partners", "Tech Fund", "Angel Investors"],
            lead_investor="Venture Partners",
            location="New York",
            announced_date="2026-02-05",
            source_urls=[
                "https://techcrunch.com/2026/02/05/acme-ai-raises-15m-series-a",
                "https://alleywatch.com/2026/02/acme-ai-funding"
            ],
            evidence_snippets=[
                "Acme AI announced today it has raised $15 million in Series A funding",
                "The round was led by Venture Partners with participation from Tech Fund",
                "Company plans to use funds to expand engineering team"
            ],
            categories=["Ai Ml"],
            who_what_why_when_where_how=WHOWHATWHYStructure(
                who="Acme AI, led by Venture Partners",
                what="Raised $15M in series-a round from Venture Partners, Tech Fund, Angel Investors",
                why="Building autonomous AI agents for enterprise automation and expanding engineering team",
                when="Announced 2026-02-05",
                where="Based in New York",
                how="Secured funding through series-a round led by top-tier VC firm Venture Partners"
            ),
            confidence_notes=[]
        ),
        FundingItem(
            title="PayFlow secures $8M seed round for fintech platform",
            startup_name="PayFlow",
            round_type="seed",
            amount="$8M",
            amount_numeric=8_000_000,
            investors=["NYC Ventures", "Fintech Capital"],
            lead_investor="NYC Ventures",
            location="Brooklyn",
            announced_date="2026-02-04",
            source_urls=[
                "https://alleywatch.com/2026/02/04/payflow-seed-funding"
            ],
            evidence_snippets=[
                "Brooklyn-based PayFlow raised $8 million in seed funding",
                "NYC Ventures led the round with participation from Fintech Capital"
            ],
            categories=["Fintech"],
            who_what_why_when_where_how=WHOWHATWHYStructure(
                who="PayFlow, led by NYC Ventures",
                what="Raised $8M in seed round from NYC Ventures, Fintech Capital",
                why="Developing next-generation payment infrastructure for small businesses",
                when="Announced 2026-02-04",
                where="Based in Brooklyn",
                how="Secured seed funding from NYC-focused venture capital firms"
            ),
            confidence_notes=[]
        ),
        FundingItem(
            title="HealthTech startup MediCare raises $20M Series B",
            startup_name="MediCare",
            round_type="series-b",
            amount="$20M",
            amount_numeric=20_000_000,
            investors=["Health Ventures", "Impact Capital", "Strategic Investors"],
            lead_investor="Health Ventures",
            location="Manhattan",
            announced_date="2026-02-03",
            source_urls=[
                "https://techcrunch.com/2026/02/03/medicare-series-b-20m"
            ],
            evidence_snippets=[
                "MediCare announced $20 million Series B round",
                "Health Ventures led the investment with strong participation"
            ],
            categories=["Health"],
            who_what_why_when_where_how=WHOWHATWHYStructure(
                who="MediCare, led by Health Ventures",
                what="Raised $20M in series-b round from Health Ventures, Impact Capital, Strategic Investors",
                why="Expanding telemedicine platform to reach underserved communities nationwide",
                when="Announced 2026-02-03",
                where="Based in Manhattan",
                how="Secured Series B from leading healthcare-focused investors"
            ),
            confidence_notes=[]
        ),
        FundingItem(
            title="EdTech platform LearnNow raises $5M seed",
            startup_name="LearnNow",
            round_type="seed",
            amount="$5M",
            amount_numeric=5_000_000,
            investors=["Education Fund", "Angel Network"],
            lead_investor="Education Fund",
            location="New York",
            announced_date="2026-02-02",
            source_urls=[
                "https://techcrunch.com/2026/02/02/learnnow-seed-round"
            ],
            evidence_snippets=[
                "LearnNow raised $5 million seed round to transform education"
            ],
            categories=["Edtech"],
            who_what_why_when_where_how=WHOWHATWHYStructure(
                who="LearnNow, led by Education Fund",
                what="Raised $5M in seed round from Education Fund, Angel Network",
                why="Building AI-powered personalized learning platform for K-12 students",
                when="Announced 2026-02-02",
                where="Based in New York",
                how="Secured seed funding from education-focused investors"
            ),
            confidence_notes=[]
        ),
        FundingItem(
            title="CyberShield raises $12M Series A for cybersecurity platform",
            startup_name="CyberShield",
            round_type="series-a",
            amount="$12M",
            amount_numeric=12_000_000,
            investors=["Security Ventures", "Tech Capital", "Industry Investors"],
            lead_investor="Security Ventures",
            location="New York",
            announced_date="2026-02-01",
            source_urls=[
                "https://techcrunch.com/2026/02/01/cybershield-series-a"
            ],
            evidence_snippets=[
                "CyberShield announced $12M Series A for next-gen security"
            ],
            categories=["Cybersecurity"],
            who_what_why_when_where_how=WHOWHATWHYStructure(
                who="CyberShield, led by Security Ventures",
                what="Raised $12M in series-a round from Security Ventures, Tech Capital, Industry Investors",
                why="Developing AI-powered threat detection and response platform for enterprises",
                when="Announced 2026-02-01",
                where="Based in New York",
                how="Secured Series A from top cybersecurity investors"
            ),
            confidence_notes=[]
        )
    ]
    return items


def create_demo_event_items():
    """Create sample event items"""
    return [
        EventItem(
            event_name="NYC Founders & Funders Meetup",
            date_time="Feb 15, 2026 6:00 PM",
            city="NYC",
            venue_or_online="The Yard - Lower East Side",
            cost="Free",
            audience="Founders, VCs, Angels",
            registration_url="https://garysguide.com/events/founders-meetup-feb",
            source_url="https://garysguide.com/events/founders-meetup-feb",
            description="Monthly networking event for NYC tech founders and investors"
        ),
        EventItem(
            event_name="AI Agents Summit 2026",
            date_time="Feb 20, 2026 9:00 AM",
            city="Manhattan",
            venue_or_online="Convene - 117 West 46th St",
            cost="$295",
            audience="AI builders, investors, founders",
            registration_url="https://garysguide.com/events/ai-summit-2026",
            source_url="https://garysguide.com/events/ai-summit-2026",
            description="Full-day conference on building autonomous AI agent companies"
        ),
        EventItem(
            event_name="FinTech Happy Hour",
            date_time="Feb 18, 2026 5:30 PM",
            city="Brooklyn",
            venue_or_online="Industry City",
            cost="Free",
            audience="Fintech founders, engineers",
            registration_url=None,
            source_url="https://garysguide.com/events/fintech-happy-hour",
            description="Casual networking for Brooklyn fintech community"
        ),
        EventItem(
            event_name="Demo Day: TechStars NYC Winter 2026",
            date_time="Feb 25, 2026 3:00 PM",
            city="Manhattan",
            venue_or_online="TechStars Office",
            cost="Invite Only",
            audience="Investors, press, founders",
            registration_url=None,
            source_url="https://garysguide.com/events/techstars-demo-day",
            description="TechStars Winter 2026 cohort presenting to investors"
        ),
        EventItem(
            event_name="Office Hours with NYC VCs",
            date_time="Every Thursday in February",
            city="NYC",
            venue_or_online="Online via Zoom",
            cost="Free",
            audience="Pre-seed and seed stage founders",
            registration_url="https://garysguide.com/events/vc-office-hours",
            source_url="https://garysguide.com/events/vc-office-hours",
            description="Weekly office hours with rotating NYC venture capital partners"
        )
    ]


def create_demo_accelerator_items():
    """Create sample accelerator items"""
    return [
        AcceleratorItem(
            name="TechStars NYC",
            city_region="New York, NY",
            focus="General Tech",
            source_url="https://openvc.app/accelerators/techstars-nyc",
            description="World's most active pre-seed investor. 13-week mentorship-driven program.",
            application_url="https://techstars.com/accelerators/nyc"
        ),
        AcceleratorItem(
            name="Y Combinator",
            city_region="Mountain View, CA (accepts NYC startups)",
            focus="All sectors",
            source_url="https://openvc.app/accelerators/yc",
            description="$500K for 7% equity. 3-month program ending in Demo Day.",
            application_url="https://ycombinator.com/apply"
        ),
        AcceleratorItem(
            name="Entrepreneur First NYC",
            city_region="New York, NY",
            focus="Deep tech, AI",
            source_url="https://openvc.app/accelerators/ef-nyc",
            description="Pre-team accelerator for exceptional individuals building deep tech companies.",
            application_url="https://joinef.com"
        ),
        AcceleratorItem(
            name="ERA (Entrepreneur Roundtable Accelerator)",
            city_region="New York, NY",
            focus="B2B, SaaS, Marketplaces",
            source_url="https://openvc.app/accelerators/era",
            description="$100K investment for 6% equity. NYC's largest accelerator.",
            application_url="https://era.co"
        ),
        AcceleratorItem(
            name="Columbia Startup Lab",
            city_region="New York, NY",
            focus="Columbia-affiliated founders",
            source_url="https://openvc.app/accelerators/columbia",
            description="Free office space and mentorship for Columbia founders.",
            application_url="https://startuplab.columbia.edu"
        ),
        AcceleratorItem(
            name="Blueprint Health",
            city_region="New York, NY",
            focus="Healthcare IT",
            source_url="https://openvc.app/accelerators/blueprint",
            description="Healthcare-focused accelerator with $20K investment and extensive mentor network.",
            application_url="https://blueprint.health"
        )
    ]


def main():
    print("=== Creating Demo Data ===")
    print()
    
    # Create demo items
    funding_items = create_demo_funding_items()
    event_items = create_demo_event_items()
    accelerator_items = create_demo_accelerator_items()
    
    print(f"Created {len(funding_items)} funding items")
    print(f"Created {len(event_items)} event items")
    print(f"Created {len(accelerator_items)} accelerator items")
    
    # Create data directory
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    
    # Save as ranked.json (skip earlier pipeline steps)
    ranked_data = {
        'funding': [item.to_dict() for item in funding_items],
        'events': [item.to_dict() for item in event_items],
        'accelerators': [item.to_dict() for item in accelerator_items],
        'trend_brief': {
            'Ai Ml': 1,
            'Fintech': 1,
            'Health': 1,
            'Edtech': 1,
            'Cybersecurity': 1
        },
        'ranked_at': datetime.now().isoformat()
    }
    
    ranked_file = data_dir / 'ranked.json'
    with open(ranked_file, 'w', encoding='utf-8') as f:
        json.dump(ranked_data, f, indent=2, ensure_ascii=False)
    
    print()
    print(f"✓ Demo data saved to: {ranked_file}")
    print()
    print("Now run: python -m newsroom.render --format md")
    print("To generate the newsletter!")


if __name__ == '__main__':
    main()
