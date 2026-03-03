# AI Factory Newsletter Generator

**An MVP newsletter system that automatically generates weekly startup funding newsletters for college students and general audiences.**

> 🎯 **PROTOTYPE MODE**: This system uses mock data for development and demos. Data sources are designed as plugins that can be swapped with real scrapers later without changing the newsletter logic.

## 🎯 What It Does

Generates a reporter-style newsletter covering:
1. **Funding Headlines**: Who raised money, how much, from whom (with WHO/WHAT/WHY/WHEN/WHERE/HOW structure)
2. **Trend Brief**: What categories are getting funded (weekly trends)
3. **Events**: Where/when to meet founders and investors (NYC-first)
4. **Accelerators**: Startup accelerators, demo days, and office hours

**Key Features:**
- ✅ Proper citations for every story
- ✅ Full bibliography at the end
- ✅ Deterministic templates (no AI freestyle)
- ✅ Deduplication across sources
- ✅ Automatic categorization
- ✅ Reporter-style structured output

## 🏗️ Architecture

```
newsroom/
├── collect.py       # Fetch raw HTML from sources
├── normalize.py     # Extract structured data (FundingItem, EventItem, etc.)
├── dedupe.py        # Merge duplicates across sources
├── rank.py          # Rank by amount, round type, credibility
├── render.py        # Generate newsletter (Markdown/HTML)
├── editorial.py     # Editorial layer: StoryCard mapping, headlines, ledes
├── web_template.py  # Newsletter HTML/CSS renderer (journalist layout)
├── sources.py       # Source-specific collectors
├── templates.py     # Markdown templates
├── models.py        # Data models (FundingItem, EventItem, etc.)
├── schema.py        # Canonical JSON types (Company, Person, Event, etc.)
├── json_builder.py  # Mapper, normalizer, validator, JSON writer
├── newsletter_schema.json  # JSON Schema (Draft-07) for contract validation
└── utils.py         # Utility functions

data/
├── raw/             # Raw HTML sources (for reproducibility)
├── normalized.json  # Extracted structured data
├── deduped.json     # Deduplicated data
├── ranked.json      # Ranked & ready for rendering
└── newsletter_data.json  # Canonical JSON contract (generated)

output/
├── newsletter.md    # Generated newsletter (Markdown)
└── newsletter.html  # Generated newsletter (HTML)
```

## � Newsletter JSON Builder

The **JSON Builder** converts aggregated newsletter data into a single canonical JSON file (`data/newsletter_data.json`) that serves as the contract between data collection and rendering.

### Build & Validate

```bash
# Build the canonical JSON from real data
python3 -m newsroom.json_builder

# Validate an existing JSON file against the schema
python3 -m newsroom.json_builder --validate data/newsletter_data.json

# Run tests
python3 -m pytest tests/test_json_builder.py -v
```

### JSON Structure

```
{
  "metadata"              → generatedAt, timeWindow, region, version, provenance
  "entities.companies"    → canonical company records (id, name, industry, etc.)
  "entities.people"       → canonical people records (id, name, role, affiliations)
  "content.investments"   → funding rounds with entityRefs, sources, amounts
  "content.events"        → events with location, topics, registration URLs
  "content.accelerators"  → accelerator programs with terms, focus areas
  "content.articles"      → (extensible) future article summaries
  "content.resources"     → (extensible) tools, reports, datasets
  "newsletterDraftPlan"   → AI writer instructions: sections, tone, audience
}
```

### Adding New Data Sources

The schema is **additive-only** — you can safely:

1. **Append items** to any `content.*` array or `entities.*` array
2. **Add new keys** to any object (all definitions use `additionalProperties: true`)
3. **Add new content categories** (e.g., `content.podcasts`) without breaking existing consumers

**Do NOT:**
- Remove or rename existing required fields (`id`, `type`, `title`, `summary`, `sources`)
- Change the id prefix convention (`company:`, `person:`, `event:`, `investment:`, etc.)
- Remove items from `sources` arrays (every fact must be traceable)

**To add a new data source:**

```python
from newsroom.schema import Source, Investment, Amount, EntityRefs
from newsroom.json_builder import EntityRegistry

# 1. Register entities (auto-deduplicates by slug)
reg = EntityRegistry()
cid = reg.add_company("New Startup", industry=["AI"])
pid = reg.add_person("Jane Founder", role="CEO", affiliations=[cid])

# 2. Create content items with sources
inv = Investment(
    title="New Startup raises $5M Seed",
    summary="One-paragraph summary.",
    date="2026-03-01",
    round="Seed",
    amount=Amount(5_000_000),
    entityRefs=EntityRefs(companies=[cid], people=[pid]),
    sources=[Source(url="https://...", publisher="TechCrunch", confidence=0.9)],
    tags=["funding", "ai"],
)

# 3. Append to the NewsletterData object and write
```

