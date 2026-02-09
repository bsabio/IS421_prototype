"""
Unit tests for the newsletter generator
"""
import pytest
from pathlib import Path
from newsroom.sources import TechCrunchCollector, AlleyWatchCollector, GarysGuideCollector
from newsroom.normalize import FundingNormalizer, EventNormalizer
from newsroom.utils import (
    parse_amount, normalize_round_type, generate_item_hash,
    extract_startup_name, categorize_content, get_round_priority
)
from newsroom.models import FundingItem, EventItem, AcceleratorItem


# Fixtures
@pytest.fixture
def sample_config():
    return {
        'categories': {
            'ai_ml': ['ai', 'artificial intelligence', 'machine learning'],
            'fintech': ['fintech', 'financial', 'payments'],
            'health': ['health', 'medical', 'healthcare']
        },
        'search': {
            'primary_city': 'NYC',
            'include_cities': ['New York', 'NYC', 'Brooklyn']
        },
        'limits': {
            'funding_items': 10,
            'event_items': 12,
            'accelerator_items': 8
        },
        'storage': {
            'data_dir': 'data',
            'raw_dir': 'data/raw'
        }
    }


@pytest.fixture
def techcrunch_html():
    """Sample TechCrunch funding article HTML"""
    return """
    <html>
    <head><title>Acme AI raises $10M Series A</title></head>
    <body>
        <article>
            <h1>Acme AI raises $10M Series A to build AI agents</h1>
            <div class="article-content">
                <p>Acme AI, a New York-based startup building autonomous AI agents,
                announced today it has raised $10 million in Series A funding.</p>
                <p>The round was led by Venture Capital Partners, with participation 
                from Angel Investors Group and Tech Fund.</p>
                <p>The company plans to use the funding to expand its engineering 
                team and accelerate product development.</p>
            </div>
        </article>
    </body>
    </html>
    """


@pytest.fixture
def alleywatch_html():
    """Sample AlleyWatch funding report HTML"""
    return """
    <html>
    <head><title>Startup Daily Funding Report 2-5-2026</title></head>
    <body>
        <article>
            <h1>Startup Daily Funding Report: 2/5/2026</h1>
            <div class="entry-content">
                <h2>FinTech Startup Secures Seed Round</h2>
                <p>PayFlow, a Brooklyn-based fintech startup, raised $3 million 
                in seed funding from NYC Ventures.</p>
            </div>
        </article>
    </body>
    </html>
    """


@pytest.fixture
def garys_guide_html():
    """Sample Gary's Guide event listing HTML"""
    return """
    <html>
    <head><title>NYC Tech Events</title></head>
    <body>
        <div class="event">
            <h3>Founders & Funders Meetup</h3>
            <p>Join us Feb 15 for networking with NYC founders and VCs</p>
            <p>Location: Manhattan</p>
            <p>Free event</p>
        </div>
    </body>
    </html>
    """


# Utility Tests
class TestUtils:
    
    def test_parse_amount_millions(self):
        """Test parsing various million-dollar amounts"""
        formatted, numeric = parse_amount("$5M")
        assert numeric == 5_000_000.0
        assert "$" in formatted and "M" in formatted
        
        formatted, numeric = parse_amount("10 million")
        assert numeric == 10_000_000.0
        
        formatted, numeric = parse_amount("$2.5M")
        assert numeric == 2_500_000.0
        assert "2.5" in formatted
    
    def test_parse_amount_billions(self):
        """Test parsing billion-dollar amounts"""
        formatted, numeric = parse_amount("$1B")
        assert numeric == 1_000_000_000.0
        assert "$" in formatted and "B" in formatted
        
        formatted, numeric = parse_amount("1.5 billion")
        assert numeric == 1_500_000_000.0
        assert "1.5" in formatted
    
    def test_parse_amount_undisclosed(self):
        """Test parsing undisclosed amounts"""
        assert parse_amount("undisclosed") == ("Undisclosed", 0.0)
        assert parse_amount("") == ("Undisclosed", 0.0)
        assert parse_amount(None) == ("Undisclosed", 0.0)
    
    def test_normalize_round_type(self):
        """Test round type normalization"""
        assert normalize_round_type("seed") == "seed"
        assert normalize_round_type("Series A") == "series-a"
        assert normalize_round_type("series-b") == "series-b"
        assert normalize_round_type("Pre-seed") == "pre-seed"
        assert normalize_round_type("unknown thing") == "unknown"
    
    def test_generate_item_hash(self):
        """Test hash generation for deduplication"""
        hash1 = generate_item_hash("https://tc.com/article", "Startup Raises 10M")
        hash2 = generate_item_hash("https://tc.com/article", "Startup Raises 10M")
        hash3 = generate_item_hash("https://tc.com/other", "Startup Raises 10M")
        
        assert hash1 == hash2  # Same URL and title
        assert hash1 != hash3  # Different URL
    
    def test_extract_startup_name(self):
        """Test startup name extraction"""
        assert "Acme" in extract_startup_name("Acme raises $10M")
        assert "TechCorp" in extract_startup_name("TechCorp secures funding")
    
    def test_categorize_content(self, sample_config):
        """Test content categorization"""
        text1 = "Building AI agents with machine learning"
        categories1 = categorize_content(text1, sample_config)
        assert "Ai Ml" in categories1
        
        text2 = "Financial technology for banking"
        categories2 = categorize_content(text2, sample_config)
        assert "Fintech" in categories2
    
    def test_get_round_priority(self):
        """Test round priority scoring"""
        assert get_round_priority("series-c") > get_round_priority("series-a")
        assert get_round_priority("series-a") > get_round_priority("seed")
        assert get_round_priority("seed") > get_round_priority("unknown")


