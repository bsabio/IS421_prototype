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
    text-align: left;
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
    max-width: 760px;
}
.home-article-kicker {
    display: inline-block;
    background: var(--accent);
    color: #fff;
    font-weight: 700;
    font-size: 0.74rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    padding: 6px 10px;
    margin-bottom: 12px;
}
.home-article-title {
    font-family: var(--serif);
    font-size: 3rem;
    line-height: 1.1;
    margin-bottom: 12px;
}
.home-article-dek {
    font-size: 1.9rem;
    line-height: 1.2;
    margin-bottom: 14px;
}
.home-article-meta {
    font-size: 0.95rem;
    margin-bottom: 14px;
    color: var(--text-2);
}
.home-article-meta .author {
    color: var(--accent);
    font-weight: 700;
}
.home-article-image {
    border: 1px solid var(--border);
    background: linear-gradient(135deg, #f3f3f3, #e4e4e4);
    min-height: 340px;
    margin-bottom: 14px;
}
.home-article-caption {
    font-size: 0.78rem;
    color: var(--text-3);
    margin-bottom: 16px;
}
.home-article-body p {
    font-family: var(--serif);
    font-size: 1.06rem;
    line-height: 1.65;
    margin-bottom: 14px;
}
.home-article-linkout {
    margin-top: 14px;
    font-size: 0.95rem;
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
) -> List[Dict[str, str]]:
    payload = []

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

            payload.append({
                'id': f'{section_key}-{idx}',
                'sectionKey': section_key,
                'sectionLabel': section_label,
                'headline': card.headline,
                'dek': card.dek or card.lede,
                'summary': card.lede,
                'author': 'AI Factory News Desk',
                'date': card.date or date_str,
                'sourceUrl': card.citations[0].url if card.citations else '',
                'body': '\n\n'.join(body_parts),
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
        '      <p class="home-article-caption">Photo credit: AI Factory archive</p>\n'
        '      <div id="home-article-body" class="home-article-body"></div>\n'
        '      <p id="home-article-linkout" class="home-article-linkout"></p>\n'
        '    </div>\n'
        '  </article>\n'
        '</section>'
    )


# ── event chronological sort ────────────────────────────────────

def _event_sort_key(card: StoryCard):
    """Sort events by extracted day number; recurring events go last."""
    m = re.search(r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d+)', card.date)
    return (0, int(m.group(1))) if m else (1, 0)


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

    for fmt in ('%B %d, %Y', '%B %d'):
        try:
            parsed = datetime.strptime(label, fmt)
            if fmt == '%B %d':
                parsed = parsed.replace(year=datetime.now().year)
            return parsed.strftime('%Y-%m-%d')
        except ValueError:
            continue
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

    function showPage(page) {
        pageSections.forEach(function (section) {
            section.hidden = section.getAttribute('data-page-group') !== page;
        });

        topicLinks.forEach(function (link) {
            var isActive = link.getAttribute('data-page') === page;
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

    var initialPage = pageFromHash() || topicLinks[0].getAttribute('data-page') || 'investments';
    showPage(initialPage);

    topicLinks.forEach(function (link) {
        link.addEventListener('click', function (event) {
            event.preventDefault();
            var page = link.getAttribute('data-page');
            var target = link.getAttribute('href');
            showPage(page);
            if (target && target.startsWith('#')) {
                window.location.hash = target;
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
        showPage(parent.getAttribute('data-page-group'));
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
    if event_cards:
        toc_items.append('<li><a href="#events">Events This Week</a></li>')
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
    investments_target = '#vc-firms' if vc_firms_html else ('#funding-radar' if radar_cards else '#lead')
    businesses_target = '#top-stories' if top_cards else ('#trends' if trend_data else '#lead')
    masthead_topics_html = (
        '<nav class="masthead-topics" aria-label="Topic sections">\n'
        '  <ul class="masthead-topics-list">\n'
        f'    <li><a class="masthead-topic-link" data-page="investments" href="#home">Home</a></li>\n'
        f'    <li><a class="masthead-topic-link" data-page="people" href="{people_target}">People</a></li>\n'
        f'    <li><a class="masthead-topic-link" data-page="events" href="{events_target}">Events</a></li>\n'
        f'    <li><a class="masthead-topic-link" data-page="investments" href="{investments_target}">Investments</a></li>\n'
        f'    <li><a class="masthead-topic-link" data-page="businesses" href="{businesses_target}">Businesses</a></li>\n'
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

    {calendar_switcher_html}

    <section class="editors-note">
        <h2>From the Editorial Desk</h2>
        <p>{en}</p>
    </section>

    {toc_html}

    {lead_html}
    {top_stories_html}
    {radar_html}
    {trends_html}
    {people_html}
    {vc_firms_html}
    {events_html}
    {accels_html}

</main>

<section class="signup-section">
    <div class="signup-container">
        <h2 class="signup-headline">Stay in the Loop</h2>
        <p class="signup-subtext">
            Get the AI Factory Newsletter delivered to your inbox every week.
            The latest funding rounds, events, and accelerator opportunities — curated for NYC's tech community.
        </p>
        <form class="signup-form" id="signupForm" onsubmit="handleSignup(event)">
            <input type="email" class="signup-input" id="signupEmail" placeholder="Enter your email" required>
            <button type="submit" class="signup-button">Subscribe</button>
        </form>
        <div class="signup-success" id="signupSuccess">
            You're in! Welcome to the AI Factory community.
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
