# Directive: Scrape LinkedIn Posts

## Goal
Fetch the most recent posts (last 24 hours) from a list of LinkedIn Data Engineering creator profiles using the Apify `supreme_coder/linkedin-post` actor.

## When to Use
- Run this as the first step in the daily pipeline.
- Run in isolation when you only need fresh raw post data.

## Inputs
| Parameter     | Source       | Description                                               |
|---------------|--------------|-----------------------------------------------------------|
| `--urls`      | CLI / config | List of LinkedIn profile URLs to scrape                   |
| `--max-posts` | CLI / config | Max posts per source URL (default: 5)                     |
| `APIFY_API_TOKEN` | `.env`   | Required. Your Apify API authorization token              |

## Tool to Call
```
python execution/scrape_posts.py [--urls URL1 URL2 ...] [--max-posts N]
```

## Outputs
| File                        | Description                          |
|-----------------------------|--------------------------------------|
| `.tmp/scraped_posts.json`   | Raw list of post dicts from Apify    |

Each post dict contains fields like:
- `text` — full post text
- `authorName`, `authorUrl`
- `numLikes`, `numComments`
- `url` (unique post URL — used as post_id)
- `postedAt` / `publishedAt`

## Edge Cases & Learnings
- **Actor ID**: Use `supreme_coder/linkedin-post` — the publicly available actor.
- **scrapeUntil**: Passed as ISO 8601 UTC string `YYYY-MM-DDTHH:MM:SS.000Z`.
- **deepScrape**: Set to `True` to ensure engagement metrics (likes, comments) are included.
- **limitPerSource**: Number of posts *per source URL*, not total.
- If Apify returns 0 results, `.tmp/scraped_posts.json` will contain `[]`. Downstream steps handle this gracefully.
- If `APIFY_API_TOKEN` is invalid, the script exits with code 1.
