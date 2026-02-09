"""
Source collectors for different news sources
"""
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from datetime import datetime
import time
import re
from pathlib import Path
from .models import RawSource
from .utils import load_config
import json


class BaseCollector:
    """Base class for source collectors"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def fetch_page(self, url: str) -> Optional[RawSource]:
        """Fetch a page and return RawSource"""
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            return RawSource(
                url=url,
                source_name=self.__class__.__name__,
                fetched_at=datetime.now().isoformat(),
                html_content=response.text,
                status_code=response.status_code
            )
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return None
    
    def save_raw(self, raw_source: RawSource, filename: str):
        """Save raw HTML to file"""
        raw_dir = Path(self.config['storage']['raw_dir'])
        raw_dir.mkdir(parents=True, exist_ok=True)
        
        filepath = raw_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(raw_source.to_dict(), f, indent=2, ensure_ascii=False)


class TechCrunchCollector(BaseCollector):
    """Collector for TechCrunch funding stories"""
    
    def collect(self, days_back: int = 7) -> List[RawSource]:
        """Collect TechCrunch funding articles"""
        print(f"[TechCrunch] Collecting articles from past {days_back} days...")
        
        raw_sources = []
        
        # For MVP, we'll use example URLs
        # In production, this would search/scrape the category pages
        example_urls = self._get_example_urls()
        
        for url in example_urls:
            print(f"  Fetching: {url}")
            raw = self.fetch_page(url)
            if raw:
                raw_sources.append(raw)
                # Save to raw directory
                filename = f"techcrunch_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(raw_sources)}.json"
                self.save_raw(raw, filename)
                time.sleep(1)  # Be polite
        
        print(f"[TechCrunch] Collected {len(raw_sources)} articles")
        return raw_sources
    
    def _get_example_urls(self) -> List[str]:
        """Get example URLs for MVP testing"""
        # These are example patterns; in production we'd search the site
        return [
            # Add real TechCrunch article URLs here for testing
            # Example format: "https://techcrunch.com/2026/02/05/startup-name-raises-10m/"
        ]
    
    def parse_article(self, html: str, url: str) -> Dict:
        """Parse a TechCrunch article"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract title
        title_tag = soup.find('h1')
        title = title_tag.get_text(strip=True) if title_tag else ""
        
        # Extract article content
        article_body = soup.find('div', class_='article-content') or soup.find('article')
        content = article_body.get_text(separator=' ', strip=True) if article_body else ""
        
        # Extract date from URL or article
        date = self._extract_date(url, soup)
        
        return {
            'url': url,
            'title': title,
            'content': content,
            'date': date,
            'source': 'TechCrunch'
        }
    
    def _extract_date(self, url: str, soup: BeautifulSoup) -> str:
        """Extract date from URL or HTML"""
        # Try URL first
        match = re.search(r'/(\d{4})/(\d{2})/(\d{2})/', url)
        if match:
            return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
        
        # Try meta tags
        date_meta = soup.find('meta', property='article:published_time')
        if date_meta and date_meta.get('content'):
            return date_meta['content'][:10]
        
        return datetime.now().strftime('%Y-%m-%d')


class AlleyWatchCollector(BaseCollector):
    """Collector for AlleyWatch funding reports"""
    
    def collect(self, days_back: int = 7) -> List[RawSource]:
        """Collect AlleyWatch funding reports"""
        print(f"[AlleyWatch] Collecting funding reports from past {days_back} days...")
        
        raw_sources = []
        example_urls = self._get_example_urls()
        
        for url in example_urls:
            print(f"  Fetching: {url}")
            raw = self.fetch_page(url)
            if raw:
                raw_sources.append(raw)
                filename = f"alleywatch_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(raw_sources)}.json"
                self.save_raw(raw, filename)
                time.sleep(1)
        
        print(f"[AlleyWatch] Collected {len(raw_sources)} reports")
        return raw_sources
    
    def _get_example_urls(self) -> List[str]:
        """Get example URLs for MVP testing"""
        return [
            # Add real AlleyWatch URLs here for testing
            # Example: "https://www.alleywatch.com/2026/02/startup-daily-funding-report-2-5-2026/"
        ]
    
    def parse_report(self, html: str, url: str) -> Dict:
        """Parse an AlleyWatch funding report"""
        soup = BeautifulSoup(html, 'html.parser')
        
        title_tag = soup.find('h1')
        title = title_tag.get_text(strip=True) if title_tag else ""
        
        # AlleyWatch reports often have structured content
        article_body = soup.find('div', class_='entry-content') or soup.find('article')
        content = article_body.get_text(separator=' ', strip=True) if article_body else ""
        
        return {
            'url': url,
            'title': title,
            'content': content,
            'date': self._extract_date_from_title(title),
            'source': 'AlleyWatch'
        }
    
    def _extract_date_from_title(self, title: str) -> str:
        """Extract date from AlleyWatch title"""
        # AlleyWatch often includes dates in titles
        match = re.search(r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})', title)
        if match:
            month, day, year = match.groups()
            return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        return datetime.now().strftime('%Y-%m-%d')


