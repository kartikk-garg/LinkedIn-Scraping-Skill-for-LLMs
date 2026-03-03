"""
execution/generate_content.py
------------------------------
Layer 3: Execution — Deterministic

Enhanced content generation pipeline:
  0. score_posts()                — Engagement scoring: likes + 3×comments + 5×shares
  1. cluster_posts()              — Semantic clustering via sentence-transformers
  2. pick_topics()                — Gemini selects the best N topics from top clusters
  3. create_post()                — Gemini writes a LinkedIn post for one topic
  4. create_infographic_prompt()  — Gemini creates a visual prompt for one topic
  5. generate_all()               — Orchestrates all above for N posts

Inputs:
    .tmp/new_posts.json
    GEMINI_API_KEY   (from .env)

Outputs:
    .tmp/generated_posts.json  — List of generated post objects
    generated_posts/generated_post_<timestamp>.json

Usage:
    python execution/generate_content.py --num-posts 2
    python execution/generate_content.py --num-posts 3 --model gemini-2.5-pro
    python execution/generate_content.py --num-posts 2 --no-cluster
"""

import os
import sys
import json
import argparse
import numpy as np
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

# ─── Enhancement 1: Engagement Scoring ───────────────────────────────────────

def score_posts(posts: list) -> list:
    """
    Scores each post by engagement:
        score = numLikes + (numComments × 3) + (numShares × 5)
    Returns posts sorted by score (descending), with 'engagement_score' added.
    """
    for p in posts:
        likes    = p.get("numLikes", 0) or 0
        comments = p.get("numComments", 0) or 0
        shares   = p.get("numShares", 0) or 0
        p["engagement_score"] = likes + (comments * 3) + (shares * 5)

    scored = sorted(posts, key=lambda x: x["engagement_score"], reverse=True)
    print(f"[generate_content] Engagement scores:")
    for i, p in enumerate(scored, 1):
        author = p.get("authorName") or p.get("authorUrl", "Unknown")
        print(f"  {i}. {author} — score: {p['engagement_score']} "
              f"(👍{p.get('numLikes',0)} 💬{p.get('numComments',0)} 🔄{p.get('numShares',0)})")
    return scored

# ─── Enhancement 2: Topic Clustering ─────────────────────────────────────────

def cluster_posts(posts: list, n_clusters: int) -> list:
    """
    Clusters posts by semantic similarity using sentence-transformers,
    then ranks clusters by total engagement score.

    Returns a list of cluster dicts:
      [{"cluster_id": 0, "posts": [...], "total_score": 123, "top_keywords": "..."}, ...]
    sorted by total_score descending.
    """
    from sentence_transformers import SentenceTransformer
    from sklearn.cluster import AgglomerativeClustering

    # Extract post texts
    texts = [p.get("text", "")[:500] for p in posts]

    if len(posts) <= n_clusters:
        # Not enough posts to cluster; return each post as its own cluster
        return [{"cluster_id": i, "posts": [p], "total_score": p.get("engagement_score", 0)}
                for i, p in enumerate(posts)]

    print(f"[generate_content] Clustering {len(posts)} posts into groups...")

    # Encode texts
    model = SentenceTransformer("all-MiniLM-L6-v2")
    embeddings = model.encode(texts, show_progress_bar=False)

    # Determine cluster count (at least n_clusters, at most len(posts))
    k = min(max(n_clusters, 2), len(posts))
    clustering = AgglomerativeClustering(n_clusters=k)
    labels = clustering.fit_predict(embeddings)

    # Group posts by cluster
    clusters = {}
    for idx, label in enumerate(labels):
        label = int(label)
        if label not in clusters:
            clusters[label] = {"cluster_id": label, "posts": [], "total_score": 0}
        clusters[label]["posts"].append(posts[idx])
        clusters[label]["total_score"] += posts[idx].get("engagement_score", 0)

    # Sort clusters by total engagement
    ranked = sorted(clusters.values(), key=lambda c: c["total_score"], reverse=True)

    for c in ranked:
        authors = set(p.get("authorName", "?") for p in c["posts"])
        print(f"  Cluster {c['cluster_id']}: {len(c['posts'])} post(s), "
              f"score={c['total_score']}, authors={', '.join(authors)}")

    return ranked

# ─── Context Builder ─────────────────────────────────────────────────────────

def _build_context(posts: list) -> str:
    ctx = "Here are recent LinkedIn posts from Data Engineering creators, ranked by engagement:\n\n"
    for i, p in enumerate(posts, 1):
        ctx += f"--- POST {i} (engagement score: {p.get('engagement_score', 0)}) ---\n"
        ctx += f"Author: {p.get('authorName') or p.get('authorUrl', 'Unknown')}\n"
        ctx += f"Likes: {p.get('numLikes', 0)} | Comments: {p.get('numComments', 0)} | Shares: {p.get('numShares', 0)}\n"
        ctx += f"Text: {p.get('text', '')}\n\n"
    return ctx


