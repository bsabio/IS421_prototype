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
import json
import urllib.parse
from html import escape
from pathlib import Path
from typing import List, Dict
from datetime import datetime

try:
    from dateutil.parser import parse as _parse_datetime
except Exception:
    _parse_datetime = None

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
    --text: #111;
    --text-2: #2a2a2a;
    --text-3: #666;
    --accent: #e10600;
    --accent-hover: #b30400;
    --accent-light: #fff1f0;
    --bg: #fff;
    --bg-warm: #f8f8f8;
    --border: #d6d6d6;
    --max-w: 980px;
    --lh: 1.62;
}

body {
    font-family: var(--sans);
    font-size: 1rem;
    line-height: var(--lh);
    color: var(--text);
    background: var(--bg);
    -webkit-font-smoothing: antialiased;
}

a { color: var(--accent); text-decoration: underline; text-underline-offset: 2px; }
a:hover { color: var(--accent-hover); }
img { max-width: 100%; }

/* ── Container ────────────────────────────────────────────── */
.container { max-width: var(--max-w); margin: 0 auto; padding: 0 24px; }

/* ── Masthead ─────────────────────────────────────────────── */
.masthead {
    border-top: 4px solid var(--accent);
    border-bottom: 2px solid var(--text);
    padding: 22px 0 12px;
    text-align: center;
}
.masthead-title {
    font-family: var(--sans);
    font-size: 3.25rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    line-height: 1;
    margin-bottom: 10px;
}
.masthead-subtitle {
    font-size: 0.74rem;
    color: var(--text-2);
    margin-bottom: 10px;
    text-transform: uppercase;
    letter-spacing: 0.16em;
    text-align: center;
}
.masthead-slogan {
    font-family: var(--sans);
    font-size: 1rem;
    color: var(--accent);
    font-weight: 700;
    font-style: italic;
    letter-spacing: 0.02em;
    text-align: center;
    margin: 0 0 12px;
}
.issue-meta {
    font-size: 0.72rem;
    color: var(--text-2);
    text-transform: uppercase;
    letter-spacing: 0.14em;
}
.issue-meta .sep { margin: 0 6px; color: var(--border); }
.masthead-rule {
    width: 100%;
    height: 1px;
    background: var(--border);
    margin-top: 14px;
}

/* ── Masthead Topic Nav ──────────────────────────────────── */
.masthead-topics {
    margin-top: 14px;
    background: #000;
}
.masthead-topics-list {
    list-style: none;
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: center;
    gap: 0;
}
.masthead-topics-list li {
    margin: 0;
}
.masthead-topic-link {
    display: inline-block;
    color: #fff;
    text-decoration: none;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-size: 0.76rem;
    font-weight: 700;
    padding: 12px 18px;
    border-bottom: 2px solid transparent;
}
.masthead-topic-link:hover,
.masthead-topic-link:focus-visible {
    color: #fff;
    background: #1f1f1f;
    border-bottom-color: var(--accent);
    outline: none;
}
.masthead-topic-link.is-active {
    color: #fff;
    background: #1f1f1f;
    border-bottom-color: var(--accent);
}

[data-page-group][hidden] {
    display: none !important;
}