Schema definition: [`newsroom/newsletter_schema.json`](newsroom/newsletter_schema.json)  
Python types: [`newsroom/schema.py`](newsroom/schema.py)  
Builder/validator: [`newsroom/json_builder.py`](newsroom/json_builder.py)

---

## �📦 Data Sources

### Current (Prototype): Mock Data
- `data/mock/funding.json` - 10 realistic funding announcements
- `data/mock/events.json` - 8 NYC tech events
- `data/mock/accelerators.json` - 7 accelerator programs

Mock data includes real-looking examples like:
- CampusAI raises $2.5M seed (EdTech)
- FinanceFlow gets $8M Series A (FinTech)
- ClimateOS secures $20M Series A (Climate)

### Future (Post-Class): Real Sources

**TODO: Implement after class presentation**

**Funding sources:**
- TechCrunch: RSS feed + article API
- AlleyWatch: HTML scraping or API access
- Crunchbase: API integration (requires key)
- PitchBook: Data feed (enterprise access)

**Events sources:**
- Gary's Guide: HTML scraping or API
- Eventbrite: API for tech events
- Luma: Calendar API

**Accelerators:**
- OpenVC: Directory scraping
- Apply accelerators manually curated list

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Generate Newsletter (PROTOTYPE MODE - Using Mock Data)

The fastest way to see the newsletter in action:

```bash
# Load mock data and prepare for ranking (skips web scraping)
python3 -m newsroom.collect --source mock

# Rank the items by importance
python3 -m newsroom.rank

# Generate the newsletter (HTML with journalist layout)
python3 -m newsroom.render --format html

# Serve and view in browser
python3 serve.py
```

That's it! Open `http://localhost:8000/newsletter.html` to see the full newsletter.

The HTML output features a masthead, editor's note, lead story hero, table of
contents, "Why It Matters" callouts, key-number chips, and a full bibliography.
It is responsive (mobile + print-friendly).

### 2b. AI Toolkit (Optional: image + paragraph enrichment)

If your `.env` includes an OpenAI-compatible API key, you can generate story-specific
images and richer paragraph prose for the full-page newsletter article views.

```bash
# .env should include OPENAI_API_KEY=...

# Build AI assets from ranked data
python3 -m newsroom.ai_toolkit

# Re-render HTML to apply assets
python3 -m newsroom.render --format html
```

The toolkit writes `output/newsletter_ai_assets.json`, and the renderer automatically
uses it to replace image placeholders and body text in article/focus views.

### 3. Customize Content

Edit the mock data files to change content:
- `data/mock/funding.json` - Add/edit funding stories
- `data/mock/events.json` - Add/edit NYC events
- `data/mock/accelerators.json` - Add/edit accelerator programs

Then re-run rank and render to see your changes.

## 🔌 Design Philosophy: Data as Plugins

**PROTOTYPE FIRST**: The system prioritizes getting the newsletter structure right before worrying about data collection:

1. **Phase 1 (NOW)**: Use mock JSON files that match the final data schema
2. **Phase 2 (LATER)**: Replace mock loaders with real scrapers/APIs

**Why this approach?**
- Focus on the product (newsletter quality, templates, storytelling)
- Test ranking and rendering logic with realistic data
- Demo-ready without needing API keys or dealing with scraper breakage
- Swap sources later without changing newsletter generation code

## ⚙️ Configuration

Edit `config.yaml` to customize:

```yaml
search:
  default_days_back: 7        # How far back to search
  primary_city: "NYC"         # Geographic focus

limits:
  funding_items: 10           # Max funding stories
  event_items: 12             # Max events
  accelerator_items: 8        # Max accelerators

categories:
  ai_ml: ["ai", "machine learning", "llm"]
  fintech: ["fintech", "payments", "banking"]
  # ... add more categories
```

## 📊 Data Models

### FundingItem
```python
FundingItem:
  - title: str
  - startup_name: str
  - round_type: str (pre-seed/seed/series-a/series-b/etc)
  - amount: str ("$10M" or "Undisclosed")
  - investors: List[str]
  - lead_investor: str | None
  - location: str | None
  - announced_date: str (YYYY-MM-DD)
  - source_urls: List[str]
  - evidence_snippets: List[str]
  - categories: List[str]
  - who_what_why_when_where_how: WHOWHATWHYStructure
```

