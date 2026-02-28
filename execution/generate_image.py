"""
execution/generate_image.py
-----------------------------
Layer 3: Execution — Deterministic

Reads generated posts from .tmp/generated_posts.json (or accepts a
--prompt CLI arg) and generates infographic images using the Gemini
Nano Banana image generation model.

Each generated image is saved as a PNG in generated_images/<timestamp>_<post#>.png

Inputs:
    .tmp/generated_posts.json   (reads infographic_prompt from each post)
    OR --prompt "your prompt"   (generates a single image)
    GEMINI_API_KEY              (from .env)

Outputs:
    generated_images/<timestamp>_post_<n>.png

Usage:
    python execution/generate_image.py
    python execution/generate_image.py --prompt "A clean infographic about Apache Spark..."
    python execution/generate_image.py --model gemini-2.0-flash-preview-image-generation
"""

import os
import sys
import json
import argparse
import base64
import time
import re
from datetime import datetime

from dotenv import load_dotenv
from google import genai
from google.genai import types

# ─── Config ──────────────────────────────────────────────────────────────────

load_dotenv()

ROOT_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP_DIR     = os.path.join(ROOT_DIR, ".tmp")
OUTPUT_DIR  = os.path.join(ROOT_DIR, "generated_images")
INPUT_FILE  = os.path.join(TMP_DIR, "generated_posts.json")

DEFAULT_MODEL = "nano-banana-pro-preview"
MAX_RETRIES   = 3

# ─── Image Generation ────────────────────────────────────────────────────────

def generate_image(client, prompt: str, model: str) -> bytes | None:
    """
    Calls Gemini with response_modalities=["IMAGE"] to generate an image.
    Retries up to MAX_RETRIES times on rate limit (429) errors.
    Returns raw PNG bytes or None on failure.
    """
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                ),
            )

            # Extract image data from response parts
            for part in response.candidates[0].content.parts:
                if part.inline_data is not None:
                    return part.inline_data.data

            print("[generate_image] WARNING: No image data in response.")
            return None

        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                # Parse retry delay from error message
                match = re.search(r"retryDelay.*?'(\d+)s'", error_str)
                wait = int(match.group(1)) + 2 if match else 30
                if attempt < MAX_RETRIES:
                    print(f"[generate_image] Rate limited. Waiting {wait}s before retry {attempt + 1}/{MAX_RETRIES}...")
                    time.sleep(wait)
                    continue
                else:
                    print(f"[generate_image] Rate limited after {MAX_RETRIES} retries. Skipping.")
                    return None
            else:
                print(f"[generate_image] ERROR: {e}")
                return None


def save_image(image_bytes: bytes, output_path: str):
    """Saves raw image bytes to a file."""
    with open(output_path, "wb") as f:
        f.write(image_bytes)
    print(f"[generate_image] ✓ Saved → {output_path}")

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Generate infographic images via Gemini Nano Banana.")
    parser.add_argument("--prompt", type=str, default=None,         help="Single prompt to generate image from")
    parser.add_argument("--model",  default=DEFAULT_MODEL,          help="Gemini image model to use")
    args = parser.parse_args()

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("[generate_image] ERROR: GEMINI_API_KEY not set in .env")
        sys.exit(1)

    client = genai.Client(api_key=api_key)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Mode 1: Single prompt from CLI
    if args.prompt:
        print(f"[generate_image] Generating image from CLI prompt...")
        image_bytes = generate_image(client, args.prompt, args.model)
        if image_bytes:
            out_path = os.path.join(OUTPUT_DIR, f"{timestamp}_custom.png")
            save_image(image_bytes, out_path)
        else:
            print("[generate_image] Failed to generate image.")
            sys.exit(1)
        return

    # Mode 2: Batch from .tmp/generated_posts.json
    if not os.path.exists(INPUT_FILE):
        print(f"[generate_image] ERROR: Input file not found: {INPUT_FILE}")
        print("  → Run generate_content.py first, or use --prompt for a single image.")
        sys.exit(1)

    with open(INPUT_FILE, encoding="utf-8") as f:
        posts = json.load(f)

    if not posts:
        print("[generate_image] No generated posts found. Skipping.")
        sys.exit(0)

    success = 0
    for post in posts:
        post_num = post.get("post_number", 0)
        prompt   = post.get("infographic_prompt", "")

        if not prompt:
            print(f"[generate_image] Post {post_num}: No infographic prompt. Skipping.")
            continue

        print(f"\n[generate_image] Generating image for Post {post_num}: '{post.get('topic', '')}'...")
        image_bytes = generate_image(client, prompt, args.model)

        if image_bytes:
            out_path = os.path.join(OUTPUT_DIR, f"{timestamp}_post_{post_num}.png")
            save_image(image_bytes, out_path)
            success += 1
        else:
            print(f"[generate_image] ✗ Failed for Post {post_num}.")

    print(f"\n[generate_image] ✓ Generated {success}/{len(posts)} image(s).")


if __name__ == "__main__":
    main()
