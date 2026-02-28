"""
execution/sync_generated_sheets.py
------------------------------------
Layer 3: Execution — Deterministic

Reads generated posts from .tmp/generated_posts.json and writes
them to a Google Sheet organized with one tab per date.

Each date tab (e.g. "2026-02-28") contains rows:
  Post # | Topic | Post Text | Infographic Prompt | Source Posts

Inputs:
    .tmp/generated_posts.json
    GENERATED_SHEET_ID          (from .env)
    GOOGLE_SERVICE_ACCOUNT_FILE (from .env)

Outputs:
    Updated Google Sheet with per-date tabs.

Usage:
    python execution/sync_generated_sheets.py
    python execution/sync_generated_sheets.py --sheet-id <ID>
"""

import os
import sys
import json
import argparse
from datetime import datetime

from dotenv import load_dotenv
import gspread
from google.oauth2.service_account import Credentials

# ─── Config ──────────────────────────────────────────────────────────────────

load_dotenv()

ROOT_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP_DIR    = os.path.join(ROOT_DIR, ".tmp")
INPUT_FILE = os.path.join(TMP_DIR, "generated_posts.json")

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# ─── Helpers ─────────────────────────────────────────────────────────────────

def get_gspread_client():
    sa_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")
    if not sa_file or not os.path.exists(sa_file):
        print(f"[sync_generated_sheets] ERROR: Service Account file not found: '{sa_file}'")
        sys.exit(1)
    creds = Credentials.from_service_account_file(sa_file, scopes=SCOPES)
    return gspread.authorize(creds)


def get_or_create_worksheet(spreadsheet, title: str):
    """Gets an existing worksheet by title, or creates it."""
    try:
        return spreadsheet.worksheet(title)
    except gspread.exceptions.WorksheetNotFound:
        print(f"[sync_generated_sheets] Creating new tab: '{title}'")
        ws = spreadsheet.add_worksheet(title=title, rows=100, cols=5)
        ws.append_row(
            ["Post #", "Topic", "Post Text", "Infographic Prompt", "Source Posts"],
            value_input_option="USER_ENTERED",
        )
        return ws

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Sync generated posts to Google Sheets (per-date tabs).")
    parser.add_argument("--sheet-id", default=os.getenv("GENERATED_SHEET_ID"), help="Generated Posts Sheet ID")
    args = parser.parse_args()

    if not args.sheet_id:
        print("[sync_generated_sheets] ERROR: GENERATED_SHEET_ID not set. Pass --sheet-id or set it in .env")
        sys.exit(1)

    if not os.path.exists(INPUT_FILE):
        print(f"[sync_generated_sheets] ERROR: Input file not found: {INPUT_FILE}")
        sys.exit(1)

    with open(INPUT_FILE, encoding="utf-8") as f:
        generated = json.load(f)

    if not generated:
        print("[sync_generated_sheets] No generated posts to sync. Skipping.")
        sys.exit(0)

    gc = get_gspread_client()
    spreadsheet = gc.open_by_key(args.sheet_id)

    # Use today's date as the tab name
    today_str = datetime.now().strftime("%Y-%m-%d")
    ws = get_or_create_worksheet(spreadsheet, today_str)

    rows = []
    for post in generated:
        rows.append([
            post.get("post_number", ""),
            post.get("topic", ""),
            post.get("post_text", "")[:50000],
            post.get("infographic_prompt", "")[:50000],
            ", ".join(post.get("source_post_ids", [])),
        ])

    ws.append_rows(rows, value_input_option="USER_ENTERED")
    print(f"[sync_generated_sheets] ✓ Added {len(rows)} generated post(s) to tab '{today_str}'.")


if __name__ == "__main__":
    main()
