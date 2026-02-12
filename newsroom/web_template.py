"""
Newsletter HTML renderer – journalist-style layout with editorial layer.

Produces a self-contained HTML page (no external dependencies) that reads
like a real newsletter issue: masthead, lead story, section flow, "why it
matters" callouts, key-number chips, and a full bibliography.

Public API (unchanged from previous version):
    render_html_page(funding_items, event_items, accelerator_items,
                     trend_data, config) -> str
"""

import re
from typing import List, Dict
from datetime import datetime

from .models import FundingItem, EventItem, AcceleratorItem
from .editorial import (
    CitationTracker, StoryCard, Citation,
    funding_to_story, event_to_story, accelerator_to_story,
    build_editors_note, build_trend_prose, transition,
    group_by_round, issue_number, issue_date, _cat_label,
)

# ═════════════════════════════════════════════════════════════════
# CSS  (plain string – no f-string, so CSS braces are literal)
# ═════════════════════════════════════════════════════════════════

_CSS = """
/* ── Reset + Base ─────────────────────────────────────────── */
*, *::before, *::after { margin: 0; padding: 0; box-sizing: border-box; }

:root {
    --serif: Georgia, 'Times New Roman', 'Noto Serif', serif;
    --sans: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto,
            'Helvetica Neue', Arial, sans-serif;
    --text: #1a1a1a;
    --text-2: #555;
    --text-3: #888;
    --accent: #c0392b;
    --accent-hover: #a93226;
    --accent-light: #fef3e8;
    --bg: #fff;
    --bg-warm: #faf8f5;
    --border: #e0dcd4;
    --max-w: 720px;
    --lh: 1.72;
}

body {
    font-family: var(--sans);
    font-size: 1rem;
    line-height: var(--lh);
    color: var(--text);
    background: var(--bg);
    -webkit-font-smoothing: antialiased;
}

a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }
img { max-width: 100%; }

/* ── Container ────────────────────────────────────────────── */
.container { max-width: var(--max-w); margin: 0 auto; padding: 0 24px; }

/* ── Masthead ─────────────────────────────────────────────── */
.masthead {
    border-top: 4px solid var(--accent);
    padding: 48px 0 0;
    text-align: center;
}
.masthead-title {
    font-family: var(--serif);
    font-size: 2.6rem;
    font-weight: 700;
    letter-spacing: -0.02em;
    line-height: 1.15;
    margin-bottom: 6px;
}
.masthead-subtitle {
    font-size: 0.95rem;
    color: var(--text-2);
    margin-bottom: 12px;
}
.issue-meta {
    font-size: 0.8rem;
    color: var(--text-3);
    text-transform: uppercase;
    letter-spacing: 0.08em;
}
.issue-meta .sep { margin: 0 6px; color: var(--border); }
.masthead-rule {
    width: 100%;
    height: 1px;
    background: var(--border);
    margin-top: 28px;
}

/* ── Editor's Note ────────────────────────────────────────── */
.editors-note {
    background: var(--bg-warm);
    border-left: 3px solid var(--accent);
    padding: 24px 28px;
    margin: 36px 0;
    border-radius: 0 4px 4px 0;
}
.editors-note h2 {
    font-family: var(--serif);
    font-size: 1.1rem;
    font-weight: 700;
    margin-bottom: 8px;
    color: var(--accent);
    text-transform: uppercase;
    letter-spacing: 0.04em;
}
.editors-note p {
    font-size: 0.98rem;
    color: var(--text);
    line-height: 1.65;
}

/* ── Table of Contents ────────────────────────────────────── */
.toc {
    margin: 28px 0 36px;
    padding: 20px 28px;
    border: 1px solid var(--border);
    border-radius: 4px;
}
.toc h3 {
    font-family: var(--serif);
    font-size: 0.95rem;
    font-weight: 700;
    margin-bottom: 10px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--text-2);
}
.toc ol {
    list-style: none;
    counter-reset: toc-counter;
    padding: 0;
}
.toc li {
    counter-increment: toc-counter;
    margin-bottom: 4px;
    font-size: 0.9rem;
}
.toc li::before {
    content: counter(toc-counter) ". ";
    color: var(--accent);
    font-weight: 700;
    font-size: 0.85rem;
}
.toc a {
    color: var(--text);
    border-bottom: 1px solid transparent;
}
.toc a:hover {
    text-decoration: none;
    border-bottom-color: var(--accent);
}

/* ── Section Rule ─────────────────────────────────────────── */
.section-rule {
    border: none;
    border-top: 1px solid var(--border);
    margin: 40px 0;
}

/* ── Section Label ────────────────────────────────────────── */
.section-label {
    display: block;
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: var(--accent);
    margin-bottom: 10px;
}

/* ── Section Transition ───────────────────────────────────── */
.section-transition {
    font-size: 0.95rem;
    font-style: italic;
    color: var(--text-2);
    margin-bottom: 28px;
    line-height: 1.6;
}

/* ── Hero / Lead Story ────────────────────────────────────── */
.lead-story { margin-bottom: 0; }
.hero-card { padding: 32px 0; }
.hero-headline {
    font-family: var(--serif);
    font-size: 2rem;
    font-weight: 700;
    line-height: 1.2;
    letter-spacing: -0.01em;
    margin-bottom: 12px;
}
.hero-dek {
    font-family: var(--serif);
    font-size: 1.15rem;
    font-style: italic;
    color: var(--text-2);
    margin-bottom: 18px;
    line-height: 1.55;
}

/* ── Chips ─────────────────────────────────────────────────── */
.chips {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-bottom: 20px;
}
.chip {
    display: inline-block;
    padding: 4px 12px;
    font-size: 0.78rem;
    font-weight: 600;
    border-radius: 3px;
    white-space: nowrap;
}
.chip-amount {
    background: #fef3e8;
    color: #b7472a;
    border: 1px solid #f0d4b8;
}
.chip-round {
    background: #eef4fb;
    color: #2c5282;
    border: 1px solid #bdd5ea;
}
.chip-tag {
    background: #f0f0ec;
    color: #555;
    border: 1px solid #ddddd4;
}

/* ── Story Card ───────────────────────────────────────────── */
.story-card {
    padding: 28px 0;
    border-bottom: 1px solid var(--border);
}
.story-card:last-child { border-bottom: none; }
.story-headline {
    font-family: var(--serif);
    font-size: 1.35rem;
    font-weight: 700;
    line-height: 1.25;
    margin-bottom: 8px;
}
.story-dek {
    font-family: var(--serif);
    font-size: 1rem;
    font-style: italic;
    color: var(--text-2);
    margin-bottom: 14px;
    line-height: 1.5;
}
.story-lede {
    margin-bottom: 16px;
    line-height: var(--lh);
}
.story-context {
    font-size: 0.92rem;
    color: var(--text-2);
    margin-bottom: 14px;
    line-height: 1.65;
}

/* ── Why It Matters ───────────────────────────────────────── */
.why-it-matters {
    background: var(--bg-warm);
    border-left: 3px solid var(--accent);
    padding: 14px 18px;
    margin: 16px 0;
    border-radius: 0 4px 4px 0;
}
.why-it-matters h4 {
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--accent);
    margin-bottom: 4px;
}
.why-it-matters p {
    font-size: 0.95rem;
    line-height: 1.6;
    color: var(--text);
}

/* ── Key Details ──────────────────────────────────────────── */
.key-details {
    list-style: none;
    padding: 0;
    margin: 14px 0;
}
.key-details li {
    position: relative;
    padding-left: 16px;
    margin-bottom: 4px;
    font-size: 0.9rem;
    color: var(--text);
}
.key-details li::before {
    content: '\\2013';
    position: absolute;
    left: 0;
    color: var(--accent);
    font-weight: 700;
}

/* ── Story Sources ────────────────────────────────────────── */
.story-sources {
    font-size: 0.8rem;
    color: var(--text-3);
    margin-top: 10px;
}
.story-sources a { font-size: 0.8rem; }
.cite-sup {
    font-size: 0.7rem;
    vertical-align: super;
    font-weight: 700;
    margin-left: 1px;
}

/* ── Funding Radar sub-group ──────────────────────────────── */
.radar-group { margin-bottom: 32px; }
.radar-group-title {
    font-family: var(--serif);
    font-size: 1.05rem;
    font-weight: 700;
    color: var(--text-2);
    text-transform: uppercase;
    letter-spacing: 0.04em;
    padding-bottom: 6px;
    border-bottom: 2px solid var(--accent);
    margin-bottom: 0;
    display: inline-block;
}
.radar-card {
    padding: 20px 0;
    border-bottom: 1px solid var(--border);
}
.radar-card:last-child { border-bottom: none; }
.radar-headline {
    font-family: var(--serif);
    font-size: 1.1rem;
    font-weight: 700;
    margin-bottom: 6px;
}
.radar-lede {
    font-size: 0.92rem;
    margin-bottom: 10px;
    line-height: 1.6;
}

/* ── Trend Brief ──────────────────────────────────────────── */
.trend-prose {
    margin-bottom: 20px;
    line-height: var(--lh);
}
.trend-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
    gap: 12px;
    margin: 20px 0;
}
.trend-chip {
    text-align: center;
    padding: 18px 8px;
    border: 1px solid var(--border);
    border-radius: 4px;
    background: var(--bg-warm);
}
.trend-chip-count {
    font-size: 1.8rem;
    font-weight: 700;
    color: var(--accent);
    line-height: 1;
    margin-bottom: 4px;
}
.trend-chip-label {
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--text-2);
}

/* ── Event Card ───────────────────────────────────────────── */
.event-card {
    padding: 24px 0;
    border-bottom: 1px solid var(--border);
}
.event-card:last-child { border-bottom: none; }
.event-headline {
    font-family: var(--serif);
    font-size: 1.2rem;
    font-weight: 700;
    margin-bottom: 6px;
}
.event-dek {
    font-style: italic;
    color: var(--text-2);
    margin-bottom: 12px;
    font-size: 0.95rem;
}
.event-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 16px;
    font-size: 0.85rem;
    margin-bottom: 12px;
}
.event-meta-item {
    display: flex;
    align-items: center;
    gap: 4px;
}
.event-meta-icon { font-size: 0.9rem; }
.event-btn {
    display: inline-block;
    background: var(--accent);
    color: #fff;
    padding: 6px 16px;
    border-radius: 3px;
    font-size: 0.8rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-top: 8px;
}
.event-btn:hover {
    background: var(--accent-hover);
    text-decoration: none;
}

/* ── Accelerator Card ─────────────────────────────────────── */
.accel-card {
    padding: 24px 0;
    border-bottom: 1px solid var(--border);
}
.accel-card:last-child { border-bottom: none; }
.accel-headline {
    font-family: var(--serif);
    font-size: 1.15rem;
    font-weight: 700;
    margin-bottom: 4px;
}
.accel-focus {
    font-size: 0.8rem;
    color: var(--text-2);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 10px;
}

/* ── Bibliography ─────────────────────────────────────────── */
.bibliography { margin-top: 40px; }
.bib-list { list-style: none; padding: 0; }
.bib-item {
    display: flex;
    gap: 12px;
    padding: 10px 0;
    border-bottom: 1px solid var(--border);
    font-size: 0.85rem;
    align-items: baseline;
}
.bib-item:last-child { border-bottom: none; }
.bib-num {
    background: var(--accent);
    color: #fff;
    font-size: 0.7rem;
    font-weight: 700;
    min-width: 26px;
    height: 20px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border-radius: 2px;
    flex-shrink: 0;
}
.bib-source {
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    font-size: 0.78rem;
    margin-right: 6px;
    color: var(--text);
}
.bib-link {
    word-break: break-all;
    color: var(--accent);
    font-size: 0.82rem;
}

/* ── Footer ───────────────────────────────────────────────── */
.footer {
    text-align: center;
    padding: 40px 24px;
    margin-top: 48px;
    border-top: 1px solid var(--border);
    font-size: 0.8rem;
    color: var(--text-3);
}
.footer-line { margin-bottom: 4px; }

/* ── Responsive ───────────────────────────────────────────── */
@media (max-width: 640px) {
    .container { padding: 0 16px; }
    .masthead-title { font-size: 1.8rem; }
    .hero-headline { font-size: 1.5rem; }
    .story-headline { font-size: 1.15rem; }
    .editors-note, .why-it-matters { padding: 16px 18px; }
    .toc { padding: 16px 18px; }
    .event-meta { flex-direction: column; gap: 6px; }
    .trend-grid { grid-template-columns: repeat(2, 1fr); }
    .chips { gap: 6px; }
}

/* ── Print ────────────────────────────────────────────────── */
@media print {
    body { font-size: 11pt; color: #000; }
    .masthead { border-top: 2pt solid #000; }
    .toc, .event-btn { display: none; }
    a { color: #000; text-decoration: underline; }
    .why-it-matters, .editors-note {
        background: #f5f5f5;
        border-left: 2pt solid #000;
    }
    .chip { border: 1px solid #999; background: #f5f5f5; color: #000; }
    .story-card, .event-card, .accel-card, .hero-card,
    .radar-card { page-break-inside: avoid; }
    .section-rule { border-top: 0.5pt solid #ccc; }
    .bib-num { background: #000; }
    .story-sources a::after {
        content: " (" attr(href) ")";
        font-size: 0.75em;
        color: #555;
    }
    .footer { border-top: 0.5pt solid #ccc; }
}
"""

