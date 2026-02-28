"""
execution/store_generated_posts.py
-----------------------------------
Layer 3: Execution — Deterministic

Reads generated post data from .tmp/generated_posts.json and stores
each generated post (topic, text, infographic prompt) into the
`generated_posts` table in the SQLite database.

Inputs:
    .tmp/generated_posts.json
    posts.db (same database as scraped posts)

Outputs:
    Updated `generated_posts` table in posts.db

Usage:
    python execution/store_generated_posts.py
    python execution/store_generated_posts.py --db /path/to/custom.db
"""

import os
import sys
import json
import sqlite3
import argparse

# ─── Config ──────────────────────────────────────────────────────────────────

ROOT_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP_DIR    = os.path.join(ROOT_DIR, ".tmp")
INPUT_FILE = os.path.join(TMP_DIR, "generated_posts.json")
DEFAULT_DB = os.path.join(ROOT_DIR, "posts.db")

# ─── DB ──────────────────────────────────────────────────────────────────────

def init_generated_table(db_path: str):
    """Creates the generated_posts table if it does not exist."""
    conn = sqlite3.connect(db_path)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS generated_posts (
            id                 INTEGER PRIMARY KEY AUTOINCREMENT,
            topic              TEXT,
            post_text          TEXT,
            infographic_prompt TEXT,
            source_post_ids    TEXT,
            generated_date     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()


def store_generated(db_path: str, post: dict):
    """Inserts a single generated post into the database."""
    conn = sqlite3.connect(db_path)
    try:
        conn.execute('''
            INSERT INTO generated_posts
              (topic, post_text, infographic_prompt, source_post_ids, generated_date)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            post.get("topic", ""),
            post.get("post_text", ""),
            post.get("infographic_prompt", ""),
            ",".join(post.get("source_post_ids", [])),
            post.get("generated_at", ""),
        ))
        conn.commit()
    except Exception as e:
        print(f"[store_generated_posts] DB insert error: {e}")
    finally:
        conn.close()

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Store generated posts into SQLite.")
    parser.add_argument("--db", default=DEFAULT_DB, help="Path to SQLite database file")
    args = parser.parse_args()

    if not os.path.exists(INPUT_FILE):
        print(f"[store_generated_posts] ERROR: Input file not found: {INPUT_FILE}")
        sys.exit(1)

    with open(INPUT_FILE, encoding="utf-8") as f:
        generated = json.load(f)

    if not generated:
        print("[store_generated_posts] No generated posts to store. Skipping.")
        sys.exit(0)

    init_generated_table(args.db)

    for post in generated:
        store_generated(args.db, post)

    print(f"[store_generated_posts] ✓ Stored {len(generated)} generated post(s) in {args.db}")


if __name__ == "__main__":
    main()
