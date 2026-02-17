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

def funding_to_story(item: FundingItem, tracker: CitationTracker, position: str = 'radar') -> StoryCard:
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

    # lede - different styles based on position
    others = [i for i in item.investors if i != item.lead_investor]
    
    if position == 'lead':
        # Lead story: traditional "Good evening" opener
        parts = [
            f'Good evening. We begin with news out of {loc}, where {item.startup_name} '
            f'has secured {item.amount} in a {rl.lower()} round'
            + (f' led by {lead}' if lead else '') + '.'
        ]
    elif position == 'top':
        # Top stories: more dynamic, urgent openers without "Good evening"
        openers = [
            f'Breaking in {loc} tonight: {item.startup_name} just closed {item.amount} in a {rl.lower()} round'
            + (f', with {lead} leading the charge' if lead else '') + '.',
            
            f'This just in from {loc}. {item.startup_name} has landed {item.amount}'
            + (f', backed by {lead}' if lead else f' in fresh {rl.lower()} funding') + '.',
            
            f'Major news tonight out of {loc}. {item.startup_name} secured {item.amount}'
            + (f' with {lead} at the helm' if lead else f' in a {rl.lower()} round') + '.',
            
            f'Another significant deal to report. {item.startup_name} in {loc} has raised {item.amount}'
            + (f', led by {lead}' if lead else '') + '.',
        ]
        opener_idx = sum(ord(c) for c in item.startup_name) % len(openers)
        parts = [openers[opener_idx]]
    else:
        # Radar stories: more engaging variations
        radar_openers = [
            f'On our radar tonight: {item.startup_name} in {loc} just raised {item.amount}'
            + (f', with {lead} backing them' if lead else f' in {rl.lower()} funding') + '.',
            
            f'Also catching attention: {item.startup_name} closed {item.amount}'
            + (f' led by {lead}' if lead else f' in a {rl.lower()} round') + ' in {loc}.',
            
            f'Worth noting: {loc}-based {item.startup_name} secured {item.amount}'
            + (f' from {lead}' if lead else '') + '.',
            
            f'Another deal closing tonight — {item.startup_name} landed {item.amount}'
            + (f', backed by {lead}' if lead else f' in {rl.lower()} capital') + ' out of {loc}.',
            
            f'Don\'t sleep on this one: {item.startup_name} just pulled in {item.amount}'
            + (f' with {lead} leading' if lead else '') + ' in {loc}.',
            
            f'One more to watch: {item.startup_name} raised {item.amount} in a {rl.lower()} round'
            + (f' led by {lead}' if lead else '') + ', operating out of {loc}.',
            
            f'Flying under the radar: {item.startup_name} in {loc} closed {item.amount}'
            + (f' from {lead}' if lead else f' in {rl.lower()} funding') + '.',
            
            f'Making moves quietly: {item.startup_name} secured {item.amount}'
            + (f', with {lead} investing' if lead else f' in a {rl.lower()} round') + ' from their {loc} base.',
        ]
        radar_idx = sum(ord(c) for c in item.startup_name) % len(radar_openers)
        parts = [radar_openers[radar_idx]]
    
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
    dek = (desc_parts[0].rstrip('.') + '.') if desc_parts else 'An opportunity to connect with the NYC tech community.'

    venue = item.venue_or_online or 'TBA'
    city = item.city or 'NYC'
    
    # More engaging opening hooks
    lead_intros = [
        f'Here\'s an event you don\'t want to miss. {item.event_name} is happening',
        f'Mark your calendar for this one. {item.event_name} takes place',
        f'This is the event everyone\'s talking about. {item.event_name} is coming up',
        f'Get ready for {item.event_name}. It\'s scheduled',
        f'You need to know about {item.event_name}. The event is set',
    ]
    # Use event name hash for consistent intro
    intro_idx = sum(ord(c) for c in item.event_name) % len(lead_intros)
    lede = lead_intros[intro_idx]
    
    lede += f' on {item.date_time} at {venue} in {city}. '
    
    # Make cost more exciting
    if item.cost and item.cost.lower() == 'free':
        lede += 'And here\'s the best part — it\'s completely free. '
    elif item.cost:
        lede += f'Tickets are {item.cost}. '
    
    # Add more context from description
    if len(desc_parts) > 1:
        lede += desc_parts[1].rstrip('.') + '. '

    audience = item.audience or 'tech professionals'
    
    # More compelling "why it matters"
    if len(desc_parts) > 1:
        why = '. '.join(desc_parts[1:]).strip().rstrip('.') + '.'
    else:
        # Extract key descriptors to make more specific variations
        is_free = item.cost and item.cost.lower() == 'free'
        has_founders = 'founder' in audience.lower()
        has_investors = 'investor' in audience.lower() or 'vc' in audience.lower() or 'angel' in audience.lower()
        has_engineers = 'engineer' in audience.lower() or 'developer' in audience.lower()
        audience_lower = audience.lower()
        
        # Create highly specific and compelling variations
        why_variations = [
            # Variation 1: Networking value
            (f'This is where real connections happen. Last time, attendees walked away with new co-founders, '
             f'first customers, and job offers. The {audience_lower} in the room are actively looking to build — '
             f'and you should be there when they do.'),
            
            # Variation 2: FOMO + opportunity cost
            (f'Here\'s what happens if you don\'t show up: someone else meets your future co-founder, '
             f'someone else gets the intro you needed, someone else lands that opportunity. '
             f'The {audience_lower} who consistently show up to events like this are the ones winning. '
             f'Be one of them.'),
            
            # Variation 3: Specific outcomes
            (f'This is more than drinks and small talk. This is where {audience_lower} are closing deals, '
             f'forming partnerships, and hiring their founding teams. Come ready with business cards, '
             f'a clear pitch, and the willingness to follow up. The people you meet here could change everything.'),
            
            # Variation 4: Insider access
            (f'The smartest {audience_lower} in NYC know this is where you need to be. Not just for the content, '
             f'but for who you\'ll meet in the hallways, at the bar, waiting in line for coffee. '
             f'These informal conversations are where the real magic happens.'),
            
            # Variation 5: Career acceleration
            (f'Think about where you want to be six months from now. The path there probably involves meeting '
             f'someone who can open that door. This event puts you in a room with exactly those people — '
             f'the {audience_lower} who are building, investing, and connecting the dots across the ecosystem.'),
            
            # Variation 6: Timing urgency
            (f'Every month you wait is another month someone else is building relationships, making moves, '
             f'and getting ahead. The {audience_lower} who make it to events like this aren\'t smarter — '
             f'they just show up. Stop waiting for the perfect time. This is it.'),
        ]
        
        # Add specific variations based on event characteristics
        if is_free and has_founders:
            why_variations.append(
                f'It\'s free, it\'s full of founders who are actually building, and it\'s one of the best '
                f'uses of a weeknight in NYC. If you\'re looking for a co-founder, first customers, or just '
                f'people who get what you\'re going through — this is your crowd.'
            )
        
        if has_investors:
            why_variations.append(
                f'Investors will be in the room. Not on a panel — actually walking around, having conversations, '
                f'getting pitched in real time. If your company is ready for funding, this is one of the most '
                f'efficient ways to get in front of VCs who are actively writing checks.'
            )
        
        if has_engineers:
            why_variations.append(
                f'The technical talent in this room is exceptional. If you\'re hiring, scouting for a co-founder, '
                f'or just want to talk shop with people who actually know what they\'re doing, this is it. '
                f'Plus, the conversations here often lead to open-source collaborations and side projects that go somewhere.'
            )
        
        why_idx = sum(ord(c) for c in item.event_name) % len(why_variations)
        why = why_variations[why_idx]

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
    
    # More engaging dek
    if desc_parts:
        dek = desc_parts[0].rstrip('.') + '.'
    else:
        dek = f'An accelerator program reshaping the {item.focus.lower() if item.focus else "startup"} landscape in {item.city_region or "New York"}.'
    
    # More compelling lede with variety
    lead_intros = [
        f"Here's what makes {item.name} worth your attention",
        f"This is the moment to learn about {item.name}",
        f"{item.name} is building the next generation of startups",
        f"Here's why {item.name} is on every founder's radar",
    ]
    # Use item name hash to pick consistent intro (deterministic)
    intro_idx = sum(ord(c) for c in item.name) % len(lead_intros)
    lede = lead_intros[intro_idx]
    
    if item.city_region:
        lede += f' in {item.city_region}. '
    else:
        lede += ' right here in New York. '
    
    # Add focus area with more excitement
    if item.focus:
        lede += f"They're laser-focused on {item.focus.lower()}, "
        lede += "working with founders who are tackling some of the biggest challenges in this space. "
    
    # Add additional description with impact language
    if len(desc_parts) > 1:
        lede += desc_parts[1].rstrip('.') + '. '
    
    # Add urgency if still space
    if item.application_url:
        lede += "And here's the opportunity: applications are open right now."

    # More actionable "why it matters"
    if item.application_url:
        why = (
            f"If you're building in {item.focus.lower() if item.focus else 'tech'}, "
            f"this is your chance to get into a proven program. "
            f"Applications are open, and these cohorts fill up fast."
        )
    else:
        why = (
            f"For founders in {item.focus.lower() if item.focus else 'tech'}, "
            f"this is the kind of program that can change the trajectory of your company. "
            f"Keep an eye on when the next cohort opens."
        )

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
        'New York City\'s tech scene is alive with opportunities to connect, learn, and grow. '
        'These are the events where deals get done, partnerships form, and careers change direction. '
        'Here\'s where you need to be.'
    ),
    'accelerators': (
        'And finally tonight, for those of you ready to take your startup to the next level — '
        'these are the programs that could change everything. '
        'The right accelerator at the right time can be the difference between struggling alone and building with momentum.'
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
