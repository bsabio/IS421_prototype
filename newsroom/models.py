"""
Data models for newsletter items
"""
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict
from datetime import datetime
import json


@dataclass
class WHOWHATWHYStructure:
    """Reporter-style structure for funding stories"""
    who: str = ""  # Who is involved (startup, founders, investors)
    what: str = ""  # What happened (funding amount, round type)
    why: str = ""  # Why they raised / use of funds
    when: str = ""  # When it was announced
    where: str = ""  # Where the company is based
    how: str = ""  # How it happened / context
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class FundingItem:
    """Funding announcement data model"""
    title: str
    startup_name: str
    round_type: str  # pre-seed/seed/series-a/series-b/series-c/unknown
    amount: str  # Number or "Undisclosed"
    investors: List[str] = field(default_factory=list)
    lead_investor: Optional[str] = None
    location: Optional[str] = None
    announced_date: Optional[str] = None  # YYYY-MM-DD
    source_urls: List[str] = field(default_factory=list)
    evidence_snippets: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    categories: List[str] = field(default_factory=list)
    who_what_why_when_where_how: WHOWHATWHYStructure = field(default_factory=WHOWHATWHYStructure)
    
    # Internal tracking
    amount_numeric: float = 0.0  # For sorting; 0 if undisclosed
    confidence_notes: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "title": self.title,
            "startup_name": self.startup_name,
            "round_type": self.round_type,
            "amount": self.amount,
            "investors": self.investors,
            "lead_investor": self.lead_investor,
            "location": self.location,
            "announced_date": self.announced_date,
            "source_urls": self.source_urls,
            "evidence_snippets": self.evidence_snippets,
            "tags": self.tags,
            "categories": self.categories,
            "who_what_why_when_where_how": self.who_what_why_when_where_how.to_dict(),
            "amount_numeric": self.amount_numeric,
            "confidence_notes": self.confidence_notes
        }
    
    @staticmethod
    def from_dict(data: Dict) -> 'FundingItem':
        """Create FundingItem from dictionary"""
        wwwwwh_data = data.get('who_what_why_when_where_how', {})
        wwwwwh = WHOWHATWHYStructure(**wwwwwh_data) if isinstance(wwwwwh_data, dict) else WHOWHATWHYStructure()
        
        return FundingItem(
            title=data.get('title', ''),
            startup_name=data.get('startup_name', ''),
            round_type=data.get('round_type', 'unknown'),
            amount=data.get('amount', 'Undisclosed'),
            investors=data.get('investors', []),
            lead_investor=data.get('lead_investor'),
            location=data.get('location'),
            announced_date=data.get('announced_date'),
            source_urls=data.get('source_urls', []),
            evidence_snippets=data.get('evidence_snippets', []),
            tags=data.get('tags', []),
            categories=data.get('categories', []),
            who_what_why_when_where_how=wwwwwh,
            amount_numeric=data.get('amount_numeric', 0.0),
            confidence_notes=data.get('confidence_notes', [])
        )


@dataclass
class EventItem:
    """Event data model"""
    event_name: str
    date_time: Optional[str] = None  # ISO format or human readable
    city: Optional[str] = None
    venue_or_online: str = "TBA"
    cost: str = "Free"
    audience: Optional[str] = None  # founders/VCs/students/general
    registration_url: Optional[str] = None
    source_url: str = ""
    description: str = ""
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @staticmethod
    def from_dict(data: Dict) -> 'EventItem':
        return EventItem(**data)


@dataclass
class AcceleratorItem:
    """Accelerator/incubator data model"""
    name: str
    city_region: Optional[str] = None
    focus: Optional[str] = None
    source_url: str = ""
    description: str = ""
    application_url: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @staticmethod
    def from_dict(data: Dict) -> 'AcceleratorItem':
        return AcceleratorItem(**data)


@dataclass
class RawSource:
    """Raw HTML source tracking"""
    url: str
    source_name: str
    fetched_at: str  # ISO timestamp
    html_content: str
    status_code: int = 200
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @staticmethod
    def from_dict(data: Dict) -> 'RawSource':
        return RawSource(**data)


def save_items_to_json(items: List, filepath: str):
    """Save items to JSON file"""
    data = [item.to_dict() for item in items]
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_funding_items_from_json(filepath: str) -> List[FundingItem]:
    """Load funding items from JSON file"""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return [FundingItem.from_dict(item) for item in data]


def load_event_items_from_json(filepath: str) -> List[EventItem]:
    """Load event items from JSON file"""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return [EventItem.from_dict(item) for item in data]


def load_accelerator_items_from_json(filepath: str) -> List[AcceleratorItem]:
    """Load accelerator items from JSON file"""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return [AcceleratorItem.from_dict(item) for item in data]