# ═════════════════════════════════════════════════════════════════
# HTML helpers
# ═════════════════════════════════════════════════════════════════

def _cite_source_line(citations: List[Citation]) -> str:
    """Render 'Sources: TechCrunch [1], AlleyWatch [2]' line."""
    if not citations:
        return ''
    parts = [
        f'{c.source} <a href="#src-{c.number}" class="cite-sup">[{c.number}]</a>'
        for c in citations
    ]
    return '<div class="story-sources">Sources: ' + ', '.join(parts) + '</div>'


def _chips_html(card: StoryCard) -> str:
    """Render key-number chips for a funding story."""
    chips = []
    if card.amount:
        chips.append(f'<span class="chip chip-amount">{card.amount}</span>')
    if card.round_type:
        chips.append(f'<span class="chip chip-round">{card.round_type}</span>')
    for tag in card.tags[:2]:
        chips.append(f'<span class="chip chip-tag">{tag}</span>')
    if not chips:
        return ''
    return '<div class="chips">\n' + '\n'.join(chips) + '\n</div>'


def _details_html(details: List[str]) -> str:
    """Render key-details bullet list; auto-links Apply: URLs."""
    items = []
    for d in details:
        if d.startswith('Apply: ') and d[7:].startswith('http'):
            url = d[7:]
            items.append(f'<li>Apply: <a href="{url}" target="_blank">{url}</a></li>')
        else:
            items.append(f'<li>{d}</li>')
    return '<ul class="key-details">\n' + '\n'.join(items) + '\n</ul>'


