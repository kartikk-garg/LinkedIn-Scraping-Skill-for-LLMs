"""
execution/generate_content.py
------------------------------
Layer 3: Execution — Deterministic

Modular content generation pipeline with 4 functions:
  1. pick_topics()              — Gemini selects the best N topics from scraped posts
  2. create_post()              — Gemini writes a LinkedIn post for one topic
  3. create_infographic_prompt() — Gemini creates a visual prompt for one topic
  4. generate_all()             — Orchestrates all 3 above for N posts

Inputs:
    .tmp/new_posts.json
    GEMINI_API_KEY   (from .env)

Outputs:
    .tmp/generated_posts.json  — List of generated post objects
    generated_posts/generated_post_<timestamp>.json

Usage:
    python execution/generate_content.py --num-posts 2
    python execution/generate_content.py --num-posts 3 --model gemini-2.5-pro
"""

import os
import sys
import json
import argparse
from datetime import datetime

from dotenv import load_dotenv
from google import genai
from google.genai import types

# ─── Config ──────────────────────────────────────────────────────────────────

load_dotenv()

ROOT_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP_DIR    = os.path.join(ROOT_DIR, ".tmp")
OUTPUT_DIR = os.path.join(ROOT_DIR, "generated_posts")
INPUT_FILE = os.path.join(TMP_DIR, "new_posts.json")

# ─── Gemini Client ───────────────────────────────────────────────────────────

def _get_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("[generate_content] ERROR: GEMINI_API_KEY not set in .env")
        sys.exit(1)
    return genai.Client(api_key=api_key)


def _call_gemini(client, model: str, system: str, prompt: str) -> str:
    """Single Gemini call, returns raw text."""
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=system,
            response_mime_type="application/json",
        ),
    )
    return response.text


def _build_context(posts: list) -> str:
    ctx = "Here are recent LinkedIn posts from Data Engineering creators:\n\n"
    for i, p in enumerate(posts, 1):
        ctx += f"--- POST {i} ---\n"
        ctx += f"Author: {p.get('authorName') or p.get('authorUrl', 'Unknown')}\n"
        ctx += f"Likes: {p.get('numLikes', 0)} | Comments: {p.get('numComments', 0)}\n"
        ctx += f"Text: {p.get('text', '')}\n\n"
    return ctx

# ─── Function 1: Pick Topics ────────────────────────────────────────────────

TOPIC_SYSTEM = """
You are a Data Engineering content strategist for LinkedIn.

Given a set of recent LinkedIn posts from Data Engineering creators, analyze
them by topic and engagement (likes + comments). Pick the BEST {n} specific
topics to write original posts about.

Each topic must be specific (not generic like "Data Engineering trends"),
grounded in the content of the source posts, and different from each other.

Return ONLY valid JSON:
{{
  "topics": [
    {{
      "topic": "short topic title",
      "reasoning": "why this topic will perform well",
      "source_post_indices": [1, 3]
    }}
  ]
}}
"""

def pick_topics(client, posts: list, n: int, model: str) -> list:
    """Analyzes posts and returns the best N topics."""
    print(f"[generate_content] Step 1: Picking {n} best topic(s)...")
    system = TOPIC_SYSTEM.replace("{n}", str(n))
    context = _build_context(posts)
    raw = _call_gemini(client, model, system, context)
    try:
        result = json.loads(raw)
        topics = result.get("topics", [])[:n]
        for t in topics:
            print(f"  → Topic: {t.get('topic')}")
        return topics
    except json.JSONDecodeError:
        print(f"[generate_content] WARNING: Could not parse topics JSON. Raw: {raw[:200]}")
        return [{"topic": "Data Engineering Best Practices", "reasoning": "fallback", "source_post_indices": [1]}]

# ─── Function 2: Create Post ────────────────────────────────────────────────

POST_SYSTEM = """
You are an expert Data Engineering LinkedIn content creator.

Write a highly engaging, informative text-format LinkedIn post on the given topic.
- Professional yet conversational tone, ideal for Data Engineers.
- Use structure (numbered points, bullet lists), emoji, and relevant hashtags.
- The post should be original and insightful, NOT a summary of the source posts.
- Make it between 150-300 words.

Return ONLY valid JSON:
{{
  "post_text": "..."
}}
"""

