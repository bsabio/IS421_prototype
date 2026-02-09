"""
Utility functions for the newsletter generator
"""
import re
import yaml
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime, timedelta
import hashlib


def load_config() -> Dict[str, Any]:
    """Load configuration from config.yaml"""
    config_path = Path(__file__).parent.parent / "config.yaml"
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def parse_amount(amount_str: str) -> tuple[str, float]:
    """
    Parse funding amount string to normalized string and numeric value
    Returns: (formatted_string, numeric_value)
    
    Examples:
    - "$5M" -> ("$5M", 5000000.0)
    - "10 million" -> ("$10M", 10000000.0)
    - "undisclosed" -> ("Undisclosed", 0.0)
    """
    if not amount_str or amount_str.lower() in ['undisclosed', 'unknown', 'n/a', '']:
        return ("Undisclosed", 0.0)
    
    amount_str = amount_str.lower().replace(',', '').replace('$', '').strip()
    
    # Extract number
    number_match = re.search(r'(\d+\.?\d*)', amount_str)
    if not number_match:
        return ("Undisclosed", 0.0)
    
    number = float(number_match.group(1))
    
    # Check for magnitude
    if 'billion' in amount_str or 'b' in amount_str:
        numeric = number * 1_000_000_000
        formatted = f"${number:.1f}B".rstrip('0').rstrip('.')
    elif 'million' in amount_str or 'm' in amount_str:
        numeric = number * 1_000_000
        formatted = f"${number:.1f}M".rstrip('0').rstrip('.')
    elif 'thousand' in amount_str or 'k' in amount_str:
        numeric = number * 1_000
        formatted = f"${number:.0f}K"
    else:
        numeric = number
        formatted = f"${number:.0f}"
    
    return (formatted, numeric)


def normalize_round_type(round_str: str) -> str:
    """
    Normalize funding round type
    Returns: pre-seed, seed, series-a, series-b, series-c, series-d+, unknown
    """
    if not round_str:
        return "unknown"
    
    round_str = round_str.lower().strip()
    
    if 'pre-seed' in round_str or 'preseed' in round_str:
        return "pre-seed"
    elif 'seed' in round_str and 'series' not in round_str:
        return "seed"
    elif 'series a' in round_str or 'series-a' in round_str:
        return "series-a"
    elif 'series b' in round_str or 'series-b' in round_str:
        return "series-b"
    elif 'series c' in round_str or 'series-c' in round_str:
        return "series-c"
    elif 'series d' in round_str or 'series e' in round_str or 'series f' in round_str:
        return "series-d+"
    elif 'bridge' in round_str:
        return "bridge"
    elif 'venture' in round_str:
        return "venture"
    else:
        return "unknown"


def extract_date_from_url(url: str) -> str:
    """
    Extract date from TechCrunch-style URLs
    Example: techcrunch.com/2026/02/05/... -> 2026-02-05
    """
    match = re.search(r'/(\d{4})/(\d{2})/(\d{2})/', url)
    if match:
        return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
    return ""


def categorize_content(text: str, config: Dict) -> List[str]:
    """
    Categorize content based on keywords from config
    """
    text_lower = text.lower()
    categories = []
    
    category_keywords = config.get('categories', {})
    
    for category, keywords in category_keywords.items():
        for keyword in keywords:
            if keyword.lower() in text_lower:
                # Convert category key to readable format
                readable = category.replace('_', ' ').title()
                if readable not in categories:
                    categories.append(readable)
                break
    
    return categories if categories else ["General"]


def generate_item_hash(url: str, title: str) -> str:
    """
    Generate a unique hash for deduplication
    Uses normalized URL and title
    """
    normalized_url = url.lower().strip().rstrip('/')
    normalized_title = re.sub(r'\s+', ' ', title.lower().strip())
    
    combined = f"{normalized_url}|{normalized_title}"
    return hashlib.md5(combined.encode()).hexdigest()


def extract_startup_name(title: str) -> str:
    """
    Extract startup name from title (first proper noun phrase)
    Marks low confidence automatically
    """
    # Remove common prefixes
    title = re.sub(r'^(startup|company|fintech|healthtech|edtech|ai)\s+', '', title, flags=re.IGNORECASE)
    
    # Look for capitalized words at the beginning
    match = re.match(r'^([A-Z][a-zA-Z0-9]*(?:\s+[A-Z][a-zA-Z0-9]*)*)', title)
    if match:
        return match.group(1)
    
    # Fallback: first word
    words = title.split()
    return words[0] if words else "Unknown Startup"


def truncate_snippet(text: str, max_words: int = 25) -> str:
    """
    Truncate a snippet to max_words
    """
    words = text.split()
    if len(words) <= max_words:
        return text
    return ' '.join(words[:max_words]) + '...'


def get_date_range(days_back: int) -> tuple[datetime, datetime]:
    """
    Get date range for collection
    Returns: (start_date, end_date)
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)
    return (start_date, end_date)


def ensure_directories():
    """Ensure all required directories exist"""
    base_dir = Path(__file__).parent.parent
    
    dirs = [
        base_dir / "data",
        base_dir / "data" / "raw",
        base_dir / "output",
    ]
    
    for directory in dirs:
        directory.mkdir(parents=True, exist_ok=True)


def get_round_priority(round_type: str) -> int:
    """
    Get priority for round type (higher = more important)
    """
    priorities = {
        "series-d+": 7,
        "series-c": 6,
        "series-b": 5,
        "series-a": 4,
        "seed": 3,
        "pre-seed": 2,
        "bridge": 1,
        "unknown": 0,
    }
    return priorities.get(round_type, 0)


def get_source_credibility(source_url: str) -> int:
    """
    Get credibility score for source (higher = more credible)
    """
    if 'techcrunch.com' in source_url:
        return 10
    elif 'alleywatch.com' in source_url:
        return 9
    elif 'crunchbase.com' in source_url:
        return 8
    elif 'forbes.com' in source_url or 'bloomberg.com' in source_url:
        return 9
    else:
        return 5
