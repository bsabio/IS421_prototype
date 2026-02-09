"""
Deduplication module - Merge duplicate items across sources
Usage: python -m newsroom.dedupe
"""
import json
from pathlib import Path
from typing import List, Dict
from datetime import datetime
from collections import defaultdict

from .models import FundingItem, EventItem, AcceleratorItem
from .utils import load_config, generate_item_hash


def dedupe_funding_items(items: List[FundingItem]) -> List[FundingItem]:
    """
    Deduplicate funding items by URL and normalized title
    Merge source URLs and evidence from duplicates
    """
    print(f"Deduplicating {len(items)} funding items...")
    
    # Group by hash
    groups = defaultdict(list)
    
    for item in items:
        # Generate hash for each source URL
        for url in item.source_urls:
            item_hash = generate_item_hash(url, item.title)
            groups[item_hash].append(item)
    
    # Also group by startup name similarity
    name_groups = defaultdict(list)
    for item in items:
        normalized_name = item.startup_name.lower().strip()
        name_groups[normalized_name].append(item)
    
    # Merge duplicates
    deduped = []
    seen_names = set()
    
    for normalized_name, group_items in name_groups.items():
        if normalized_name in seen_names:
            continue
        
        if len(group_items) == 1:
            deduped.append(group_items[0])
            seen_names.add(normalized_name)
        else:
            # Merge items with same startup name
            merged = merge_funding_items(group_items)
            deduped.append(merged)
            seen_names.add(normalized_name)
    
    print(f"Deduplicated to {len(deduped)} unique funding items")
    return deduped


def merge_funding_items(items: List[FundingItem]) -> FundingItem:
    """
    Merge multiple FundingItems into one, keeping all sources
    """
    if len(items) == 1:
        return items[0]
    
    # Use the most complete item as base
    base = max(items, key=lambda x: len(x.source_urls) + len(x.investors))
    
    # Merge source URLs
    all_urls = set()
    for item in items:
        all_urls.update(item.source_urls)
    base.source_urls = sorted(list(all_urls))
    
    # Merge investors
    all_investors = set(base.investors)
    for item in items:
        all_investors.update(item.investors)
    base.investors = sorted(list(all_investors))
    
    # Keep lead investor from item with most info
    if not base.lead_investor:
        for item in items:
            if item.lead_investor:
                base.lead_investor = item.lead_investor
                break
    
    # Merge evidence snippets
    all_snippets = set(base.evidence_snippets)
    for item in items:
        all_snippets.update(item.evidence_snippets)
    base.evidence_snippets = list(all_snippets)[:5]  # Keep top 5
    
    # Merge categories
    all_categories = set(base.categories)
    for item in items:
        all_categories.update(item.categories)
    base.categories = sorted(list(all_categories))
    
    # Use best amount (non-zero)
    if base.amount_numeric == 0:
        for item in items:
            if item.amount_numeric > 0:
                base.amount = item.amount
                base.amount_numeric = item.amount_numeric
                break
    
    # Use best round type (not unknown)
    if base.round_type == "unknown":
        for item in items:
            if item.round_type != "unknown":
                base.round_type = item.round_type
                break
    
    # Add merge note
    base.confidence_notes.append(f"Merged from {len(items)} sources")
    
    return base


def dedupe_event_items(items: List[EventItem]) -> List[EventItem]:
    """
    Deduplicate event items by event name and date
    """
    print(f"Deduplicating {len(items)} event items...")
    
    # Group by normalized name
    groups = defaultdict(list)
    
    for item in items:
        normalized_name = item.event_name.lower().strip()
        key = f"{normalized_name}_{item.date_time}"
        groups[key].append(item)
    
    # Take first of each group
    deduped = []
    for group_items in groups.values():
        deduped.append(group_items[0])
    
    print(f"Deduplicated to {len(deduped)} unique event items")
    return deduped


def dedupe_accelerator_items(items: List[AcceleratorItem]) -> List[AcceleratorItem]:
    """
    Deduplicate accelerator items by name
    """
    print(f"Deduplicating {len(items)} accelerator items...")
    
    # Group by normalized name
    groups = defaultdict(list)
    
    for item in items:
        normalized_name = item.name.lower().strip()
        groups[normalized_name].append(item)
    
    # Take most complete of each group
    deduped = []
    for group_items in groups.values():
        # Pick item with most info
        best = max(group_items, key=lambda x: bool(x.city_region) + bool(x.focus) + len(x.description))
        deduped.append(best)
    
    print(f"Deduplicated to {len(deduped)} unique accelerator items")
    return deduped


def main():
    print("=== AI Factory Newsletter - Deduplication ===")
    print("Merging duplicate items across sources...")
    print()
    
    config = load_config()
    data_dir = Path(config['storage']['data_dir'])
    
    # Load normalized data
    normalized_file = data_dir / 'normalized.json'
    
    if not normalized_file.exists():
        print("No normalized data found. Run: python -m newsroom.normalize first")
        return
    
    with open(normalized_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Convert to objects
    funding_items = [FundingItem.from_dict(item) for item in data.get('funding', [])]
    event_items = [EventItem.from_dict(item) for item in data.get('events', [])]
    accelerator_items = [AcceleratorItem.from_dict(item) for item in data.get('accelerators', [])]
    
    print(f"Loaded:")
    print(f"  - {len(funding_items)} funding items")
    print(f"  - {len(event_items)} event items")
    print(f"  - {len(accelerator_items)} accelerator items")
    print()
    
    # Deduplicate
    deduped_funding = dedupe_funding_items(funding_items)
    deduped_events = dedupe_event_items(event_items)
    deduped_accelerators = dedupe_accelerator_items(accelerator_items)
    
    print()
    print("Deduplication complete!")
    
    # Save deduped data
    deduped_data = {
        'funding': [item.to_dict() for item in deduped_funding],
        'events': [item.to_dict() for item in deduped_events],
        'accelerators': [item.to_dict() for item in deduped_accelerators],
        'deduped_at': datetime.now().isoformat()
    }
    
    deduped_file = data_dir / 'deduped.json'
    with open(deduped_file, 'w', encoding='utf-8') as f:
        json.dump(deduped_data, f, indent=2, ensure_ascii=False)
    
    print(f"Deduped data saved to: {deduped_file}")
    print()
    print("Next step: python -m newsroom.rank")


if __name__ == '__main__':
    main()