def create_post(client, topic: dict, posts: list, model: str) -> str:
    """Creates a LinkedIn post for the given topic."""
    topic_title = topic.get("topic", "Data Engineering")
    print(f"[generate_content] Step 2: Creating post for '{topic_title}'...")
    
    # Build source context from the indicated posts
    indices = topic.get("source_post_indices", [])
    source_context = ""
    for idx in indices:
        if 1 <= idx <= len(posts):
            p = posts[idx - 1]
            source_context += f"Source post ({p.get('authorName', 'Unknown')}): {p.get('text', '')[:500]}\n\n"
    
    prompt = f"Topic: {topic_title}\nReasoning: {topic.get('reasoning', '')}\n\nSource material:\n{source_context}"
    raw = _call_gemini(client, model, POST_SYSTEM, prompt)
    try:
        return json.loads(raw).get("post_text", raw)
    except json.JSONDecodeError:
        return raw

# ─── Function 3: Create Infographic Prompt ───────────────────────────────────

INFOGRAPHIC_SYSTEM = """
You are a visual design expert specializing in Data Engineering infographics.

Given a topic and the LinkedIn post text, create a detailed visual prompt for
an infographic that complements this post. The prompt will be used with
Midjourney, Ideogram, or similar tools.

Be VERY descriptive:
- Overall layout (vertical/horizontal, sections)
- Color palette (specific colors, not just "professional")
- Typography style
- Specific icons, data visualizations, or diagrams to include
- Section headers and what content goes in each section

Return ONLY valid JSON:
{{
  "infographic_prompt": "..."
}}
"""

def create_infographic_prompt(client, topic: dict, post_text: str, model: str) -> str:
    """Creates an infographic visual prompt for the given topic + post."""
    topic_title = topic.get("topic", "Data Engineering")
    print(f"[generate_content] Step 3: Creating infographic prompt for '{topic_title}'...")
    
    prompt = f"Topic: {topic_title}\n\nLinkedIn Post:\n{post_text}"
    raw = _call_gemini(client, model, INFOGRAPHIC_SYSTEM, prompt)
    try:
        return json.loads(raw).get("infographic_prompt", raw)
    except json.JSONDecodeError:
        return raw

# ─── Function 4: Orchestrator ────────────────────────────────────────────────

def generate_all(posts: list, num_posts: int, model: str) -> list:
    """
    Full generation pipeline:
      1. Pick N topics
      2. For each topic, create post + infographic prompt
    Returns list of generated post dicts.
    """
    client = _get_client()
    
    # Step 1: Pick topics
    topics = pick_topics(client, posts, num_posts, model)
    
    generated = []
    for i, topic in enumerate(topics, 1):
        print(f"\n[generate_content] === Generating Post {i}/{len(topics)} ===")
        
        # Step 2: Create post text
        post_text = create_post(client, topic, posts, model)
        
        # Step 3: Create infographic prompt
        infographic = create_infographic_prompt(client, topic, post_text, model)
        
        # Collect source post IDs
        source_ids = []
        for idx in topic.get("source_post_indices", []):
            if 1 <= idx <= len(posts):
                p = posts[idx - 1]
                source_ids.append(p.get("url") or p.get("urn") or "")
        
        generated.append({
            "post_number": i,
            "topic": topic.get("topic", ""),
            "post_text": post_text,
            "infographic_prompt": infographic,
            "source_post_ids": source_ids,
            "generated_at": datetime.now().isoformat(),
        })
    
    return generated

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Generate LinkedIn post drafts via Gemini.")
    parser.add_argument("--num-posts", type=int, default=2,                help="Number of posts to generate")
    parser.add_argument("--model",     default="gemini-2.5-flash",         help="Gemini model to use")
    args = parser.parse_args()

    if not os.path.exists(INPUT_FILE):
        print(f"[generate_content] ERROR: Input file not found: {INPUT_FILE}")
        sys.exit(1)

    with open(INPUT_FILE, encoding="utf-8") as f:
        posts = json.load(f)

    if not posts:
        print("[generate_content] No new posts to generate from. Skipping.")
        sys.exit(0)

    generated = generate_all(posts, args.num_posts, args.model)

    # Save to .tmp/ for downstream steps (store_generated_posts, sync_generated_sheets)
    os.makedirs(TMP_DIR, exist_ok=True)
    tmp_out = os.path.join(TMP_DIR, "generated_posts.json")
    with open(tmp_out, "w", encoding="utf-8") as f:
        json.dump(generated, f, indent=2, ensure_ascii=False)

    # Also save a timestamped copy in generated_posts/
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path  = os.path.join(OUTPUT_DIR, f"generated_post_{timestamp}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(generated, f, indent=2, ensure_ascii=False)

    print(f"\n[generate_content] ✓ Generated {len(generated)} post(s).")
    print(f"[generate_content] Output → {out_path}")
    print(f"[generate_content] Tmp    → {tmp_out}")


if __name__ == "__main__":
    main()