class GarysGuideCollector(BaseCollector):
    """Collector for Gary's Guide events"""
    
    def collect(self, days_back: int = 7) -> List[RawSource]:
        """Collect Gary's Guide events"""
        print(f"[Gary's Guide] Collecting events from past {days_back} days...")
        
        raw_sources = []
        example_urls = self._get_example_urls()
        
        for url in example_urls:
            print(f"  Fetching: {url}")
            raw = self.fetch_page(url)
            if raw:
                raw_sources.append(raw)
                filename = f"garysguide_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(raw_sources)}.json"
                self.save_raw(raw, filename)
                time.sleep(1)
        
        print(f"[Gary's Guide] Collected {len(raw_sources)} event pages")
        return raw_sources
    
    def _get_example_urls(self) -> List[str]:
        """Get example URLs for MVP testing"""
        return [
            # Add real Gary's Guide URLs here for testing
            # Example: "https://www.garysguide.com/events"
        ]
    
    def parse_events(self, html: str, url: str) -> Dict:
        """Parse Gary's Guide event listing"""
        soup = BeautifulSoup(html, 'html.parser')
        
        return {
            'url': url,
            'content': soup.get_text(separator=' ', strip=True),
            'source': 'GarysGuide'
        }


class OpenVCCollector(BaseCollector):
    """Collector for OpenVC accelerators directory"""
    
    def collect(self) -> List[RawSource]:
        """Collect OpenVC accelerator listings"""
        print(f"[OpenVC] Collecting accelerator directory...")
        
        raw_sources = []
        example_urls = self._get_example_urls()
        
        for url in example_urls:
            print(f"  Fetching: {url}")
            raw = self.fetch_page(url)
            if raw:
                raw_sources.append(raw)
                filename = f"openvc_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(raw_sources)}.json"
                self.save_raw(raw, filename)
                time.sleep(1)
        
        print(f"[OpenVC] Collected {len(raw_sources)} pages")
        return raw_sources
    
    def _get_example_urls(self) -> List[str]:
        """Get example URLs for MVP testing"""
        return [
            # Add real OpenVC URLs here for testing
            # Example: "https://www.openvc.app/accelerators"
        ]
    
    def parse_directory(self, html: str, url: str) -> Dict:
        """Parse OpenVC accelerator directory"""
        soup = BeautifulSoup(html, 'html.parser')
        
        return {
            'url': url,
            'content': soup.get_text(separator=' ', strip=True),
            'source': 'OpenVC'
        }


def collect_all_sources(config: Dict, days_back: int) -> Dict[str, List[RawSource]]:
    """Collect from all enabled sources"""
    all_sources = {}
    
    if config['sources']['techcrunch']['enabled']:
        collector = TechCrunchCollector(config)
        all_sources['techcrunch'] = collector.collect(days_back)
    
    if config['sources']['alleywatch']['enabled']:
        collector = AlleyWatchCollector(config)
        all_sources['alleywatch'] = collector.collect(days_back)
    
    if config['sources']['garys_guide']['enabled']:
        collector = GarysGuideCollector(config)
        all_sources['garys_guide'] = collector.collect(days_back)
    
    if config['sources']['openvc']['enabled']:
        collector = OpenVCCollector(config)
        all_sources['openvc'] = collector.collect()
    
    return all_sources
