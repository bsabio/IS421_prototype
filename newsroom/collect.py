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
from typing import Dict
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
        print(f"❌ Mock data directory not found: {mock_dir}")
        print("   Run demo_data.py first or create mock data files.")
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
