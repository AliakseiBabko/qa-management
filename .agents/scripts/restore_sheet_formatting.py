#!/usr/bin/env python3
"""Copy a tab's *formatting* from one Google Sheet onto another, leaving values alone.

Written for the case where `format_all_sheets.py` swept a hand-designed
workbook (it recurses the whole M1/M2 roots and applies a generic fallback
profile to any Sheet without an explicit entry in its `PROFILES` map) and
flattened the original layout. If an untouched copy of the workbook still
exists somewhere outside those roots, this restores the design from it.

Copies per-cell `userEnteredFormat`, column widths, and row heights. Never
writes cell values, formulas, or notes, so a target whose *content* has moved
on since the copy was taken keeps its newer content. Merges are compared and
reported but only rewritten with `--merges`, since a merge change moves
content between cells.

The target's current formatting is dumped to a backup JSON before any write.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from google_api_smoke_test import build_services, ensure_utf8_stdout, load_credentials

# Sheets rejects oversized batchUpdate bodies; chunk the per-cell format rows.
ROWS_PER_UPDATE_CHUNK = 200


def fetch_tab(sheets: Any, spreadsheet_id: str, tab: str, max_col: str, max_row: int) -> dict[str, Any]:
    """Grid data for one tab: per-cell formats plus row/column dimension metadata."""
    meta = (
        sheets.spreadsheets()
        .get(
            spreadsheetId=spreadsheet_id,
            ranges=[f"'{tab}'!A1:{max_col}{max_row}"],
            includeGridData=True,
            fields=(
                "properties.title,"
                "sheets.properties,"
                "sheets.merges,"
                "sheets.data.rowData.values.userEnteredFormat,"
                "sheets.data.rowMetadata.pixelSize,"
                "sheets.data.columnMetadata.pixelSize"
            ),
        )
        .execute()
    )
    for sheet in meta.get("sheets", []):
        if sheet["properties"]["title"] == tab:
            return sheet
    raise SystemExit(f"tab {tab!r} not found in spreadsheet {spreadsheet_id}")


def dimension_requests(grid_id: int, sizes: list[int | None], dimension: str) -> list[dict[str, Any]]:
    """Collapse a per-index size list into one request per run of equal sizes."""
    requests: list[dict[str, Any]] = []
    run_start = 0
    for idx in range(1, len(sizes) + 1):
        if idx < len(sizes) and sizes[idx] == sizes[run_start]:
            continue
        size = sizes[run_start]
        if size is not None:
            requests.append(
                {
                    "updateDimensionProperties": {
                        "range": {
                            "sheetId": grid_id,
                            "dimension": dimension,
                            "startIndex": run_start,
                            "endIndex": idx,
                        },
                        "properties": {"pixelSize": size},
                        "fields": "pixelSize",
                    }
                }
            )
        run_start = idx
    return requests


def format_requests(grid_id: int, source_rows: list[dict[str, Any]], col_count: int) -> list[dict[str, Any]]:
    """`updateCells` requests carrying only `userEnteredFormat`.

    A source cell with no format yields an empty cell, which, combined with the
    `userEnteredFormat` field mask, clears whatever the target had there.
    """
    requests: list[dict[str, Any]] = []
    for start in range(0, len(source_rows), ROWS_PER_UPDATE_CHUNK):
        chunk = source_rows[start : start + ROWS_PER_UPDATE_CHUNK]
        rows = []
        for row in chunk:
            values = row.get("values", [])
            cells = []
            for col in range(col_count):
                fmt = values[col].get("userEnteredFormat") if col < len(values) else None
                cells.append({"userEnteredFormat": fmt} if fmt else {})
            rows.append({"values": cells})
        requests.append(
            {
                "updateCells": {
                    "range": {
                        "sheetId": grid_id,
                        "startRowIndex": start,
                        "endRowIndex": start + len(chunk),
                        "startColumnIndex": 0,
                        "endColumnIndex": col_count,
                    },
                    "rows": rows,
                    "fields": "userEnteredFormat",
                }
            }
        )
    return requests


def merge_requests(grid_id: int, merges: list[dict[str, Any]], row_count: int, col_count: int) -> list[dict[str, Any]]:
    requests: list[dict[str, Any]] = [
        {
            "unmergeCells": {
                "range": {
                    "sheetId": grid_id,
                    "startRowIndex": 0,
                    "endRowIndex": row_count,
                    "startColumnIndex": 0,
                    "endColumnIndex": col_count,
                }
            }
        }
    ]
    for merge in merges:
        requests.append({"mergeCells": {"range": {**merge, "sheetId": grid_id}, "mergeType": "MERGE_ALL"}})
    return requests


def normalized_merges(sheet: dict[str, Any]) -> list[dict[str, Any]]:
    return sorted(
        ({k: v for k, v in merge.items() if k != "sheetId"} for merge in sheet.get("merges", [])),
        key=lambda m: (m.get("startRowIndex", 0), m.get("startColumnIndex", 0)),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", required=True, help="Spreadsheet ID to copy formatting FROM (the good copy).")
    parser.add_argument("--target", required=True, help="Spreadsheet ID to copy formatting ONTO.")
    parser.add_argument("--tab", required=True, help="Tab title, present in both spreadsheets.")
    parser.add_argument("--target-tab", help="Target tab title, if it differs from --tab.")
    parser.add_argument("--max-col", default="Z", help="Last column to copy formats for (default Z).")
    parser.add_argument("--max-row", type=int, default=200, help="Last row to copy formats for (default 200).")
    parser.add_argument("--merges", action="store_true", help="Also rewrite merges (moves content; off by default).")
    parser.add_argument("--backup-dir", default=".", help="Where to write the pre-write backup JSON.")
    parser.add_argument("--dry-run", action="store_true", help="Report the planned requests without writing.")
    parser.add_argument("--credentials", default=".local/google/credentials.json")
    parser.add_argument("--token", default=".local/google/token.json")
    return parser.parse_args()


def main() -> int:
    ensure_utf8_stdout()
    args = parse_args()
    target_tab = args.target_tab or args.tab

    creds = load_credentials(Path(args.credentials), Path(args.token))
    sheets = build_services(creds)["sheets"]

    source = fetch_tab(sheets, args.source, args.tab, args.max_col, args.max_row)
    target = fetch_tab(sheets, args.target, target_tab, args.max_col, args.max_row)

    backup_path = Path(args.backup_dir) / f"formatting-backup-{args.target}-{target_tab}.json"
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    backup_path.write_text(json.dumps(target, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"backed up target formatting -> {backup_path}")

    grid_id = target["properties"]["sheetId"]
    grid = target["properties"].get("gridProperties", {})
    row_count = grid.get("rowCount", 1000)
    col_count = grid.get("columnCount", 26)

    source_data = source["data"][0]
    source_rows = source_data.get("rowData", [])
    fmt_cols = min(col_count, len(source_data.get("columnMetadata", [])) or col_count)

    requests: list[dict[str, Any]] = []
    requests += format_requests(grid_id, source_rows, fmt_cols)
    requests += dimension_requests(
        grid_id, [c.get("pixelSize") for c in source_data.get("columnMetadata", [])], "COLUMNS"
    )
    requests += dimension_requests(grid_id, [r.get("pixelSize") for r in source_data.get("rowMetadata", [])], "ROWS")

    src_merges, tgt_merges = normalized_merges(source), normalized_merges(target)
    if src_merges == tgt_merges:
        print(f"merges: identical ({len(src_merges)}), nothing to do")
    elif args.merges:
        requests += merge_requests(grid_id, src_merges, row_count, col_count)
        print(f"merges: rewriting {len(tgt_merges)} -> {len(src_merges)}")
    else:
        print(f"merges: DIFFER (source {len(src_merges)}, target {len(tgt_merges)}) - pass --merges to rewrite")

    print(
        f"planned {len(requests)} requests: formats for {len(source_rows)} rows x {fmt_cols} cols, "
        f"{len(source_data.get('columnMetadata', []))} column widths, "
        f"{len(source_data.get('rowMetadata', []))} row heights"
    )
    if args.dry_run:
        print("DRY RUN, nothing written")
        return 0

    sheets.spreadsheets().batchUpdate(spreadsheetId=args.target, body={"requests": requests}).execute()
    print(f"restored formatting onto {args.target} / {target_tab}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
