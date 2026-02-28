"""
LinkedIn Automation Main Script

This script coordinates:
1. Scraping LinkedIn data via Apify
2. Filtering out duplicate posts using local SQLite and saving full content for OpenClaw
3. Appending extracted posts to a Google Doc for Notebook LM
4. Analyzing topics and generating new posts via Gemini API

Ensure you have set up your .env file.
"""

import os
import json
from datetime import datetime
from dotenv import load_dotenv

from scraper import scrape_linkedin_posts
from db import init_db, filter_recent_and_new_posts, mark_post_processed
from google_sync import append_posts_to_doc
from ai_generator import generate_linkedin_content

# Load environment variables
load_dotenv()

# Configuration
CREATORS_TO_SCRAPE = [
    # Replace these with actual LinkedIn profile URLs of Data Engineering creators you follow
    "https://www.linkedin.com/in/zachwilson",
    "https://www.linkedin.com/in/seattledataguy",
    "https://www.linkedin.com/in/andreas-kretz"
]
MAX_POSTS_PER_CREATOR = 5
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "generated_posts")

def main():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting LinkedIn Automation Pipeline...")
    
    # Ensure dependencies exist
    init_db()
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        
    doc_id = os.getenv("GOOGLE_DOC_ID")
    if not doc_id:
        print("ERROR: GOOGLE_DOC_ID not set in .env")
        return

    # 1. Scrape posts (Apify)
    print("\n--- Step 1: Scraping recent posts ---")
    raw_posts = scrape_linkedin_posts(CREATORS_TO_SCRAPE, MAX_POSTS_PER_CREATOR)
    if not raw_posts:
        print("Pipeline aborted: Failed to retrieve posts.")
        return
        
    print(f"Retrieved {len(raw_posts)} total posts from Apify.")

    # 1.5 Filter already processed posts
    new_posts = filter_recent_and_new_posts(raw_posts)
    if not new_posts:
        print("Pipeline finished early: No new posts to process since last run.")
        return
        
    print(f"Found {len(new_posts)} new, unprocessed posts.")

    # 2. Add to Knowledge Base (Google Docs)
    print("\n--- Step 2: Syncing posts to Google Docs Knowledge Base ---")
    success = append_posts_to_doc(new_posts, doc_id)
    if success:
        print("Google Docs sync successful.")
    else:
        print("Warning: Google Docs sync failed or was skipped. Proceeding anyway.")

    # 3. Analyze and Generate content (Gemini API)
    print("\n--- Step 3: Generating new post and infographic prompt ---")
    generated_content = generate_linkedin_content(new_posts)
    
    if generated_content:
        # Save output to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"generated_post_{timestamp}.json"
        filepath = os.path.join(OUTPUT_DIR, filename)
        
        with open(filepath, 'w') as f:
            json.dump(generated_content, f, indent=4)
            
        print(f"Successfully generated new content! Saved drafts to: {filepath}")
        
    else:
        print("Warning: Failed to generate new content via Gemini.")

    # 4. Mark posts as processed and save to SQLite for OpenClaw vectorization
    print("\n--- Step 4: Updating tracking database for OpenClaw ---")
    for post in new_posts:
        mark_post_processed(post)
            
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Pipeline completed successfully.")

if __name__ == "__main__":
    main()
