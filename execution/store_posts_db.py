"""
execution/store_posts_db.py
---------------------------
Layer 3: Execution — Deterministic

Reads scraped posts from .tmp/scraped_posts.json, deduplicates
against the local SQLite database, stores new posts (with full
content) for OpenClaw vectorization, and writes only new posts
to .tmp/new_posts.json for downstream steps.

Inputs:
    .tmp/scraped_posts.json

Outputs:
    .tmp/new_posts.json      — Only new (not previously seen) posts
    posts.db                 — Updated SQLite database

Usage:
    python execution/store_posts_db.py
    python execution/store_posts_db.py --db /path/to/custom.db
"""

import os
import sys
import json
import sqlite3
import argparse

# ─── Config ──────────────────────────────────────────────────────────────────

ROOT_DIR     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP_DIR      = os.path.join(ROOT_DIR, ".tmp")
INPUT_FILE   = os.path.join(TMP_DIR, "scraped_posts.json")
OUTPUT_FILE  = os.path.join(TMP_DIR, "new_posts.json")
DEFAULT_DB   = os.path.join(ROOT_DIR, "posts.db")

# ─── DB Helpers ──────────────────────────────────────────────────────────────

def init_db(db_path: str):
    """Creates the processed_posts table if it does not exist."""
    conn = sqlite3.connect(db_path)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS processed_posts (
            post_id        TEXT PRIMARY KEY,
            creator_url    TEXT,
            author_name    TEXT,
            post_text      TEXT,
            likes          INTEGER,
            comments       INTEGER,
            post_url       TEXT,
            processed_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()


def is_processed(db_path: str, post_id: str) -> bool:
    conn   = sqlite3.connect(db_path)
    cursor = conn.execute("SELECT 1 FROM processed_posts WHERE post_id = ?", (post_id,))
    found  = cursor.fetchone() is not None
    conn.close()
    return found


def store_post(db_path: str, post: dict):
    """Inserts a post record into the database (ignoring duplicates)."""
    post_id     = post.get("url") or post.get("urn") or str(hash(post.get("text", "")))
    conn        = sqlite3.connect(db_path)
    try:
        conn.execute('''
            INSERT OR IGNORE INTO processed_posts
              (post_id, creator_url, author_name, post_text, likes, comments, post_url)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            post_id,
            post.get("authorUrl",  ""),
            post.get("authorName", ""),
            post.get("text",       ""),
            post.get("numLikes",   0),
            post.get("numComments",0),
            post.get("url",        ""),
        ))
        conn.commit()
    except Exception as e:
        print(f"[store_posts_db] DB insert error: {e}")
    finally:
        conn.close()

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Deduplicate and store scraped LinkedIn posts.")
    parser.add_argument("--db", default=DEFAULT_DB, help="Path to SQLite database file")
    args = parser.parse_args()

    if not os.path.exists(INPUT_FILE):
        print(f"[store_posts_db] ERROR: Input file not found: {INPUT_FILE}")
        sys.exit(1)

    with open(INPUT_FILE, encoding="utf-8") as f:
        all_posts = json.load(f)

    print(f"[store_posts_db] Loaded {len(all_posts)} posts from {INPUT_FILE}")

    init_db(args.db)

    new_posts = []
    for post in all_posts:
        post_id = post.get("url") or post.get("urn") or str(hash(post.get("text", "")))
        if not post_id:
            continue
        if not is_processed(args.db, post_id):
            new_posts.append(post)

    print(f"[store_posts_db] {len(new_posts)} new posts (not seen before).")

    # Store new posts in DB
    for post in new_posts:
        store_post(args.db, post)
    print(f"[store_posts_db] ✓ Saved {len(new_posts)} posts to {args.db}")

    # Write new_posts.json for downstream steps
    os.makedirs(TMP_DIR, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(new_posts, f, indent=2, ensure_ascii=False)
    print(f"[store_posts_db] Output saved → {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
