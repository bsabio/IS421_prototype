#!/usr/bin/env python3
"""Quick generator to create newsletter HTML from demo data"""
import json
from pathlib import Path
from datetime import datetime
import sys

# Import the demo data generator
from demo_data import (
    create_demo_funding_items,
    create_demo_events, 
    create_demo_accelerators,
    create_demo_trend_data
)
from newsroom.web_template import render_html_page
from newsroom.utils import load_config

def main():
    """Generate HTML newsletter from demo data"""
    print("=== Generating Newsletter HTML ===")
    print()
    
    # Load config
    config = load_config()
    
    # Create demo data
    print("Loading demo data...")
    funding_items = create_demo_funding_items()
    event_items = create_demo_events()
    accelerator_items = create_demo_accelerators()
    trend_data = create_demo_trend_data()
    
    print(f"  - {len(funding_items)} funding stories")
    print(f"  - {len(event_items)} events")
    print(f"  - {len(accelerator_items)} accelerators")
    print()
    
    # Render HTML
    print("Rendering HTML...")
    html_content = render_html_page(
        funding_items,
        event_items,
        accelerator_items,
        trend_data,
        config
    )
    
    # Save output
    output_dir = Path(config['output']['output_dir'])
    output_dir.mkdir(exist_ok=True)
    
    html_file = output_dir / 'newsletter.html'
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✓ HTML saved to: {html_file}")
    print()
    print("=== Generation Complete ===")
    print()

if __name__ == '__main__':
    main()
