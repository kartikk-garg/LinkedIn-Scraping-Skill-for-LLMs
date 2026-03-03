"""
execution/upload_drive.py
--------------------------
Layer 3: Execution — Deterministic

Uploads generated infographic images to a Google Drive folder,
organized in date-based subfolders.

Inputs:
    generated_images/*.png
    GOOGLE_SERVICE_ACCOUNT_FILE  (from .env)
    DRIVE_FOLDER_ID              (from .env)

Outputs:
    JSON with shareable links for each uploaded image

Usage:
    python execution/upload_drive.py
    python execution/upload_drive.py --folder-id <drive_folder_id>
"""

import os
import sys
import json
import glob
import argparse
from datetime import datetime

from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# ─── Config ──────────────────────────────────────────────────────────────────

load_dotenv()

ROOT_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMAGE_DIR  = os.path.join(ROOT_DIR, "generated_images")
TMP_DIR    = os.path.join(ROOT_DIR, ".tmp")

SCOPES = ["https://www.googleapis.com/auth/drive"]


def _get_drive_service():
    """Authenticate via Service Account and return Drive API service."""
    sa_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "service.json")
    sa_path = os.path.join(ROOT_DIR, sa_file)

    if not os.path.exists(sa_path):
        print(f"[upload_drive] ERROR: Service account file not found: {sa_path}")
        sys.exit(1)

    creds = service_account.Credentials.from_service_account_file(sa_path, scopes=SCOPES)
    return build("drive", "v3", credentials=creds)


def _get_or_create_subfolder(service, parent_id: str, folder_name: str) -> str:
    """
    Finds or creates a subfolder inside the parent Drive folder.
    Returns the subfolder ID.
    """
    # Check if folder already exists
    query = (
        f"'{parent_id}' in parents and "
        f"name = '{folder_name}' and "
        f"mimeType = 'application/vnd.google-apps.folder' and "
        f"trashed = false"
    )
    results = service.files().list(q=query, fields="files(id, name)").execute()
    files = results.get("files", [])

    if files:
        print(f"[upload_drive] Found existing subfolder '{folder_name}' ({files[0]['id']})")
        return files[0]["id"]

    # Create new subfolder
    metadata = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_id],
    }
    folder = service.files().create(body=metadata, fields="id").execute()
    print(f"[upload_drive] Created subfolder '{folder_name}' ({folder['id']})")
    return folder["id"]


def _upload_file(service, file_path: str, folder_id: str) -> dict:
    """Upload a single file to the specified Drive folder. Returns file metadata."""
    filename = os.path.basename(file_path)
    media = MediaFileUpload(file_path, mimetype="image/png", resumable=True)
    metadata = {
        "name": filename,
        "parents": [folder_id],
    }

    uploaded = service.files().create(
        body=metadata,
        media_body=media,
        fields="id, name, webViewLink, webContentLink",
    ).execute()

    # Make file publicly viewable
    service.permissions().create(
        fileId=uploaded["id"],
        body={"type": "anyone", "role": "reader"},
    ).execute()

    print(f"  ✓ Uploaded: {filename} → {uploaded.get('webViewLink', 'N/A')}")
    return uploaded


def upload_images(folder_id: str) -> list:
    """
    Uploads all .png images from generated_images/ to Google Drive.
    Creates a date-based subfolder (e.g., 2026-03-01/).
    Returns list of uploaded file metadata.
    """
    if not folder_id:
        print("[upload_drive] ERROR: DRIVE_FOLDER_ID not set in .env")
        sys.exit(1)

    # Find images to upload
    patterns = [os.path.join(IMAGE_DIR, "*.png"), os.path.join(IMAGE_DIR, "*.jpg")]
    image_files = []
    for pattern in patterns:
        image_files.extend(glob.glob(pattern))

    if not image_files:
        print(f"[upload_drive] No images found in {IMAGE_DIR}. Skipping upload.")
        return []

    print(f"[upload_drive] Found {len(image_files)} image(s) to upload.")

    service = _get_drive_service()

    # Create date subfolder
    date_str = datetime.now().strftime("%Y-%m-%d")
    subfolder_id = _get_or_create_subfolder(service, folder_id, date_str)

    # Upload each image
    uploaded = []
    for img_path in sorted(image_files):
        try:
            result = _upload_file(service, img_path, subfolder_id)
            uploaded.append({
                "filename": os.path.basename(img_path),
                "drive_id": result["id"],
                "web_view_link": result.get("webViewLink", ""),
                "web_content_link": result.get("webContentLink", ""),
            })
        except Exception as e:
            print(f"  ✗ Failed to upload {os.path.basename(img_path)}: {e}")

    # Save upload results
    os.makedirs(TMP_DIR, exist_ok=True)
    out_path = os.path.join(TMP_DIR, "drive_uploads.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(uploaded, f, indent=2, ensure_ascii=False)

    print(f"\n[upload_drive] ✓ Uploaded {len(uploaded)}/{len(image_files)} image(s).")
    print(f"[upload_drive] Results → {out_path}")
    return uploaded


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Upload generated images to Google Drive.")
    parser.add_argument("--folder-id", default=None, help="Google Drive folder ID (overrides .env)")
    args = parser.parse_args()

    folder_id = args.folder_id or os.getenv("DRIVE_FOLDER_ID")
    upload_images(folder_id)


if __name__ == "__main__":
    main()
