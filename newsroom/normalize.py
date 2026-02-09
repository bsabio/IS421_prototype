"""
Normalization module - Extract structured data from raw HTML
Usage: python -m newsroom.normalize
"""
import json
import re
from pathlib import Path
from bs4 import BeautifulSoup
from typing import List, Dict
from datetime import datetime

from .models import (
    FundingItem, EventItem, AcceleratorItem, RawSource,
    WHOWHATWHYStructure, save_items_to_json
)
from .utils import (
    load_config, parse_amount, normalize_round_type,
    extract_startup_name, categorize_content, truncate_snippet
)


class FundingNormalizer:
    """Normalize funding articles to FundingItem"""
    
    def __init__(self, config: Dict):
        self.config = config
    
    def normalize(self, raw_source: RawSource) -> List[FundingItem]:
        """Extract FundingItems from raw source"""
        soup = BeautifulSoup(raw_source.html_content, 'html.parser')
        
        # Extract basic info
        title = self._extract_title(soup)
        content = self._extract_content(soup)
        
        if not title or not content:
            return []
        
        # Check if it's a funding story
        if not self._is_funding_story(title, content):
            return []
        
        # Extract funding details
        item = self._extract_funding_details(
            title, content, raw_source.url, raw_source.source_name
        )
        
        if item:
            return [item]
        return []
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract article title"""
        title_tag = soup.find('h1')
        if not title_tag:
            title_tag = soup.find('title')
        return title_tag.get_text(strip=True) if title_tag else ""
    
    def _extract_content(self, soup: BeautifulSoup) -> str:
        """Extract article content"""
        # Try multiple content selectors
        selectors = [
            {'name': 'div', 'attrs': {'class': 'article-content'}},
            {'name': 'div', 'attrs': {'class': 'entry-content'}},
            {'name': 'article'},
            {'name': 'main'},
        ]
        
        for selector in selectors:
            content_tag = soup.find(**selector)
            if content_tag:
                return content_tag.get_text(separator=' ', strip=True)
        
        # Fallback to body
        body = soup.find('body')
        return body.get_text(separator=' ', strip=True) if body else ""
    
    def _is_funding_story(self, title: str, content: str) -> bool:
        """Check if this is a funding story"""
        combined = (title + " " + content).lower()
        
        funding_keywords = [
            'raise', 'raised', 'raises', 'funding', 'investment',
            'seed', 'series a', 'series b', 'series c',
            'million', 'billion', 'round', 'capital', 'investors'
        ]
        
        return any(keyword in combined for keyword in funding_keywords)
    
    def _extract_funding_details(
        self, title: str, content: str, url: str, source_name: str
    ) -> FundingItem:
        """Extract detailed funding information"""
        
        # Extract startup name
        startup_name = self._extract_startup_name_from_text(title, content)
        
        # Extract amount
        amount_str, amount_numeric = self._extract_amount(title, content)
        
        # Extract round type
        round_type = self._extract_round_type(title, content)
        
        # Extract investors
        investors, lead_investor = self._extract_investors(content)
        
        # Extract location
        location = self._extract_location(content)
        
        # Extract date
        announced_date = self._extract_date(url, content)
        
        # Categorize
        categories = categorize_content(title + " " + content, self.config)
        
        # Extract evidence snippets
        snippets = self._extract_evidence_snippets(content)
        
        # Build WHO/WHAT/WHY structure
        wwwwwh = self._build_wwwwwh(
            startup_name, amount_str, round_type, investors,
            lead_investor, location, announced_date, content
        )
        
        # Confidence notes
        confidence_notes = []
        if not amount_numeric:
            confidence_notes.append("Amount undisclosed")
        if round_type == "unknown":
            confidence_notes.append("Round type inferred")
        if not investors:
            confidence_notes.append("Investors not found in text")
        
        return FundingItem(
            title=title,
            startup_name=startup_name,
            round_type=round_type,
            amount=amount_str,
            investors=investors,
            lead_investor=lead_investor,
            location=location,
            announced_date=announced_date,
            source_urls=[url],
            evidence_snippets=snippets,
            tags=[],
            categories=categories,
            who_what_why_when_where_how=wwwwwh,
            amount_numeric=amount_numeric,
            confidence_notes=confidence_notes
        )
    
    def _extract_startup_name_from_text(self, title: str, content: str) -> str:
        """Extract startup name from title/content"""
        # Look for patterns like "Startup raises" or "Startup secures"
        patterns = [
            r'^([A-Z][a-zA-Z0-9]+(?:\s+[A-Z][a-zA-Z0-9]+)*)\s+(?:raises|raised|secures|secured|closes)',
            r'^([A-Z][a-zA-Z0-9]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, title)
            if match:
                return match.group(1)
        
        return extract_startup_name(title)
    
    def _extract_amount(self, title: str, content: str) -> tuple[str, float]:
        """Extract funding amount"""
        combined = title + " " + content[:500]
        
        # Look for amount patterns
        patterns = [
            r'\$(\d+(?:\.\d+)?)\s*(million|billion|M|B)',
            r'(\d+(?:\.\d+)?)\s*(million|billion)',
            r'\$(\d+(?:\.\d+)?)M',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, combined, re.IGNORECASE)
            if match:
                amount_str = f"${match.group(1)}{match.group(2)[0].upper()}"
                return parse_amount(amount_str)
        
        return ("Undisclosed", 0.0)
    
    def _extract_round_type(self, title: str, content: str) -> str:
        """Extract round type"""
        combined = (title + " " + content[:500]).lower()
        
        round_patterns = [
            'pre-seed', 'preseed', 'seed', 'series a', 'series b',
            'series c', 'series d', 'series-a', 'series-b'
        ]
        
        for pattern in round_patterns:
            if pattern in combined:
                return normalize_round_type(pattern)
        
        return "unknown"
    
    def _extract_investors(self, content: str) -> tuple[List[str], str]:
        """Extract investors and lead investor"""
        investors = []
        lead_investor = None
        
        # Look for investor mentions
        investor_section = re.search(
            r'(investors?|participants?|backers?|led by|participated|joined)[\s\S]{0,300}',
            content,
            re.IGNORECASE
        )
        
        if investor_section:
            section_text = investor_section.group(0)
            
            # Look for "led by X"
            led_match = re.search(r'led by\s+([A-Z][a-zA-Z\s&]+?)(?:\s+and|\s+with|,|\.)', section_text)
            if led_match:
                lead_investor = led_match.group(1).strip()
                investors.append(lead_investor)
            
            # Find capitalized names (likely investors)
            names = re.findall(r'\b([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){0,3})\b', section_text)
            for name in names:
                if name not in investors and len(name) > 3:
                    investors.append(name)
        
        return (investors[:5], lead_investor)  # Limit to 5
    
    def _extract_location(self, content: str) -> str:
        """Extract company location"""
        # Look for common location patterns
        location_match = re.search(
            r'\b(New York|NYC|Brooklyn|Manhattan|San Francisco|SF|Boston|Austin|Los Angeles|LA|Seattle|based in|headquartered in)\b',
            content,
            re.IGNORECASE
        )
        
        if location_match:
            loc = location_match.group(1)
            # Normalize
            if loc.upper() == 'SF':
                return 'San Francisco'
            elif loc.upper() in ['NYC', 'NEW YORK']:
                return 'New York'
            return loc
        
        return None
    
    def _extract_date(self, url: str, content: str) -> str:
        """Extract announcement date"""
        # Try URL first
        date_match = re.search(r'/(\d{4})/(\d{2})/(\d{2})/', url)
        if date_match:
            return f"{date_match.group(1)}-{date_match.group(2)}-{date_match.group(3)}"
        
        # Fallback to today
        return datetime.now().strftime('%Y-%m-%d')
    
    def _extract_evidence_snippets(self, content: str) -> List[str]:
        """Extract relevant evidence snippets"""
        snippets = []
        
        # Look for funding-related sentences
        sentences = re.split(r'[.!?]', content)
        for sentence in sentences[:50]:  # Check first 50 sentences
            if any(keyword in sentence.lower() for keyword in ['raise', 'million', 'funding', 'investor']):
                snippet = truncate_snippet(sentence.strip(), 25)
                if snippet and len(snippet) > 20:
                    snippets.append(snippet)
                if len(snippets) >= 3:
                    break
        
        return snippets
    
    def _build_wwwwwh(
        self, startup_name: str, amount: str, round_type: str,
        investors: List[str], lead_investor: str, location: str,
        date: str, content: str
    ) -> WHOWHATWHYStructure:
        """Build WHO/WHAT/WHY/WHEN/WHERE/HOW structure"""
        
        who = f"{startup_name}"
        if lead_investor:
            who += f", led by {lead_investor}"
        
        what = f"Raised {amount} in {round_type} round"
        if investors:
            what += f" from {', '.join(investors[:3])}"
        
        # Extract why (use case) from content
        why_match = re.search(
            r'(will use|plans to|aims to|focus on|building|developing)[\s\S]{0,100}',
            content,
            re.IGNORECASE
        )
        why = truncate_snippet(why_match.group(0), 20) if why_match else "Use of funds not disclosed"
        
        when = f"Announced {date}" if date else "Date not specified"
        
        where = f"Based in {location}" if location else "Location not specified"
        
        how = f"Secured funding through {round_type} round"
        
        return WHOWHATWHYStructure(
            who=who,
            what=what,
            why=why,
            when=when,
            where=where,
            how=how
        )


class EventNormalizer:
    """Normalize event listings to EventItem"""
    
    def __init__(self, config: Dict):
        self.config = config
    
    def normalize(self, raw_source: RawSource) -> List[EventItem]:
        """Extract EventItems from raw source"""
        soup = BeautifulSoup(raw_source.html_content, 'html.parser')
        
        # For MVP, extract basic event info
        # In production, this would parse specific event structures
        events = []
        
        # Look for event-like structures
        event_containers = soup.find_all(['div', 'article'], class_=re.compile(r'event', re.I))
        
        for container in event_containers[:10]:  # Limit to 10
            event = self._extract_event(container, raw_source.url)
            if event:
                events.append(event)
        
        return events
    
    def _extract_event(self, container, source_url: str) -> EventItem:
        """Extract single event"""
        # Extract name
        name_tag = container.find(['h1', 'h2', 'h3', 'h4'])
        name = name_tag.get_text(strip=True) if name_tag else "Unnamed Event"
        
        text = container.get_text(separator=' ', strip=True)
        
        # Extract date/time (simple pattern matching)
        date_match = re.search(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2}', text)
        date_time = date_match.group(0) if date_match else "TBA"
        
        # Extract location
        location_match = re.search(r'(New York|NYC|Brooklyn|Manhattan)', text, re.IGNORECASE)
        city = location_match.group(1) if location_match else "NYC"
        
        # Check if online
        venue = "Online" if 'online' in text.lower() or 'virtual' in text.lower() else "TBA"
        
        # Check cost
        cost = "Free" if 'free' in text.lower() else "Check website"
        
        return EventItem(
            event_name=name,
            date_time=date_time,
            city=city,
            venue_or_online=venue,
            cost=cost,
            audience="General",
            registration_url=None,
            source_url=source_url,
            description=truncate_snippet(text, 30)
        )


class AcceleratorNormalizer:
    """Normalize accelerator listings to AcceleratorItem"""
    
    def __init__(self, config: Dict):
        self.config = config
    
    def normalize(self, raw_source: RawSource) -> List[AcceleratorItem]:
        """Extract AcceleratorItems from raw source"""
        soup = BeautifulSoup(raw_source.html_content, 'html.parser')
        
        accelerators = []
        
        # Look for accelerator entries
        containers = soup.find_all(['div', 'article', 'li'], class_=re.compile(r'accelerator|incubator', re.I))
        
        for container in containers[:15]:  # Limit to 15
            acc = self._extract_accelerator(container, raw_source.url)
            if acc:
                accelerators.append(acc)
        
        return accelerators
    
    def _extract_accelerator(self, container, source_url: str) -> AcceleratorItem:
        """Extract single accelerator"""
        # Extract name
        name_tag = container.find(['h1', 'h2', 'h3', 'h4', 'strong'])
        name = name_tag.get_text(strip=True) if name_tag else "Unknown Accelerator"
        
        text = container.get_text(separator=' ', strip=True)
        
        # Extract location
        location_match = re.search(r'(New York|NYC|San Francisco|Boston|Global)', text, re.IGNORECASE)
        city = location_match.group(1) if location_match else None
        
        # Extract focus
        focus_keywords = ['AI', 'fintech', 'health', 'climate', 'b2b', 'consumer']
        focus = None
        for keyword in focus_keywords:
            if keyword.lower() in text.lower():
                focus = keyword
                break
        
        return AcceleratorItem(
            name=name,
            city_region=city,
            focus=focus,
            source_url=source_url,
            description=truncate_snippet(text, 30)
        )


def load_raw_sources(config: Dict) -> List[RawSource]:
    """Load all raw sources from data/raw directory"""
    raw_dir = Path(config['storage']['raw_dir'])
    
    if not raw_dir.exists():
        return []
    
    raw_sources = []
    for json_file in raw_dir.glob('*.json'):
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            raw_sources.append(RawSource.from_dict(data))
    
    return raw_sources


def main():
    print("=== AI Factory Newsletter - Normalization ===")
    print("Extracting structured data from raw sources...")
    print()
    
    config = load_config()
    
    # Load raw sources
    raw_sources = load_raw_sources(config)
    
    if not raw_sources:
        print("No raw sources found. Run: python -m newsroom.collect first")
        return
    
    print(f"Found {len(raw_sources)} raw sources")
    
    # Initialize normalizers
    funding_normalizer = FundingNormalizer(config)
    event_normalizer = EventNormalizer(config)
    accelerator_normalizer = AcceleratorNormalizer(config)
    
    # Normalize each source
    all_funding = []
    all_events = []
    all_accelerators = []
    
    for raw in raw_sources:
        print(f"Processing: {raw.url[:60]}...")
        
        # Try funding normalization
        funding_items = funding_normalizer.normalize(raw)
        all_funding.extend(funding_items)
        
        # Try event normalization
        event_items = event_normalizer.normalize(raw)
        all_events.extend(event_items)
        
        # Try accelerator normalization
        acc_items = accelerator_normalizer.normalize(raw)
        all_accelerators.extend(acc_items)
    
    print()
    print(f"Extracted:")
    print(f"  - {len(all_funding)} funding items")
    print(f"  - {len(all_events)} event items")
    print(f"  - {len(all_accelerators)} accelerator items")
    
    # Save normalized data
    data_dir = Path(config['storage']['data_dir'])
    
    normalized_data = {
        'funding': [item.to_dict() for item in all_funding],
        'events': [item.to_dict() for item in all_events],
        'accelerators': [item.to_dict() for item in all_accelerators],
        'normalized_at': datetime.now().isoformat()
    }
    
    normalized_file = data_dir / 'normalized.json'
    with open(normalized_file, 'w', encoding='utf-8') as f:
        json.dump(normalized_data, f, indent=2, ensure_ascii=False)
    
    print()
    print(f"Normalized data saved to: {normalized_file}")
    print()
    print("Next step: python -m newsroom.dedupe")


if __name__ == '__main__':
    main()
