# 🔗 LinkedIn Automation

An agentic LinkedIn content automation system for Data Engineering creators. Scrapes trending posts, stores them for analysis, syncs to Google Docs & Sheets, and generates ready-to-post LinkedIn content with infographic prompts via Gemini.

Built with a **3-layer modular architecture** — every function is a standalone script callable by OpenClaw or any AI agent via `SKILL.md`.

---

## ✨ Features

- **Automated Scraping** — Fetches latest posts from Data Engineering creators via Apify
- **Smart Deduplication** — SQLite-backed dedup ensures no duplicate processing
- **Dual Storage** — Google Docs (Notebook LM) + Google Sheets (structured per-user tabs)
- **AI Content Generation** — Gemini picks top topics, writes posts, creates infographic prompts
- **Fully Modular** — Each step is an independent Python script with CLI args
- **Agentic Ready** — `SKILL.md` enables OpenClaw / any AI agent to call tools directly

---

## 📁 Project Structure

```
├── execution/                    # Layer 3: Deterministic execution scripts
│   ├── scrape_posts.py           # Apify → .tmp/scraped_posts.json
│   ├── store_posts_db.py         # Dedup + SQLite → .tmp/new_posts.json
│   ├── sync_google_docs.py       # Append to Google Doc (Notebook LM)
│   ├── sync_scraped_sheets.py    # Per-user tabs in Scraped Sheet
│   ├── generate_content.py       # Gemini: pick topics → write post → infographic
│   ├── store_generated_posts.py  # Save generated content to SQLite
│   ├── sync_generated_sheets.py  # Per-date tabs in Generated Sheet
│   └── run_pipeline.py           # Full 7-step orchestrator
├── directives/                   # Layer 1: SOPs for each tool
├── SKILL.md                      # OpenClaw skill definition
├── AGENTS.md                     # Agentic architecture spec
├── .tmp/                         # Transient intermediate JSON files
├── generated_posts/              # Timestamped output files
├── posts.db                      # SQLite database
├── requirements.txt
├── .env                          # API keys & config (not tracked)
└── .env.example                  # Template for .env
```

---

## 🚀 Quick Start

### 1. Clone & Install

```bash
git clone <repo-url>
cd "LinkedIn automation"
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and fill in your credentials:

```env
APIFY_API_TOKEN=your_apify_token
GEMINI_API_KEY=your_gemini_key
GOOGLE_SERVICE_ACCOUNT_FILE=service.json
GOOGLE_DOC_ID=your_notebook_lm_doc_id
SCRAPED_SHEET_ID=your_scraped_sheet_id
GENERATED_SHEET_ID=your_generated_sheet_id
```

### 3. Google Setup

1. **Service Account** — Create one in Google Cloud Console, download the JSON key as `service.json`
2. **Google Doc** — Create a doc, share with the Service Account email as Editor
3. **Google Sheets** — Create 2 sheets (Scraped Posts + Generated Posts), share both with the Service Account as Editor
4. Copy all IDs into `.env`

### 4. Run the Full Pipeline

```bash
python execution/run_pipeline.py --max-posts 5 --num-posts 2
```

This runs all 7 steps: Scrape → Dedup → Google Docs → Scraped Sheets → Generate Content → Store Generated → Generated Sheets

---

## 🔧 Individual Tools

Each script works independently:

```bash
# Scrape specific profiles
python execution/scrape_posts.py --urls https://linkedin.com/in/someone --max-posts 10

# Store & deduplicate
python execution/store_posts_db.py

# Sync to Google Docs
python execution/sync_google_docs.py

# Sync to Scraped Sheets (per-user tabs)
python execution/sync_scraped_sheets.py

# Generate N posts via Gemini
python execution/generate_content.py --num-posts 3 --model gemini-2.5-pro

# Store generated posts in SQLite
python execution/store_generated_posts.py

# Sync generated posts to Sheets (per-date tabs)
python execution/sync_generated_sheets.py
```

---

## 🤖 Agentic Usage (OpenClaw)

This project is designed as an **OpenClaw skill**. The AI agent:

1. Reads `SKILL.md` to discover available tools
2. Reads `directives/*.md` for input/output specs and edge cases
3. Calls `execution/*.py` scripts with appropriate CLI args
4. Can skip Gemini and use its own LLM by reading `.tmp/new_posts.json` directly

---

## 📊 Data Flow

```
Apify ──► .tmp/scraped_posts.json
              │
              ▼
          store_posts_db.py ──► posts.db
              │
              ├──► sync_google_docs.py    ──► Google Doc (Notebook LM)
              ├──► sync_scraped_sheets.py ──► Google Sheet (per-user tabs)
              │
              └──► generate_content.py ──► .tmp/generated_posts.json
                           │
                           ├──► store_generated_posts.py ──► posts.db
                           └──► sync_generated_sheets.py ──► Google Sheet (per-date tabs)
```

---

## 📦 Dependencies

| Package | Purpose |
|---------|---------|
| `apify-client` | LinkedIn post scraping via Apify |
| `google-api-python-client` | Google Docs API |
| `google-auth-oauthlib` | Google OAuth |
| `gspread` | Google Sheets API |
| `google-genai` | Gemini API for content generation |
| `python-dotenv` | Environment variable management |

---

## 📄 License

MIT
