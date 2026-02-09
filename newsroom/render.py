"""
Render module - Generate newsletter output
Usage: python -m newsroom.render --format md
"""
import argparse
import json
from pathlib import Path
from datetime import datetime
from typing import List

from .models import FundingItem, EventItem, AcceleratorItem
from .templates import render_markdown, render_html
from .web_template import render_html_page
from .utils import load_config


def main():
    parser = argparse.ArgumentParser(
        description='Render newsletter to output format'
    )
    parser.add_argument(
        '--format',
        type=str,
        default='md',
        choices=['md', 'html', 'both'],
        help='Output format (md, html, or both)'
    )
    
    args = parser.parse_args()
    
    print("=== AI Factory Newsletter - Rendering ===")
    print(f"Generating newsletter in {args.format} format...")
    print()
    
    config = load_config()
    data_dir = Path(config['storage']['data_dir'])
    output_dir = Path(config['output']['output_dir'])
    output_dir.mkdir(exist_ok=True)
    
    # Load ranked data
    ranked_file = data_dir / 'ranked.json'
    
    if not ranked_file.exists():
        print("No ranked data found. Run: python -m newsroom.rank first")
        return
    
    with open(ranked_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Convert to objects
    funding_items = [FundingItem.from_dict(item) for item in data.get('funding', [])]
    event_items = [EventItem.from_dict(item) for item in data.get('events', [])]
    accelerator_items = [AcceleratorItem.from_dict(item) for item in data.get('accelerators', [])]
    trend_data = data.get('trend_brief', {})
    
    print(f"Rendering newsletter with:")
    print(f"  - {len(funding_items)} funding stories")
    print(f"  - {len(event_items)} events")
    print(f"  - {len(accelerator_items)} accelerators")
    print(f"  - {len(trend_data)} trending categories")
    print()
    
    # Render markdown
    markdown_content = render_markdown(
        funding_items, event_items, accelerator_items, trend_data, config
    )
    
    # Save markdown
    if args.format in ['md', 'both']:
        md_file = output_dir / 'newsletter.md'
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        print(f"✓ Markdown saved to: {md_file}")
    
    # Save HTML
    if args.format in ['html', 'both']:
        # Use modern web template instead of simple markdown wrapper
        html_content = render_html_page(
            funding_items, event_items, accelerator_items, trend_data, config
        )
        html_file = output_dir / 'newsletter.html'
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"✓ HTML saved to: {html_file}")
    
    print()
    print("=== Newsletter Generation Complete ===")
    print()
    print("Your newsletter is ready! 🎉")


if __name__ == '__main__':
    main()