def _why_html(text: str, label: str = 'Here\u2019s What This Means') -> str:
    return (
        f'<aside class="why-it-matters">\n'
        f'  <h4>{label}</h4>\n'
        f'  <p>{text}</p>\n'
        f'</aside>'
    )


# ── section renderers ────────────────────────────────────────────

def _hero_html(card: StoryCard) -> str:
    ctx = f'<p class="story-context">{card.context}</p>' if card.context else ''
    return (
        f'<section id="lead" class="lead-story">\n'
        f'  <span class="section-label">Lead Story</span>\n'
        f'  <article class="hero-card">\n'
        f'    <h2 class="hero-headline">{card.headline}</h2>\n'
        f'    <p class="hero-dek">{card.dek}</p>\n'
        f'    {_chips_html(card)}\n'
        f'    <p class="story-lede">{card.lede}</p>\n'
        f'    {ctx}\n'
        f'    {_why_html(card.why_it_matters)}\n'
        f'    {_details_html(card.key_details)}\n'
        f'    {_cite_source_line(card.citations)}\n'
        f'  </article>\n'
        f'</section>'
    )


def _story_html(card: StoryCard) -> str:
    chips = _chips_html(card) if card.card_type == 'funding' else ''
    ctx = f'<p class="story-context">{card.context}</p>' if card.context else ''
    return (
        f'<article class="story-card">\n'
        f'  <h3 class="story-headline">{card.headline}</h3>\n'
        f'  <p class="story-dek">{card.dek}</p>\n'
        f'  {chips}\n'
        f'  <p class="story-lede">{card.lede}</p>\n'
        f'  {ctx}\n'
        f'  {_why_html(card.why_it_matters)}\n'
        f'  {_details_html(card.key_details)}\n'
        f'  {_cite_source_line(card.citations)}\n'
        f'</article>'
    )


