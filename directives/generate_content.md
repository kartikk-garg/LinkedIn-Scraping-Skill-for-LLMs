# Directive: Generate LinkedIn Content via Gemini

## Goal
Analyze scraped posts, pick the best N topics, then for each topic generate an original LinkedIn post and a detailed infographic prompt.

## When to Use
- Run after `store_posts_db.py` (requires `.tmp/new_posts.json`).
- Use `--num-posts` to control how many posts are generated (default: 2).

## Inputs
| Parameter             | Source         | Description                                        |
|-----------------------|----------------|----------------------------------------------------|
| `.tmp/new_posts.json` | Previous step  | New posts from deduplication step                  |
| `GEMINI_API_KEY`      | `.env`         | Google AI Studio Gemini API key                    |
| `--num-posts`         | CLI (optional) | Number of posts to generate (default: 2)           |
| `--model`             | CLI (optional) | Gemini model to use (default: `gemini-2.5-flash`)  |

## Tool to Call
```
python execution/generate_content.py --num-posts 2
```

## Internal Function Flow
The script makes **3 separate Gemini API calls per generated post**:

| # | Function                     | What it does                                      |
|---|------------------------------|---------------------------------------------------|
| 1 | `pick_topics(posts, n)`      | Analyzes all posts, returns the N best topics     |
| 2 | `create_post(topic, posts)`  | Writes one LinkedIn post for a specific topic     |
| 3 | `create_infographic_prompt()`| Creates a visual prompt for Midjourney/Ideogram   |

## Outputs
| File                                       | Description                                   |
|--------------------------------------------|-----------------------------------------------|
| `.tmp/generated_posts.json`                | List of generated post objects for downstream |
| `generated_posts/generated_post_<ts>.json` | Timestamped copy as deliverable               |

Each generated post object:
```json
{
  "post_number": 1,
  "topic": "Spark vs Flink for streaming",
  "post_text": "...",
  "infographic_prompt": "...",
  "source_post_ids": ["https://..."],
  "generated_at": "2026-02-28T12:05:00"
}
```

## Edge Cases & Learnings
- If `new_posts.json` is empty, exits 0 with skip message.
- If Gemini returns malformed JSON for topics, falls back to a default topic.
- Each function's Gemini call uses a different system prompt optimized for that task.
