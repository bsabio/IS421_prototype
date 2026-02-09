"""
Enhanced HTML templates with modern styling for newsletter web display
"""
from typing import List, Dict
from datetime import datetime
from .models import FundingItem, EventItem, AcceleratorItem


def render_html_page(
    funding_items: List[FundingItem],
    event_items: List[EventItem],
    accelerator_items: List[AcceleratorItem],
    trend_data: Dict[str, int],
    config: Dict
) -> str:
    """Render complete newsletter as modern HTML page"""
    
    title = config['newsletter']['title']
    subtitle = config['newsletter']['subtitle']
    date = datetime.now().strftime('%B %d, %Y')
    
    # Citation tracking
    citation_map = {}
    citation_counter = 1
    
    def get_citation(url: str) -> int:
        nonlocal citation_counter
        if url not in citation_map:
            citation_map[url] = citation_counter
            citation_counter += 1
        return citation_map[url]
    
    # Build HTML sections
    funding_html = render_funding_section_html(funding_items, get_citation)
    trends_html = render_trends_section_html(trend_data)
    events_html = render_events_section_html(event_items, get_citation)
    accelerators_html = render_accelerators_section_html(accelerator_items, get_citation)
    bibliography_html = render_bibliography_html(citation_map)
    
    # Complete page
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        /* Swiss Design / International Typographic Style */
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
            line-height: 1.5;
            color: #000;
            background: #fff;
            font-weight: 400;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 60px 80px;
        }}
        
        /* Header */
        .header {{
            background: #fff;
            color: #000;
            padding: 0;
            border-bottom: 2px solid #000;
            padding-bottom: 40px;
            margin-bottom: 60px;
        }}
        
        .header h1 {{
            font-size: 4em;
            font-weight: 700;
            letter-spacing: -0.02em;
            margin-bottom: 8px;
            text-transform: uppercase;
        }}
        
        .header .subtitle {{
            font-size: 1em;
            font-weight: 400;
            letter-spacing: 0.05em;
            text-transform: uppercase;
            color: #666;
            margin-bottom: 8px;
        }}
        
        .header .date {{
            font-size: 0.85em;
            color: #999;
            letter-spacing: 0.05em;
            text-transform: uppercase;
        }}
        
        /* Main content */
        .main-content {{
            background: #fff;
            margin: 0;
            padding: 0;
        }}
        
        .section {{
            margin-bottom: 80px;
        }}
        
        .section:last-child {{
            margin-bottom: 0;
        }}
        
        .section-header {{
            display: flex;
            align-items: center;
            margin-bottom: 40px;
            padding-bottom: 0;
            border-bottom: none;
            position: relative;
        }}
        
        .section-icon {{
            display: none;
        }}
        
        .section-title {{
            font-size: 2.5em;
            font-weight: 700;
            color: #000;
            text-transform: uppercase;
            letter-spacing: -0.01em;
            position: relative;
            padding-left: 80px;
        }}
        
        .section-title::before {{
            content: '';
            position: absolute;
            left: 0;
            top: 50%;
            transform: translateY(-50%);
            width: 60px;
            height: 3px;
            background: #e00;
        }}
        
        /* Funding cards */
        .funding-list {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 60px 80px;
        }}
        
        .funding-card {{
            background: #fff;
            border-left: 3px solid #e00;
            padding-left: 20px;
            margin-bottom: 0;
        }}
        
        .funding-card:hover {{
            transform: none;
        }}
        
        .funding-header {{
            display: block;
            margin-bottom: 20px;
            border-bottom: 1px solid #e0e0e0;
            padding-bottom: 12px;
        }}
        
        .startup-name {{
            font-size: 1.8em;
            font-weight: 700;
            color: #000;
            margin: 0 0 6px 0;
            letter-spacing: -0.01em;
        }}
        
        .funding-amount {{
            font-size: 2.2em;
            font-weight: 700;
            color: #e00;
            white-space: nowrap;
            letter-spacing: -0.02em;
            display: block;
            margin-top: 8px;
        }}
        
        .funding-meta {{
            display: block;
            margin: 12px 0;
            font-size: 0.85em;
            color: #000;
        }}
        
        .funding-meta-item {{
            display: block;
            margin: 8px 0;
        }}
        
        .funding-meta-label {{
            font-weight: 700;
            margin-right: 8px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            font-size: 0.95em;
        }}
        
        .tag {{
            display: inline-block;
            background: #000;
            color: #fff;
            padding: 4px 12px;
            font-size: 0.75em;
            font-weight: 700;
            letter-spacing: 0.1em;
            text-transform: uppercase;
            margin: 12px 8px 12px 0;
        }}
        
        .reporter-block {{
            background: #fff;
            padding: 20px 0;
            margin-top: 15px;
        }}
        
        .reporter-line {{
            margin-bottom: 12px;
            line-height: 1.7;
        }}
        
        .reporter-line:last-child {{
            margin-bottom: 0;
        }}
        
        .reporter-label {{
            font-weight: 700;
            color: #000;
            text-transform: uppercase;
            font-size: 0.85em;
            letter-spacing: 0.05em;
        }}
        
        .citation {{
            display: inline;
            background: none;
            color: #e00;
            padding: 0;
            font-size: 0.75em;
            font-weight: 700;
            text-decoration: none;
            vertical-align: super;
            margin-left: 2px;
        }}
        
        .citation:hover {{
            text-decoration: underline;
        }}
        
        /* Trends */
        .trend-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 0;
            border: 2px solid #000;
            margin: 40px 0;
        }}
        
        .trend-card {{
            background: #fff;
            padding: 40px 20px;
            text-align: center;
            border-right: 1px solid #000;
            border-bottom: 1px solid #000;
        }}
        
        .trend-card:nth-child(4n) {{
            border-right: none;
        }}
        
        .trend-card:nth-last-child(-n+4) {{
            border-bottom: none;
        }}
        
        .trend-category {{
            font-weight: 700;
            font-size: 0.85em;
            color: #666;
            margin-bottom: 12px;
            text-transform: uppercase;
            letter-spacing: 0.1em;
        }}
        
        .trend-count {{
            font-size: 3em;
            font-weight: 700;
            color: #e00;
            letter-spacing: -0.02em;
        }}
        
        .trend-label {{
            font-size: 0.75em;
            color: #999;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        
        /* Events */
        .event-card {{
            background: #fff;
            padding: 30px;
            margin-bottom: 40px;
            border: 2px solid #000;
            position: relative;
        }}
        
        .event-card::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 4px;
            background: #e00;
        }}
        
        .event-name {{
            font-size: 1.5em;
            font-weight: 700;
            color: #000;
            margin-bottom: 12px;
            letter-spacing: -0.01em;
        }}
        
        .event-details {{
            display: block;
            margin-bottom: 15px;
            font-size: 0.9em;
            color: #000;
        }}
        
        .event-detail {{
            display: block;
            margin: 8px 0;
        }}
        
        .event-detail strong {{
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            font-size: 0.9em;
            margin-right: 8px;
        }}
        
        .event-description {{
            font-style: normal;
            color: #000;
            margin-top: 15px;
            line-height: 1.7;
        }}
        
        .btn {{
            display: inline-block;
            background: #000;
            color: #fff;
            padding: 8px 20px;
            text-decoration: none;
            font-weight: 700;
            font-size: 0.85em;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            margin-top: 15px;
        }}
        
        .btn:hover {{
            background: #e00;
        }}
        
        /* Accelerators */
        .accelerator-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 60px 80px;
        }}
        
        .accelerator-card {{
            background: #fff;
            padding: 30px;
            border: 1px solid #000;
        }}
        
        .accelerator-name {{
            font-size: 1.3em;
            font-weight: 700;
            color: #000;
            margin-bottom: 16px;
            letter-spacing: -0.01em;
            text-transform: uppercase;
        }}
        
        .accelerator-meta {{
            font-size: 0.85em;
            color: #666;
            margin-bottom: 12px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            font-weight: 700;
        }}
        
        .accelerator-description {{
            line-height: 1.7;
            margin-bottom: 15px;
            color: #000;
        }}
        
        /* Bibliography */
        .bibliography {{
            background: #f8f8f8;
            padding: 60px;
            margin: 80px 0;
            border-left: 4px solid #e00;
        }}
        
        .bibliography .section-title {{
            padding-left: 0;
        }}
        
        .bibliography .section-title::before {{
            display: none;
        }}
        
        .bibliography-item {{
            padding: 16px 0;
            border-bottom: 1px solid #e0e0e0;
            display: flex;
            align-items: start;
            gap: 20px;
        }}
        
        .bibliography-item:last-child {{
            border-bottom: none;
        }}
        
        .bibliography-number {{
            background: #e00;
            color: #fff;
            padding: 6px 12px;
            font-weight: 700;
            font-size: 0.85em;
            min-width: 40px;
            text-align: center;
        }}
        
        .bibliography-source {{
            font-weight: 700;
            color: #000;
            margin-right: 10px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            font-size: 0.85em;
        }}
        
        .bibliography-link {{
            color: #e00;
            text-decoration: none;
            word-break: break-all;
            border-bottom: 1px solid #e00;
        }}
        
        .bibliography-link:hover {{
            background: #e00;
            color: #fff;
        }}
        
        /* Footer */
        .footer {{
            text-align: center;
            padding: 60px 20px;
            color: #999;
            font-size: 0.85em;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            border-top: 1px solid #e0e0e0;
            margin-top: 80px;
        }}
        
        /* Responsive */
        @media (max-width: 1200px) {{
            .container {{
                padding: 40px 40px;
            }}
            
            .section-title::before {{
                width: 30px;
            }}
            
            .funding-list {{
                grid-template-columns: 1fr;
                gap: 50px;
            }}
            
            .accelerator-grid {{
                grid-template-columns: repeat(2, 1fr);
                gap: 40px;
            }}
            
            .trend-grid {{
                grid-template-columns: repeat(2, 1fr);
            }}
            
            .trend-card:nth-child(4n) {{
                border-right: 1px solid #000;
            }}
            
            .trend-card:nth-child(2n) {{
                border-right: none;
            }}
            
            .trend-card:nth-last-child(-n+4) {{
                border-bottom: 1px solid #000;
            }}
            
            .trend-card:nth-last-child(-n+2) {{
                border-bottom: none;
            }}
        }}
        
        @media (max-width: 768px) {{
            .container {{
                padding: 30px 20px;
            }}
            
            .header h1 {{
                font-size: 2.5em;
            }}
            
            .section-title {{
                font-size: 1.8em;
                padding-left: 0;
            }}
            
            .section-title::before {{
                display: none;
            }}
            
            .main-content {{
                padding: 0;
            }}
            
            .funding-list {{
                gap: 40px;
            }}
            
            .trend-grid {{
                grid-template-columns: 1fr;
            }}
            
            .trend-card {{
                border-right: none !important;
                border-bottom: 1px solid #000 !important;
            }}
            
            .trend-card:last-child {{
                border-bottom: none !important;
            }}
            
            .accelerator-grid {{
                grid-template-columns: 1fr;
                gap: 30px;
            }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <div class="container">
            <h1>{title}</h1>
            <div class="subtitle">{subtitle}</div>
            <div class="date">{date}</div>
        </div>
    </div>
    
    <div class="container">
        <div class="main-content">
            {funding_html}
            {trends_html}
            {events_html}
            {accelerators_html}
            {bibliography_html}
        </div>
    </div>
    
    <div class="footer">
        <div class="container">
            Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')} &bull; 
            Built for the startup community
        </div>
    </div>
</body>
</html>"""
    
    return html


def render_funding_section_html(items: List[FundingItem], get_citation) -> str:
    """Render funding section"""
    if not items:
        return '<div class="section"><p>No funding announcements this period.</p></div>'
    
    html = '''<div class="section">
        <div class="section-header">
            <div class="section-icon">💰</div>
            <h2 class="section-title">Funding Headlines</h2>
        </div>
        <div class="funding-list">'''
    
    for item in items:
        citations = ''.join([f'<a href="#source-{get_citation(url)}" class="citation">{get_citation(url)}</a>' 
                            for url in item.source_urls])
        
        investors_str = ', '.join(item.investors[:3]) if item.investors else "N/A"
        categories_str = ', '.join(item.categories[:2]) if item.categories else "General"
        
        www = item.who_what_why_when_where_how
        
        html += f'''
            <div class="funding-card">
                <div class="funding-header">
                    <h3 class="startup-name">{item.startup_name}</h3>
                    <div class="funding-amount">{item.amount}</div>
                </div>
                
                <div class="funding-meta">
                    <div class="funding-meta-item">
                        <span class="funding-meta-label">Round:</span> {item.round_type.title()}
                    </div>
                    {f'<div class="funding-meta-item"><span class="funding-meta-label">Lead:</span> {item.lead_investor}</div>' if item.lead_investor else ''}
                    {f'<div class="funding-meta-item"><span class="funding-meta-label">Location:</span> {item.location}</div>' if item.location else ''}
                    <div class="funding-meta-item">
                        <span class="tag">{categories_str}</span>
                    </div>
                </div>
                
                <div class="reporter-block">
                    <div class="reporter-line">
                        <span class="reporter-label">Who/What:</span> {www.who}. {www.what}
                    </div>
                    <div class="reporter-line">
                        <span class="reporter-label">Why/How:</span> {www.why} {www.how}
                    </div>
                    <div class="reporter-line">
                        <span class="reporter-label">When/Where:</span> {www.when}. {www.where}
                    </div>
                </div>
                
                <div style="margin-top: 12px;">
                    {citations}
                </div>
            </div>'''
    
    html += '</div></div>'
    return html


def render_trends_section_html(trend_data: Dict[str, int]) -> str:
    """Render trends section"""
    if not trend_data:
        return ''
    
    html = '''<div class="section">
        <div class="section-header">
            <div class="section-icon">📊</div>
            <h2 class="section-title">Trend Brief</h2>
        </div>
        <div class="trend-grid">'''
    
    for category, count in trend_data.items():
        html += f'''
            <div class="trend-card">
                <div class="trend-category">{category}</div>
                <div class="trend-count">{count}</div>
                <div class="trend-label">deal{'s' if count > 1 else ''}</div>
            </div>'''
    
    html += '</div></div>'
    return html


def render_events_section_html(items: List[EventItem], get_citation) -> str:
    """Render events section"""
    if not items:
        return '<div class="section"><p>No events scheduled.</p></div>'
    
    html = '''<div class="section">
        <div class="section-header">
            <div class="section-icon">🎯</div>
            <h2 class="section-title">Events & Rooms to Be In</h2>
        </div>
        <div class="events-list">'''
    
    for item in items:
        citation = f'<a href="#source-{get_citation(item.source_url)}" class="citation">{get_citation(item.source_url)}</a>'
        register_btn = f'<a href="{item.registration_url}" class="btn" target="_blank">Register</a>' if item.registration_url else ''
        
        html += f'''
            <div class="event-card">
                <h3 class="event-name">{item.event_name}</h3>
                <div class="event-details">
                    <div class="event-detail"><strong>📅</strong> {item.date_time}</div>
                    <div class="event-detail"><strong>📍</strong> {item.venue_or_online}</div>
                    <div class="event-detail"><strong>💵</strong> {item.cost}</div>
                </div>
                {f'<div class="event-description">{item.description}</div>' if item.description else ''}
                <div style="margin-top: 12px; display: flex; gap: 10px; align-items: center;">
                    {register_btn}
                    {citation}
                </div>
            </div>'''
    
    html += '</div></div>'
    return html


def render_accelerators_section_html(items: List[AcceleratorItem], get_citation) -> str:
    """Render accelerators section"""
    if not items:
        return '<div class="section"><p>No accelerator updates.</p></div>'
    
    html = '''<div class="section">
        <div class="section-header">
            <div class="section-icon">🚀</div>
            <h2 class="section-title">Accelerators Watch</h2>
        </div>
        <div class="accelerator-grid">'''
    
    for item in items:
        citation = f'<a href="#source-{get_citation(item.source_url)}" class="citation">{get_citation(item.source_url)}</a>'
        
        html += f'''
            <div class="accelerator-card">
                <h3 class="accelerator-name">{item.name}</h3>
                <div class="accelerator-meta">
                    {f'📍 {item.city_region}' if item.city_region else ''} 
                    {' &bull; ' if item.city_region and item.focus else ''}
                    {f'🎯 {item.focus}' if item.focus else ''}
                </div>
                {f'<div class="accelerator-description">{item.description}</div>' if item.description else ''}
                <div>
                    {citation}
                </div>
            </div>'''
    
    html += '</div></div>'
    return html


def render_bibliography_html(citation_map: Dict[str, int]) -> str:
    """Render bibliography section"""
    if not citation_map:
        return ''
    
    html = '''<div class="section bibliography">
        <div class="section-header">
            <div class="section-icon">📚</div>
            <h2 class="section-title">Sources & Bibliography</h2>
        </div>'''
    
    sorted_citations = sorted(citation_map.items(), key=lambda x: x[1])
    
    for url, number in sorted_citations:
        # Extract source name
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
        
        html += f'''
            <div class="bibliography-item" id="source-{number}">
                <div class="bibliography-number">{number}</div>
                <div style="flex: 1;">
                    <span class="bibliography-source">{source_name}</span>
                    <a href="{url}" class="bibliography-link" target="_blank">{url}</a>
                </div>
            </div>'''
    
    html += '</div>'
    return html