def _radar_card_html(card: StoryCard) -> str:
    return (
        f'<div class="radar-card">\n'
        f'  <h4 class="radar-headline">{card.headline}</h4>\n'
        f'  <p class="radar-lede">{card.lede}</p>\n'
        f'  {_why_html(card.why_it_matters)}\n'
        f'  {_cite_source_line(card.citations)}\n'
        f'</div>'
    )


def _event_html(card: StoryCard) -> str:
    reg = (
        f'<a href="{card.registration_url}" class="event-btn" '
        f'target="_blank">Register \u2192</a>'
    ) if card.registration_url else ''
    return (
        f'<article class="event-card">\n'
        f'  <h3 class="event-headline">{card.headline}</h3>\n'
        f'  <p class="event-dek">{card.dek}</p>\n'
        f'  <div class="event-meta">\n'
        f'    <span class="event-meta-item"><span class="event-meta-icon">\U0001F4C5</span> {card.date}</span>\n'
        f'    <span class="event-meta-item"><span class="event-meta-icon">\U0001F4CD</span> {card.venue}</span>\n'
        f'    <span class="event-meta-item"><span class="event-meta-icon">\U0001F4B5</span> {card.cost}</span>\n'
        f'  </div>\n'
        f'  {_why_html(card.why_it_matters, "Why You Should Be There")}\n'
        f'  {_cite_source_line(card.citations)}\n'
        f'  {reg}\n'
        f'</article>'
    )


