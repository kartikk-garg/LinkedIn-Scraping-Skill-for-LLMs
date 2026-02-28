# Directive: Sync Scraped Posts to Google Sheets

## Goal
Write newly scraped LinkedIn posts to a Google Sheet organized by author. Each author gets their own tab (worksheet). Posts are appended as rows.

## When to Use
- Run after `store_posts_db.py` to sync new posts to the Scraped Sheet.

## Inputs
| Parameter                    | Source   | Description                                    |
|------------------------------|----------|------------------------------------------------|
| `.tmp/new_posts.json`        | Previous step | New posts from deduplication step          |
| `SCRAPED_SHEET_ID`           | `.env`   | Google Sheet ID for scraped posts              |
| `GOOGLE_SERVICE_ACCOUNT_FILE`| `.env`   | Path to Service Account JSON                   |

## Tool to Call
```
python execution/sync_scraped_sheets.py
```

## Outputs
Google Sheet tabs by author name, each with columns:
`Date | Post Text | Likes | Comments | Post URL`

## Setup
1. Create a Google Sheet in your Google Drive.
2. Share it with the Service Account email as **Editor**.
3. Copy the Sheet ID from the URL and set it as `SCRAPED_SHEET_ID` in `.env`.

## Edge Cases
- Tabs are auto-created when a new author is first encountered.
- If `new_posts.json` is empty, exits 0 gracefully.
