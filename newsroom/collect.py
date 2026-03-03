"""
Collection module - CLI entry point for fetching raw sources
Usage: python -m newsroom.collect --source mock --since 7d

PROTOTYPE MODE: Uses mock data by default for class demos.
  --source mock  = Load from data/mock/*.json (default, for development)
  --source real  = Fetch from actual websites (TODO: implement after class)
"""
import argparse
from pathlib import Path
import json
from datetime import datetime
from typing import Dict, List
import re

import requests
from bs4 import BeautifulSoup
from .sources import collect_all_sources
from .utils import load_config, ensure_directories
from .models import FundingItem, EventItem, AcceleratorItem


def parse_since(since_str: str) -> int:
    """
    Parse --since argument to days
    Examples: 7d, 14d, 1d
    """
    if since_str.endswith('d'):
        return int(since_str[:-1])
    return int(since_str)


def _fetch_html(url: str, timeout: int = 12) -> str:
    try:
        resp = requests.get(
            url,
            timeout=timeout,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            },
        )
        resp.raise_for_status()
        return resp.text
    except Exception:
        return ""


def _extract_garys_guide_events(limit: int = 10) -> List[EventItem]:
    html = _fetch_html("https://www.garysguide.com/events")
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    items: List[EventItem] = []
    seen = set()

    month_re = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*"
    date_re = re.compile(rf"({month_re}\s+\d{{1,2}}(?:,\s*\d{{4}})?(?:\s+\d{{1,2}}:\d{{2}}\s*(?:AM|PM))?)", re.IGNORECASE)

    for anchor in soup.find_all("a", href=True):
        href = anchor["href"].strip()
        title = anchor.get_text(" ", strip=True)
        if not title or len(title) < 8:
            continue
        if "event" not in href.lower() and "events" not in href.lower():
            continue

        full_url = href if href.startswith("http") else f"https://www.garysguide.com{href}"
        surrounding = " ".join(anchor.parent.get_text(" ", strip=True).split()) if anchor.parent else ""
        m = date_re.search(surrounding)
        date_text = m.group(1) if m else ""

        key = (title.lower(), date_text.lower())
        if key in seen:
            continue
        seen.add(key)

        items.append(
            EventItem(
                event_name=title,
                date_time=date_text or None,
                city="NYC",
                venue_or_online="NYC / Online",
                cost="See listing",
                audience="founders, builders, investors",
                registration_url=full_url,
                source_url=full_url,
                description="Curated from Gary's Guide events listing.",
            )
        )
        if len(items) >= limit:
            break

    return items


def _extract_meetup_events(limit: int = 10) -> List[EventItem]:
    html = _fetch_html("https://www.meetup.com/find/events/?allMeetups=true&keywords=ai%20startup&location=us--ny--New%20York")
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    items: List[EventItem] = []
    seen = set()

    for anchor in soup.find_all("a", href=True):
        href = anchor["href"].strip()
        if "meetup.com" not in href.lower() or "/events/" not in href.lower():
            continue

        title = " ".join(anchor.get_text(" ", strip=True).split())
        if not title or len(title) < 8:
            continue

        parent_text = ""
        if anchor.parent:
            parent_text = " ".join(anchor.parent.get_text(" ", strip=True).split())

        date_match = re.search(
            r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2}(?:,\s*\d{4})?(?:\s+\d{1,2}:\d{2}\s*(?:AM|PM))?)",
            parent_text,
            re.IGNORECASE,
        )
        date_text = date_match.group(1) if date_match else ""

        key = (title.lower(), href.lower())
        if key in seen:
            continue
        seen.add(key)

        items.append(
            EventItem(
                event_name=title,
                date_time=date_text or None,
                city="NYC",
                venue_or_online="Meetup listing",
                cost="See listing",
                audience="founders, builders, investors",
                registration_url=href,
                source_url=href,
                description="Curated from Meetup event search.",
            )
        )
        if len(items) >= limit:
            break

    return items


def _merge_live_events(existing: List[EventItem], live: List[EventItem]) -> List[EventItem]:
    merged = list(existing)
    keys = {
        (item.event_name.strip().lower(), (item.date_time or "").strip().lower())
        for item in merged
    }

    for item in live:
        key = (item.event_name.strip().lower(), (item.date_time or "").strip().lower())
        if key in keys:
            continue
        keys.add(key)
        merged.append(item)

    return merged


