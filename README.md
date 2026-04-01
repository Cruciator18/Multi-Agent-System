# Automated Competitive Intelligence Agent

A production-grade multi-agent AI pipeline that autonomously monitors competitor pricing pages, extracts structured data using LLM tool calling, validates it against a strict schema, and persists clean records to a SQLite database.

Built as a portfolio project demonstrating **Agentic AI**, **Tool Calling**, **Structured Outputs**, and **Multi-Agent Orchestration**.

---

## What It Does

Feed it a list of competitor URLs. It runs three specialized agents in sequence:

1. **Scraper Agent** — fetches raw HTML, strips DOM noise with BeautifulSoup, then uses a fast LLM to semantically filter only commercially relevant content
2. **Extractor Agent** — uses Groq's tool-calling API to force structured JSON output from a 70B LLM, validated against a Pydantic schema
3. **Validator Agent** — runs Python hard rules (negative prices, empty company names) then a second LLM call for semantic consistency checks before any DB write

Clean, timestamped records land in SQLite. Failed records go to an error log with the exact stage that failed.

```
============================================================
[14:23:01] Processing: https://linear.app/pricing
============================================================
  [Agent 1] Scraping and cleaning HTML...
  [Agent 1] ✓ Cleaned text: 1278 chars
  [Agent 2] Extracting structured intel...
  [Agent 2] ✓ Extracted: Linear | 4 tiers | confidence: 0.80
  [Agent 3] Validating against schema and business rules...
  [DB]      ✓ Saved to database (row id: 1)

PIPELINE SUMMARY
============================================================
  ✓ Successful: 3/3
      Linear  — 4 pricing tiers (confidence: 80%)
      Notion  — 4 pricing tiers (confidence: 90%)
      ClickUp — 3 pricing tiers (confidence: 95%)
```

---

## Tech Stack

