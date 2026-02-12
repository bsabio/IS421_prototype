"""
Editorial layer – Lester Holt newscast-style mapping from ranked data
items to StoryCards.

Every headline, dek, lede, and "here's what this means" is assembled
from data fields using template patterns modeled on Lester Holt's
authoritative, clear, direct NBC Nightly News delivery.
No AI generation, no randomness, no invented facts.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Tuple
from collections import defaultdict
from datetime import datetime

from .models import FundingItem, EventItem, AcceleratorItem

# ── helpers ──────────────────────────────────────────────────────

_SOURCE_NAMES = {
    'techcrunch.com': 'TechCrunch',
    'alleywatch.com': 'AlleyWatch',
    'garysguide.com': "Gary's Guide",
    'openvc.app': 'OpenVC',
    'techstars.com': 'Techstars',
    'eranyc.com': 'ERA',
    'joinef.com': 'Entrepreneur First',
    'futurelabs.nyc': 'NYU Future Labs',
    'blueprinthealth.org': 'Blueprint Health',
    'eventbrite.com': 'Eventbrite',
}


def _source_label(url: str) -> str:
    for pat, name in _SOURCE_NAMES.items():
        if pat in url:
            return name
    return 'Source'


_ROUND_LABELS = {
    'pre-seed': 'Pre-Seed', 'seed': 'Seed',
    'series-a': 'Series A', 'series-b': 'Series B',
    'series-c': 'Series C', 'series-d': 'Series D',
    'unknown': 'Funding Round',
}


def _round(raw: str) -> str:
    return _ROUND_LABELS.get(raw, raw.replace('-', ' ').title())


def _fmt_date(s: str) -> str:
    """YYYY-MM-DD → Mon DD, YYYY"""
    try:
        return datetime.strptime(s, '%Y-%m-%d').strftime('%b %d, %Y')
    except (ValueError, TypeError):
        return s or ''


_CAT_DISPLAY = {'Ai Ml': 'AI/ML', 'Ai_Ml': 'AI/ML'}


def _cat_label(raw: str) -> str:
    if raw in _CAT_DISPLAY:
        return _CAT_DISPLAY[raw]
    return raw.replace('_', ' ').title()


# ── data classes ─────────────────────────────────────────────────

@dataclass
class Citation:
    number: int
    url: str
    source: str


@dataclass
class StoryCard:
    headline: str
    dek: str
    lede: str
    why_it_matters: str
    key_details: List[str]
    context: str = ''
    citations: List[Citation] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    category: str = ''
    location: str = ''
    date: str = ''
    card_type: str = ''        # funding | event | accelerator
    amount: str = ''
    round_type: str = ''
    cost: str = ''
    registration_url: str = ''
    venue: str = ''


class CitationTracker:
    """Global citation numbering across the entire newsletter."""

    def __init__(self):
        self._map: Dict[str, int] = {}
        self._n = 1

    def cite(self, url: str) -> Citation:
        if url not in self._map:
            self._map[url] = self._n
            self._n += 1
        return Citation(self._map[url], url, _source_label(url))

    @property
    def all(self) -> List[Citation]:
        return sorted(
            [Citation(n, u, _source_label(u)) for u, n in self._map.items()],
            key=lambda c: c.number,
        )


# ── Funding → StoryCard ─────────────────────────────────────────

def funding_to_story(item: FundingItem, tracker: CitationTracker) -> StoryCard:
    rl = _round(item.round_type)
    loc = item.location or 'New York'
    lead = item.lead_investor or ''
    www = item.who_what_why_when_where_how

    # headline — Lester Holt style: declarative, authoritative
    if lead and item.amount != 'Undisclosed':
        headline = f'{item.startup_name} Secures {item.amount} {rl} Backed by {lead}'
    elif item.amount != 'Undisclosed':
        headline = f'{item.startup_name} Raises {item.amount} in New {rl}'
    else:
        headline = f'{item.startup_name} Closes {rl} — Financial Terms Not Disclosed'

    # dek (one-sentence hook — anchor tease)
    raw_dek = item.evidence_snippets[0] if item.evidence_snippets else www.what
    dek = raw_dek.rstrip('.') + '.'

    # lede (2-3 sentences: Lester Holt newscast open)
    others = [i for i in item.investors if i != item.lead_investor]
    parts = [
        f'Good evening. We begin with news out of {loc}, where {item.startup_name} '
        f'has secured {item.amount} in a {rl.lower()} round'
        + (f' led by {lead}' if lead else '') + '.'
    ]
    if others:
        if len(others) <= 2:
            oth_str = ' and '.join(others)
        else:
            oth_str = ', '.join(others[:2]) + ', and ' + others[2]
        parts.append(f'{oth_str} also took part in the round.')
    if www.when:
        parts.append(
            f'The announcement came {www.when.lower().replace("announced ", "").rstrip(".")}.'
        )
    lede = ' '.join(parts)

    # why it matters — "here's what this means" Holt sign-off
    wparts = []
    if www.why:
        wparts.append(www.why.rstrip('.') + '.')
    if www.how and www.how not in (www.why or ''):
        wparts.append(www.how.rstrip('.') + '.')
    why = ' '.join(wparts) or (
        f'It\'s a signal that investors are watching '
        f'{", ".join(item.categories[:2]).lower() if item.categories else "this space"} closely.'
    )

    # key details (3-6 bullets)
    details = [f'Amount: {item.amount}', f'Round: {rl}']
    if lead:
        details.append(f'Lead investor: {lead}')
    if others:
        details.append(f'Other investors: {", ".join(others[:4])}')
    details.append(f'Location: {loc}')
    if item.announced_date:
        details.append(f'Announced: {_fmt_date(item.announced_date)}')

    # context (optional extra color from evidence)
    ctx = ' '.join(item.evidence_snippets[1:3]) if len(item.evidence_snippets) > 1 else ''

    return StoryCard(
        headline=headline, dek=dek, lede=lede, why_it_matters=why,
        key_details=details, context=ctx,
        citations=[tracker.cite(u) for u in item.source_urls],
        tags=[_cat_label(c) for c in item.categories],
        category=', '.join(_cat_label(c) for c in item.categories[:2]) if item.categories else 'General',
        location=loc, date=item.announced_date or '',
        card_type='funding', amount=item.amount, round_type=rl,
    )


# ── Event → StoryCard ───────────────────────────────────────────

def event_to_story(item: EventItem, tracker: CitationTracker) -> StoryCard:
    desc_parts = [s.strip() for s in (item.description or '').split('. ') if s.strip()]
    dek = (desc_parts[0].rstrip('.') + '.') if desc_parts else 'A gathering for the NYC tech community.'

    venue = item.venue_or_online or 'TBA'
    city = item.city or 'NYC'
    lede = f'Turning now to what\'s coming up on the calendar. {item.event_name} is set for {item.date_time} at {venue} in {city}.'
    if item.cost and item.cost.lower() == 'free':
        lede += ' There is no cost to attend.'
    elif item.cost:
        lede += f' Tickets are {item.cost}.'

    audience = item.audience or 'tech professionals'
    why = (
        '. '.join(desc_parts[1:]).strip().rstrip('.') + '.'
    ) if len(desc_parts) > 1 else (
        f'If you\'re a {audience.lower().rstrip("s")} in this city, this is one worth putting on your calendar.'
    )

    details = [f'Date: {item.date_time}', f'Venue: {venue}', f'Cost: {item.cost}']
    if item.audience:
        details.append(f'Audience: {item.audience}')

    return StoryCard(
        headline=item.event_name, dek=dek, lede=lede, why_it_matters=why,
        key_details=details,
        citations=[tracker.cite(item.source_url)] if item.source_url else [],
        location=city, date=item.date_time or '', card_type='event',
        cost=item.cost, registration_url=item.registration_url or '', venue=venue,
    )


# ── Accelerator → StoryCard ─────────────────────────────────────

def accelerator_to_story(item: AcceleratorItem, tracker: CitationTracker) -> StoryCard:
    desc_parts = [s.strip() for s in (item.description or '').split('. ') if s.strip()]
    dek = (desc_parts[0].rstrip('.') + '.') if desc_parts else (
        f'A program based in {item.city_region or "New York"}.'
    )

    lede = (
        f'We want to tell you about {item.name}, headquartered in {item.city_region}.'
        if item.city_region else f'We want to tell you about {item.name}, a New York–based program.'
    )
    if item.focus:
        lede += f' Their focus: {item.focus.lower()}.'
    if len(desc_parts) > 1:
        lede += ' ' + desc_parts[1].rstrip('.') + '.'

    why = f'For founders working in {item.focus.lower() if item.focus else "tech"}, this is a program to know about.'
    if item.application_url:
        why += ' And applications are currently open.'

    details = []
    if item.city_region:
        details.append(f'Location: {item.city_region}')
    if item.focus:
        details.append(f'Focus: {item.focus}')
    if desc_parts:
        details.append(desc_parts[0])
    if item.application_url:
        details.append(f'Apply: {item.application_url}')

    return StoryCard(
        headline=item.name, dek=dek, lede=lede, why_it_matters=why,
        key_details=details,
        citations=[tracker.cite(item.source_url)] if item.source_url else [],
        location=item.city_region or '', card_type='accelerator',
        category=item.focus or '',
    )


# ── Editor's Note ────────────────────────────────────────────────

def build_editors_note(
    funding: List[FundingItem],
    events: List[EventItem],
    accelerators: List[AcceleratorItem],
    trend_data: Dict[str, int],
) -> str:
    total = sum(i.amount_numeric for i in funding)
    if total >= 1_000_000_000:
        total_s = f'${total / 1_000_000_000:.1f}B'
    elif total >= 1_000_000:
        total_s = f'${total / 1_000_000:.1f}M'
    else:
        total_s = f'${total:,.0f}'

    cats = list(trend_data.keys())[:3] if trend_data else []
    cat_s = ', '.join(_cat_label(c) for c in cats) or 'tech'

    note = f'Good evening, everyone. Tonight we\'re tracking {len(funding)} startup funding deals '
    note += f'here in New York City, totaling a combined {total_s}. '
    note += f'The sectors driving the action: {cat_s}. '
    if events:
        note += f'We\'re also keeping an eye on {len(events)} events on the calendar this month. '
    if accelerators:
        note += f'And {len(accelerators)} accelerator programs that deserve your attention. '
    note += 'Let\'s get to it.'
    return note


# ── Trend brief prose ────────────────────────────────────────────

def build_trend_prose(trend_data: Dict[str, int]) -> str:
    if not trend_data:
        return ''
    items = list(trend_data.items())
    top_cat, top_n = items[0]
    label = _cat_label(top_cat)
    prose = (
        f'Now, when you step back and look at where the money is going, '
        f'a clear picture emerges. {label} is leading the way, with {top_n} '
        f'deal{"s" if top_n != 1 else ""} this week alone.'
    )
    if len(items) > 1:
        rest = [f'{_cat_label(c)} ({n})' for c, n in items[1:]]
        prose += f' Also seeing activity: {", ".join(rest)}.'
    return prose


# ── Section transitions ─────────────────────────────────────────

_TRANSITIONS = {
    'top_stories': (
        'But that was not the only deal making news tonight. '
        'Several other rounds also caught our attention this week.'
    ),
    'funding_radar': (
        'Meanwhile, more startups across New York City quietly closed rounds of their own.'
    ),
    'trend_brief': (
        'Now, let\'s take a wider look at what\'s happening across '
        'the funding landscape.'
    ),
    'events': (
        'Turning now to the week ahead. '
        'The New York City tech calendar has no shortage of places to be.'
    ),
    'accelerators': (
        'And finally tonight, for those of you still building — '
        'these are the programs worth a serious look.'
    ),
}


def transition(section: str) -> str:
    return _TRANSITIONS.get(section, '')


# ── Funding grouping ────────────────────────────────────────────

def group_by_round(cards: List[StoryCard]) -> List[Tuple[str, List[StoryCard]]]:
    """Group funding cards by round type, later stages first."""
    groups: Dict[str, List[StoryCard]] = defaultdict(list)
    for c in cards:
        groups[c.round_type].append(c)
    order = [
        'Series D', 'Series C', 'Series B', 'Series A',
        'Seed', 'Pre-Seed', 'Funding Round',
    ]
    result = []
    for stage in order:
        if stage in groups:
            result.append((stage, groups.pop(stage)))
    for stage, cs in sorted(groups.items()):
        result.append((stage, cs))
    return result


# ── Issue metadata ───────────────────────────────────────────────

def issue_number() -> int:
    """Deterministic issue number from ISO week."""
    return datetime.now().isocalendar()[1]


def issue_date() -> str:
    return datetime.now().strftime('%B %d, %Y')
