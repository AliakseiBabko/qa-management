#!/usr/bin/env python3
"""Format every Google Sheet under the workspace root for readability -
both 10_M1_People_Management and 20_M2_Project_Management by default.

For each non-empty column: wrap text, align left/top, and size the column so
wrapped text fits in roughly 5 lines. Column widths also try to keep the
whole sheet's total width within a single 1920x1200 laptop screen; when a
column's content genuinely needs more room to stay under ~5 wrapped lines,
that constraint wins over fitting on screen.

Also resets every cell across the sheet's full declared grid (not just the
non-empty data range) to a standard, uncolored, borderless look (white
background, black text, no cell borders - cleared via a dedicated
`updateBorders` request, since `repeatCell`'s `userEnteredFormat.borders`
was tried first and empirically does not actually clear an existing
border despite matching the documented request shape) and un-collapses
rows - clears any leftover `hiddenByUser` flag and sets row height from
computed wrapped-line count, same heuristic as column width.
`autoResizeDimensions` was tried for row height (to match the Sheets UI's
own "Fit to data") but empirically resets rows to the flat single-line
default instead of measuring wrapped content via the API - it is not a
substitute for computing height explicitly. The line-count heuristic's
`CELL_PADDING_PX` must match the Sheets default cell padding (~3px each
side, 6px total - confirmed via `effectiveFormat.padding` on a real cell)
or it overestimates wrapped line count and leaves a visible gap at the
bottom of every cell; a much larger value here was the original cause of
that gap. A row that looks "collapsed"/clipped is usually just a stale
fixed row height left over from before WRAP was turned on, not an actual
fold - a real case of a row's full multi-line comment being invisible in
the UI was found and fixed this way.

Every column is also floored at the pixel width its own single longest
word needs (`longest_word_width`) - Sheets' WRAP strategy wraps on word
boundaries but falls back to a mid-word character break for any word wider
than the column, which reads badly for short category-label columns (e.g.
a value landing one letter short of the column width, splitting that
letter onto its own line). This floor overrides the screen-budget shrink
step if the two conflict - a slightly-over-budget sheet looks better than
a broken word.

When a sheet has few enough columns that everyone's true single-line width
still fits on screen (e.g. `_m1_pr_calendar`, `_m2_pr_calendar`-style views),
columns are widened up to that single-line width instead of being capped at
the 5-line minimum - no reason to force wrapping just because a narrower
sheet happens to have room to spare. If single-line widths for everyone
don't fit but the 5-line minimums do, the spare screen budget is still
handed out proportionally so wide columns get closer to one line without
starving the others.

This is a heuristic (character-count based, no real font metrics), so it
will not be exact for every cell - long single-column narrative text may
still exceed 5 lines at the width cap.

Pass --dry-run to print what would change (per-sheet column widths) without
calling batchUpdate - worth doing at least once whenever the scope of what
this script walks changes, since it wasn't run against 10_M1_People_Management
before this option existed.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Any, Callable

from googleapiclient.errors import HttpError

from google_api_smoke_test import build_services, ensure_utf8_stdout, load_credentials
from show_project_state import find_folder
from sync_m2_source_docs_to_sheets import ROOT_FOLDER_ID, drive_query

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
CELL_PADDING_PX = 6  # Sheets default cell padding is ~3px each side (confirmed via effectiveFormat.padding)
MIN_WIDTH_PX = 90
MAX_WIDTH_PX = 420
TARGET_LINES = 5
SCREEN_BUDGET_PX = 1780  # ~1920px laptop screen minus browser chrome/row numbers
VERTICAL_PADDING_PX = 4  # top+bottom cell padding (confirmed via effectiveFormat.padding), applied once per row
TEXT_LINE_HEIGHT_PX = 17  # single text line's own height, excluding padding
MAX_ROW_HEIGHT_PX = 800  # sanity cap so one runaway cell can't blow out the sheet


def row_height(lines: int) -> int:
    """Row height for `lines` wrapped text lines - padding applies once per
    row, not once per line (multiplying a single-line height, padding
    included, by the line count double-counts padding and was the second,
    smaller source of the bottom-gap bug after the CELL_PADDING_PX fix)."""
    return min(MAX_ROW_HEIGHT_PX, VERTICAL_PADDING_PX + TEXT_LINE_HEIGHT_PX * max(1, lines))


def cell_line_count(text: str, width_px: int) -> int:
    """How many wrapped lines `text` needs at `width_px` - explicit newlines force
    a break regardless of width; each segment between them wraps on its own."""
    if not text:
        return 1
    chars_per_line = max(1, int((width_px - CELL_PADDING_PX) / CHAR_WIDTH_PX))
    lines = 0
    for segment in text.split("\n"):
        lines += max(1, -(-len(segment) // chars_per_line))  # ceil div
    return max(1, lines)


DEFAULT_ROOTS = ["10_M1_People_Management", "20_M2_Project_Management"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Format all Sheets under the workspace root.")
    parser.add_argument("--credentials", default=".local/google/credentials.json")
    parser.add_argument("--token", default=".local/google/token.json")
    parser.add_argument(
        "--root-folder-id",
        action="append",
        help="Format Sheets under this specific folder ID instead of the default "
        f"({' + '.join(DEFAULT_ROOTS)}). Repeatable.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print planned column widths without writing.")
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


def column_width(values: list[str], target_lines: int = TARGET_LINES) -> int:
    if not values:
        return MIN_WIDTH_PX
    lengths = sorted(len(v) for v in values if v)
    if not lengths:
        return MIN_WIDTH_PX
    p90 = lengths[int(len(lengths) * 0.9)]
    target_line_chars = max(p90 / target_lines, 8)
    width = int(target_line_chars * CHAR_WIDTH_PX + CELL_PADDING_PX)
    return max(MIN_WIDTH_PX, min(MAX_WIDTH_PX, width))


WORD_WIDTH_SAFETY_MARGIN_PX = 10  # headroom against per-char width estimation error and bold header text


def longest_word_width(values: list[str]) -> int:
    """Pixel width needed to fit this column's single longest word without
    breaking it mid-word - Sheets' WRAP strategy wraps on word boundaries
    but falls back to a mid-word character break for any word that doesn't
    fit the column width on its own (e.g. a short category label like
    "Неясно" landing one letter short of the column and splitting a single
    letter onto its own line). Includes the header row (row 0 of `values`,
    always bold) - bold text is wider per character than CHAR_WIDTH_PX's
    flat average accounts for, so a header word that's an exact fit on
    paper can still overflow by a pixel in the real bold rendering; the
    safety margin below covers that along with normal proportional-font
    variance. Capped at MAX_WIDTH_PX - an outlier word long enough to blow
    past that (e.g. a URL) still gets broken; that's an acceptable rare
    exception to keep normal columns from ballooning."""
    longest = max((len(w) for v in values for w in v.split() if w), default=0)
    if not longest:
        return MIN_WIDTH_PX
    return min(MAX_WIDTH_PX, int(longest * CHAR_WIDTH_PX + CELL_PADDING_PX) + WORD_WIDTH_SAFETY_MARGIN_PX)


def format_sheet(sheets_service: Any, spreadsheet_id: str, name: str, dry_run: bool = False) -> str:
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

        min_widths = {i: column_width(col_values[i]) for i in non_empty_cols}
        ideal_widths = {i: column_width(col_values[i], target_lines=1) for i in non_empty_cols}
        total_min = sum(min_widths.values())
        total_ideal = sum(ideal_widths.values())

        if total_ideal <= SCREEN_BUDGET_PX:
            # Whole sheet fits on screen even if every column gets its
            # single-line width - no reason to cap anyone at TARGET_LINES.
            widths = ideal_widths
        elif total_min <= SCREEN_BUDGET_PX:
            # Can't give everyone a single line, but there's slack beyond the
            # 5-line minimum - hand it out proportionally to how much each
            # column actually wants (ideal - min), capped at that column's
            # own single-line width so no one overshoots what it needs.
            widths = dict(min_widths)
            slack = SCREEN_BUDGET_PX - total_min
            wants = {i: ideal_widths[i] - min_widths[i] for i in non_empty_cols}
            total_want = sum(wants.values())
            if total_want > 0:
                for i in non_empty_cols:
                    grow = int(slack * (wants[i] / total_want))
                    widths[i] = min(ideal_widths[i], min_widths[i] + grow)
        else:
            # Even the 5-line minimum doesn't fit - shrink proportionally,
            # same as before.
            widths = dict(min_widths)
            over_min = {i: w for i, w in widths.items() if w > MIN_WIDTH_PX}
            shrinkable_total = sum(over_min.values())
            excess = total_min - SCREEN_BUDGET_PX
            if shrinkable_total > 0:
                for i in over_min:
                    reduction = int(excess * (widths[i] / shrinkable_total))
                    widths[i] = max(MIN_WIDTH_PX, widths[i] - reduction)

        # Never let a column end up narrower than its own longest word -
        # this floor wins even over the screen-budget shrink above, since a
        # mid-word break looks worse than a slightly-over-budget sheet.
        for i in non_empty_cols:
            widths[i] = max(widths[i], longest_word_width(col_values[i]))

        full_range = {
            "sheetId": grid_id,
            "startRowIndex": 0,
            "endRowIndex": row_count,
            "startColumnIndex": 0,
            "endColumnIndex": col_count,
        }
        requests.append(
            {
                "repeatCell": {
                    "range": full_range,
                    "cell": {
                        "userEnteredFormat": {
                            "wrapStrategy": "WRAP",
                            "horizontalAlignment": "LEFT",
                            "verticalAlignment": "TOP",
                            "backgroundColor": {"red": 1, "green": 1, "blue": 1},
                            "textFormat": {"foregroundColor": {"red": 0, "green": 0, "blue": 0}},
                        }
                    },
                    "fields": "userEnteredFormat(wrapStrategy,horizontalAlignment,verticalAlignment,"
                    "backgroundColor,textFormat.foregroundColor)",
                }
            }
        )
        # repeatCell's userEnteredFormat.borders does not reliably clear an
        # existing border (tried first, empirically a no-op here) - the
        # dedicated updateBorders request is what actually works.
        no_border = {"style": "NONE"}
        requests.append(
            {
                "updateBorders": {
                    "range": full_range,
                    "top": no_border, "bottom": no_border,
                    "left": no_border, "right": no_border,
                    "innerHorizontal": no_border, "innerVertical": no_border,
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
        # Un-collapse: clear any hiddenByUser flag left over from a source
        # template, then set each row's real needed height from its wrapped
        # line count at the final column widths, same heuristic as
        # column_width.
        requests.append(
            {
                "updateDimensionProperties": {
                    "range": {"sheetId": grid_id, "dimension": "ROWS", "startIndex": 0, "endIndex": row_count},
                    "properties": {"hiddenByUser": False},
                    "fields": "hiddenByUser",
                }
            }
        )
        row_heights = [
            row_height(max(
                (cell_line_count(col_values[i][row_idx], widths[i]) for i in non_empty_cols), default=1,
            ))
            for row_idx in range(len(values))
        ]
        # Collapse consecutive rows sharing the same computed height into one
        # range request instead of one request per row - most rows in a typical
        # sheet are single-line, so this stays small even for hundreds of rows.
        run_start = 0
        for row_idx in range(1, len(row_heights) + 1):
            if row_idx < len(row_heights) and row_heights[row_idx] == row_heights[run_start]:
                continue
            requests.append(
                {
                    "updateDimensionProperties": {
                        "range": {"sheetId": grid_id, "dimension": "ROWS", "startIndex": run_start, "endIndex": row_idx},
                        "properties": {"pixelSize": row_heights[run_start]},
                        "fields": "pixelSize",
                    }
                }
            )
            run_start = row_idx
        log_parts.append(f"{title}: {len(non_empty_cols)} cols, total_width={sum(widths.values())}px")

    if requests:
        if dry_run:
            return f"{name}: DRY RUN, would format ({'; '.join(log_parts)})"
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

    if args.root_folder_id:
        root_ids = args.root_folder_id
    else:
        root_ids = []
        for name in DEFAULT_ROOTS:
            folder = find_folder(drive, ROOT_FOLDER_ID, name)
            if not folder:
                print(f"WARNING: {name} not found under the workspace root - skipping.")
                continue
            root_ids.append(folder["id"])

    found: list[dict[str, Any]] = []
    for root_id in root_ids:
        find_all_sheets(drive, root_id, found)

    print(f"Found {len(found)} Sheets across {len(root_ids)} root folder(s).")
    for f in found:
        try:
            result = format_sheet(sheets, f["id"], f["name"], dry_run=args.dry_run)
        except Exception as exc:  # noqa: BLE001
            result = f"{f['name']}: FAILED ({exc})"
        print(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