### EventItem
```python
EventItem:
  - event_name: str
  - date_time: str
  - city: str
  - venue_or_online: str
  - cost: str
  - audience: str
  - registration_url: str | None
  - source_url: str
```

### AcceleratorItem
```python
AcceleratorItem:
  - name: str
  - city_region: str | None
  - focus: str | None
  - source_url: str
```

## 🧪 Testing

Run unit tests:

```bash
pytest tests/test_newsroom.py -v
```

Tests include:
- ✅ Parsing TechCrunch articles
- ✅ Parsing AlleyWatch reports
- ✅ Parsing Gary's Guide events
- ✅ Amount parsing ($5M, $1B, undisclosed)
- ✅ Round type normalization
- ✅ Deduplication logic
- ✅ Data model serialization

## 📝 Newsletter Output Format

```markdown
# AI Factory Newsletter
**Weekly startup funding, events, and accelerators**

## 💰 Funding Headlines

**Acme AI** — $10M Series-A Round — Lead: Venture Partners — Other: Angel Fund — Category: AI Ml — [1][2]

**WHO/WHAT:** Acme AI, led by Venture Partners. Raised $10M in series-a round from Venture Partners, Angel Fund

**WHY/HOW:** Building autonomous AI agents for enterprise. Secured funding through series-a round

**WHEN/WHERE:** Announced 2026-02-05. Based in New York

---

## 📊 Trend Brief

**Top categories getting funded this week:**

- **AI Ml**: 5 deals
- **Fintech**: 3 deals
- **Health**: 2 deals

## 🎯 Events & Rooms to Be In

**Founders & Funders Meetup** — Feb 15 — Manhattan — Free — [3]

## 🚀 Accelerators Watch

**TechStars NYC** — New York — Focus: AI — [4]

## 📚 Sources & Bibliography

[1] TechCrunch — https://techcrunch.com/2026/02/05/acme-ai-raises-10m/
[2] AlleyWatch — https://alleywatch.com/2026/02/funding-report/
[3] Gary's Guide — https://garysguide.com/events/founders-meetup
[4] OpenVC — https://openvc.app/accelerators/techstars-nyc
```

## 🎛️ Quality Guards

The system handles missing data gracefully:

- **Amount missing**: Set to "Undisclosed"
- **Round missing**: Infer from keywords (seed/series-a/etc); default "Unknown"
- **Startup name missing**: Infer from title (first proper noun), mark low confidence
- **Limitations block**: Reports any inferred fields at bottom of newsletter

## 🔄 Pipeline Details (Prototype Mode)

### Mock Mode (Default - Current)

```bash
python3 -m newsroom.collect --source mock  # Load from JSON files
python3 -m newsroom.rank                    # Rank by importance
python3 -m newsroom.render --format md      # Generate newsletter
```

**What happens:**
1. **Collect**: Loads pre-formatted JSON from `data/mock/` (already normalized)
2. **Rank**: Sorts funding by amount/round, filters events by city, ranks accelerators
3. **Render**: Applies deterministic templates, assigns citations, builds bibliography

### Real Mode (TODO - Future)

```bash
python3 -m newsroom.collect --source real --since 14d  # Scrape websites
python3 -m newsroom.normalize                          # Extract structured data
python3 -m newsroom.dedupe                            # Merge duplicates
python3 -m newsroom.rank                              # Rank items
python3 -m newsroom.render --format md                # Generate newsletter
```

**What will happen:**
1. **Collection**: Fetch HTML from TechCrunch, AlleyWatch, etc.
2. **Normalization**: Parse HTML → extract FundingItem/EventItem
3. **Deduplication**: Merge duplicates across sources
4. **Ranking**: Sort by importance
5. **Rendering**: Generate newsletter

## 📊 Evaluation Criteria (Class-Focused)

**Can a reader quickly answer:**
- ✅ WHO got money?
- ✅ WHO gave money?
- ✅ WHAT is getting funded?
- ✅ WHY does it matter?
- ✅ WHERE can I meet these people?

**Quality checks:**
- ✅ Does every claim have a source link?
- ✅ Is the output consistent?
- ✅ Is it readable for college students?
- ✅ Reporter-style structure (WHO/WHAT/WHY/WHEN/WHERE/HOW)

## 🛠️ Development

### Editing Mock Data

The easiest way to customize the newsletter:

1. Open `data/mock/funding.json` (or events/accelerators)
2. Add/edit entries following the JSON schema
3. Run: `python3 -m newsroom.rank && python3 -m newsroom.render --format md`

