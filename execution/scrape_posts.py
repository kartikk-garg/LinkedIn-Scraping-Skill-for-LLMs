"""
execution/scrape_posts.py
-------------------------
Layer 3: Execution — Deterministic

Scrapes recent LinkedIn posts from specified creator profile URLs
using the Apify 'supreme_coder/linkedin-post' Actor.

Outputs:
    .tmp/scraped_posts.json  — Raw list of scraped post dicts

Usage:
    python execution/scrape_posts.py
    python execution/scrape_posts.py --max-posts 5
    python execution/scrape_posts.py --urls https://www.linkedin.com/in/someone

Edge cases:
    - If Apify token is invalid, prints error and exits with code 1.
    - If actor returns 0 results, writes an empty list and exits with code 0.
"""

import os
import sys
import json
import argparse
import datetime

from apify_client import ApifyClient
from dotenv import load_dotenv

# ─── Config ──────────────────────────────────────────────────────────────────

load_dotenv()

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP_DIR  = os.path.join(ROOT_DIR, ".tmp")
OUTPUT_FILE = os.path.join(TMP_DIR, "scraped_posts.json")

ACTOR_ID = "supreme_coder/linkedin-post"

DEFAULT_URLS = [
    "https://www.linkedin.com/in/zachwilson",
    "https://www.linkedin.com/in/seattledataguy",
    "https://www.linkedin.com/in/andreas-kretz",
]

# ─── Main ─────────────────────────────────────────────────────────────────────

def scrape_posts(profile_urls: list, max_posts: int = 5) -> list:
    """Calls Apify actor and returns list of raw post dicts."""
    api_token = os.getenv("APIFY_API_TOKEN")
    if not api_token:
        print("ERROR: APIFY_API_TOKEN not set in .env")
        sys.exit(1)

    client = ApifyClient(api_token)

    # Scrape posts published since 24 hours ago
    since = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1)
    scrape_until = since.strftime("%Y-%m-%dT%H:%M:%S.000Z")

    print(f"[scrape_posts] Scraping {len(profile_urls)} profile(s) via Apify...")
    print(f"[scrape_posts] Limit: {max_posts} posts/source | scrapeUntil: {scrape_until}")

    run_input = {
        "urls":           profile_urls,
        "deepScrape":     True,
        "limitPerSource": max_posts,
        "scrapeUntil":    scrape_until,
        "rawData":        False,
    }

    try:
        run     = client.actor(ACTOR_ID).call(run_input=run_input)
        dataset = client.dataset(run["defaultDatasetId"])
        items   = dataset.list_items().items
        print(f"[scrape_posts] ✓ Scraped {len(items)} posts.")
        return items
    except Exception as e:
        print(f"[scrape_posts] ERROR: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Scrape recent LinkedIn posts via Apify.")
    parser.add_argument("--urls",      nargs="*", default=DEFAULT_URLS, help="LinkedIn profile URLs to scrape")
    parser.add_argument("--max-posts", type=int,  default=5,            help="Max posts per source URL")
    args = parser.parse_args()

    os.makedirs(TMP_DIR, exist_ok=True)

    posts = scrape_posts(args.urls, args.max_posts)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(posts, f, indent=2, ensure_ascii=False)

    print(f"[scrape_posts] Output saved → {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
