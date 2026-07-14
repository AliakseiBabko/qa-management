"""Refresh `_timeline` from every project's `action_items`.

Mechanical rollup only, same spirit as `refresh_project_registry.py`: it
copies open rows across with no judgment of its own. It does not decide
what belongs in `action_items` — that's a conversational/skill step (see
`.agents/skills/m2-timeline`) — it only concatenates every project's
`Статус = Открыто` rows and sorts by `Дата события` so "what's due
today/tomorrow across everything" is one Sheet instead of N.

`_timeline` is fully generated: never edit it directly, an edit there is
silently overwritten on the next run.

Safe to rerun anytime after an `action_items` update.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from google_api_smoke_test import build_services, ensure_utf8_stdout, load_credentials
from sync_m2_source_docs_to_sheets import (
    ROOT_FOLDER_ID,
    find_or_create_folder,
    find_sheet_in_folder,
    read_sheet_values,
    upsert_sheet,
)

ACTION_ITEMS_HEADER = ["Проект", "Дата события", "Тип", "Что нужно сделать", "Статус", "Owner", "Источник", "Комментарии"]
OPEN_STATUS = "Открыто"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--credentials", default=".local/google/credentials.json")
    parser.add_argument("--token", default=".local/google/token.json")
    return parser.parse_args()


def main() -> int:
    ensure_utf8_stdout()
    args = parse_args()
    creds = load_credentials(Path(args.credentials), Path(args.token))
    services = build_services(creds)
    drive = services["drive"]

    m2_root = find_or_create_folder(drive, ROOT_FOLDER_ID, "20_M2_Project_Management")
    project_folders = [
        f
        for f in drive.files()
        .list(
            q=f"'{m2_root['id']}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false",
            fields="files(id,name)",
        )
        .execute()
        .get("files", [])
        if not f["name"].startswith("_")
    ]

    open_rows: list[list[str]] = []
    for folder in sorted(project_folders, key=lambda f: f["name"]):
        project = folder["name"]
        sheet = find_sheet_in_folder(drive, folder["id"], "action_items")
        if not sheet:
            print(f"{project}: no action_items yet, skipped")
            continue
        rows = read_sheet_values(services, sheet["id"])
        project_open = [row for row in rows[1:] if row and len(row) > 4 and row[4].strip() == OPEN_STATUS]
        open_rows.extend(project_open)
        print(f"{project}: {len(project_open)} open item(s)")

    open_rows.sort(key=lambda row: row[1] if len(row) > 1 else "")

    upsert_sheet(services, m2_root["id"], "_timeline", [ACTION_ITEMS_HEADER] + open_rows)
    print(f"_timeline: {len(open_rows)} open item(s) written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
