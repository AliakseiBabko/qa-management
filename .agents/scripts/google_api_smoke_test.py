"""Smoke test Google Drive, Sheets, and Docs API access.

This script creates temporary Google Sheet and Doc files in a specific Drive
folder, writes test content, reads it back, and trashes the files by default.
It is intentionally folder-scoped by behavior and does not touch production
QA-management files.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any

SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive.metadata.readonly",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/calendar",
]

FOLDER_MIME_TYPE = "application/vnd.google-apps.folder"


def ensure_utf8_stdout() -> None:
    """Rewrap stdout/stderr as UTF-8 so Cyrillic prints don't crash under the
    Windows console's default cp1252 encoding. Safe to call unconditionally;
    a no-op once already wrapped or on platforms where it isn't needed."""
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name)
        if getattr(stream, "encoding", "").lower().replace("-", "") != "utf8":
            try:
                setattr(sys, stream_name, __import__("io").TextIOWrapper(stream.buffer, encoding="utf-8"))
            except (AttributeError, ValueError):
                pass


def import_google_libs() -> tuple[Any, Any, Any, Any]:
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError as exc:
        print(
            "Missing Google API dependencies.\n"
            "Install them with:\n"
            "  python -m pip install google-api-python-client "
            "google-auth google-auth-oauthlib",
            file=sys.stderr,
        )
        raise SystemExit(2) from exc

    return Request, Credentials, InstalledAppFlow, build


def load_credentials(credentials_path: Path, token_path: Path):
    Request, Credentials, InstalledAppFlow, _ = import_google_libs()

    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not credentials_path.exists():
                raise SystemExit(
                    f"OAuth client file not found: {credentials_path}\n"
                    "Create an OAuth Desktop client in the qa-manage-integration "
                    "project and download it to this path."
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                str(credentials_path),
                SCOPES,
            )
            creds = flow.run_local_server(port=0)

        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text(creds.to_json(), encoding="utf-8")

    return creds


def load_service_account_credentials(credentials_path: Path):
    try:
        from google.oauth2 import service_account
    except ImportError as exc:
        print(
            "Missing google-auth service account support.\n"
            "Install dependencies with:\n"
            "  python -m pip install google-api-python-client google-auth",
            file=sys.stderr,
        )
        raise SystemExit(2) from exc

    if not credentials_path.exists():
        raise SystemExit(
            f"Service account JSON not found: {credentials_path}\n"
            "Download the service account key to this path and share the "
            "target Drive folder with the service account email."
        )

    return service_account.Credentials.from_service_account_file(
        str(credentials_path),
        scopes=SCOPES,
    )


def build_services(creds):
    _, _, _, build = import_google_libs()
    return {
        "drive": build("drive", "v3", credentials=creds),
        "sheets": build("sheets", "v4", credentials=creds),
        "docs": build("docs", "v1", credentials=creds),
        "calendar": build("calendar", "v3", credentials=creds),
    }


def assert_folder_access(drive, folder_id: str) -> dict[str, Any]:
    folder = (
        drive.files()
        .get(fileId=folder_id, fields="id,name,mimeType,trashed,webViewLink")
        .execute()
    )
    if folder.get("mimeType") != FOLDER_MIME_TYPE:
        raise SystemExit(f"Target ID is not a Drive folder: {folder_id}")
    if folder.get("trashed"):
        raise SystemExit(f"Target folder is trashed: {folder_id}")
    return folder


def move_file_to_folder(drive, file_id: str, folder_id: str) -> None:
    metadata = drive.files().get(fileId=file_id, fields="parents").execute()
    previous_parents = ",".join(metadata.get("parents", []))
    drive.files().update(
        fileId=file_id,
        addParents=folder_id,
        removeParents=previous_parents,
        fields="id,parents",
    ).execute()