/* ── Home Newspaper Experience ───────────────────────────── */
.home-page {
    margin: 22px 0 34px;
}
.home-subview.is-hidden {
    display: none;
}
.home-front-grid {
    display: grid;
    grid-template-columns: 1fr 2fr 1fr;
    gap: 16px;
}
.home-col-title {
    font-family: var(--serif);
    color: var(--accent);
    font-size: 2rem;
    margin-bottom: 10px;
    line-height: 1.1;
}
.home-col-link {
    border: 0;
    background: transparent;
    color: var(--accent);
    font-family: var(--serif);
    font-size: 2rem;
    margin-bottom: 10px;
    line-height: 1.1;
    cursor: pointer;
    text-align: left;
    padding: 0;
}
.home-front-lead {
    border-top: 2px solid var(--border);
    padding-top: 8px;
}
.home-front-lead-headline {
    font-family: var(--serif);
    font-size: 2rem;
    margin: 8px 0;
    line-height: 1.1;
}
.home-front-lead-body {
    color: var(--text-2);
    line-height: 1.6;
    font-size: 1rem;
}
.home-teaser {
    width: 100%;
    text-align: left;
    border: 1px solid var(--border);
    background: #fff;
    padding: 12px;
    margin-bottom: 10px;
    cursor: pointer;
}
.home-teaser:hover {
    border-color: var(--accent);
}
.home-teaser-kicker {
    color: var(--accent);
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 6px;
    font-weight: 700;
}
.home-teaser-headline {
    font-family: var(--serif);
    font-size: 1.05rem;
    line-height: 1.25;
    color: var(--text);
    margin-bottom: 6px;
}
.home-teaser-meta {
    font-size: 0.72rem;
    color: var(--text-3);
}
.home-view-head {
    display: flex;
    align-items: center;
    gap: 12px;
    margin: 10px 0 20px;
}
.home-back-btn {
    border: 1px solid var(--border);
    background: #fff;
    color: var(--text);
    font-size: 0.78rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-weight: 700;
    padding: 8px 12px;
    cursor: pointer;
}
.home-back-btn:hover {
    border-color: var(--accent);
    color: var(--accent);
}
.home-list-title {
    font-family: var(--serif);
    font-size: 2rem;
    color: var(--accent);
}
.home-list-item {
    display: grid;
    grid-template-columns: 170px 1fr;
    gap: 12px;
    border-top: 1px solid var(--border);
    padding: 14px 0;
    text-align: left;
    width: 100%;
    background: transparent;
    border-left: 0;
    border-right: 0;
    border-bottom: 0;
    cursor: pointer;
}
.home-list-thumb {
    background: linear-gradient(135deg, #ececec, #dcdcdc);
    border: 1px solid var(--border);
    min-height: 96px;
}
.home-list-headline {
    font-family: var(--serif);
    font-size: 1.8rem;
    line-height: 1.1;
    margin-bottom: 8px;
}
.home-list-summary {
    color: var(--text-2);
    font-size: 0.98rem;
    line-height: 1.6;
}
.home-article-wrap {
    max-width: 860px;
    margin: 0 auto;
}
.home-article-kicker {
    display: inline-block;
    background: var(--accent);
    color: #fff;
    font-weight: 700;
    font-size: 1rem;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    padding: 8px 12px;
    margin-bottom: 20px;
    border-radius: 3px;
}
.home-article-title {
    font-family: var(--serif);
    font-size: 3.2rem;
    line-height: 1.08;
    margin-bottom: 16px;
}
.home-article-dek {
    font-family: var(--sans);
    font-size: 1.15rem;
    line-height: 1.45;
    margin-bottom: 20px;
    color: var(--text-2);
}
.home-article-meta {
    font-size: 1rem;
    margin-bottom: 18px;
    color: var(--text);
}
.home-article-meta .author {
    color: var(--accent);
    font-weight: 700;
}
.home-article-meta .role {
    color: var(--text);
}
.home-article-image {
    border: 1px solid var(--border);
    background: linear-gradient(135deg, #f3f3f3, #e4e4e4);
    min-height: 520px;
    margin-bottom: 0;
}
.home-article-image img {
    display: block;
    width: 100%;
    height: 100%;
    min-height: 520px;
    object-fit: cover;
}
.home-article-caption {
    font-size: 0.88rem;
    color: var(--text-2);
    margin-bottom: 22px;
    padding: 8px 12px;
    background: #efefef;
    border-left: 1px solid var(--border);
    border-right: 1px solid var(--border);
    border-bottom: 1px solid var(--border);
}
.home-article-body p {
    font-family: var(--serif);
    font-size: 1.18rem;
    line-height: 1.6;
    margin-bottom: 18px;
}
.home-article-linkout {
    margin-top: 14px;
    font-size: 0.95rem;
}

/* ── Story Focus View ─────────────────────────────────────── */
.hero-card,
.story-card,
.radar-card,
.accel-card,
.event-card {
    cursor: pointer;
}
.story-focus-view {
    margin: 18px 0 26px;
    background: var(--bg-warm);
    padding: 26px 0 30px;
}
.story-focus-head {
    display: flex;
    align-items: center;
    gap: 12px;
    max-width: 760px;
    margin: 0 auto 18px;
}
.story-focus-back {
    border: 1px solid var(--border);
    background: #fff;
    color: var(--text);
    font-size: 0.78rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-weight: 700;
    padding: 8px 12px;
    cursor: pointer;
}
.story-focus-back:hover {
    border-color: var(--accent);
    color: var(--accent);
}
.story-focus-title {
    font-family: var(--serif);
    font-size: 1.6rem;
    color: var(--accent);
}
.story-focus-article {
    max-width: 760px;
    margin: 0 auto;
}
.story-focus-kicker {
    display: inline-block;
    background: var(--accent);
    color: #fff;
    font-size: 0.78rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    padding: 6px 10px;
    margin-bottom: 18px;
}
.story-focus-headline {
    font-family: var(--serif);
    font-size: 2.9rem;
    line-height: 1.08;
    margin-bottom: 14px;
}
.story-focus-dek {
    font-size: 1.05rem;
    line-height: 1.2;
    margin-bottom: 16px;
}
.story-focus-meta {
    font-size: 1rem;
    color: var(--text-2);
    margin-bottom: 18px;
}
.story-focus-meta .author {
    color: var(--accent);
    font-weight: 700;
}
.story-focus-image {
    width: 100%;
    min-height: 420px;
    background: linear-gradient(135deg, var(--bg-warm), var(--border));
    border: 1px solid var(--border);
    margin-bottom: 8px;
}
.story-focus-image img {
    display: block;
    width: 100%;
    height: 100%;
    min-height: 420px;
    object-fit: cover;
}
.story-focus-caption {
    font-size: 0.9rem;
    color: var(--text-2);
    margin-bottom: 18px;
}
.story-focus-body p {
    font-family: var(--serif);
    font-size: 1.06rem;
    line-height: 1.65;
    margin-bottom: 14px;
}
.story-focus-link {
    margin-top: 16px;
    font-size: 1rem;
}

/* ── Editor's Note ────────────────────────────────────────── */
.editors-note {
    background: transparent;
    border: none;
    border-left: 3px solid var(--accent);
    padding: 0 0 0 20px;
    margin: 32px 0;
}
.editors-note h2 {
    font-family: var(--sans);
    font-size: 0.7rem;
    font-weight: 700;
    margin-bottom: 10px;
    color: var(--accent);
    background: transparent;
    display: inline-block;
    padding: 0;
    text-transform: uppercase;
    letter-spacing: 0.16em;
}
.editors-note p {
    font-size: 1.05rem;
    color: var(--text);
    line-height: 1.7;
    font-family: var(--serif);
    font-style: italic;
}

/* ── Table of Contents ────────────────────────────────────── */
.toc {
    margin: 22px 0 30px;
    padding: 16px 18px;
    border: 1px solid var(--border);
    border-left: 4px solid var(--accent);
}
.toc h3 {
    font-family: var(--sans);
    font-size: 0.78rem;
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
    margin: 48px 0 32px 0;
    opacity: 0.4;
}

/* ── Section Label ────────────────────────────────────────── */
.section-label {
    display: inline;
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.16em;
    color: var(--accent);
    background: transparent;
    margin-bottom: 0;
    padding: 0;
    font-family: var(--sans);
    border-bottom: 2px solid var(--accent);
    padding-bottom: 2px;
}

/* ── Section Transition ───────────────────────────────────── */
.section-transition {
    font-size: 1.05rem;
    font-style: normal;
    color: var(--text);
    margin: 18px 0 32px 0;
    line-height: 1.65;
    font-family: var(--serif);
}

/* ── Hero / Lead Story ────────────────────────────────────── */
.lead-story { margin-bottom: 0; }
.hero-card { padding: 36px 0 48px 0; }
.hero-headline {
    font-family: var(--serif);
    font-size: 2.6rem;
    font-weight: 700;
    line-height: 1.15;
    letter-spacing: -0.02em;
    margin-bottom: 16px;
}
.hero-dek {
    font-family: var(--serif);
    font-size: 1.15rem;
    font-style: italic;
    color: var(--text-2);
    margin-bottom: 20px;
    line-height: 1.6;
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
    background: var(--accent-light);
    color: var(--accent);
    border: 1px solid #f4bfbc;
}
.chip-round {
    background: #f3f3f3;
    color: var(--text);
    border: 1px solid var(--border);
}
.chip-tag {
    background: #f3f3f3;
    color: #333;
    border: 1px solid var(--border);
}

/* ── Story Card ───────────────────────────────────────────── */
.story-card {
    padding: 36px 0;
    border-bottom: none;
}
.story-card:last-child { border-bottom: none; }
.story-headline {
    font-family: var(--serif);
    font-size: 1.4rem;
    font-weight: 700;
    line-height: 1.3;
    margin-bottom: 10px;
}
.story-dek {
    font-family: var(--serif);
    font-size: 1.05rem;
    font-style: italic;
    color: var(--text-2);
    margin-bottom: 16px;
    line-height: 1.55;
}
.story-lede {
    margin-bottom: 18px;
    line-height: var(--lh);
}
.story-context {
    font-size: 0.95rem;
    color: var(--text);
    margin-bottom: 16px;
    line-height: 1.68;
}

/* ── Why It Matters ───────────────────────────────────────── */
.why-it-matters {
    background: #fff;
    border-left: 4px solid var(--accent);
    padding: 14px 18px;
    margin: 16px 0;
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
    font-size: 0.7rem;
    color: var(--text-3);
    margin-top: 8px;
}
.story-sources a { font-size: 0.7rem; }
.cite-sup {
    font-size: 0.6rem;
    vertical-align: super;
    font-weight: 700;
    margin-left: 1px;
}

/* ── Funding Radar sub-group ──────────────────────────────── */
.radar-group { margin-bottom: 48px; }
.radar-group:last-child { margin-bottom: 0; }
.radar-group-title {
    font-family: var(--sans);
    font-size: 0.75rem;
    font-weight: 700;
    color: var(--accent);
    text-transform: uppercase;
    letter-spacing: 0.14em;
    padding-bottom: 4px;
    border-bottom: 2px solid var(--accent);
    margin-bottom: 20px;
    display: inline-block;
}
.radar-card {
    padding: 24px 0;
    border-bottom: none;
}
.radar-card:last-child { border-bottom: none; }
.radar-headline {
    font-family: var(--serif);
    font-size: 1.15rem;
    font-weight: 700;
    margin-bottom: 8px;
    line-height: 1.3;
}
.radar-lede {
    font-size: 0.95rem;
    margin-bottom: 12px;
    line-height: 1.65;
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

/* ── Models Benchmark ─────────────────────────────────────── */
.model-benchmark-note {
    margin: 14px 0 18px;
    color: var(--text-2);
    font-size: 0.96rem;
}
.benchmark-table {
    width: 100%;
    border-collapse: collapse;
    margin: 10px 0 16px;
    font-size: 0.92rem;
}
.benchmark-table th,
.benchmark-table td {
    border: 1px solid var(--border);
    padding: 10px 8px;
    text-align: left;
}
.benchmark-table th {
    font-size: 0.74rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--text-2);
    background: var(--bg-warm);
}
.benchmark-score {
    font-weight: 700;
    color: var(--text);
}
.benchmark-bar {
    width: 180px;
    height: 8px;
    border: 1px solid var(--border);
    background: #f2f2f2;
}
.benchmark-bar span {
    display: block;
    height: 100%;
    background: var(--accent);
}
.benchmark-defs {
    list-style: none;
    padding: 0;
    margin: 10px 0 0;
}
.benchmark-defs li {
    margin-bottom: 8px;
    font-size: 0.92rem;
}
.benchmark-defs strong {
    color: var(--text);
}

/* ── Event Card ───────────────────────────────────────────── */
.event-card {
    padding: 32px 0;
    border-bottom: none;
}
.event-card:last-child { border-bottom: none; }
.event-headline {
    font-family: var(--serif);
    font-size: 1.25rem;
    font-weight: 700;
    margin-bottom: 8px;
    line-height: 1.3;
}
.event-dek {
    font-style: italic;
    color: var(--text-2);
    margin-bottom: 14px;
    font-size: 1rem;
    line-height: 1.55;
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

/* ── Calendar Switcher ───────────────────────────────────── */
.calendar-toolbar {
    margin: 24px 0 18px;
    padding: 12px 18px;
    border-top: 1px solid var(--border);
    border-bottom: 1px solid var(--border);
    background: #efeeea;
}
.calendar-toolbar .section-label {
    margin: 0;
}
.calendar-switcher {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 12px;
}
.calendar-filter-group {
    display: flex;
    align-items: center;
    gap: 10px;
}
.calendar-filter-label {
    font-size: 0.9rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--text-2);
}
.calendar-filter-icon {
    font-size: 0.95rem;
    line-height: 1;
}
.calendar-filter-input-wrap {
    position: relative;
}
.calendar-filter-input {
    width: 176px;
    border: 1px solid var(--border);
    border-radius: 4px;
    background: #fff;
    color: var(--text);
    font-size: 1rem;
    font-weight: 500;
    padding: 10px 36px 10px 12px;
}
.calendar-filter-input::-webkit-calendar-picker-indicator {
    opacity: 0.01;
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    cursor: pointer;
}
.calendar-filter-input:focus {
    outline: none;
    border-color: var(--accent);
}
.calendar-filter-input-icon {
    position: absolute;
    right: 10px;
    top: 50%;
    transform: translateY(-50%);
    font-size: 0.95rem;
    pointer-events: none;
    color: var(--text-2);
}
.calendar-nav-btn {
    border: 1px solid var(--border);
    border-radius: 4px;
    background: var(--accent);
    color: #fff;
    font-size: 0.82rem;
    line-height: 1;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    padding: 10px 16px;
    cursor: pointer;
}
.calendar-nav-btn:hover {
    background: var(--accent-hover);
}
.calendar-nav-btn:disabled {
    opacity: 0.55;
    cursor: not-allowed;
}

/* ── Accelerator Card ─────────────────────────────────────── */
.accel-card {
    padding: 28px 0;
    border-bottom: none;
}
.accel-card:last-child { border-bottom: none; }
.accel-headline {
    font-family: var(--serif);
    font-size: 1.2rem;
    font-weight: 700;
    margin-bottom: 6px;
    line-height: 1.3;
}
.accel-focus {
    font-size: 0.8rem;
    color: var(--text-2);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 10px;
}

/* ── Bibliography ─────────────────────────────────────────── */
.bibliography { margin-top: 32px; }
.bib-list { list-style: none; padding: 0; }
.bib-item {
    display: flex;
    gap: 8px;
    padding: 6px 0;
    border-bottom: 1px solid var(--border);
    font-size: 0.72rem;
    align-items: baseline;
}
.bib-item:last-child { border-bottom: none; }
.bib-num {
    background: var(--accent);
    color: #fff;
    font-size: 0.6rem;
    font-weight: 700;
    min-width: 20px;
    height: 16px;
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
    font-size: 0.68rem;
    margin-right: 4px;
    color: var(--text);
}
.bib-link {
    word-break: break-all;
    color: var(--accent);
    font-size: 0.68rem;
}

/* ── Signup Form ──────────────────────────────────────────── */
.signup-section {
    background: var(--bg-warm);
    border-top: 2px solid var(--text);
    border-bottom: 2px solid var(--text);
    padding: 48px 24px;
    margin-top: 48px;
    text-align: center;
}
.signup-container {
    max-width: 520px;
    margin: 0 auto;
}
.signup-headline {
    font-family: var(--sans);
    font-size: 1.5rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 12px;
}
.signup-subtext {
    font-size: 0.95rem;
    color: var(--text-2);
    margin-bottom: 24px;
    line-height: 1.5;
}
.signup-form {
    display: flex;
    gap: 12px;
    justify-content: center;
    flex-wrap: wrap;
}
.signup-input {
    flex: 1;
    min-width: 240px;
    max-width: 320px;
    padding: 14px 16px;
    font-size: 1rem;
    font-family: var(--sans);
    border: 2px solid var(--text);
    background: var(--bg);
    outline: none;
    transition: border-color 0.2s;
}
.signup-input:focus {
    border-color: var(--accent);
}
.signup-input::placeholder {
    color: var(--text-3);
}
.signup-button {
    padding: 14px 28px;
    font-size: 0.85rem;
    font-weight: 700;
    font-family: var(--sans);
    text-transform: uppercase;
    letter-spacing: 0.1em;
    background: var(--accent);
    color: #fff;
    border: 2px solid var(--accent);
    cursor: pointer;
    transition: background 0.2s, border-color 0.2s;
}
.signup-button:hover {
    background: var(--accent-hover);
    border-color: var(--accent-hover);
}
.signup-privacy {
    font-size: 0.75rem;
    color: var(--text-3);
    margin-top: 16px;
}
.signup-success {
    display: none;
    padding: 16px;
    background: #f0fff4;
    border: 2px solid #22c55e;
    color: #166534;
    font-weight: 600;
}

/* ── Footer ───────────────────────────────────────────────── */
.footer {
    text-align: center;
    padding: 40px 24px;
    margin-top: 0;
    border-top: none;
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
    .masthead-topics-list {
        justify-content: center;
    }
    .masthead-topic-link {
        padding: 10px 12px;
        font-size: 0.72rem;
    }
    .calendar-switcher {
        align-items: stretch;
    }
    .calendar-filter-group {
        width: 100%;
        justify-content: space-between;
    }
}

/* ── Print ────────────────────────────────────────────────── */
@media print {
    body { font-size: 11pt; color: #000; }
    .masthead { border-top: 2pt solid #000; }
    .toc, .event-btn, .calendar-toolbar { display: none; }
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
        f'<a href="{c.url}" target="_blank" rel="noopener noreferrer">{c.source}</a> '
        f'<a href="{c.url}" target="_blank" rel="noopener noreferrer" class="cite-sup">[{c.number}]</a>'
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
        f'<section id="lead" class="lead-story" data-page-group="investments">\n'
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
    month_label = _event_month_label(card.date)
    month_key = _event_month_key(card.date)
    date_label = _event_date_label(card.date)
    date_key = _event_date_key(card.date)
    date_iso = _event_date_iso(card.date)
    reg = (
        f'<a href="{card.registration_url}" class="event-btn" '
        f'target="_blank">Register \u2192</a>'
    ) if card.registration_url else ''
    return (
        f'<article class="event-card" data-event-month-key="{month_key}" data-event-month-label="{month_label}" data-event-date-key="{date_key}" data-event-date-label="{date_label}" data-event-date-iso="{date_iso}">\n'
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


def _model_benchmarks_html() -> str:
    rows = [
        ("GPT-4.1", 1387, 89.4, 95.1, 92.2),
        ("Claude 3.7 Sonnet", 1331, 86.2, 92.8, 90.6),
        ("Gemini 2.0 Pro", 1309, 84.7, 90.3, 89.1),
        ("Llama 3.1 405B", 1264, 81.2, 88.0, 85.4),
        ("DeepSeek-V3", 1241, 79.5, 86.1, 83.7),
    ]

    row_html = ''
    for model, arena_elo, mmlu, gsm8k, humaneval in rows:
        elo_width = max(5, min(100, int((arena_elo - 1100) / 3.5)))
        row_html += (
            '<tr>'
            f'<td><strong>{model}</strong></td>'
            f'<td><span class="benchmark-score">{arena_elo}</span><div class="benchmark-bar"><span style="width:{elo_width}%"></span></div></td>'
            f'<td class="benchmark-score">{mmlu:.1f}%</td>'
            f'<td class="benchmark-score">{gsm8k:.1f}%</td>'
            f'<td class="benchmark-score">{humaneval:.1f}%</td>'
            '</tr>'
        )

    upcoming_releases = [
        ("GPT-5", "Expected to expand multimodal planning and stronger tool-use reliability."),
        ("Claude 4", "Likely focused on long-context consistency and enterprise governance controls."),
        ("Gemini 2.5", "Expected to improve reasoning depth and native video/document workflows."),
        ("Llama 4", "Open-weight trajectory with stronger coding and agentic orchestration benchmarks."),
    ]

    upcoming_html = ''.join(
        f'<li><strong>{model}:</strong> {note}</li>' for model, note in upcoming_releases
    )

    latest_updates = [
        ("Reasoning", "Frontier closed models still lead in chain-of-thought stability under complex prompts."),
        ("Coding", "Claude and GPT families remain strongest on code quality; open models continue to narrow the gap."),
        ("Cost/Speed", "Open-weight models often win on cost control and deployment flexibility for internal workloads."),
    ]

    updates_html = ''.join(
        f'<li><strong>{topic}:</strong> {note}</li>' for topic, note in latest_updates
    )

    return (
        '<hr class="section-rule">\n'
        '<section id="model-benchmarks" data-page-group="businesses">\n'
        '  <span class="section-label">Model Benchmarks</span>\n'
        '  <p class="section-transition">Performance snapshot for current frontier and open-weight models, including LLM Arena ranking context and core capability tests.</p>\n'
        '  <p class="model-benchmark-note">LLM Arena is a head-to-head preference leaderboard where users compare anonymous model outputs. Live context: <a href="https://arena.ai/" target="_blank" rel="noopener noreferrer">arena.ai</a>. Values below are demo newsroom snapshot values for presentation formatting.</p>\n'
        '  <table class="benchmark-table">\n'
        '    <thead><tr><th>Model</th><th>Arena Elo</th><th>MMLU</th><th>GSM8K</th><th>HumanEval</th></tr></thead>\n'
        f'    <tbody>{row_html}</tbody>\n'
        '  </table>\n'
        '  <h3 class="story-headline">Models Releasing Soon</h3>\n'
        f'  <ul class="benchmark-defs">{upcoming_html}</ul>\n'
        '  <h3 class="story-headline">Latest Model Updates & Comparisons</h3>\n'
        f'  <ul class="benchmark-defs">{updates_html}</ul>\n'
        '  <ul class="benchmark-defs">\n'
        '    <li><strong>Arena Elo:</strong> preference-style ranking from head-to-head model comparisons.</li>\n'
        '    <li><strong>MMLU:</strong> broad academic and professional knowledge test across many subjects.</li>\n'
        '    <li><strong>GSM8K:</strong> grade-school math reasoning benchmark.</li>\n'
        '    <li><strong>HumanEval:</strong> code generation pass-rate benchmark for programming tasks.</li>\n'
        '  </ul>\n'
        '</section>'
    )


def _svg_placeholder_data_uri(headline: str, section_label: str) -> str:
    safe_headline = escape((headline or 'Newsletter Story').strip())[:72]
    safe_section = escape((section_label or 'OrdoAI').strip())[:28]
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 675" role="img" aria-label="Placeholder graphic">'
        '<defs>'
        '<linearGradient id="g" x1="0" x2="1" y1="0" y2="1">'
        '<stop offset="0%" stop-color="#f5f6ff"/>'
        '<stop offset="100%" stop-color="#e8edff"/>'
        '</linearGradient>'
        '</defs>'
        '<rect width="1200" height="675" fill="url(#g)"/>'
        '<rect x="70" y="70" width="1060" height="535" rx="24" fill="#ffffff" stroke="#d7def7"/>'
        f'<text x="110" y="170" font-size="40" font-family="Georgia, serif" fill="#23315d">{safe_section}</text>'
        f'<text x="110" y="250" font-size="52" font-family="Georgia, serif" fill="#1b1f30">{safe_headline}</text>'
        '<text x="110" y="330" font-size="28" font-family="Georgia, serif" fill="#4a567f">Placeholder SVG graphic for newsletter production preview.</text>'
        '</svg>'
    )
    encoded = urllib.parse.quote(svg, safe=':/%#[]@!$&\'()*+,;=?')
    return f'data:image/svg+xml;utf8,{encoded}'


def _vc_firms_html(tracker: CitationTracker) -> str:
    firms = [
        {
            'name': 'Andreessen Horowitz (a16z)',
            'blurb': 'Active AI investor with published analysis on AI application spending and enterprise demand trends.',
            'people': ['Marc Andreessen', 'Ben Horowitz'],
            'links': [
                ('AI Application Spending Report', 'https://a16z.com/the-ai-application-spending-report-where-startup-dollars-really-go/'),
            ],
        },
        {
            'name': 'ARCH Venture Partners',
            'blurb': 'Deep-tech focused investor with new-fund momentum and long-running science commercialization track record.',
            'people': ['Robert Nelsen', 'Keith Crandell', 'Kristina Burow', 'Mark McDonnell', 'Steve Gillis', 'Paul Berns'],
            'links': [
                ('Fund XIII Announcement', 'https://www.archventure.com/arch-venture-partners-announces-new-fund-xiii/'),
            ],
        },
        {
            'name': 'General Catalyst',
            'blurb': 'Backs AI infrastructure and application-layer companies, including Together AI, with a clear AI adoption thesis.',
            'people': ['Ahmed Alveed'],
            'links': [
                ('Investment in Together AI', 'https://www.generalcatalyst.com/stories/our-investment-in-together-ai'),
                ('AI Adoption in Startups', 'https://www.generalcatalyst.com/stories/ai-adoption-in-startups'),
            ],
        },
        {
            'name': 'Bessemer Venture Partners',
            'blurb': 'Publishes extensive AI market frameworks and vertical AI analysis used by operators and founders.',
            'people': ['Kent Bennett', 'Byron Deeter', 'Mike Droesch', 'Maha Malik', 'Sam Bondy', 'Brian Feinstein', 'Sameer Dholakia', 'Caty Rea', 'Alex Yuditski', 'Aia Sarycheva'],
            'links': [
                ('BVP AI Hub', 'https://www.bvp.com/ai'),
                ('Future of Vertical AI', 'https://www.bvp.com/atlas/part-i-the-future-of-ai-is-vertical'),
                ('Everything Everywhere All AI (2024)', 'https://www.bvp.com/assets/uploads/2024/09/AI-Bessemer-Book-Everything-Everywhere-All-AI-2024.pdf'),
            ],
        },
        {
            'name': 'New Enterprise Associates (NEA)',
            'blurb': 'Large multi-stage platform with notable AI bets including Synthesia and Perplexity.',
            'people': ['Scott Sandell', 'Tony Florence', 'Mohamad Makhzoumi', 'Ali Behbahani', 'Paul Walker', 'Rick Yang'],
            'links': [
                ('Data + AI Revolution (Foresight)', 'https://www.nea.com/blog/foresight-the-data-ai-revolution-for-the-private-markets'),
                ('Investment in Synthesia', 'https://www.nea.com/blog/synthesia-ai-video-creation'),
                ('Investment in Perplexity', 'https://www.nea.com/blog/our-investment-in-perplexity-ai-answer-engines-and-the-end-of-traditional-search'),
            ],
        },
        {
            'name': 'Flagship Pioneering',
            'blurb': 'Strong AI-in-health and AI-enabled innovation positioning across scientific and consumer applications.',
            'people': ['Daniel Acker', 'Raffi Afeyan', 'Theonie Anastassiadis', 'Yiqun Bai', 'Simon Brunner'],
            'links': [
                ('AI and Medicine Explainer', 'https://www.flagshippioneering.com/stories/explainer-artificial-intelligence-and-medicine'),
                ('Extuitive AI Launch', 'https://www.flagshippioneering.com/news/press-release/flagship-pioneering-unveils-extuitive-to-revolutionize-consumer-product-innovation-and-creative-marketing-using-next-gen-ai'),
            ],
        },
        {
            'name': 'B Capital',
            'blurb': 'Highlights AI-driven investment momentum and global operating partnerships across its portfolio.',
            'people': ['Nick Whitehead', 'Patrick Harmon', 'Priya Banerjee'],
            'links': [
                ('AI-Driven Investment Momentum (2025 AGM)', 'https://b.capital/news-article/b-capital-highlights-ai-driven-investment-momentum-and-global-thought-leadership-at-2025-annual-general-meeting-and-ceo-summit/'),
            ],
        },
        {
            'name': 'HSG',
            'blurb': 'Appears in your research as an AI-active investor with interest in culturally focused AI experiences.',
            'people': [],
            'links': [
                ('HSG Startups and AI', 'https://www.unisg.ch/en/newsdetail/news/hsg-startups-focus-on-artificial-intelligence/'),
            ],
        },
        {
            'name': 'Kleiner Perkins',
            'blurb': 'Notable AI investor with positions in Together AI and AI healthcare startup Viz.ai.',
            'people': [],
            'links': [
                ('Together AI Perspective', 'https://www.kleinerperkins.com/perspectives/together-ai/'),
                ('Viz.ai Investment', 'https://www.kleinerperkins.com/perspectives/kleiner-perkins-and-gv-invest-21-million-in-ai-health-care-startup-viz-ai/'),
            ],
        },
    ]

    firm_cards = ''
    for firm in firms:
        cites = [tracker.cite(url) for _, url in firm['links']]
        people_line = ', '.join(firm['people']) if firm['people'] else 'Not specified in this research note.'
        links_html = ''.join(
            f'<li><a href="{url}" target="_blank">{label}</a></li>'
            for label, url in firm['links']
        )
        firm_cards += (
            '<article class="story-card">\n'
            f'  <h3 class="story-headline">{firm["name"]}</h3>\n'
            f'  <p class="story-dek">{firm["blurb"]}</p>\n'
            f'  <aside class="why-it-matters"><h4>Key People</h4><p>{people_line}</p></aside>\n'
            f'  <ul class="key-details">{links_html}</ul>\n'
            f'  {_cite_source_line(cites)}\n'
            '</article>\n'
        )

    return (
        '<hr class="section-rule">\n'
        '<section id="vc-firms" data-page-group="investments">\n'
        '  <span class="section-label">Top VC Firms</span>\n'
        '  <p class="section-transition">From your research notes, these firms stand out for fundraising scale, AI thesis development, and recent portfolio activity.</p>\n'
        f'{firm_cards}'
        '</section>'
    )


def _vc_people_html() -> str:
    people_by_firm = [
        ('Andreessen Horowitz (a16z)', ['Marc Andreessen', 'Ben Horowitz']),
        ('ARCH Venture Partners', ['Robert Nelsen', 'Keith Crandell', 'Kristina Burow', 'Mark McDonnell', 'Steve Gillis', 'Paul Berns']),
        ('General Catalyst', ['Ahmed Alveed']),
        ('Bessemer Venture Partners', ['Kent Bennett', 'Byron Deeter', 'Mike Droesch', 'Maha Malik', 'Sam Bondy', 'Brian Feinstein', 'Sameer Dholakia', 'Caty Rea', 'Alex Yuditski', 'Aia Sarycheva']),
        ('New Enterprise Associates (NEA)', ['Scott Sandell', 'Tony Florence', 'Mohamad Makhzoumi', 'Ali Behbahani', 'Paul Walker', 'Rick Yang']),
        ('Flagship Pioneering', ['Daniel Acker', 'Raffi Afeyan', 'Theonie Anastassiadis', 'Yiqun Bai', 'Simon Brunner']),
        ('B Capital', ['Nick Whitehead', 'Patrick Harmon', 'Priya Banerjee']),
    ]

    people_cards = ''
    for firm_name, names in people_by_firm:
        names_html = ''.join(f'<li>{name}</li>' for name in names)
        people_cards += (
            '<article class="story-card">\n'
            f'  <h3 class="story-headline">{firm_name}</h3>\n'
            f'  <ul class="key-details">{names_html}</ul>\n'
            '</article>\n'
        )

    return (
        '<hr class="section-rule">\n'
        '<section id="people" data-page-group="people">\n'
        '  <span class="section-label">People</span>\n'
        '  <p class="section-transition">Key VC leaders and principals from your research notes, grouped by firm.</p>\n'
        f'{people_cards}'
        '</section>'
    )


def _home_articles_payload(
    lead_card: StoryCard,
    top_cards: List[StoryCard],
    radar_cards: List[StoryCard],
    event_cards: List[StoryCard],
    accel_cards: List[StoryCard],
    date_str: str,
    ai_assets: Dict[str, Dict[str, str]] | None = None,
) -> List[Dict[str, str]]:
    payload = []
    ai_assets = ai_assets or {}

    def _word_count(text: str) -> int:
        return len([part for part in (text or '').split() if part.strip()])

    def _offline_longform(card: StoryCard, section_label: str, source_url: str) -> str:
        details = '; '.join(card.key_details[:5]) if card.key_details else ''
        body_parts = [
            (
                f"{card.headline} is a lead development in this week’s {section_label.lower()} briefing. "
                f"{card.dek or card.lede} What stands out is not just the headline itself, but how quickly this update has moved from announcement to practical implications for teams tracking momentum across the market."
            ),
            (
                f"The immediate update is straightforward: {card.lede} "
                "For readers following execution signals, the important question is how this development changes near-term priorities and whether the underlying progress can be sustained over time."
            ),
            (
                f"Context from the reporting reinforces that this is tied to real operating decisions, not just narrative positioning. {card.context or card.why_it_matters} "
                "That makes it useful as a benchmark for what credible progress looks like in the current cycle."
            ),
            (
                f"Key facts remain central to the story: {details}. "
                "When viewed together, these details indicate where the organization is concentrating resources and what outcomes stakeholders are likely to expect over the next few quarters."
            ),
            (
                "For peers in adjacent categories, this kind of update tends to raise the bar on execution quality. "
                "It can influence hiring pace, partnership timing, product roadmaps, and investor expectations, especially when similar signals cluster in a short period."
            ),
            (
                "The practical takeaway is to watch follow-through rather than headlines alone. "
                "Announcements set direction, but sustained delivery is what ultimately confirms whether the strategy is durable and whether the early momentum can translate into long-term outcomes."
            ),
        ]

        if source_url:
            body_parts.append(
                f"Source context: this article was expanded from the structured newsletter record and linked source ({source_url}) using deterministic local rendering. "
                "It is intended to improve readability while preserving the factual details in the original item."
            )

        text = '\n\n'.join(body_parts)
        while _word_count(text) < 320:
            text += (
                "\n\nIn short, this story should be read as a directional signal with measurable checkpoints ahead: adoption, operational consistency, and the ability to execute as scrutiny increases."
            )
        return text

    def add_cards(cards: List[StoryCard], section_key: str, section_label: str):
        for idx, card in enumerate(cards, start=1):
            if not card:
                continue
            body_parts = [card.lede]
            if card.context:
                body_parts.append(card.context)
            if card.why_it_matters:
                body_parts.append(card.why_it_matters)
            if card.key_details:
                body_parts.append('Key details: ' + '; '.join(card.key_details[:4]))

            story_id = f'{section_key}-{idx}'
            asset = ai_assets.get(story_id, {})
            source_url = card.citations[0].url if card.citations else ''
            merged_body = asset.get('body', '')
            if _word_count(merged_body) < 220:
                merged_body = _offline_longform(card, section_label, source_url)

            payload.append({
                'id': story_id,
                'sectionKey': section_key,
                'sectionLabel': section_label,
                'headline': card.headline,
                'dek': card.dek or card.lede,
                'summary': card.lede,
                'author': 'OrdoAI News Desk',
                'date': card.date or date_str,
                'sourceUrl': source_url,
                'body': merged_body,
                'imageUrl': asset.get('image_url') or _svg_placeholder_data_uri(card.headline, section_label),
                'imagePrompt': asset.get('image_prompt', ''),
            })

    funding_cards = [lead_card] + top_cards + radar_cards if lead_card else top_cards + radar_cards
    add_cards(funding_cards, 'front-page', 'Front Page')
    add_cards(event_cards, 'news', 'News')
    add_cards(accel_cards, 'opinion', 'Opinion')
    return payload


def _home_front_page_html(home_articles: List[Dict[str, str]]) -> str:
    groups = {'news': [], 'front-page': [], 'opinion': []}
    for article in home_articles:
        groups.setdefault(article['sectionKey'], []).append(article)

    def teaser(article: Dict[str, str]) -> str:
        return (
            f'<button type="button" class="home-teaser" data-open-article="{article["id"]}">\n'
            f'  <div class="home-teaser-kicker">{article["sectionLabel"]}</div>\n'
            f'  <div class="home-teaser-headline">{article["headline"]}</div>\n'
            f'  <div class="home-teaser-meta">{article["author"]} • {article["date"]}</div>\n'
            f'</button>'
        )

    lead = groups['front-page'][0] if groups['front-page'] else None
    lead_html = ''
    if lead:
        lead_html = (
            '<div class="home-front-lead">\n'
            f'  <button type="button" class="home-col-link" data-open-list="front-page">Front Page</button>\n'
            f'  <button type="button" class="home-teaser" data-open-article="{lead["id"]}">\n'
            f'    <h2 class="home-front-lead-headline">{lead["headline"]}</h2>\n'
            f'    <p class="home-front-lead-body">{lead["summary"]}</p>\n'
            f'    <div class="home-teaser-meta">{lead["author"]} • {lead["date"]}</div>\n'
            f'  </button>\n'
            '</div>'
        )

    news_html = ''.join(teaser(item) for item in groups['news'][:3])
    opinion_html = ''.join(teaser(item) for item in groups['opinion'][:3])
    return (
        '<section id="home-page" class="home-page" data-page-group="home">\n'
        '  <div id="home-subview-front" class="home-subview">\n'
        '    <div class="home-front-grid">\n'
        '      <div>\n'
        '        <button type="button" class="home-col-link" data-open-list="news">News</button>\n'
        f'{news_html}\n'
        '      </div>\n'
        f'      <div>{lead_html}</div>\n'
        '      <div>\n'
        '        <button type="button" class="home-col-link" data-open-list="opinion">Opinion</button>\n'
        f'{opinion_html}\n'
        '      </div>\n'
        '    </div>\n'
        '  </div>\n'
        '  <section id="home-subview-list" class="home-subview is-hidden">\n'
        '    <div class="home-view-head">\n'
        '      <button type="button" class="home-back-btn" data-home-back="front">← Back to Front Page</button>\n'
        '      <h2 id="home-list-title" class="home-list-title">News</h2>\n'
        '    </div>\n'
        '    <div id="home-list-items"></div>\n'
        '  </section>\n'
        '  <article id="home-subview-article" class="home-subview is-hidden">\n'
        '    <div class="home-view-head">\n'
        '      <button type="button" class="home-back-btn" data-home-back="list">← Back to Newspaper</button>\n'
        '    </div>\n'
        '    <div class="home-article-wrap">\n'
        '      <span id="home-article-kicker" class="home-article-kicker">News</span>\n'
        '      <h2 id="home-article-title" class="home-article-title"></h2>\n'
        '      <p id="home-article-dek" class="home-article-dek"></p>\n'
        '      <p id="home-article-meta" class="home-article-meta"></p>\n'
        '      <div class="home-article-image"></div>\n'
        '      <p id="home-article-caption" class="home-article-caption">Placeholder graphic: OrdoAI archive</p>\n'
        '      <div id="home-article-body" class="home-article-body"></div>\n'
        '      <p id="home-article-linkout" class="home-article-linkout"></p>\n'
        '    </div>\n'
        '  </article>\n'
        '</section>'
    )


def _load_ai_assets(config: Dict) -> Dict[str, Dict[str, str]]:
    output_dir = Path(config.get('output', {}).get('output_dir', 'output'))
    assets_path = output_dir / 'newsletter_ai_assets.json'

    if not assets_path.exists():
        return {}

    try:
        payload = json.loads(assets_path.read_text(encoding='utf-8'))
        articles = payload.get('articles', {})
        return articles if isinstance(articles, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def build_home_articles_payload(
    funding_items: List[FundingItem],
    event_items: List[EventItem],
    accelerator_items: List[AcceleratorItem],
    config: Dict,
) -> List[Dict[str, str]]:
    tracker = CitationTracker()

    all_funding_cards = []
    for idx, item in enumerate(funding_items):
        if idx == 0:
            all_funding_cards.append(funding_to_story(item, tracker, position='lead'))
        elif idx < 4:
            all_funding_cards.append(funding_to_story(item, tracker, position='top'))
        else:
            all_funding_cards.append(funding_to_story(item, tracker, position='radar'))

    event_cards = sorted(
        [event_to_story(i, tracker) for i in event_items],
        key=_event_sort_key,
    )
    event_cards = _filter_upcoming_event_cards(event_cards)
    accel_cards = [accelerator_to_story(i, tracker) for i in accelerator_items]

    lead_card = all_funding_cards[0] if all_funding_cards else None
    top_cards = all_funding_cards[1:4] if len(all_funding_cards) > 1 else []
    radar_cards = all_funding_cards[4:] if len(all_funding_cards) > 4 else []

    ai_assets = _load_ai_assets(config)
    return _home_articles_payload(
        lead_card,
        top_cards,
        radar_cards,
        event_cards,
        accel_cards,
        issue_date(),
        ai_assets=ai_assets,
    )


def render_home_article_page(article: Dict[str, str], config: Dict) -> str:
    title = config.get('newsletter', {}).get('title', 'OrdoAI')
    headline = escape(article.get('headline', 'Story'))
    section_label = escape(article.get('sectionLabel', 'News'))
    author = escape(article.get('author', 'OrdoAI News Desk'))
    published = escape(article.get('date', issue_date()))
    source_url = article.get('sourceUrl', '')
    image_url = article.get('imageUrl', '')
    image_prompt = article.get('imagePrompt', '')

    body_parts = [part.strip() for part in (article.get('body', '') or '').split('\n\n') if part.strip()]
    if not body_parts and article.get('summary'):
        body_parts = [article['summary']]
    body_html = '\n'.join(f'<p>{escape(part)}</p>' for part in body_parts)

    image_block = ''
    if image_url:
        caption = 'AI-generated illustration based on newsletter story content'
        if image_prompt:
            caption = 'AI-generated illustration'
        image_block = (
            '<figure class="story-image">\n'
            f'  <img src="{escape(image_url)}" alt="{headline}" loading="lazy">\n'
            f'  <figcaption>{caption}</figcaption>\n'
            '</figure>'
        )

    source_block = ''
    if source_url:
        source_block = (
            '<p class="story-linkout">'
            f'<a href="{escape(source_url)}" target="_blank" rel="noopener noreferrer">Read original source →</a>'
            '</p>'
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{headline} — {title}</title>
    <style>
        :root {{
            --serif: Georgia, 'Times New Roman', 'Noto Serif', serif;
            --sans: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            --text: #111;
            --text-2: #2a2a2a;
            --accent: #e10600;
            --border: #d6d6d6;
            --bg: #f5f5f5;
        }}
        * {{ box-sizing: border-box; }}
        body {{ margin: 0; background: var(--bg); color: var(--text); font-family: var(--serif); }}
        .container {{ max-width: 860px; margin: 0 auto; padding: 36px 28px 60px; }}
        .back-link {{ font-family: var(--sans); font-size: .82rem; text-transform: uppercase; letter-spacing: .08em; color: var(--accent); text-decoration: none; font-weight: 700; }}
        .kicker {{ display: inline-block; margin-top: 24px; background: var(--accent); color: #fff; padding: 7px 10px; font-family: var(--sans); font-size: .8rem; text-transform: uppercase; letter-spacing: .06em; font-weight: 700; }}
        h1 {{ font-size: 3.2rem; line-height: 1.08; margin: 24px 0 14px; }}
        .meta {{ font-family: var(--sans); font-size: 1.02rem; color: var(--text-2); margin-bottom: 18px; }}
        .meta .author {{ color: var(--accent); font-weight: 700; }}
        .story-image {{ margin: 0 0 24px; border: 1px solid var(--border); background: #fff; }}
        .story-image img {{ display: block; width: 100%; height: auto; }}
        .story-image figcaption {{ font-family: var(--sans); font-size: .82rem; color: #6f6f6f; padding: 8px 12px; border-top: 1px solid var(--border); }}
        .story-body p {{ font-size: 2rem; line-height: 1.55; margin: 0 0 18px; }}
        .story-linkout {{ margin-top: 22px; font-family: var(--sans); font-size: 1rem; }}
        .story-linkout a {{ color: var(--accent); }}
        @media (max-width: 900px) {{
            h1 {{ font-size: 2.45rem; }}
            .story-body p {{ font-size: 1.4rem; }}
        }}
    </style>
</head>
<body>
    <main class="container">
        <a class="back-link" href="../newsletter.html#home">← Back to Home</a>
        <span class="kicker">{section_label}</span>
        <h1>{headline}</h1>
        <p class="meta"><span class="author">{author}</span> • {published}</p>
        {image_block}
        <section class="story-body">
            {body_html}
        </section>
        {source_block}
    </main>
</body>
</html>
"""


# ── event chronological sort ────────────────────────────────────

def _event_sort_key(card: StoryCard):
    """Sort events by extracted day number; recurring events go last."""
    m = re.search(r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d+)', card.date)
    return (0, int(m.group(1))) if m else (1, 0)


def _filter_upcoming_event_cards(event_cards: List[StoryCard]) -> List[StoryCard]:
    """Keep events that are upcoming within the next 5 weeks (35 days)."""
    today_iso = datetime.now().strftime('%Y-%m-%d')
    today = datetime.now().date()
    filtered: List[StoryCard] = []
    for card in event_cards:
        date_iso = _event_date_iso(card.date)
        if not date_iso:
            continue
        if date_iso >= today_iso:
            try:
                event_day = datetime.strptime(date_iso, '%Y-%m-%d').date()
            except ValueError:
                continue
            delta_days = (event_day - today).days
            if 0 <= delta_days <= 35:
                filtered.append(card)
    return filtered


def _slugify(text: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', (text or '').lower()).strip('-') or 'unscheduled'


def _event_calendar_parts(date_text: str):
    months = 'January|February|March|April|May|June|July|August|September|October|November|December'
    cleaned = (date_text or '').strip()
    if not cleaned:
        return 'Unscheduled', 'unscheduled', 'Unscheduled', 'unscheduled'

    exact_match = re.search(rf'({months})\s+\d{{1,2}}(?:,\s*\d{{4}})?', cleaned)
    if exact_match:
        date_label = exact_match.group(0)
        month_label = re.match(rf'({months})', date_label).group(1)
        return month_label, _slugify(month_label), date_label, _slugify(date_label)

    month_match = re.search(rf'({months})', cleaned)
    if month_match:
        month_label = month_match.group(1)
        return month_label, _slugify(month_label), cleaned, _slugify(cleaned)

    return 'Unscheduled', 'unscheduled', cleaned, _slugify(cleaned)


def _event_month_label(date_text: str) -> str:
    return _event_calendar_parts(date_text)[0]


def _event_month_key(date_text: str) -> str:
    return _event_calendar_parts(date_text)[1]


def _event_date_label(date_text: str) -> str:
    return _event_calendar_parts(date_text)[2]


def _event_date_key(date_text: str) -> str:
    return _event_calendar_parts(date_text)[3]


def _event_date_iso(date_text: str) -> str:
    label = _event_date_label(date_text)
    if not label or label == 'Unscheduled':
        return ''

    for fmt in (
        '%B %d, %Y',
        '%B %d, %Y %I:%M %p',
        '%b %d, %Y',
        '%b %d, %Y %I:%M %p',
        '%B %d',
        '%b %d',
    ):
        try:
            parsed = datetime.strptime(label, fmt)
            if fmt in ('%B %d', '%b %d'):
                parsed = parsed.replace(year=datetime.now().year)
            return parsed.strftime('%Y-%m-%d')
        except ValueError:
            continue

    if _parse_datetime is not None:
        try:
            parsed = _parse_datetime(label, fuzzy=True)
            return parsed.strftime('%Y-%m-%d')
        except Exception:
            pass

    return ''


def _calendar_switcher_html(event_cards: List[StoryCard]) -> str:
    """Render top calendar controls for upcoming-window filtering."""
    date_options = []
    seen_dates = set()

    for card in event_cards:
        date_label = _event_date_label(card.date)
        date_key = _event_date_key(card.date)
        date_iso = _event_date_iso(card.date)

        if date_key not in seen_dates and date_iso:
            seen_dates.add(date_key)
            date_options.append((date_iso, date_label))

    date_options.sort(key=lambda item: item[0])
    today_iso = datetime.now().strftime('%Y-%m-%d')
    selected_date = next((iso for iso, _ in date_options if iso >= today_iso), '')
    if not selected_date:
        selected_date = date_options[0][0] if date_options else ''

    return (
        '<section class="calendar-toolbar" id="calendar" data-page-group="events">\n'
        '  <div class="calendar-switcher" data-calendar-switcher>\n'
        '    <div class="calendar-filter-group">\n'
        '      <span class="calendar-filter-icon" aria-hidden="true">🗓️</span>\n'
        '      <label class="calendar-filter-label" for="calendar-date-filter">Select Start Date:</label>\n'
        '      <div class="calendar-filter-input-wrap">\n'
        f'        <input id="calendar-date-filter" class="calendar-filter-input" data-calendar-date type="date" value="{selected_date}">\n'
        '        <span class="calendar-filter-input-icon" aria-hidden="true">📅</span>\n'
        '      </div>\n'
        '      <button type="button" class="calendar-nav-btn" data-calendar-prev>Previous</button>\n'
        '      <button type="button" class="calendar-nav-btn" data-calendar-next>Next</button>\n'
        '    </div>\n'
        '    <div data-calendar-dates hidden>' + ','.join(date_iso for date_iso, _ in date_options) + '</div>\n'
        '  </div>\n'
        '</section>'
    )


_CALENDAR_SWITCHER_JS = """
document.addEventListener('DOMContentLoaded', function () {
    var switcher = document.querySelector('[data-calendar-switcher]');
    if (!switcher) return;

    var dateInput = switcher.querySelector('[data-calendar-date]');
    var prevButton = switcher.querySelector('[data-calendar-prev]');
    var nextButton = switcher.querySelector('[data-calendar-next]');
    var cards = document.querySelectorAll('#events .event-card[data-event-date-iso]');
    if (!dateInput || !prevButton || !nextButton || !cards.length) return;

    var dateListNode = switcher.querySelector('[data-calendar-dates]');
    var availableDates = dateListNode && dateListNode.textContent
        ? dateListNode.textContent.split(',').filter(Boolean)
        : [];
    if (!availableDates.length) return;

    function firstUpcomingOrFirst() {
        var todayIso = new Date().toISOString().slice(0, 10);
        var upcoming = availableDates.find(function (dateIso) { return dateIso >= todayIso; });
        return upcoming || availableDates[0];
    }

    function addDays(isoDate, dayCount) {
        var baseDate = new Date(isoDate + 'T00:00:00');
        baseDate.setDate(baseDate.getDate() + dayCount);
        return baseDate.toISOString().slice(0, 10);
    }

    dateInput.min = availableDates[0];
    dateInput.max = availableDates[availableDates.length - 1];
    var defaultDate = firstUpcomingOrFirst();
    if (!dateInput.value || availableDates.indexOf(dateInput.value) === -1 || dateInput.value < defaultDate) {
        dateInput.value = defaultDate;
    }

    function selectedIndex() {
        return availableDates.indexOf(dateInput.value);
    }

    function applyFilter() {
        var startDateIso = dateInput.value;
        var endDateIso = addDays(startDateIso, 27);

        cards.forEach(function (card) {
            var cardDateIso = card.getAttribute('data-event-date-iso');
            card.style.display = cardDateIso >= startDateIso && cardDateIso <= endDateIso ? '' : 'none';
        });

        var idx = selectedIndex();
        prevButton.disabled = idx <= 0;
        nextButton.disabled = idx >= availableDates.length - 1;
    }

    function moveDate(offset) {
        var idx = selectedIndex();
        if (idx < 0) idx = 0;
        var nextIdx = idx + offset;
        if (nextIdx < 0 || nextIdx >= availableDates.length) return;
        dateInput.value = availableDates[nextIdx];
        applyFilter();
    }

    prevButton.addEventListener('click', function () { moveDate(-1); });
    nextButton.addEventListener('click', function () { moveDate(1); });

    dateInput.addEventListener('change', function () {
        if (availableDates.indexOf(dateInput.value) === -1) {
            dateInput.value = firstUpcomingOrFirst();
        }
        applyFilter();
    });

    applyFilter();
});

document.addEventListener('DOMContentLoaded', function () {
    var topicLinks = document.querySelectorAll('.masthead-topic-link[data-page]');
    var pageSections = document.querySelectorAll('[data-page-group]');
    if (!topicLinks.length || !pageSections.length) return;

    function normalizePage(page) {
        if (page === 'investments') return 'money';
        if (page === 'businesses' || page === 'news') return 'models';
        return page;
    }

    function pageGroupFor(page) {
        var normalized = normalizePage(page);
        if (normalized === 'home') return 'home';
        if (normalized === 'money') return 'investments';
        if (normalized === 'models') return 'businesses';
        return normalized;
    }

    function showPage(page) {
        var normalized = normalizePage(page);
        var pageGroup = pageGroupFor(normalized);
        pageSections.forEach(function (section) {
            section.hidden = section.getAttribute('data-page-group') !== pageGroup;
        });

        topicLinks.forEach(function (link) {
            var isActive = link.getAttribute('data-page') === normalized;
            link.classList.toggle('is-active', isActive);
            link.setAttribute('aria-current', isActive ? 'page' : 'false');
        });
    }

    function pageFromHash() {
        var hash = window.location.hash;
        if (!hash) return '';
        var target = document.querySelector(hash);
        if (!target) return '';
        var parent = target.closest('[data-page-group]');
        return parent ? parent.getAttribute('data-page-group') : '';
    }

    var initialPage = normalizePage(pageFromHash() || topicLinks[0].getAttribute('data-page') || 'money');
    showPage(initialPage);

    topicLinks.forEach(function (link) {
        link.addEventListener('click', function (event) {
            event.preventDefault();
            var page = link.getAttribute('data-page');
            var target = link.getAttribute('href');
            showPage(page);
            if (target && target.startsWith('#')) {
                var targetNode = document.querySelector(target);
                window.location.hash = target;
                if (targetNode) {
                    targetNode.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    return;
                }
            }
            window.scrollTo({ top: 0, behavior: 'smooth' });
        });
    });

    document.addEventListener('click', function (event) {
        var anchor = event.target.closest('a[href^="#"]');
        if (!anchor) return;
        var targetId = anchor.getAttribute('href');
        if (!targetId || targetId.length < 2) return;
        var targetNode = document.querySelector(targetId);
        if (!targetNode) return;
        var parent = targetNode.closest('[data-page-group]');
        if (!parent) return;
        showPage(normalizePage(parent.getAttribute('data-page-group')));
    });
});

// Home newspaper experience navigation controller
document.addEventListener('DOMContentLoaded', function() {
    var homePageEl = document.getElementById('home-page');
    if (!homePageEl) return;

    var frontView = document.getElementById('home-subview-front');
    var listView = document.getElementById('home-subview-list');
    var articleView = document.getElementById('home-subview-article');
    var homeArticlesAttr = homePageEl.getAttribute('data-articles');
    var articles = (window.homeArticles && Array.isArray(window.homeArticles))
        ? window.homeArticles
        : (homeArticlesAttr ? JSON.parse(homeArticlesAttr) : []);

    function esc(value) {
        return (value || '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/\"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function formatDate(value) {
        if (!value) return '';
        if (/^\\d{4}-\\d{2}-\\d{2}$/.test(value)) {
            var parsed = new Date(value + 'T00:00:00');
            if (!isNaN(parsed.getTime())) {
                return parsed.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' });
            }
        }
        return value;
    }

    function showView(view) {
        [frontView, listView, articleView].forEach(function(v) {
            v.classList.toggle('is-hidden', v !== view);
        });
    }

    document.addEventListener('click', function(event) {
        // Handle section list button clicks (News, Opinion, etc.)
        var openList = event.target.closest('[data-open-list]');
        if (openList) {
            var sectionKey = openList.getAttribute('data-open-list');
            var items = articles.filter(function(a) { return a.sectionKey === sectionKey; });
            var listTitle = document.getElementById('home-list-title');
            if (items.length > 0) {
                listTitle.textContent = items[0].sectionLabel;
            }
            var listItemsContainer = document.getElementById('home-list-items');
            listItemsContainer.innerHTML = items.map(function(article) {
                return (
                    '<button type="button" class="home-list-item" data-open-article="' + esc(article.id) + '">' +
                    '  <div class="home-list-thumb"></div>' +
                    '  <div>' +
                    '    <h3 class="home-list-headline">' + esc(article.headline) + '</h3>' +
                    '    <p class="home-list-summary">' + esc(article.summary) + '</p>' +
                    '  </div>' +
                    '</button>'
                );
            }).join('');
            showView(listView);
            window.scrollTo({ top: 0, behavior: 'smooth' });
            return;
        }

        var openArticle = event.target.closest('[data-open-article]');
        if (openArticle) {
            var articleId = openArticle.getAttribute('data-open-article');
            var article = articles.find(function(a) { return a.id === articleId; });
            if (!article) return;

            document.getElementById('home-article-kicker').textContent = article.sectionLabel;
            document.getElementById('home-article-title').textContent = article.headline;
            document.getElementById('home-article-dek').textContent = article.dek;
            var prettyDate = formatDate(article.date);
            document.getElementById('home-article-meta').innerHTML =
                '<span class="author">' + esc(article.author) + '</span>, <span class="role">Staff Writer</span>' + (prettyDate ? ' • ' + esc(prettyDate) : '');

            var homeImage = document.querySelector('.home-article-image');
            var captionNode = document.getElementById('home-article-caption');
            if (homeImage) {
                if (article.imageUrl) {
                    homeImage.innerHTML = '<img src="' + esc(article.imageUrl) + '" alt="' + esc(article.headline) + '" loading="lazy">';
                    if (captionNode) {
                        captionNode.textContent = 'AI-generated editorial image based on newsletter story content';
                    }
                } else {
                    homeImage.innerHTML = '';
                    if (captionNode) {
                        captionNode.textContent = 'Placeholder graphic: OrdoAI archive';
                    }
                }
            }

            var bodyHtml = (article.body || '').split('\\n\\n').map(function(para) {
                return '<p>' + esc(para) + '</p>';
            }).join('');
            document.getElementById('home-article-body').innerHTML = bodyHtml;

            var linkoutHtml = '';
            if (article.sourceUrl) {
                linkoutHtml = '<a href="' + esc(article.sourceUrl) + '" target="_blank" rel="noopener noreferrer">Read original article →</a>';
            }
            document.getElementById('home-article-linkout').innerHTML = linkoutHtml;

            showView(articleView);
            window.scrollTo({ top: 0, behavior: 'smooth' });
            return;
        }

        // Handle back button clicks
        var homeBack = event.target.closest('[data-home-back]');
        if (homeBack) {
            var target = homeBack.getAttribute('data-home-back');
            showView(target === 'front' ? frontView : listView);
            window.scrollTo({ top: 0, behavior: 'smooth' });
        }
    });
});

// Main newsletter story focus controller
document.addEventListener('DOMContentLoaded', function () {
    var focusView = document.getElementById('story-focus-view');
    var focusBack = document.getElementById('story-focus-back');
    var focusContent = document.getElementById('story-focus-content');
    var pageSections = document.querySelectorAll('[data-page-group]');
    if (!focusView || !focusBack || !focusContent || !pageSections.length) return;

    var lastPage = '';
    var lastStory = null;

    function currentPage() {
        var active = document.querySelector('.masthead-topic-link.is-active[data-page]');
        return active ? active.getAttribute('data-page') : '';
    }

    function setFocusMode(isFocused) {
        var editorsNote = document.querySelector('.editors-note');
        var toc = document.querySelector('.toc');
        if (editorsNote) editorsNote.hidden = isFocused;
        if (toc) toc.hidden = isFocused;
        focusView.hidden = !isFocused;
    }

    function openStory(cardNode) {
        lastPage = currentPage();
        lastStory = cardNode;
        setFocusMode(true);

        pageSections.forEach(function (section) {
            section.hidden = true;
        });

        function textFrom(selector) {
            var node = cardNode.querySelector(selector);
            return node ? node.textContent.trim() : '';
        }

        function esc(value) {
            return (value || '')
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/\"/g, '&quot;')
                .replace(/'/g, '&#39;');
        }

        var section = cardNode.closest('section');
        var sectionLabel = section ? section.querySelector('.section-label') : null;
        var kicker = sectionLabel ? sectionLabel.textContent.trim() : 'News';

        var headline = textFrom('.hero-headline, .story-headline, .radar-headline, .accel-headline, .event-headline') || 'Story';
        var dek = textFrom('.hero-dek, .story-dek, .radar-lede, .accel-dek, .event-dek') || textFrom('.story-lede');

        var announced = '';
        cardNode.querySelectorAll('.key-details li').forEach(function (item) {
            var value = item.textContent.trim();
            if (!announced && value.toLowerCase().indexOf('announced:') === 0) {
                announced = value.split(':').slice(1).join(':').trim();
            }
        });

        var bodyParts = [];
        var storyLede = textFrom('.story-lede');
        var storyContext = textFrom('.story-context');
        var whyMatters = textFrom('.why-it-matters p');
        if (storyLede) bodyParts.push(storyLede);
        if (storyContext) bodyParts.push(storyContext);
        if (whyMatters) bodyParts.push(whyMatters);
        cardNode.querySelectorAll('.key-details li').forEach(function (item) {
            bodyParts.push(item.textContent.trim());
        });

        if (!bodyParts.length && dek) {
            bodyParts.push(dek);
        }

        var articleMatch = null;
        if (window.homeArticles && Array.isArray(window.homeArticles)) {
            articleMatch = window.homeArticles.find(function (item) {
                return (item.headline || '').trim() === headline;
            }) || null;
        }
        if (articleMatch && articleMatch.body) {
            bodyParts = articleMatch.body.split(/\n\n+/).filter(Boolean);
        }

        var sourceAnchor = cardNode.querySelector('.story-sources a:not(.cite-sup)');
        var sourceHtml = '';
        if (sourceAnchor) {
            var href = sourceAnchor.getAttribute('href') || '#';
            sourceHtml = '<p class="story-focus-link"><a href="' + esc(href) + '" target="_blank" rel="noopener noreferrer">Read source article →</a></p>';
        }

        var bodyHtml = bodyParts.map(function (part) {
            return '<p>' + esc(part) + '</p>';
        }).join('');

        var focusImageHtml = '  <div class="story-focus-image"></div>';
        var focusCaption = '  <p class="story-focus-caption">Placeholder graphic by OrdoAI archive</p>';
        if (articleMatch && articleMatch.imageUrl) {
            focusImageHtml = '  <div class="story-focus-image"><img src="' + esc(articleMatch.imageUrl) + '" alt="' + esc(headline) + '" loading="lazy"></div>';
            focusCaption = '  <p class="story-focus-caption">AI-generated illustration based on newsletter content</p>';
        }

        focusContent.innerHTML = (
            '<article class="story-focus-article">' +
            '  <span class="story-focus-kicker">' + esc(kicker) + '</span>' +
            '  <h2 class="story-focus-headline">' + esc(headline) + '</h2>' +
            (dek ? '  <p class="story-focus-dek">' + esc(dek) + '</p>' : '') +
            '  <p class="story-focus-meta"><span class="author">OrdoAI News Desk</span>' +
            (announced ? ' • ' + esc(announced) : '') +
            '</p>' +
            focusImageHtml +
            focusCaption +
            '  <div class="story-focus-body">' + bodyHtml + '</div>' +
            sourceHtml +
            '</article>'
        );
        focusView.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    function restorePage(page) {
        pageSections.forEach(function (section) {
            section.hidden = section.getAttribute('data-page-group') !== page;
        });

        document.querySelectorAll('.masthead-topic-link[data-page]').forEach(function (link) {
            var isActive = link.getAttribute('data-page') === page;
            link.classList.toggle('is-active', isActive);
            link.setAttribute('aria-current', isActive ? 'page' : 'false');
        });
    }

    focusBack.addEventListener('click', function () {
        var page = lastPage || currentPage() || 'home';
        setFocusMode(false);
        focusContent.innerHTML = '';
        restorePage(page);
        if (lastStory) {
            lastStory.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    });

    document.addEventListener('click', function (event) {
        if (event.target.closest('a')) return;
        var cardNode = event.target.closest('.hero-card, .story-card, .radar-card, .accel-card, .event-card');
        if (!cardNode) return;
        if (focusView.contains(cardNode)) return;
        openStory(cardNode);
    });
});

function handleSignup(event) {
    event.preventDefault();
    var email = document.getElementById('signupEmail').value;
    var form = document.getElementById('signupForm');
    var success = document.getElementById('signupSuccess');
    
    // In production, this would POST to a backend API
    // For now, show success and store in localStorage as demo
    localStorage.setItem('newsletter_subscriber', email);
    
    form.style.display = 'none';
    success.style.display = 'block';
    
    console.log('Newsletter signup:', email);
}
"""


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
    # Convert all funding items first (default position)
    all_funding_cards = []
    for idx, item in enumerate(funding_items):
        if idx == 0:
            all_funding_cards.append(funding_to_story(item, tracker, position='lead'))
        elif idx < 4:
            all_funding_cards.append(funding_to_story(item, tracker, position='top'))
        else:
            all_funding_cards.append(funding_to_story(item, tracker, position='radar'))
    
    event_cards = sorted(
        [event_to_story(i, tracker) for i in event_items],
        key=_event_sort_key,
    )
    event_cards = _filter_upcoming_event_cards(event_cards)
    accel_cards = [accelerator_to_story(i, tracker) for i in accelerator_items]

    # ── split funding into lead / top / radar ───────────────────
    lead_card = all_funding_cards[0] if all_funding_cards else None
    top_cards = all_funding_cards[1:4] if len(all_funding_cards) > 1 else []
    radar_cards = all_funding_cards[4:] if len(all_funding_cards) > 4 else []

    # ── metadata ────────────────────────────────────────────────
    title = config['newsletter']['title']
    subtitle = config['newsletter']['subtitle']
    date_str = issue_date()
    num = issue_number()

    # ── editorial prose ─────────────────────────────────────────
    en = build_editors_note(funding_items, event_items, accelerator_items, trend_data)
    tp = build_trend_prose(trend_data)

    # ── build HTML sections ─────────────────────────────────────
    ai_assets = _load_ai_assets(config)
    
    # Home newspaper experience (front page → list → article)
    home_articles = _home_articles_payload(
        lead_card,
        top_cards,
        radar_cards,
        event_cards,
        accel_cards,
        date_str,
        ai_assets=ai_assets,
    )
    home_page_html = _home_front_page_html(home_articles)
    home_articles_json = json.dumps(home_articles)

    # Lead story
    lead_html = _hero_html(lead_card) if lead_card else ''

    # Top stories
    if top_cards:
        top_stories_html = (
            '<hr class="section-rule">\n'
            '<section id="top-stories" data-page-group="businesses">\n'
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
            '<section id="funding-radar" data-page-group="investments">\n'
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
            '<section id="trends" data-page-group="businesses">\n'
            '  <span class="section-label">Trend Brief</span>\n'
            f'  <p class="section-transition">{transition("trend_brief")}</p>\n'
            f'  <p class="trend-prose">{tp}</p>\n'
            f'  <div class="trend-grid">\n{trend_chips}</div>\n'
            '</section>'
        )
    else:
        trends_html = ''

    if event_cards:
        calendar_switcher_html = _calendar_switcher_html(event_cards)
    else:
        calendar_switcher_html = ''

    # Events
    if event_cards:
        events_html = (
            '<hr class="section-rule">\n'
            '<section id="events" data-page-group="events">\n'
            '  <span class="section-label">Upcoming Events</span>\n'
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
            '<section id="accelerators" data-page-group="people">\n'
            '  <span class="section-label">Accelerator Watch</span>\n'
            f'  <p class="section-transition">{transition("accelerators")}</p>\n'
            + ''.join(_accel_html(c) for c in accel_cards)
            + '\n</section>'
        )
    else:
        accels_html = ''

    people_html = _vc_people_html()
    vc_firms_html = _vc_firms_html(tracker)
    model_benchmarks_html = _model_benchmarks_html()

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
            '<section id="sources" class="bibliography" data-page-group="businesses">\n'
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
    toc_items.append('<li><a href="#model-benchmarks">Model Benchmarks</a></li>')
    if event_cards:
        toc_items.append('<li><a href="#events">Upcoming Events</a></li>')
    if accel_cards:
        toc_items.append('<li><a href="#accelerators">Accelerator Watch</a></li>')
    if people_html:
        toc_items.append('<li><a href="#people">People</a></li>')
    if vc_firms_html:
        toc_items.append('<li><a href="#vc-firms">Top VC Firms</a></li>')
    if all_cites:
        toc_items.append('<li><a href="#sources">Sources</a></li>')
    toc_html = (
        '<nav class="toc">\n'
        '  <h3>In This Issue</h3>\n'
        '  <ol>\n    ' + '\n    '.join(toc_items) + '\n  </ol>\n'
        '</nav>'
    )

    people_target = '#people' if people_html else ('#accelerators' if accel_cards else ('#top-stories' if top_cards else '#lead'))
    events_target = '#events' if event_cards else '#calendar'
    home_target = '#home'
    money_target = '#lead'
    models_target = '#model-benchmarks'
    masthead_topics_html = (
        '<nav class="masthead-topics" aria-label="Topic sections">\n'
        '  <ul class="masthead-topics-list">\n'
        f'    <li><a class="masthead-topic-link" data-page="home" href="{home_target}">Home</a></li>\n'
        f'    <li><a class="masthead-topic-link" data-page="money" href="{money_target}">Money</a></li>\n'
        f'    <li><a class="masthead-topic-link" data-page="models" href="{models_target}">Models</a></li>\n'
        f'    <li><a class="masthead-topic-link" data-page="people" href="{people_target}">People</a></li>\n'
        f'    <li><a class="masthead-topic-link" data-page="events" href="{events_target}">Events</a></li>\n'
        '  </ul>\n'
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
        <p class="masthead-slogan">Don't stand on the sidelines, get in the game!</p>
        {masthead_topics_html}
        <div class="masthead-rule"></div>
    </div>
</header>

<main class="container" id="home">

    {home_page_html}
    <script id="home-articles-data">
    window.homeArticles = {home_articles_json};
    </script>

    {calendar_switcher_html}

    <section class="editors-note">
        <h2>From the Editorial Desk</h2>
        <p>{en}</p>
    </section>

    {toc_html}

    <section id="story-focus-view" class="story-focus-view" hidden>
        <div class="story-focus-head">
            <button type="button" id="story-focus-back" class="story-focus-back">← Back to Topic</button>
            <h2 class="story-focus-title">Story View</h2>
        </div>
        <div id="story-focus-content"></div>
    </section>

    {lead_html}
    {top_stories_html}
    {radar_html}
    {trends_html}
    {model_benchmarks_html}
    {people_html}
    {vc_firms_html}
    {events_html}
    {accels_html}

</main>

<section class="signup-section">
    <div class="signup-container">
        <h2 class="signup-headline">Stay in the Loop</h2>
        <p class="signup-subtext">
            Get the OrdoAI newsletter delivered to your inbox every week.
            The latest funding rounds, events, and accelerator opportunities — curated for NYC's tech community.
        </p>
        <form class="signup-form" id="signupForm" onsubmit="handleSignup(event)">
            <input type="email" class="signup-input" id="signupEmail" placeholder="Enter your email" required>
            <button type="submit" class="signup-button">Subscribe</button>
        </form>
        <div class="signup-success" id="signupSuccess">
            You're in! Welcome to the OrdoAI community.
        </div>
        <p class="signup-privacy">No spam, ever. Unsubscribe anytime.</p>
    </div>
</section>

<section class="container">
    {bib_html}
</section>

<footer class="footer">
    <div class="container">
        <div class="footer-line">Generated on {gen_ts}</div>
        <div class="footer-line">{title} &bull; Thank you for being here with us tonight</div>
    </div>
</footer>

<script>{_CALENDAR_SWITCHER_JS}</script>

</body>
</html>"""