def _accel_html(card: StoryCard) -> str:
    focus = (
        f'<div class="accel-focus">{card.category}</div>'
    ) if card.category else ''
    return (
        f'<article class="accel-card">\n'
        f'  <h3 class="accel-headline">{card.headline}</h3>\n'
        f'  {focus}\n'
        f'  <p class="story-lede">{card.lede}</p>\n'
        f'  {_why_html(card.why_it_matters)}\n'
        f'  {_details_html(card.key_details)}\n'
        f'  {_cite_source_line(card.citations)}\n'
        f'</article>'
    )


# ── event chronological sort ────────────────────────────────────

def _event_sort_key(card: StoryCard):
    """Sort events by extracted day number; recurring events go last."""
    m = re.search(r'(?:January|February|March|April|May)\s+(\d+)', card.date)
    return (0, int(m.group(1))) if m else (1, 0)


# ═════════════════════════════════════════════════════════════════
# Main public function
# ═════════════════════════════════════════════════════════════════

def render_html_page(
    funding_items: List[FundingItem],
    event_items: List[EventItem],
    accelerator_items: List[AcceleratorItem],
    trend_data: Dict[str, int],
    config: Dict,
) -> str:
    """Render complete newsletter as a self-contained HTML page."""

    tracker = CitationTracker()

    # ── convert items to StoryCards ──────────────────────────────
    funding_cards = [funding_to_story(i, tracker) for i in funding_items]
    event_cards = sorted(
        [event_to_story(i, tracker) for i in event_items],
        key=_event_sort_key,
    )
    accel_cards = [accelerator_to_story(i, tracker) for i in accelerator_items]

    # ── split funding into lead / top / radar ───────────────────
    lead_card = funding_cards[0] if funding_cards else None
    top_cards = funding_cards[1:4] if len(funding_cards) > 1 else []
    radar_cards = funding_cards[4:] if len(funding_cards) > 4 else []

    # ── metadata ────────────────────────────────────────────────
    title = config['newsletter']['title']
    subtitle = config['newsletter']['subtitle']
    date_str = issue_date()
    num = issue_number()

    # ── editorial prose ─────────────────────────────────────────
    en = build_editors_note(funding_items, event_items, accelerator_items, trend_data)
    tp = build_trend_prose(trend_data)

    # ── build HTML sections ─────────────────────────────────────

    # Lead story
    lead_html = _hero_html(lead_card) if lead_card else ''

    # Top stories
    if top_cards:
        top_stories_html = (
            '<hr class="section-rule">\n'
            '<section id="top-stories">\n'
            '  <span class="section-label">Top Stories</span>\n'
            f'  <p class="section-transition">{transition("top_stories")}</p>\n'
            + ''.join(_story_html(c) for c in top_cards) +
            '\n</section>'
        )
    else:
        top_stories_html = ''

    # Funding radar (grouped by stage)
    if radar_cards:
        groups = group_by_round(radar_cards)
        radar_inner = ''
        for stage, cards in groups:
            radar_inner += (
                f'<div class="radar-group">\n'
                f'  <h3 class="radar-group-title">{stage}</h3>\n'
                + ''.join(_radar_card_html(c) for c in cards)
                + '\n</div>\n'
            )
        radar_html = (
            '<hr class="section-rule">\n'
            '<section id="funding-radar">\n'
            '  <span class="section-label">Funding Radar</span>\n'
            f'  <p class="section-transition">{transition("funding_radar")}</p>\n'
            + radar_inner +
            '</section>'
        )
    else:
        radar_html = ''

    # Trend brief
    if trend_data:
        trend_chips = ''
        for cat, count in trend_data.items():
            label = _cat_label(cat)
            trend_chips += (
                f'<div class="trend-chip">\n'
                f'  <div class="trend-chip-count">{count}</div>\n'
                f'  <div class="trend-chip-label">{label}</div>\n'
                f'</div>\n'
            )
        trends_html = (
            '<hr class="section-rule">\n'
            '<section id="trends">\n'
            '  <span class="section-label">Trend Brief</span>\n'
            f'  <p class="section-transition">{transition("trend_brief")}</p>\n'
            f'  <p class="trend-prose">{tp}</p>\n'
            f'  <div class="trend-grid">\n{trend_chips}</div>\n'
            '</section>'
        )
    else:
        trends_html = ''

    # Events
    if event_cards:
        events_html = (
            '<hr class="section-rule">\n'
            '<section id="events">\n'
            '  <span class="section-label">Events This Week</span>\n'
            f'  <p class="section-transition">{transition("events")}</p>\n'
            + ''.join(_event_html(c) for c in event_cards)
            + '\n</section>'
        )
    else:
        events_html = ''

    # Accelerators
    if accel_cards:
        accels_html = (
            '<hr class="section-rule">\n'
            '<section id="accelerators">\n'
            '  <span class="section-label">Accelerator Watch</span>\n'
            f'  <p class="section-transition">{transition("accelerators")}</p>\n'
            + ''.join(_accel_html(c) for c in accel_cards)
            + '\n</section>'
        )
    else:
        accels_html = ''

    # Bibliography
    all_cites = tracker.all
    if all_cites:
        bib_items = ''
        for c in all_cites:
            bib_items += (
                f'<li class="bib-item" id="src-{c.number}">\n'
                f'  <span class="bib-num">{c.number}</span>\n'
                f'  <div>\n'
                f'    <span class="bib-source">{c.source}</span>\n'
                f'    <a href="{c.url}" class="bib-link" target="_blank">{c.url}</a>\n'
                f'  </div>\n'
                f'</li>\n'
            )
        bib_html = (
            '<hr class="section-rule">\n'
            '<section id="sources" class="bibliography">\n'
            '  <span class="section-label">Sources &amp; Bibliography</span>\n'
            f'  <ul class="bib-list">\n{bib_items}</ul>\n'
            '</section>'
        )
    else:
        bib_html = ''

    # Table of contents
    toc_items = []
    if lead_card:
        short = lead_card.headline[:60] + ('...' if len(lead_card.headline) > 60 else '')
        toc_items.append(f'<li><a href="#lead">Lead: {short}</a></li>')
    if top_cards:
        toc_items.append('<li><a href="#top-stories">Top Stories</a></li>')
    if radar_cards:
        toc_items.append('<li><a href="#funding-radar">Funding Radar</a></li>')
    if trend_data:
        toc_items.append('<li><a href="#trends">Trend Brief</a></li>')
    if event_cards:
        toc_items.append('<li><a href="#events">Events This Week</a></li>')
    if accel_cards:
        toc_items.append('<li><a href="#accelerators">Accelerator Watch</a></li>')
    if all_cites:
        toc_items.append('<li><a href="#sources">Sources</a></li>')
    toc_html = (
        '<nav class="toc">\n'
        '  <h3>In This Issue</h3>\n'
        '  <ol>\n    ' + '\n    '.join(toc_items) + '\n  </ol>\n'
        '</nav>'
    )

    # ── assemble full page ──────────────────────────────────────
    gen_ts = datetime.now().strftime('%B %d, %Y at %I:%M %p')

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} \u2014 Issue #{num}</title>
    <style>{_CSS}
    </style>
</head>
<body>

<header class="masthead">
    <div class="container">
        <h1 class="masthead-title">{title}</h1>
        <p class="masthead-subtitle">{subtitle}</p>
        <div class="issue-meta">
            <span>Issue #{num}</span>
            <span class="sep">&middot;</span>
            <span>{date_str}</span>
            <span class="sep">&middot;</span>
            <span>Anchored by Lester Holt \u2014 AI Factory Newsroom</span>
        </div>
        <div class="masthead-rule"></div>
    </div>
</header>

<main class="container">

    <section class="editors-note">
        <h2>From the Anchor Desk</h2>
        <p>{en}</p>
    </section>

    {toc_html}

    {lead_html}
    {top_stories_html}
    {radar_html}
    {trends_html}
    {events_html}
    {accels_html}
    {bib_html}

</main>

<footer class="footer">
    <div class="container">
        <div class="footer-line">Generated on {gen_ts}</div>
        <div class="footer-line">{title} &bull; Thank you for being here with us tonight</div>
    </div>
</footer>

</body>
</html>"""
