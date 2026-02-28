"""
execution/sync_scraped_sheets.py
---------------------------------
Layer 3: Execution — Deterministic

Reads new posts from .tmp/new_posts.json and writes them to a
Google Sheet organized with one tab per LinkedIn creator.

Each tab is named after the author (e.g. "Andreas Kretz").
Rows contain: Date, Post Text, Likes, Comments, Post URL.

Inputs:
    .tmp/new_posts.json
    SCRAPED_SHEET_ID            (from .env)
    GOOGLE_SERVICE_ACCOUNT_FILE (from .env)

Outputs:
    Updated Google Sheet with per-user tabs.

Usage:
    python execution/sync_scraped_sheets.py
    python execution/sync_scraped_sheets.py --sheet-id <ID>
"""

import os
import sys
import json
import argparse

from dotenv import load_dotenv
import gspread
from google.oauth2.service_account import Credentials

# ─── Config ──────────────────────────────────────────────────────────────────

load_dotenv()

ROOT_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP_DIR    = os.path.join(ROOT_DIR, ".tmp")
INPUT_FILE = os.path.join(TMP_DIR, "new_posts.json")

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# ─── Helpers ─────────────────────────────────────────────────────────────────

def get_gspread_client():
    sa_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")
    if not sa_file or not os.path.exists(sa_file):
        print(f"[sync_scraped_sheets] ERROR: Service Account file not found: '{sa_file}'")
        sys.exit(1)
    creds = Credentials.from_service_account_file(sa_file, scopes=SCOPES)
    return gspread.authorize(creds)


def get_or_create_worksheet(spreadsheet, title: str):
    """Gets an existing worksheet by title, or creates it."""
    try:
        return spreadsheet.worksheet(title)
    except gspread.exceptions.WorksheetNotFound:
        print(f"[sync_scraped_sheets] Creating new tab: '{title}'")
        ws = spreadsheet.add_worksheet(title=title, rows=100, cols=6)
        # Add headers
        ws.append_row(["Date", "Post Text", "Likes", "Comments", "Post URL"],
                       value_input_option="USER_ENTERED")
        return ws


def post_to_row(post: dict) -> list:
    """Converts a post dict to a spreadsheet row."""
    return [
        post.get("postedAt") or post.get("publishedAt", "Unknown"),
        post.get("text", "")[:50000],  # Sheets cell limit
        post.get("numLikes", 0),
        post.get("numComments", 0),
        post.get("url", ""),
    ]

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Sync scraped posts to Google Sheets (per-user tabs).")
    parser.add_argument("--sheet-id", default=os.getenv("SCRAPED_SHEET_ID"), help="Scraped Posts Sheet ID")
    args = parser.parse_args()

    if not args.sheet_id:
        print("[sync_scraped_sheets] ERROR: SCRAPED_SHEET_ID not set. Pass --sheet-id or set it in .env")
        sys.exit(1)

    if not os.path.exists(INPUT_FILE):
        print(f"[sync_scraped_sheets] ERROR: Input file not found: {INPUT_FILE}")
        sys.exit(1)

    with open(INPUT_FILE, encoding="utf-8") as f:
        posts = json.load(f)

    if not posts:
        print("[sync_scraped_sheets] No new posts to sync. Skipping.")
        sys.exit(0)

    # Group posts by author
    by_author = {}
    for post in posts:
        author = post.get("authorName") or post.get("authorUrl", "Unknown")
        by_author.setdefault(author, []).append(post)

    gc = get_gspread_client()
    spreadsheet = gc.open_by_key(args.sheet_id)

    total = 0
    for author, author_posts in by_author.items():
        ws = get_or_create_worksheet(spreadsheet, author)
        rows = [post_to_row(p) for p in author_posts]
        ws.append_rows(rows, value_input_option="USER_ENTERED")
        total += len(rows)
        print(f"[sync_scraped_sheets] Added {len(rows)} post(s) to tab '{author}'")

    print(f"[sync_scraped_sheets] ✓ Synced {total} post(s) across {len(by_author)} tab(s).")


if __name__ == "__main__":
    main()