def load_mock_data(config: Dict) -> Dict:
    """
    Load mock data from JSON files (PROTOTYPE MODE)
    
    This is the primary mode for development and class demos.
    Mock data is already in normalized format, so we skip collection
    and normalization steps entirely.
    
    TODO (FUTURE): Replace with real scrapers after class presentation
    - TechCrunch RSS/API integration
    - AlleyWatch scraper
    - Gary's Guide API
    - Live accelerator directory feeds
    """
    print("📦 MOCK MODE: Loading pre-formatted data from /data/mock/")
    print("   (This is prototype mode - real scrapers will come later)")
    print()
    
    base_dir = Path(__file__).parent.parent
    mock_dir = base_dir / "data" / "mock"
    
    if not mock_dir.exists():
        print(f"⚠️ Mock data directory not found: {mock_dir}")
        print("   Falling back to data/ranked.json for prototype mode.")

        ranked_file = base_dir / "data" / "ranked.json"
        if ranked_file.exists():
            with open(ranked_file, 'r', encoding='utf-8') as f:
                ranked = json.load(f)

            funding_items = [FundingItem.from_dict(item) for item in ranked.get('funding', [])]
            event_items = [EventItem.from_dict(item) for item in ranked.get('events', [])]
            accelerator_items = [AcceleratorItem.from_dict(item) for item in ranked.get('accelerators', [])]

            try:
                garys_events = _extract_garys_guide_events(limit=8)
                meetup_events = _extract_meetup_events(limit=8)
                live_events = garys_events + meetup_events
                if live_events:
                    before = len(event_items)
                    event_items = _merge_live_events(event_items, live_events)
                    added = len(event_items) - before
                    if added > 0:
                        print(f"   ✓ Added {added} live events from Gary's Guide / Meetup")
            except Exception:
                pass

            print(f"   ✓ Loaded {len(funding_items)} funding items from ranked.json")
            print(f"   ✓ Loaded {len(event_items)} event items from ranked.json (+ live)")
            print(f"   ✓ Loaded {len(accelerator_items)} accelerator items from ranked.json")

            return {
                'funding': funding_items,
                'events': event_items,
                'accelerators': accelerator_items,
            }

        print("   No fallback ranked.json found.")
        return {'funding': [], 'events': [], 'accelerators': []}
    
    # Load funding items
    funding_file = mock_dir / "funding.json"
    funding_items = []
    if funding_file.exists():
        with open(funding_file, 'r') as f:
            data = json.load(f)
            funding_items = [FundingItem.from_dict(item) for item in data]
            print(f"   ✓ Loaded {len(funding_items)} funding items")
    
    # Load event items
    events_file = mock_dir / "events.json"
    event_items = []
    if events_file.exists():
        with open(events_file, 'r') as f:
            data = json.load(f)
            event_items = [EventItem.from_dict(item) for item in data]
            print(f"   ✓ Loaded {len(event_items)} event items")

    # Add live event fallbacks from Gary's Guide and Meetup (best-effort)
    try:
        garys_events = _extract_garys_guide_events(limit=8)
        meetup_events = _extract_meetup_events(limit=8)
        live_events = garys_events + meetup_events
        if live_events:
            before = len(event_items)
            event_items = _merge_live_events(event_items, live_events)
            added = len(event_items) - before
            if added > 0:
                print(f"   ✓ Added {added} live events from Gary's Guide / Meetup")
    except Exception:
        pass
    
    # Load accelerator items
    accelerators_file = mock_dir / "accelerators.json"
    accelerator_items = []
    if accelerators_file.exists():
        with open(accelerators_file, 'r') as f:
            data = json.load(f)
            accelerator_items = [AcceleratorItem.from_dict(item) for item in data]
            print(f"   ✓ Loaded {len(accelerator_items)} accelerator items")
    
    return {
        'funding': funding_items,
        'events': event_items,
        'accelerators': accelerator_items
    }


def main():
    parser = argparse.ArgumentParser(
        description='Collect raw sources for newsletter (PROTOTYPE: uses mock data by default)'
    )
    parser.add_argument(
        '--source',
        type=str,
        default='mock',
        choices=['mock', 'real'],
        help='Data source: mock (default, from JSON files) or real (web scraping - TODO)'
    )
    parser.add_argument(
        '--since',
        type=str,
        default='7d',
        help='Time range to collect (e.g., 7d for 7 days) - only used for real sources'
    )
    
    args = parser.parse_args()
    
    # Load config
    config = load_config()
    ensure_directories()
    
    print(f"=== AI Factory Newsletter - Collection ===")
    print(f"Mode: {args.source.upper()}")
    print()
    
    if args.source == 'mock':
        # PROTOTYPE MODE: Load mock data (already normalized)
        all_items = load_mock_data(config)
        
        # Save directly to deduped.json (skip normalization step)
        data_dir = Path(config['storage']['data_dir'])
        
        deduped_data = {
            'funding': [item.to_dict() for item in all_items['funding']],
            'events': [item.to_dict() for item in all_items['events']],
            'accelerators': [item.to_dict() for item in all_items['accelerators']],
            'deduped_at': datetime.now().isoformat(),
            'source': 'mock'
        }
        
        deduped_file = data_dir / 'deduped.json'
        with open(deduped_file, 'w', encoding='utf-8') as f:
            json.dump(deduped_data, f, indent=2, ensure_ascii=False)
        
        print()
        print(f"=== Collection Complete (Mock Mode) ===")
        print(f"✓ Data saved to: {deduped_file}")
        print()
        print("📊 PROTOTYPE: Mock data is already normalized and deduped.")
        print("   Skip to: python3 -m newsroom.rank")
        print()
        print("💡 TIP: Edit data/mock/*.json to customize your newsletter content")
        
    else:
        # REAL MODE: Scrape websites (TODO: implement after class)
        print("⚠️  REAL SOURCE MODE - NOT YET IMPLEMENTED")
        print()
        print("This mode will be implemented after the class presentation.")
        print("It will include:")
        print("  - TechCrunch RSS/API scraping")
        print("  - AlleyWatch HTML parsing")
        print("  - Gary's Guide event scraping")
        print("  - OpenVC accelerator directory")
        print()
        print("For now, use: --source mock (default)")
        
        # TODO: Uncomment when real scrapers are ready
        # days_back = parse_since(args.since)
        # all_sources = collect_all_sources(config, days_back)
        # ... (existing real collection code)


if __name__ == '__main__':
    main()
