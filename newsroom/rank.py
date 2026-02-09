"""
Ranking module - Rank and sort items for newsletter
Usage: python -m newsroom.rank
"""
import json
from pathlib import Path
from typing import List, Dict
from datetime import datetime
from collections import Counter

from .models import FundingItem, EventItem, AcceleratorItem
from .utils import load_config, get_round_priority, get_source_credibility


def rank_funding_items(items: List[FundingItem], config: Dict) -> List[FundingItem]:
    """
    Rank funding items by:
    1. Disclosed amount (descending)
    2. Round importance (series-c > series-b > series-a > seed)
    3. Source credibility
    """
    print(f"Ranking {len(items)} funding items...")
    
    def funding_score(item: FundingItem) -> tuple:
        """
        Calculate ranking score (returns tuple for sorting)
        Higher values = higher priority
        """
        # Amount score (primary)
        amount_score = item.amount_numeric
        
        # Round priority score
        round_score = get_round_priority(item.round_type)
        
        # Source credibility (average if multiple sources)
        credibility_scores = [get_source_credibility(url) for url in item.source_urls]
        avg_credibility = sum(credibility_scores) / len(credibility_scores) if credibility_scores else 0
        
        # NYC bonus (if location matches)
        nyc_bonus = 1 if item.location and 'new york' in item.location.lower() else 0
        
        # Return tuple for sorting (descending)
        return (amount_score, round_score, avg_credibility, nyc_bonus)
    
    # Sort by score (descending)
    ranked = sorted(items, key=funding_score, reverse=True)
    
    # Limit to max items from config
    max_items = config['limits']['funding_items']
    ranked = ranked[:max_items]
    
    print(f"Ranked and limited to top {len(ranked)} funding items")
    return ranked


def rank_event_items(items: List[EventItem], config: Dict) -> List[EventItem]:
    """
    Rank event items by:
    1. Date (upcoming first)
    2. NYC preference
    3. Target audience
    """
    print(f"Ranking {len(items)} event items...")
    
    # Filter by city
    primary_city = config['search']['primary_city']
    include_cities = config['search']['include_cities']
    
    filtered = []
    for item in items:
        if item.city:
            city_lower = item.city.lower()
            if any(c.lower() in city_lower for c in include_cities):
                filtered.append(item)
        else:
            # Include if city not specified
            filtered.append(item)
    
    # Simple sorting: free events first, then by name
    def event_score(item: EventItem) -> tuple:
        free_score = 1 if item.cost.lower() == 'free' else 0
        return (free_score, item.event_name.lower())
    
    ranked = sorted(filtered, key=event_score, reverse=True)
    
    # Limit to max items
    max_items = config['limits']['event_items']
    ranked = ranked[:max_items]
    
    print(f"Ranked and limited to top {len(ranked)} event items")
    return ranked


def rank_accelerator_items(items: List[AcceleratorItem], config: Dict) -> List[AcceleratorItem]:
    """
    Rank accelerator items by:
    1. NYC location preference
    2. Focus area relevance
    """
    print(f"Ranking {len(items)} accelerator items...")
    
    def accelerator_score(item: AcceleratorItem) -> tuple:
        nyc_score = 1 if item.city_region and 'new york' in item.city_region.lower() else 0
        has_focus = 1 if item.focus else 0
        return (nyc_score, has_focus, item.name.lower())
    
    ranked = sorted(items, key=accelerator_score, reverse=True)
    
    # Limit to max items
    max_items = config['limits']['accelerator_items']
    ranked = ranked[:max_items]
    
    print(f"Ranked and limited to top {len(ranked)} accelerator items")
    return ranked


def generate_trend_brief(funding_items: List[FundingItem]) -> Dict[str, int]:
    """
    Generate category trend brief (top categories and counts)
    """
    print("Generating category trends...")
    
    category_counts = Counter()
    
    for item in funding_items:
        for category in item.categories:
            category_counts[category] += 1
    
    # Get top 5 categories
    top_categories = dict(category_counts.most_common(5))
    
    print(f"Top categories: {', '.join(top_categories.keys())}")
    return top_categories


def main():
    print("=== AI Factory Newsletter - Ranking ===")
    print("Ranking items for newsletter...")
    print()
    
    config = load_config()
    data_dir = Path(config['storage']['data_dir'])
    
    # Load deduped data
    deduped_file = data_dir / 'deduped.json'
    
    if not deduped_file.exists():
        print("No deduped data found. Run: python -m newsroom.dedupe first")
        return
    
    with open(deduped_file, 'r', encoding='utf-8') as f:
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
    
    # Rank items
    ranked_funding = rank_funding_items(funding_items, config)
    ranked_events = rank_event_items(event_items, config)
    ranked_accelerators = rank_accelerator_items(accelerator_items, config)
    
    # Generate trend brief
    trend_brief = generate_trend_brief(ranked_funding)
    
    print()
    print("Ranking complete!")
    
    # Save ranked data
    ranked_data = {
        'funding': [item.to_dict() for item in ranked_funding],
        'events': [item.to_dict() for item in ranked_events],
        'accelerators': [item.to_dict() for item in ranked_accelerators],
        'trend_brief': trend_brief,
        'ranked_at': datetime.now().isoformat()
    }
    
    ranked_file = data_dir / 'ranked.json'
    with open(ranked_file, 'w', encoding='utf-8') as f:
        json.dump(ranked_data, f, indent=2, ensure_ascii=False)
    
    print(f"Ranked data saved to: {ranked_file}")
    print()
    print("Next step: python -m newsroom.render --format md")


if __name__ == '__main__':
    main()