def _build_cluster_context(clusters: list, n: int) -> str:
    """Build context from the top N clusters."""
    ctx = "Here are semantically clustered LinkedIn posts from Data Engineering creators.\n"
    ctx += "Posts are grouped by topic similarity and ranked by total engagement.\n"
    ctx += "Pick topics that represent the BEST content opportunity from these clusters.\n\n"

    for c in clusters[:n]:
        ctx += f"=== CLUSTER (total engagement: {c['total_score']}) ===\n"
        for i, p in enumerate(c["posts"], 1):
            ctx += f"  POST {i} (score: {p.get('engagement_score', 0)}):\n"
            ctx += f"  Author: {p.get('authorName', 'Unknown')}\n"
            ctx += f"  Text: {p.get('text', '')[:400]}\n\n"
        ctx += "\n"
    return ctx

# ─── Function: Pick Topics ──────────────────────────────────────────────────

TOPIC_SYSTEM = """
You are a Data Engineering content strategist for LinkedIn.

Given a set of recent LinkedIn posts (grouped by topic cluster and ranked by
engagement score), pick the BEST {n} specific topics to write original posts about.

Prioritize topics from HIGH engagement clusters — these represent what's trending.

Each topic must be specific (not generic like "Data Engineering trends"),
grounded in the content of the source posts, and different from each other.

Return ONLY valid JSON:
{{
  "topics": [
    {{
      "topic": "short topic title",
      "reasoning": "why this topic will perform well based on engagement data",
      "source_post_indices": [1, 3]
    }}
  ]
}}
"""

def pick_topics(client, posts: list, n: int, model: str, cluster_context: str = None) -> list:
    """Analyzes posts and returns the best N topics."""
    print(f"[generate_content] Step 1: Picking {n} best topic(s)...")
    system = TOPIC_SYSTEM.replace("{n}", str(n))
    context = cluster_context if cluster_context else _build_context(posts)
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

# ─── Function: Create Post ──────────────────────────────────────────────────

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

# ─── Function: Create Infographic Prompt ─────────────────────────────────────

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

# ─── Orchestrator ────────────────────────────────────────────────────────────

def generate_all(posts: list, num_posts: int, model: str, use_clustering: bool = True) -> list:
    """
    Full generation pipeline:
      0. Score posts by engagement
      1. Cluster posts by semantic similarity (optional)
      2. Pick N topics from top clusters
      3. For each topic, create post + infographic prompt
    Returns list of generated post dicts.
    """
    client = _get_client()

    # Step 0: Score posts
    scored_posts = score_posts(posts)

    # Step 1: Cluster (optional)
    cluster_context = None
    if use_clustering and len(scored_posts) >= 3:
        try:
            clusters = cluster_posts(scored_posts, max(num_posts + 1, 3))
            cluster_context = _build_cluster_context(clusters, num_posts + 1)
        except Exception as e:
            print(f"[generate_content] WARNING: Clustering failed ({e}). Falling back to scored ranking.")

    # Step 2: Pick topics
    topics = pick_topics(client, scored_posts, num_posts, model, cluster_context)

    generated = []
    for i, topic in enumerate(topics, 1):
        print(f"\n[generate_content] === Generating Post {i}/{len(topics)} ===")

        # Step 3: Create post text
        post_text = create_post(client, topic, scored_posts, model)

        # Step 4: Create infographic prompt
        infographic = create_infographic_prompt(client, topic, post_text, model)

        # Collect source post IDs
        source_ids = []
        for idx in topic.get("source_post_indices", []):
            if 1 <= idx <= len(scored_posts):
                p = scored_posts[idx - 1]
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
    parser.add_argument("--no-cluster", action="store_true",               help="Disable topic clustering (use scored ranking only)")
    args = parser.parse_args()

    if not os.path.exists(INPUT_FILE):
        print(f"[generate_content] ERROR: Input file not found: {INPUT_FILE}")
        sys.exit(1)

    with open(INPUT_FILE, encoding="utf-8") as f:
        posts = json.load(f)

    if not posts:
        print("[generate_content] No new posts to generate from. Skipping.")
        sys.exit(0)

    generated = generate_all(posts, args.num_posts, args.model, use_clustering=not args.no_cluster)

    # Save to .tmp/ for downstream steps
    os.makedirs(TMP_DIR, exist_ok=True)
    tmp_out = os.path.join(TMP_DIR, "generated_posts.json")
    with open(tmp_out, "w", encoding="utf-8") as f:
        json.dump(generated, f, indent=2, ensure_ascii=False)

    # Also save a timestamped copy
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
