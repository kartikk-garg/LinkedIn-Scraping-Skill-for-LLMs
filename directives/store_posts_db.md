# Directive: Store Posts in Database

## Goal
Read scraped posts from `.tmp/scraped_posts.json`, deduplicate against the local SQLite database (`posts.db`), save new post full-text content to the DB for OpenClaw vectorization, and output only the new posts for downstream steps.

## When to Use
- Always run immediately after `scrape_posts.py` succeeds.
- Run in isolation when you want to manually inject posts into the DB or re-process scraped data.

## Inputs
| Parameter             | Source             | Description                                     |
|-----------------------|--------------------|-------------------------------------------------|
| `.tmp/scraped_posts.json` | Previous step  | Raw posts from Apify scraper                    |
| `--db`                | CLI (optional)     | Custom path to SQLite DB (default: `posts.db`)  |

## Tool to Call
```
python execution/store_posts_db.py [--db /path/to/db]
```

## Outputs
| File                    | Description                                                   |
|-------------------------|---------------------------------------------------------------|
| `.tmp/new_posts.json`   | New (unprocessed) posts only — passed to downstream steps     |
| `posts.db`              | Updated SQLite DB with full post content                      |

## Database Schema
| Column          | Type      | Description                                    |
|-----------------|-----------|------------------------------------------------|
| `post_id`       | TEXT (PK) | Post URL or URN (unique identifier)             |
| `creator_url`   | TEXT      | LinkedIn profile URL of the author             |
| `author_name`   | TEXT      | Display name of the author                     |
| `post_text`     | TEXT      | Full post content (for OpenClaw vectorization) |
| `likes`         | INTEGER   | Number of likes                                |
| `comments`      | INTEGER   | Number of comments                             |
| `post_url`      | TEXT      | Direct URL to post                             |
| `processed_date`| TIMESTAMP | When we processed this post                    |

## Edge Cases & Learnings
- **Post ID fallback**: Uses `url` → `urn` → `hash(text)` in that priority order.
- **Deduplication**: Uses `INSERT OR IGNORE` so re-runs are safe.
- If `.tmp/new_posts.json` contains `[]`, downstream steps (sync, generate) will skip gracefully.
- OpenClaw should query `posts.db` via the `post_text` column for vectorization.
