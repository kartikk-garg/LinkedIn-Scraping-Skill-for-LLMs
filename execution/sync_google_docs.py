"""
execution/sync_google_docs.py
-----------------------------
Layer 3: Execution — Deterministic

Reads new posts from .tmp/new_posts.json and appends them in a
formatted, human-readable text block to a Google Doc for Notebook LM.

Inputs:
    .tmp/new_posts.json
    GOOGLE_DOC_ID          (from .env)
    GOOGLE_SERVICE_ACCOUNT_FILE  (from .env — path to Service Account JSON)

Outputs:
    Appends formatted post text to the target Google Doc.

Usage:
    python execution/sync_google_docs.py
    python execution/sync_google_docs.py --doc-id <YOUR_DOC_ID>

Edge cases:
    - If no new posts exist (.tmp/new_posts.json is empty list), gracefully skips.
    - If the Service Account file is missing, prints clear error and exits 1.
    - If the Service Account lacks Editor access to the Doc, prints 403 hint.
"""

import os
import sys
import json
import argparse

from dotenv import load_dotenv
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# ─── Config ──────────────────────────────────────────────────────────────────

load_dotenv()

ROOT_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP_DIR    = os.path.join(ROOT_DIR, ".tmp")
INPUT_FILE = os.path.join(TMP_DIR, "new_posts.json")
SCOPES     = ["https://www.googleapis.com/auth/documents"]

# ─── Helpers ─────────────────────────────────────────────────────────────────

def get_docs_service():
    sa_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")
    if not sa_file or not os.path.exists(sa_file):
        print(f"[sync_google_docs] ERROR: Service Account file not found: '{sa_file}'")
        print("  → Set GOOGLE_SERVICE_ACCOUNT_FILE in .env to the path of your Service Account JSON.")
        sys.exit(1)
    creds = Credentials.from_service_account_file(sa_file, scopes=SCOPES)
    return build("docs", "v1", credentials=creds)


def format_post(post: dict) -> str:
    author   = post.get("authorName") or post.get("authorUrl", "Unknown")
    date     = post.get("postedAt") or post.get("publishedAt", "Unknown Date")
    likes    = post.get("numLikes",    0)
    comments = post.get("numComments", 0)
    text     = post.get("text",        "")
    return (
        f"\n\n---\n"
        f"Author: {author}\n"
        f"Date: {date}\n"
        f"Engagement: {likes} likes, {comments} comments\n\n"
        f"Content:\n{text}\n"
        f"---\n\n"
    )


def append_to_doc(service, doc_id: str, content: str):
    """Fetches end index of the document and appends content."""
    doc        = service.documents().get(documentId=doc_id).execute()
    end_index  = doc["body"]["content"][-1]["endIndex"] - 1

    service.documents().batchUpdate(
        documentId=doc_id,
        body={"requests": [{"insertText": {"location": {"index": end_index}, "text": content}}]},
    ).execute()

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Append new LinkedIn posts to Google Doc.")
    parser.add_argument("--doc-id", default=os.getenv("GOOGLE_DOC_ID"), help="Google Doc ID")
    args = parser.parse_args()

    if not args.doc_id:
        print("[sync_google_docs] ERROR: GOOGLE_DOC_ID not set. Pass --doc-id or set it in .env")
        sys.exit(1)

    if not os.path.exists(INPUT_FILE):
        print(f"[sync_google_docs] ERROR: Input file not found: {INPUT_FILE}")
        sys.exit(1)

    with open(INPUT_FILE, encoding="utf-8") as f:
        posts = json.load(f)

    if not posts:
        print("[sync_google_docs] No new posts to sync. Skipping.")
        sys.exit(0)

    formatted = "".join(format_post(p) for p in posts)

    service = get_docs_service()
    try:
        append_to_doc(service, args.doc_id, formatted)
        print(f"[sync_google_docs] ✓ Appended {len(posts)} posts to Google Doc '{args.doc_id}'")
    except Exception as e:
        print(f"[sync_google_docs] ERROR appending to Google Doc: {e}")
        if "403" in str(e) or "permission" in str(e).lower():
            print("  → Share the Google Doc with your Service Account email as Editor.")
        sys.exit(1)


if __name__ == "__main__":
    main()