# Parsing Tests
class TestTechCrunchParsing:
    
    def test_parse_techcrunch_article(self, techcrunch_html, sample_config):
        """Test parsing a TechCrunch funding article"""
        from newsroom.models import RawSource
        from bs4 import BeautifulSoup
        
        normalizer = FundingNormalizer(sample_config)
        
        raw_source = RawSource(
            url="https://techcrunch.com/2026/02/05/acme-ai-raises-10m/",
            source_name="TechCrunch",
            fetched_at="2026-02-05T10:00:00",
            html_content=techcrunch_html,
            status_code=200
        )
        
        items = normalizer.normalize(raw_source)
        
        assert len(items) > 0
        item = items[0]
        
        assert "Acme" in item.startup_name
        assert item.amount_numeric > 0
        assert "series-a" in item.round_type.lower()
        assert len(item.source_urls) > 0


class TestAlleyWatchParsing:
    
    def test_parse_alleywatch_report(self, alleywatch_html, sample_config):
        """Test parsing an AlleyWatch funding report"""
        from newsroom.models import RawSource
        
        normalizer = FundingNormalizer(sample_config)
        
        raw_source = RawSource(
            url="https://alleywatch.com/2026/02/startup-daily-funding-report-2-5-2026/",
            source_name="AlleyWatch",
            fetched_at="2026-02-05T10:00:00",
            html_content=alleywatch_html,
            status_code=200
        )
        
        items = normalizer.normalize(raw_source)
        
        assert len(items) > 0
        item = items[0]
        
        # Check that some data was extracted
        assert item.title is not None
        assert len(item.source_urls) > 0


class TestGarysGuideParsing:
    
    def test_parse_garys_guide_events(self, garys_guide_html, sample_config):
        """Test parsing Gary's Guide event page"""
        from newsroom.models import RawSource
        
        normalizer = EventNormalizer(sample_config)
        
        raw_source = RawSource(
            url="https://garysguide.com/events",
            source_name="GarysGuide",
            fetched_at="2026-02-05T10:00:00",
            html_content=garys_guide_html,
            status_code=200
        )
        
        items = normalizer.normalize(raw_source)
        
        assert len(items) > 0
        item = items[0]
        
        assert item.event_name is not None
        assert len(item.source_url) > 0


# Data Model Tests
class TestDataModels:
    
    def test_funding_item_creation(self):
        """Test FundingItem creation and serialization"""
        item = FundingItem(
            title="Test Startup raises $5M",
            startup_name="Test Startup",
            round_type="seed",
            amount="$5M",
            amount_numeric=5_000_000,
            investors=["VC Fund"],
            source_urls=["https://example.com/article"]
        )
        
        # Test serialization
        data = item.to_dict()
        assert data['startup_name'] == "Test Startup"
        assert data['amount_numeric'] == 5_000_000
        
        # Test deserialization
        item2 = FundingItem.from_dict(data)
        assert item2.startup_name == item.startup_name
        assert item2.amount_numeric == item.amount_numeric
    
    def test_event_item_creation(self):
        """Test EventItem creation"""
        item = EventItem(
            event_name="Test Event",
            date_time="Feb 15",
            city="NYC",
            cost="Free",
            source_url="https://example.com/event"
        )
        
        assert item.event_name == "Test Event"
        assert item.cost == "Free"
    
    def test_accelerator_item_creation(self):
        """Test AcceleratorItem creation"""
        item = AcceleratorItem(
            name="Test Accelerator",
            city_region="NYC",
            focus="AI",
            source_url="https://example.com/acc"
        )
        
        assert item.name == "Test Accelerator"
        assert item.focus == "AI"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
