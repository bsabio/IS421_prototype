# AI Factory Newsletter - Quick Start Guide

## 🎯 Prototype-First Approach

This project uses **mock data by default** to focus on newsletter quality first, real data collection later.

---

## 🚀 3-Step Workflow (Prototype Mode)

### Step 1: Collect (Load Mock Data)
```bash
python3 -m newsroom.collect --source mock
```
**What it does:** Loads pre-formatted data from `data/mock/*.json`  
**Time:** < 1 second  
**Output:** `data/deduped.json`

### Step 2: Rank (Sort by Importance)
```bash
python3 -m newsroom.rank
```
**What it does:** Ranks funding by amount, events by date, accelerators by NYC location  
**Time:** < 1 second  
**Output:** `data/ranked.json`

### Step 3: Render (Generate Newsletter)
```bash
python3 -m newsroom.render --format md
```
**What it does:** Applies templates, adds citations, builds bibliography  
**Time:** < 1 second  
**Output:** `output/newsletter.md`

### Step 4 (Optional): AI Enrich Paragraphs + Images
```bash
# .env should include OPENAI_API_KEY=...
python3 -m newsroom.ai_toolkit
python3 -m newsroom.render --format html
```
**What it does:** Uses OpenAI-compatible APIs to rewrite story bodies into natural paragraphs and generate contextual images for full-page article placeholders  
**Output:** `output/newsletter_ai_assets.json` + enriched `output/newsletter.html`

---

## ✏️ Customizing Content

### Edit Mock Data Files

**Funding stories:**
```bash
nano data/mock/funding.json
```

**Events:**
```bash
nano data/mock/events.json
```

**Accelerators:**
```bash
nano data/mock/accelerators.json
```

### After editing, regenerate:
```bash
python3 -m newsroom.collect --source mock
python3 -m newsroom.rank
python3 -m newsroom.render --format md
```

---

## 📊 View Output

**Markdown:**
```bash
cat output/newsletter.md
```

**HTML:**
```bash
python3 -m newsroom.render --format html
# Open output/newsletter.html in browser
```

**Both:**
```bash
python3 -m newsroom.render --format both
```

---

## 🧪 Testing

**Run all tests:**
```bash
python3 -m pytest tests/test_newsroom.py -v
```

**Run specific test:**
```bash
python3 -m pytest tests/test_newsroom.py::TestUtils::test_parse_amount_millions -v
```

---

## 🔌 Plugin Architecture

### Current: Mock Sources
- `data/mock/funding.json`
- `data/mock/events.json`
- `data/mock/accelerators.json`

### Future: Real Sources (TODO)
When ready to add real scrapers:

1. Implement in `newsroom/sources.py`
2. Run with: `python3 -m newsroom.collect --source real`
3. Newsletter generation (rank + render) stays the same!

---

## 💡 Design Principles

1. **Templates are the product** - Focus on newsletter quality
2. **Data sources are plugins** - Easy to swap mock → real
3. **Deterministic output** - Same input = same newsletter
4. **Citations mandatory** - Every claim has a source
5. **Student-friendly** - Clear WHO/WHAT/WHY/WHEN/WHERE/HOW

---

## 🎓 For Class Demos

The mock data includes realistic examples:
- **10 funding announcements** ($2.5M to $20M, various stages)
- **8 NYC tech events** (meetups, conferences, office hours)
- **7 accelerators** (TechStars, ERA, Y Combinator, etc.)

All data looks real but is manually curated for storytelling quality.

---

## 🚧 What's NOT in Prototype

**Intentionally deferred to Phase 2:**
- ❌ Web scraping (too brittle for demos)
- ❌ API integrations (requires keys, rate limits)
- ❌ Live data (changes unpredictably)
- ❌ Email delivery (out of scope for MVP)

**Focus instead on:**
- ✅ Newsletter structure
- ✅ Template consistency
- ✅ Citation tracking
- ✅ Readability
- ✅ Categorization logic

---

## 📁 Project Structure

```
IS421_prototype/
├── data/
│   └── mock/              # 👈 EDIT THESE for content changes
│       ├── funding.json
│       ├── events.json
│       └── accelerators.json
├── newsroom/              # Core pipeline code
├── output/
│   └── newsletter.md      # 👈 YOUR GENERATED NEWSLETTER
└── tests/                 # Unit tests
```

---

## ⚡ Common Operations

**See what's in your current newsletter:**
```bash
cat output/newsletter.md | grep "^##"  # Section headers
cat output/newsletter.md | grep "^\*\*" | head -5  # First 5 stories
```

**Add a new funding story:**
1. Copy an existing item in `data/mock/funding.json`
2. Edit the fields (startup_name, amount, etc.)
3. Regenerate: `python3 -m newsroom.rank && python3 -m newsroom.render --format md`

**Change output format:**
```bash
python3 -m newsroom.render --format html    # HTML only
python3 -m newsroom.render --format both    # Both MD and HTML
```

---

## 🎯 Success Criteria

Your newsletter is good if:
1. Every funding story has WHO/WHAT/WHY/WHEN/WHERE/HOW
2. Every claim has a citation [1][2][3]
3. Bibliography lists all sources
4. A college student can read it in 5 minutes
5. You can answer: "Who's getting funded? Where can I meet them?"

---

## 🆘 Troubleshooting

**"No mock data found":**
- Check that `data/mock/*.json` files exist
- They should have been created during setup

**"Module not found":**
```bash
pip install -r requirements.txt
```

**"Tests failing":**
- Tests expect specific return formats
- Check that utils.py functions match test expectations

**"Newsletter looks wrong":**
- Check `data/ranked.json` to see what data is being used
- Verify your mock data follows the schema in `newsroom/models.py`

---

**Questions? Check the full README.md for detailed documentation.**
