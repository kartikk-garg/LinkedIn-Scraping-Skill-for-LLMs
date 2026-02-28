# Directive: Sync Generated Posts to Google Sheets

## Goal
Write generated LinkedIn posts (text + infographic prompt) to a Google Sheet organized by date. Each day gets its own tab.

## When to Use
- Run after `generate_content.py` to sync generated content to the Generated Sheet.

## Inputs
| Parameter                    | Source   | Description                                    |
|------------------------------|----------|------------------------------------------------|
| `.tmp/generated_posts.json`  | Previous step | Generated post data                       |
| `GENERATED_SHEET_ID`         | `.env`   | Google Sheet ID for generated posts            |
| `GOOGLE_SERVICE_ACCOUNT_FILE`| `.env`   | Path to Service Account JSON                   |

## Tool to Call
```
python execution/sync_generated_sheets.py
```

## Outputs
Google Sheet tabs by date (e.g. `2026-02-28`), each with columns:
`Post # | Topic | Post Text | Infographic Prompt | Source Posts`

## Setup
1. Create a Google Sheet in your Google Drive.
2. Share it with the Service Account email as **Editor**.
3. Copy the Sheet ID from the URL and set it as `GENERATED_SHEET_ID` in `.env`.

## Edge Cases
- Date tabs are auto-created on first run of that day.
- If `generated_posts.json` is empty, exits 0 gracefully.
