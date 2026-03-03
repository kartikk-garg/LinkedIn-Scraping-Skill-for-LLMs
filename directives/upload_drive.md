# Directive: Upload Images to Google Drive

## Goal
Upload generated infographic images from `generated_images/` to a Google Drive folder, organized in date-based subfolders. Returns shareable links for each uploaded image.

## When to Use
- Run after `generate_image.py` to upload the generated infographic images to Drive.
- Run standalone to upload any images currently in `generated_images/`.

## Inputs
| Parameter                     | Source        | Description                                          |
|-------------------------------|---------------|------------------------------------------------------|
| `generated_images/*.png`      | Previous step | Images to upload                                     |
| `--folder-id`                 | CLI (optional)| Drive folder ID — overrides `.env`                   |
| `GOOGLE_SERVICE_ACCOUNT_FILE` | `.env`        | Service Account JSON (same as other Google tools)    |
| `DRIVE_FOLDER_ID`             | `.env`        | Target Google Drive folder ID                        |

## Tool to Call
```bash
# Upload all images in generated_images/
python execution/upload_drive.py

# Override folder ID
python execution/upload_drive.py --folder-id 1ABC...xyz
```

## Outputs
| File                          | Description                                    |
|-------------------------------|------------------------------------------------|
| `.tmp/drive_uploads.json`     | JSON array with Drive IDs and shareable links  |

## Setup
1. The target Google Drive folder must be **shared with the Service Account email** (found in `service.json` under `client_email`).
2. Add `DRIVE_FOLDER_ID` to your `.env` file.
3. The service account needs Drive API access enabled in the Google Cloud project.

## Edge Cases & Learnings
- Creates a date subfolder (e.g., `2026-03-01/`) inside the target folder automatically.
- If the subfolder already exists, it reuses it (idempotent).
- Each uploaded file is made publicly viewable (anyone with the link).
- Supports both `.png` and `.jpg` files.
- No new dependencies — uses the same `google-api-python-client` and `google-auth` packages.
