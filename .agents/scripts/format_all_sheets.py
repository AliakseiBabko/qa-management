#!/usr/bin/env python3
"""Format every Google Sheet under 20_M2_Project_Management for readability.

For each non-empty column: wrap text, align left/top, and size the column so
wrapped text fits in roughly 5 lines. Column widths also try to keep the
whole sheet's total width within a single 1920x1200 laptop screen; when a
column's content genuinely needs more room to stay under ~5 wrapped lines,
that constraint wins over fitting on screen.

This is a heuristic (character-count based, no real font metrics), so it
will not be exact for every cell - long single-column narrative text may
still exceed 5 lines at the width cap.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Any, Callable

from googleapiclient.errors import HttpError

from google_api_smoke_test import build_services, ensure_utf8_stdout, load_credentials
from sync_m2_source_docs_to_sheets import drive_query

MAX_RETRIES = 5


def call_with_retry(request: Callable[[], Any]) -> Any:
    """Run a googleapiclient request's .execute() with backoff on 429 (rate limit).

    The Sheets API read-request quota (60/min/user, see google-workspace-rules.md
    API Safety) is easy to exceed here since every sheet costs 2 read calls
    (spreadsheets().get + values().get) and this script iterates every Sheet in
    the workspace in one run. A 429 is a rate limit, not a real failure - back
    off and retry rather than giving up on that sheet.
    """
    delay = 5.0
    for attempt in range(MAX_RETRIES):
        try:
            return request()
        except HttpError as exc:
            if exc.resp.status == 429 and attempt < MAX_RETRIES - 1:
                time.sleep(delay)
                delay *= 2
                continue
            raise

CHAR_WIDTH_PX = 7.2
CELL_PADDING_PX = 14
MIN_WIDTH_PX = 90
MAX_WIDTH_PX = 420
TARGET_LINES = 5
SCREEN_BUDGET_PX = 1780  # ~1920px laptop screen minus browser chrome/row numbers


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Format all Sheets under 20_M2_Project_Management.")
    parser.add_argument("--credentials", default=".local/google/credentials.json")
    parser.add_argument("--token", default=".local/google/token.json")
    parser.add_argument("--root-folder-id", default="1rrNLanrQXcqpxDjnrNPYDdcnhO26qJy1")
    return parser.parse_args()


def find_all_sheets(drive: Any, folder_id: str, found: list[dict[str, Any]]) -> None:
    children = drive_query(
        drive,
        f"'{folder_id}' in parents and trashed = false",
        fields="id,name,mimeType,parents",
    )
    for child in children:
        if child["mimeType"] == "application/vnd.google-apps.spreadsheet":
            found.append(child)
        elif child["mimeType"] == "application/vnd.google-apps.folder":
            find_all_sheets(drive, child["id"], found)


def column_width(values: list[str]) -> int:
    if not values:
        return MIN_WIDTH_PX
    lengths = sorted(len(v) for v in values if v)
    if not lengths:
        return MIN_WIDTH_PX
    p90 = lengths[int(len(lengths) * 0.9)]
    target_line_chars = max(p90 / TARGET_LINES, 8)
    width = int(target_line_chars * CHAR_WIDTH_PX + CELL_PADDING_PX)
    return max(MIN_WIDTH_PX, min(MAX_WIDTH_PX, width))


def format_sheet(sheets_service: Any, spreadsheet_id: str, name: str) -> str:
    meta = call_with_retry(lambda: sheets_service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute())
    requests: list[dict[str, Any]] = []
    log_parts = []

    for tab in meta["sheets"]:
        grid_id = tab["properties"]["sheetId"]
        row_count = tab["properties"]["gridProperties"].get("rowCount", 1000)
        col_count = tab["properties"]["gridProperties"].get("columnCount", 26)
        title = tab["properties"]["title"]

        values = call_with_retry(
            lambda: sheets_service.spreadsheets()
            .values()
            .get(spreadsheetId=spreadsheet_id, range=f"'{title}'!A1:{chr(64 + min(col_count, 26))}{min(row_count, 500)}")
            .execute()
        ).get("values", [])
        if not values:
            continue

        num_cols = max(len(r) for r in values)
        col_values: list[list[str]] = [[] for _ in range(num_cols)]
        for row in values:
            for i in range(num_cols):
                col_values[i].append(row[i] if i < len(row) else "")

        non_empty_cols = [i for i in range(num_cols) if any(v.strip() for v in col_values[i])]
        if not non_empty_cols:
            continue

        widths = {i: column_width(col_values[i]) for i in non_empty_cols}
        total_width = sum(widths.values())
        if total_width > SCREEN_BUDGET_PX:
            over_min = {i: w for i, w in widths.items() if w > MIN_WIDTH_PX}
            shrinkable_total = sum(over_min.values())
            excess = total_width - SCREEN_BUDGET_PX
            if shrinkable_total > 0:
                for i in over_min:
                    reduction = int(excess * (widths[i] / shrinkable_total))
                    widths[i] = max(MIN_WIDTH_PX, widths[i] - reduction)

        requests.append(
            {
                "repeatCell": {
                    "range": {
                        "sheetId": grid_id,
                        "startRowIndex": 0,
                        "endRowIndex": row_count,
                        "startColumnIndex": 0,
                        "endColumnIndex": num_cols,
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "wrapStrategy": "WRAP",
                            "horizontalAlignment": "LEFT",
                            "verticalAlignment": "TOP",
                        }
                    },
                    "fields": "userEnteredFormat(wrapStrategy,horizontalAlignment,verticalAlignment)",
                }
            }
        )
        for i, width in widths.items():
            requests.append(
                {
                    "updateDimensionProperties": {
                        "range": {"sheetId": grid_id, "dimension": "COLUMNS", "startIndex": i, "endIndex": i + 1},
                        "properties": {"pixelSize": width},
                        "fields": "pixelSize",
                    }
                }
            )
        log_parts.append(f"{title}: {len(non_empty_cols)} cols, total_width={sum(widths.values())}px")

    if requests:
        call_with_retry(
            lambda: sheets_service.spreadsheets()
            .batchUpdate(spreadsheetId=spreadsheet_id, body={"requests": requests})
            .execute()
        )
        return f"{name}: formatted ({'; '.join(log_parts)})"
    return f"{name}: skipped (no non-empty columns)"


def main() -> int:
    ensure_utf8_stdout()
    args = parse_args()
    creds = load_credentials(Path(args.credentials), Path(args.token))
    services = build_services(creds)
    drive = services["drive"]
    sheets = services["sheets"]

    found: list[dict[str, Any]] = []
    find_all_sheets(drive, args.root_folder_id, found)

    print(f"Found {len(found)} Sheets under root folder.")
    for f in found:
        try:
            result = format_sheet(sheets, f["id"], f["name"])
        except Exception as exc:  # noqa: BLE001
            result = f"{f['name']}: FAILED ({exc})"
        print(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
