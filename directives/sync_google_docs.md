# Directive: Sync Posts to Google Docs

## Goal
Append newly scraped LinkedIn posts, formatted as readable text blocks, to the designated Google Doc. This builds the Notebook LM knowledge base that continuously grows with Data Engineering content.

## When to Use
- Run after `store_posts_db.py` to sync new posts to Google Doc.
- Run in isolation to manually sync a specific batch from `.tmp/new_posts.json`.

## Inputs
| Parameter                    | Source   | Description                                       |
|------------------------------|----------|---------------------------------------------------|
| `.tmp/new_posts.json`        | Previous step | New posts from deduplication step            |
| `GOOGLE_DOC_ID`              | `.env`   | The doc ID (from the Google Doc URL)              |
| `GOOGLE_SERVICE_ACCOUNT_FILE`| `.env`   | Path to the Service Account JSON file             |
| `--doc-id`                   | CLI (optional) | Override the doc ID from .env              |

## Tool to Call
```
python execution/sync_google_docs.py [--doc-id <DOC_ID>]
```

## Outputs
The target Google Doc will have new post blocks appended in this format:
```
---
Author: Andreas Kretz
Date: 2026-02-28T06:10:33.000Z
Engagement: 16 likes, 6 comments

Content:
Spark Streaming isn't real streaming...
---
```

## Setup Requirements
1. Create a Google Cloud Service Account.
2. Download the Service Account JSON key and save it next to `.env` as `google_secret.json` (or whatever `GOOGLE_SERVICE_ACCOUNT_FILE` points to).
3. Share the Google Doc with the Service Account's `client_email` as **Editor**.

## Edge Cases & Learnings
- **403 Permission error**: The Service Account has not been granted Editor access to the Doc. Share the Doc with the `client_email` from `google_secret.json`.
- **MalformedError (missing client_email, token_uri)**: The JSON file is an OAuth Client ID file, not a Service Account key. Download the correct Service Account key from Google Cloud Console → IAM & Admin → Service Accounts → Keys.
- If `new_posts.json` is empty, the script logs a skip message and exits 0.
