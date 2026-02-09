"""
Templates for newsletter rendering
Deterministic templates that fill in data fields
"""
from typing import List, Dict
from datetime import datetime
from .models import FundingItem, EventItem, AcceleratorItem


class NewsletterTemplate:
    """Base template for newsletter"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.citation_map = {}  # URL -> [citation_number]
        self.citation_counter = 1
    
    def get_citation(self, url: str) -> int:
        """Get or create citation number for URL"""
        if url not in self.citation_map:
            self.citation_map[url] = self.citation_counter
            self.citation_counter += 1
        return self.citation_map[url]
    
    def render_header(self) -> str:
        """Render newsletter header"""
        title = self.config['newsletter']['title']
        subtitle = self.config['newsletter']['subtitle']
        date = datetime.now().strftime('%B %d, %Y')
        
        return f"""# {title}
**{subtitle}**

*{date}*

---

"""
    
    def render_funding_item(self, item: FundingItem) -> str:
        """Render a single funding item with reporter-style structure"""
        # Get citations for sources
        citations = [self.get_citation(url) for url in item.source_urls]
        citation_str = ''.join([f'[{c}]' for c in citations])
        
        # Format investors
        other_investors = [inv for inv in item.investors if inv != item.lead_investor]
        other_str = ', '.join(other_investors[:3]) if other_investors else "N/A"
        
        # Build bullet line
        bullet = f"**{item.startup_name}** — {item.amount} {item.round_type.title()} Round"
        
        if item.lead_investor:
            bullet += f" — Lead: {item.lead_investor}"
        
        if other_investors:
            bullet += f" — Other: {other_str}"
        
        if item.categories:
            bullet += f" — Category: {', '.join(item.categories[:2])}"
        
        bullet += f" — {citation_str}"
        
        # Reporter structure
        www = item.who_what_why_when_where_how
        
        reporter_lines = f"""
**WHO/WHAT:** {www.who} {www.what}

**WHY/HOW:** {www.why} {www.how}

**WHEN/WHERE:** {www.when} {www.where}
"""
        
        return f"{bullet}\n{reporter_lines}\n"
    
    def render_funding_section(self, items: List[FundingItem]) -> str:
        """Render all funding items"""
        if not items:
            return "## 💰 Funding Headlines\n\n*No funding announcements this period.*\n\n"
        
        section = "## 💰 Funding Headlines\n\n"
        
        for item in items:
            section += self.render_funding_item(item)
            section += "---\n\n"
        
        return section
    
    def render_trend_brief(self, trend_data: Dict[str, int]) -> str:
        """Render category trends"""
        if not trend_data:
            return "## 📊 Trend Brief\n\n*Insufficient data for trend analysis.*\n\n"
        
        section = "## 📊 Trend Brief\n\n"
        section += "**Top categories getting funded this week:**\n\n"
        
        for category, count in trend_data.items():
            section += f"- **{category}**: {count} deal{'s' if count > 1 else ''}\n"
        
        section += "\n"
        return section
    
    def render_event_item(self, item: EventItem) -> str:
        """Render a single event item"""
        citation = self.get_citation(item.source_url)
        
        line = f"**{item.event_name}** — {item.date_time} — {item.venue_or_online} — {item.cost}"
        
        if item.registration_url:
            line += f" — [Register]({item.registration_url})"
        
        line += f" — [{citation}]"
        
        if item.description:
            line += f"\n  *{item.description}*"
        
        return line + "\n\n"
    
    def render_events_section(self, items: List[EventItem]) -> str:
        """Render all events"""
        if not items:
            return "## 🎯 Events & Rooms to Be In\n\n*No events scheduled.*\n\n"
        
        section = "## 🎯 Events & Rooms to Be In\n\n"
        
        for item in items:
            section += self.render_event_item(item)
        
        return section
    
    def render_accelerator_item(self, item: AcceleratorItem) -> str:
        """Render a single accelerator item"""
        citation = self.get_citation(item.source_url)
        
        line = f"**{item.name}**"
        
        if item.city_region:
            line += f" — {item.city_region}"
        
        if item.focus:
            line += f" — Focus: {item.focus}"
        
        line += f" — [{citation}]"
        
        if item.description:
            line += f"\n  *{item.description}*"
        
        return line + "\n\n"
    
    def render_accelerators_section(self, items: List[AcceleratorItem]) -> str:
        """Render all accelerators"""
        if not items:
            return "## 🚀 Accelerators Watch\n\n*No accelerator updates.*\n\n"
        
        section = "## 🚀 Accelerators Watch\n\n"
        
        for item in items:
            section += self.render_accelerator_item(item)
        
        return section
    
    def render_bibliography(self) -> str:
        """Render bibliography with all citations"""
        if not self.citation_map:
            return ""
        
        section = "## 📚 Sources & Bibliography\n\n"
        
        # Sort by citation number
        sorted_citations = sorted(self.citation_map.items(), key=lambda x: x[1])
        
        for url, number in sorted_citations:
            # Extract source name from URL
            if 'techcrunch.com' in url:
                source_name = "TechCrunch"
            elif 'alleywatch.com' in url:
                source_name = "AlleyWatch"
            elif 'garysguide.com' in url:
                source_name = "Gary's Guide"
            elif 'openvc.app' in url:
                source_name = "OpenVC"
            else:
                source_name = "Source"
            
            section += f"[{number}] {source_name} — {url}\n\n"
        
        return section
    
    def render_limitations(self, funding_items: List[FundingItem]) -> str:
        """Render limitations/notes section"""
        has_limitations = any(item.confidence_notes for item in funding_items)
        
        if not has_limitations:
            return ""
        
        section = "## ⚠️ Limitations & Notes\n\n"
        section += "Some data points were inferred or estimated:\n\n"
        
        # Collect unique limitations
        all_notes = set()
        for item in funding_items:
            all_notes.update(item.confidence_notes)
        
        for note in sorted(all_notes):
            section += f"- {note}\n"
        
        section += "\n"
        return section


def render_markdown(
    funding_items: List[FundingItem],
    event_items: List[EventItem],
    accelerator_items: List[AcceleratorItem],
    trend_data: Dict[str, int],
    config: Dict
) -> str:
    """Render complete newsletter in Markdown format"""
    
    template = NewsletterTemplate(config)
    
    content = template.render_header()
    content += template.render_funding_section(funding_items)
    content += template.render_trend_brief(trend_data)
    content += template.render_events_section(event_items)
    content += template.render_accelerators_section(accelerator_items)
    content += template.render_limitations(funding_items)
    content += template.render_bibliography()
    
    # Add footer
    content += f"\n---\n\n*Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}*\n"
    
    return content


def render_html(markdown_content: str, config: Dict) -> str:
    """Convert markdown to simple HTML"""
    
    # Simple HTML wrapper (for MVP, not full markdown->HTML conversion)
    title = config['newsletter']['title']
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            line-height: 1.6;
            max-width: 800px;
            margin: 40px auto;
            padding: 0 20px;
            color: #333;
        }}
        h1 {{
            border-bottom: 3px solid #0066cc;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #0066cc;
            margin-top: 40px;
        }}
        hr {{
            border: none;
            border-top: 1px solid #ddd;
            margin: 20px 0;
        }}
        a {{
            color: #0066cc;
            text-decoration: none;
        }}
        a:hover {{
            text-decoration: underline;
        }}
        strong {{
            color: #000;
        }}
    </style>
</head>
<body>
    <pre style="white-space: pre-wrap; font-family: inherit;">{markdown_content}</pre>
</body>
</html>
"""
    
    return html
