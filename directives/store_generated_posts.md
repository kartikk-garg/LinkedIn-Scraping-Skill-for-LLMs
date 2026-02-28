# Directive: Store Generated Posts in Database

## Goal
Save generated LinkedIn post drafts (topic, post text, infographic prompt) into the `generated_posts` SQLite table for persistence and OpenClaw access.

## When to Use
- Run after `generate_content.py`.

## Inputs
| Parameter                    | Source   | Description                                    |
|------------------------------|----------|------------------------------------------------|
| `.tmp/generated_posts.json`  | Previous step | Generated post data                       |
| `--db`                       | CLI (optional) | Path to SQLite DB (default: `posts.db`)  |

## Tool to Call
```
python execution/store_generated_posts.py
```

## Database Schema: `generated_posts` table
| Column             | Type      | Description                             |
|--------------------|-----------|-----------------------------------------|
| `id`               | INTEGER PK| Auto-increment                          |
| `topic`            | TEXT      | Selected topic title                    |
| `post_text`        | TEXT      | Generated LinkedIn post text            |
| `infographic_prompt`| TEXT     | Generated infographic prompt            |
| `source_post_ids`  | TEXT      | Comma-separated source post URLs        |
| `generated_date`   | TIMESTAMP | When this was generated                 |

## Edge Cases
- If `generated_posts.json` is empty, exits 0 gracefully.
- Table is auto-created if it doesn't exist.
