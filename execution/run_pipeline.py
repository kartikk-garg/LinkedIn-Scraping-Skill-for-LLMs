"""
execution/run_pipeline.py
--------------------------
Layer 3: Execution — Orchestrator

Runs the full LinkedIn Automation pipeline by calling each
modular execution script in sequence:

  1. scrape_posts.py           → .tmp/scraped_posts.json
  2. store_posts_db.py         → .tmp/new_posts.json + posts.db
  3. sync_google_docs.py       → appends to Google Doc (Notebook LM)
  4. sync_scraped_sheets.py    → per-user tabs in Scraped Sheet
  5. generate_content.py       → .tmp/generated_posts.json + generated_posts/
  6. store_generated_posts.py  → posts.db generated_posts table
  7. sync_generated_sheets.py  → per-date tabs in Generated Sheet
  8. generate_image.py         → generated_images/*.png
  9. upload_drive.py           → Google Drive (date subfolders)

Usage:
    python execution/run_pipeline.py
    python execution/run_pipeline.py --max-posts 10 --num-posts 3 --model gemini-2.5-pro
"""

import os
import sys
import subprocess
import argparse
from datetime import datetime

# ─── Config ──────────────────────────────────────────────────────────────────

ROOT_DIR  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXEC_DIR  = os.path.join(ROOT_DIR, "execution")
PYTHON    = sys.executable

# ─── Helpers ─────────────────────────────────────────────────────────────────

def run_step(name: str, script: str, extra_args: list = None):
    """Runs a subprocess step; exits the pipeline on non-zero return code."""
    cmd = [PYTHON, os.path.join(EXEC_DIR, script)] + (extra_args or [])
    print(f"\n{'='*60}")
    print(f"  STEP: {name}")
    print(f"{'='*60}")
    result = subprocess.run(cmd, cwd=ROOT_DIR)
    if result.returncode != 0:
        print(f"\n[run_pipeline] ✗ Step '{name}' failed (exit {result.returncode}). Aborting.")
        sys.exit(result.returncode)
    print(f"[run_pipeline] ✓ Step '{name}' completed successfully.")

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Run the full LinkedIn Automation pipeline.")
    parser.add_argument("--max-posts", type=int, default=5,            help="Max scraped posts per creator")
    parser.add_argument("--num-posts", type=int, default=2,            help="Number of posts to generate")
    parser.add_argument("--model",     default="gemini-2.5-flash",     help="Gemini model for generation")
    args = parser.parse_args()

    start = datetime.now()
    print(f"[run_pipeline] ▶ Pipeline started at {start.strftime('%Y-%m-%d %H:%M:%S')}")

    # Phase 1: Data Collection
    run_step("1. Scrape LinkedIn Posts",      "scrape_posts.py",        ["--max-posts", str(args.max_posts)])
    run_step("2. Store & Deduplicate",        "store_posts_db.py")

    # Phase 2: Sync Scraped Data
    run_step("3. Sync to Google Docs",        "sync_google_docs.py")
    run_step("4. Sync Scraped → Sheets",      "sync_scraped_sheets.py")

    # Phase 3: Content Generation
    run_step("5. Generate Post Content",      "generate_content.py",    ["--num-posts", str(args.num_posts), "--model", args.model])
    run_step("6. Store Generated Posts (DB)",  "store_generated_posts.py")
    run_step("7. Sync Generated → Sheets",    "sync_generated_sheets.py")

    # Phase 4: Image Generation
    run_step("8. Generate Infographic Images", "generate_image.py")

    # Phase 5: Cloud Upload
    run_step("9. Upload Images to Drive",      "upload_drive.py")

    elapsed = (datetime.now() - start).seconds
    print(f"\n[run_pipeline] ✓ Pipeline completed in {elapsed}s.")


if __name__ == "__main__":
    main()
