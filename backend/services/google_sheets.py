"""Google Sheets / Drive 連携（サービスアカウント）。"""

from __future__ import annotations

import io
import json
import os
import re

from fastapi import HTTPException
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

SCOPES = (
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
)


def is_google_configured() -> bool:
    if os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip():
        return True
    path = os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE", "").strip()
    return bool(path and os.path.isfile(path))


def _credentials():
    if not is_google_configured():
        raise HTTPException(
            status_code=503,
            detail=(
                "Google Sheets 連携が未設定です。"
                "環境変数 GOOGLE_SERVICE_ACCOUNT_FILE または GOOGLE_SERVICE_ACCOUNT_JSON を設定してください。"
            ),
        )
    json_str = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    if json_str:
        info = json.loads(json_str)
        return service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    path = os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE", "").strip()
    return service_account.Credentials.from_service_account_file(path, scopes=SCOPES)


def parse_spreadsheet_id(url_or_id: str) -> str:
    text = url_or_id.strip()
    match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", text)
    if match:
        return match.group(1)
    if re.fullmatch(r"[a-zA-Z0-9-_]+", text):
        return text
    raise HTTPException(status_code=400, detail="スプレッドシート ID または URL が不正です")


def download_spreadsheet_xlsx(spreadsheet_id: str) -> bytes:
    creds = _credentials()
    service = build("drive", "v3", credentials=creds, cache_discovery=False)
    request = service.files().export_media(
        fileId=spreadsheet_id,
        mimeType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    buffer = io.BytesIO()
    downloader = MediaIoBaseDownload(buffer, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    return buffer.getvalue()


def upload_spreadsheet_xlsx(spreadsheet_id: str, content: bytes) -> None:
    creds = _credentials()
    service = build("drive", "v3", credentials=creds, cache_discovery=False)
    media = MediaIoBaseUpload(
        io.BytesIO(content),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        resumable=True,
    )
    service.files().update(fileId=spreadsheet_id, media_body=media).execute()


def create_spreadsheet_from_xlsx(title: str, content: bytes) -> dict[str, str]:
    creds = _credentials()
    service = build("drive", "v3", credentials=creds, cache_discovery=False)
    media = MediaIoBaseUpload(
        io.BytesIO(content),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        resumable=True,
    )
    metadata = {
        "name": title,
        "mimeType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }
    created = service.files().create(body=metadata, media_body=media, fields="id,webViewLink").execute()
    file_id = created["id"]
    return {
        "spreadsheet_id": file_id,
        "web_view_link": created.get("webViewLink") or f"https://docs.google.com/spreadsheets/d/{file_id}/edit",
    }