Example funding item:
```json
{
  "startup_name": "YourStartup",
  "round_type": "seed",
  "amount": "$5M",
  "amount_numeric": 5000000,
  "lead_investor": "Cool VC",
  "investors": ["Cool VC", "Angel Fund"],
  "location": "New York, NY",
  "announced_date": "2026-02-01",
  "categories": ["Ai Ml"],
  "source_urls": ["https://techcrunch.com/example"],
  "who_what_why_when_where_how": {
    "who": "YourStartup, led by Cool VC",
    "what": "Raised $5M seed from Cool VC, Angel Fund",
    "why": "Building amazing product that solves X problem",
    "when": "Announced February 1, 2026",
    "where": "Based in New York, NY",
    "how": "Secured funding after initial traction"
  }
}
```

### Adding New Sources (Future)

When ready to add real scrapers:
When ready to add real scrapers:

1. Create collector in `sources.py`:
```python
class NewSourceCollector(BaseCollector):
    def collect(self, days_back: int) -> List[RawSource]:
        # Fetch logic
        pass
```

2. Add parser in `normalize.py`:
```python
class NewSourceNormalizer:
    def normalize(self, raw_source: RawSource) -> List[FundingItem]:
        # Parse logic
        pass
```

3. Register in `config.yaml`:
```yaml
sources:
  new_source:
    enabled: true
    base_url: "https://newsource.com"
```

### Adding Categories

Edit `config.yaml`:
```yaml
categories:
  your_category:
    - "keyword1"
    - "keyword2"
```

## 📋 Requirements

- Python 3.11+
- requests
- beautifulsoup4
- PyYAML
- python-dateutil
- pytest (for testing)
Prototype Limitations & Future Work

### Current (Intentional) Limitations
- ✅ Uses mock data (not live scraping) - **By design for prototype**
- ✅ Manual data entry required - **Allows focus on newsletter quality**
- ✅ No live API integrations - **Avoids rate limits during development**

### Future Enhancements (Post-Class)

**TODO: Data Collection**
- [ ] TechCrunch RSS feed integration
**TODO: Quality**
- [ ] Expand test coverage to 50+ tests
- [ ] Add logging and monitoring
- [ ] Selenium/Playwright for JavaScript-heavy sites
- [ ] Smart date parsing (handles relative dates)
- [ ] Better citation formatting
- [ ] PDF generation option

## 💡 Why This Architecture?

**Priorities for class prototype:**
1. **Newsletter quality** > Data accuracy
2. **Template consistency** > Source coverage  
3. **Readable output** > Perfect extraction
---

**Built with ❤️ for the startup community | Prototype-first, production-later approach
- **Software design**: Plugin architecture, separation of concerns
- **Data modeling**: Structured schemas, serialization
- **Template engineering**: Deterministic output, citation tracking
- **Testing**: Unit tests for parsing, ranking, data models
- **Documentation**: Clear README, inline comments
- **Prototype thinking**: MVP with clear path to production

The mock data approach is **intentional** - it allows focus on the product (newsletter) rather than fighting with scrapers during development.

---

## 🚀 Quick Command Reference

```bash
# Full workflow (mock mode - default)
python3 -m newsroom.collect --source mock
python3 -m newsroom.rank
python3 -m newsroom.render --format md

# Generate both Markdown and HTML
python3 -m newsroom.render --format both

# Run tests
python3 -m pytest tests/test_newsroom.py -v

# Edit mock data
nano data/mock/funding.json

# View output
cat output/newsletter.md
```

---stories
- [ ] Duplicate detection using fuzzy matching
- [ ] Auto-summarization of long articles

**TODO: Distribution**
- [ ] Email delivery via SendGrid/Mailchimp
- [ ] RSS feed generation
- [ ] Web interface for subscriptions
- [ ] Personalization by city/interest/major

**TODO: Analytics**
- [ ] Historical trend analysis
- [ ] Investor spotlight section
- [ ] Category deep-dives
- [ ] Charts and visualizations

**TODO: Quality**
## 🔮 Future Enhancements

- [ ] Add Selenium/Playwright for JavaScript-heavy sites
- [ ] ML-based category classification
- [ ] Sentiment analysis for funding stories
- [ ] Email delivery integration
- [ ] RSS feed generation
- [ ] Historical trend analysis
- [ ] Investor spotlight section
- [ ] Smart date parsing (relative dates like "yesterday")
- [ ] Web interface for configuration

## 📄 License

See LICENSE file.

## 🤝 Contributing

This is an MVP prototype. For production use:
1. Add rate limiting for web scraping
2. Implement caching layer
3. Add error recovery and retry logic
4. Expand test coverage
5. Add logging and monitoring

---

**Generated with ❤️ for the startup community**