def create_and_test_sheet(services: dict[str, Any], folder_id: str, suffix: str):
    sheets = services["sheets"]
    drive = services["drive"]
    title = f"api_smoke_sheet_{suffix}"

    spreadsheet = (
        sheets.spreadsheets()
        .create(body={"properties": {"title": title}}, fields="spreadsheetId,spreadsheetUrl")
        .execute()
    )
    spreadsheet_id = spreadsheet["spreadsheetId"]
    move_file_to_folder(drive, spreadsheet_id, folder_id)

    values = [
        ["check", "status", "timestamp"],
        ["sheets_write_read", "ok", suffix],
    ]
    sheets.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range="A1:C2",
        valueInputOption="RAW",
        body={"values": values},
    ).execute()

    read_back = (
        sheets.spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range="A1:C2")
        .execute()
        .get("values", [])
    )
    if read_back != values:
        raise SystemExit(f"Sheet read-back mismatch: {json.dumps(read_back, ensure_ascii=False)}")

    return {
        "id": spreadsheet_id,
        "title": title,
        "url": spreadsheet["spreadsheetUrl"],
    }


def create_and_test_doc(services: dict[str, Any], folder_id: str, suffix: str):
    docs = services["docs"]
    drive = services["drive"]
    title = f"api_smoke_doc_{suffix}"

    document = docs.documents().create(body={"title": title}).execute()
    document_id = document["documentId"]
    move_file_to_folder(drive, document_id, folder_id)

    text = f"Google Docs API smoke test passed at {suffix}."
    docs.documents().batchUpdate(
        documentId=document_id,
        body={
            "requests": [
                {
                    "insertText": {
                        "location": {"index": 1},
                        "text": text,
                    }
                }
            ]
        },
    ).execute()

    read_back = docs.documents().get(documentId=document_id).execute()
    body_text = extract_doc_text(read_back)
    if text not in body_text:
        raise SystemExit("Docs read-back mismatch: inserted text was not found.")

    metadata = drive.files().get(fileId=document_id, fields="webViewLink").execute()
    return {
        "id": document_id,
        "title": title,
        "url": metadata.get("webViewLink"),
    }


def extract_doc_text(document: dict[str, Any]) -> str:
    parts: list[str] = []
    for element in document.get("body", {}).get("content", []):
        paragraph = element.get("paragraph")
        if not paragraph:
            continue
        for item in paragraph.get("elements", []):
            text_run = item.get("textRun")
            if text_run:
                parts.append(text_run.get("content", ""))
    return "".join(parts)


def trash_file(drive, file_id: str) -> None:
    drive.files().update(fileId=file_id, body={"trashed": True}, fields="id,trashed").execute()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a harmless Google Drive/Sheets/Docs API smoke test.",
    )
    parser.add_argument(
        "--auth",
        choices=["oauth", "service-account"],
        default="oauth",
        help="Authentication mode to use.",
    )
    parser.add_argument(
        "--folder-id",
        required=True,
        help="Drive folder ID where temporary test files should be created.",
    )
    parser.add_argument(
        "--credentials",
        default=".local/google/credentials.json",
        help="OAuth Desktop client JSON or service account key JSON path.",
    )
    parser.add_argument(
        "--token",
        default=".local/google/token.json",
        help="OAuth token cache path.",
    )
    parser.add_argument(
        "--keep-files",
        action="store_true",
        help="Keep the created test Sheet and Doc instead of trashing them.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    credentials_path = Path(args.credentials)
    token_path = Path(args.token)

    if args.auth == "service-account":
        creds = load_service_account_credentials(credentials_path)
    else:
        creds = load_credentials(credentials_path, token_path)
    services = build_services(creds)

    suffix = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    folder = assert_folder_access(services["drive"], args.folder_id)
    print(f"Folder access ok: {folder['name']} ({folder['id']})")

    created_files: list[dict[str, str | None]] = []
    try:
        sheet = create_and_test_sheet(services, args.folder_id, suffix)
        created_files.append(sheet)
        print(f"Sheets API ok: {sheet['title']} ({sheet['id']})")

        doc = create_and_test_doc(services, args.folder_id, suffix)
        created_files.append(doc)
        print(f"Docs API ok: {doc['title']} ({doc['id']})")
    finally:
        if not args.keep_files:
            for created in created_files:
                trash_file(services["drive"], str(created["id"]))
                print(f"Trashed test file: {created['title']} ({created['id']})")

    print("Google API smoke test passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
