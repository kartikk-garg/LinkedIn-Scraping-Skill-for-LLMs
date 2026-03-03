---
name: linkedin-automation
description: >
  Automates LinkedIn content intelligence for Data Engineering creators.
  Scrapes recent posts via Apify, stores them in SQLite for vectorization,
  syncs to Google Docs (Notebook LM) and Google Sheets (structured tabs),
  and generates N LinkedIn posts + infographic prompts via Gemini.
---

# LinkedIn Automation Skill

This skill gives you agentic access to a modular LinkedIn content automation system.
Each capability is a standalone Python script in `execution/`. You can call them
individually for targeted tasks, or run the full pipeline at once.

## Available Tools

### 1. Scrape LinkedIn Posts
**Script:** `execution/scrape_posts.py`  
**Directive:** `directives/scrape_posts.md`  
**What it does:** Calls Apify `supreme_coder/linkedin-post` to fetch posts from the last 24 hours.  
**Output:** `.tmp/scraped_posts.json`

```bash
python execution/scrape_posts.py
python execution/scrape_posts.py --urls https://www.linkedin.com/in/someone --max-posts 10
```

---

### 2. Store & Deduplicate Posts
**Script:** `execution/store_posts_db.py`  
**Directive:** `directives/store_posts_db.md`  
**What it does:** Reads `.tmp/scraped_posts.json`, filters already-seen posts, saves new ones to SQLite, writes `.tmp/new_posts.json`.  
**Output:** `.tmp/new_posts.json` + `posts.db`

```bash
python execution/store_posts_db.py
```

---

### 3. Sync to Google Docs (Notebook LM)
**Script:** `execution/sync_google_docs.py`  
**Directive:** `directives/sync_google_docs.md`  
**What it does:** Appends formatted new posts to the Google Doc for Notebook LM context.  
**Input:** `.tmp/new_posts.json`

```bash
python execution/sync_google_docs.py
```

---

### 4. Sync Scraped Posts → Google Sheets
**Script:** `execution/sync_scraped_sheets.py`  
**Directive:** `directives/sync_scraped_sheets.md`  
**What it does:** Writes scraped posts to a Google Sheet with one tab per LinkedIn creator.  
**Input:** `.tmp/new_posts.json`

```bash
python execution/sync_scraped_sheets.py
```

---

### 5. Generate LinkedIn Content (N posts)
**Script:** `execution/generate_content.py`  
**Directive:** `directives/generate_content.md`  
**What it does:** Picks the best N topics from scraped posts, then for each: creates a LinkedIn post text + infographic prompt via Gemini.  
**Input:** `.tmp/new_posts.json` → **Output:** `.tmp/generated_posts.json` + `generated_posts/<ts>.json`

```bash
python execution/generate_content.py --num-posts 2
python execution/generate_content.py --num-posts 3 --model gemini-2.5-pro
```

---

### 6. Store Generated Posts (SQLite)
**Script:** `execution/store_generated_posts.py`  
**Directive:** `directives/store_generated_posts.md`  
**What it does:** Saves generated posts (topic, text, infographic prompt) into the `generated_posts` SQLite table.  
**Input:** `.tmp/generated_posts.json`

```bash
python execution/store_generated_posts.py
```

---

### 7. Sync Generated Posts → Google Sheets
**Script:** `execution/sync_generated_sheets.py`  
**Directive:** `directives/sync_generated_sheets.md`  
**What it does:** Writes generated posts to a Google Sheet with one tab per date.  
**Input:** `.tmp/generated_posts.json`

```bash
python execution/sync_generated_sheets.py
```

---

### 8. Generate Infographic Images (Nano Banana)
**Script:** `execution/generate_image.py`  
**Directive:** `directives/generate_image.md`  
**What it does:** Generates infographic images from prompts using Gemini Nano Banana image generation model.  
**Input:** `.tmp/generated_posts.json` (reads `infographic_prompt`) or `--prompt` for single image  
**Output:** `generated_images/<timestamp>_post_<n>.png`

```bash
python execution/generate_image.py
python execution/generate_image.py --prompt "A clean data engineering infographic..."
```

---

### 9. Upload Images to Google Drive
**Script:** `execution/upload_drive.py`  
**Directive:** `directives/upload_drive.md`  
**What it does:** Uploads all images from `generated_images/` to a Google Drive folder, organized in date-based subfolders.  
**Input:** `generated_images/*.png` → **Output:** `.tmp/drive_uploads.json`

```bash
python execution/upload_drive.py
python execution/upload_drive.py --folder-id 1ABC...xyz
```

---

### 10. Run Full Pipeline
**Script:** `execution/run_pipeline.py`  
**What it does:** Runs all 9 steps above in sequence.

```bash
python execution/run_pipeline.py
python execution/run_pipeline.py --max-posts 10 --num-posts 3 --model gemini-2.5-pro
```

---

## Environment Variables (`.env`)
| Variable                      | Description                                        |
|-------------------------------|----------------------------------------------------|
| `APIFY_API_TOKEN`             | Apify API key for scraper                          |
| `GEMINI_API_KEY`              | Google AI Studio key for content + image generation |
| `GOOGLE_DOC_ID`               | Google Doc ID for Notebook LM                      |
| `GOOGLE_SERVICE_ACCOUNT_FILE` | Path to Service Account JSON                       |
| `SCRAPED_SHEET_ID`            | Google Sheet ID for scraped posts (per-user tabs)  |
| `GENERATED_SHEET_ID`          | Google Sheet ID for generated posts (per-date tabs)|
| `DRIVE_FOLDER_ID`             | Google Drive folder ID for infographic uploads     |

## Data Flow
```
Apify ──► .tmp/scraped_posts.json
              │
              ▼
          store_posts_db.py ──► posts.db (OpenClaw vectorizes this)
              │
              ├──► .tmp/new_posts.json
              │          │
              │          ├──► sync_google_docs.py    ──► Google Doc (Notebook LM)
              │          ├──► sync_scraped_sheets.py ──► Google Sheet (per-user tabs)
              │          │
              │          └──► generate_content.py ──► .tmp/generated_posts.json
              │                      │
              │                      ├──► store_generated_posts.py ──► posts.db
              │                      ├──► sync_generated_sheets.py ──► Google Sheet (per-date tabs)
              │                      ├──► generate_image.py        ──► generated_images/*.png
              │                      └──► upload_drive.py          ──► Google Drive (date folders)
```

## Using with OpenClaw
OpenClaw can call any script by name. Always read the directive first.