| Component | Tool | Purpose |
|---|---|---|
| LLM inference | [Groq API](https://console.groq.com) | Fast cloud inference — GPU not required |
| Cleaning model | `llama-3.1-8b-instant` | Low-cost model for text filtering |
| Extraction model | `llama-3.3-70b-versatile` | Strong reasoning for structured extraction |
| Schema validation | Pydantic v2 | Runtime type enforcement at the LLM boundary |
| HTTP client | httpx | Async-ready, timeout handling, redirect following |
| HTML parsing | BeautifulSoup4 | DOM traversal and tag removal |
| Database | SQLite3 | Zero-config, file-based, portable |
| Env management | python-dotenv | Keeps API keys out of source code |

---

## Project Structure

```
agent_project/
├── .env                    # GROQ_API_KEY=gsk_...
├── main.py                 # Orchestrator — runs all 3 agents per URL
├── requirements.txt
├── agents/
│   ├── scraper.py          # Agent 1: fetch + BeautifulSoup + LLM clean
│   ├── extractor.py        # Agent 2: Groq tool calling + Pydantic
│   └── validator.py        # Agent 3: hard rules + LLM semantic review
├── models/
│   └── schema.py           # Pydantic models (single source of truth)
└── database/
    └── db.py               # SQLite init, save, error logging
```

---

## Quickstart

### 1. Clone and set up environment

```bash
git clone https://github.com/your-username/competitive-intel-agent.git
cd competitive-intel-agent
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Add your Groq API key

Create a `.env` file in the project root:

```
GROQ_API_KEY=gsk_your_key_here
```

Get a free key at [console.groq.com](https://console.groq.com) → API Keys → Create API Key.

> **Note:** The file must be named `.env` (not `_env` or `env.txt`) and the key must be spelled `GROQ_API_KEY` exactly.

### 3. Add your competitor URLs

Edit `main.py`:

```python
COMPETITOR_URLS = [
    "https://linear.app/pricing",
    "https://www.notion.so/pricing",
    "https://clickup.com/pricing",
]
```

### 4. Run

```bash
python main.py
```

---

## Requirements

```
groq==0.9.0
pydantic==2.12.5
httpx==0.28.1
beautifulsoup4==4.12.3
python-dotenv==1.0.1
```

Install all at once:

```bash
pip install -r requirements.txt
```

---

## Data Schema

Every validated record conforms to this Pydantic model:

```python
class CompetitorIntel(BaseModel):
    url: str
    company_name: str
    scraped_at: datetime

    pricing_tiers: list[PricingTier]   # name, price, billing cycle, features
    has_free_tier: bool
    has_enterprise_tier: bool

    headline: Optional[str]            # hero value proposition
    key_features: list[str]
    new_features: list[str]            # anything labeled "new" or "just launched"
    primary_cta: Optional[str]         # e.g. "Start free trial"
    target_persona: Optional[str]

    confidence_score: float            # 0.0–1.0, self-reported by the LLM
    extraction_notes: str              # caveats ("pricing was behind a login")
```

Array fields (`pricing_tiers`, `key_features`, `new_features`) are JSON-serialized to TEXT in SQLite and deserialized on read.

---

## Querying the Database

After a run, inspect stored records:

```python
import sqlite3, json

conn = sqlite3.connect("competitor_intel.db")
conn.row_factory = sqlite3.Row

rows = conn.execute(
    "SELECT company_name, confidence_score, pricing_tiers FROM competitor_intel ORDER BY created_at DESC"
).fetchall()

for r in rows:
    tiers = json.loads(r["pricing_tiers"])
    print(f"\n{r['company_name']} (confidence: {r['confidence_score']:.0%})")
    for t in tiers:
        price = f"${t['price_usd_monthly']}/mo" if t["price_usd_monthly"] is not None else "Contact sales"
        print(f"  {t['name']}: {price}")
```

---

## How Each Agent Works

### Agent 1 — Scraper (`agents/scraper.py`)

Two-stage cleaning pipeline:

1. **BeautifulSoup** removes structural noise — strips `<script>`, `<style>`, `<nav>`, `<footer>`, `<header>`, `<aside>`, `<iframe>` tags entirely
2. **LLM (`llama-3.1-8b-instant`)** performs semantic filtering — understands that "Cookie Policy" is irrelevant even if it sits inside `<main>`

Text is truncated to 8,000 characters to stay within token limits while keeping the most commercially dense content.

### Agent 2 — Extractor (`agents/extractor.py`)

Uses Groq's **tool-calling API** to guarantee structured output. Rather than prompting the LLM to "respond in JSON", a typed function schema is registered as a tool — the API enforces that the model's response matches the schema or rejects it.

Null-coercion is applied after parsing to handle cases where the LLM returns `null` for optional array fields:

```python
data["new_features"] = data.get("new_features") or []
data["key_features"] = data.get("key_features") or []
data["pricing_tiers"] = data.get("pricing_tiers") or []
```

Pydantic validates the final object before it leaves the function.

### Agent 3 — Validator (`agents/validator.py`)

Two-stage quality gate:

**Stage 1 — Python hard rules (free, instant):**
- Confidence score must be ≥ 0.4
- Company name must be at least 2 characters after stripping
- No negative prices or prices above $100,000

**Stage 2 — LLM semantic review:**
- Checks for logical inconsistencies (e.g. `has_free_tier: True` but no free tier in the list)
- Uses `temperature=0.0` for deterministic, reproducible verdicts
- Uses `response_format: json_object` to force a clean `{"approved": bool, "reason": str}` response

> **Important:** The validator prompt explicitly states what IS valid (free tiers at $0.0/mo, null prices for Enterprise) — not just what's invalid. Without this, the LLM fills in assumptions that may be wrong.

---

## Database Schema

```sql
CREATE TABLE IF NOT EXISTS competitor_intel (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    url              TEXT NOT NULL,
    company_name     TEXT,
    scraped_at       TEXT,
    pricing_tiers    TEXT,    -- JSON array
    has_free_tier    INTEGER, -- 0 or 1
    has_enterprise   INTEGER,
    headline         TEXT,
    key_features     TEXT,    -- JSON array
    new_features     TEXT,    -- JSON array
    primary_cta      TEXT,
    target_persona   TEXT,
    confidence_score REAL,
    extraction_notes TEXT,
    created_at       TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS error_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    url         TEXT,
    stage       TEXT,    -- 'scraper' | 'extractor' | 'validator'
    error_msg   TEXT,
    raw_output  TEXT,
    logged_at   TEXT DEFAULT (datetime('now'))
);
```

---

## Common Errors and Fixes

### `KeyError: 'GROQ_API_KEY'`

**Causes (in order of likelihood):**
- Typo in `.env` — must be `GROQ_API_KEY` not `GROK_API_KEY`
- `load_dotenv()` is called after agent imports in `main.py` — it must be the first two lines
- `.env` file is in the wrong directory or named `_env`
- `client = Groq(...)` is at module level in an agent file — move it inside the function

**Correct `main.py` structure:**
```python
from dotenv import load_dotenv
load_dotenv()  # must come before any agent import

import os
from agents.scraper import fetch_and_clean
# ...
```

### `tool_use_failed: expected array, got null`

The LLM returned `null` for an array field. Fix in `extractor.py` after `json.loads()`:

```python
data["new_features"] = data.get("new_features") or []
data["key_features"] = data.get("key_features") or []
data["pricing_tiers"] = data.get("pricing_tiers") or []
```

### Validator rejects free tiers

The validator LLM prompt must explicitly allow `$0.0/mo` prices. Add to the system prompt:

```
IMPORTANT: A free tier priced at $0.0/mo is VALID. Do NOT reject this.
Enterprise tiers with null price are VALID.
Only reject negative prices or impossibly large values.
```

---

## Extending This Project

**Change detection** — re-run and diff against previous DB records to detect when a competitor changes a price:

```python
def detect_price_changes(company_name: str) -> list[dict]:
    rows = conn.execute(
        "SELECT pricing_tiers FROM competitor_intel WHERE company_name=? ORDER BY created_at DESC LIMIT 2",
        (company_name,)
    ).fetchall()
    if len(rows) < 2:
        return []
    new = {t["name"]: t["price_usd_monthly"] for t in json.loads(rows[0]["pricing_tiers"])}
    old = {t["name"]: t["price_usd_monthly"] for t in json.loads(rows[1]["pricing_tiers"])}
    return [{"tier": k, "old": old.get(k), "new": v} for k, v in new.items() if old.get(k) != v]
```

**Scheduled runs** — add APScheduler to re-scrape daily automatically:

```bash
pip install apscheduler
```

```python
from apscheduler.schedulers.blocking import BlockingScheduler

scheduler = BlockingScheduler()
scheduler.add_job(main, 'interval', hours=24)
scheduler.start()
```

**Streamlit dashboard** — visualize stored intel in 20 lines:

```bash
pip install streamlit
streamlit run dashboard.py
```

**Async parallel scraping** — process all URLs simultaneously instead of sequentially:

```python
import asyncio
import httpx

async def fetch_all(urls):
    async with httpx.AsyncClient() as client:
        tasks = [client.get(url, follow_redirects=True) for url in urls]
        return await asyncio.gather(*tasks)
```

---

## License

MIT

---

## Author

Pull requests welcome.
