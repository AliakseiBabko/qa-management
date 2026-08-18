#!/usr/bin/env python3
"""Format every Google Sheet under the workspace root for readability.

Supports explicit formatting profiles for executive and living M2 sheets:
- `_project_registry`: 13-column executive layout (1,680 px budget) with risk traffic-light and stale warnings.
- `project_metrics`: 12-column layout (1,600 px) with trend and confidence conditional formatting.
- `project_risk` (Summary tab): 14-column layout (1,600 px) with 5-dimension risk traffic-lights and prediction signals.
- `project_risk` (Risk Items tab): 20-column layout with severity, lifecycle dates, prediction status, and item status formatting.

For sheets without an explicit profile, falls back to dynamic content-based column sizing and row height heuristics.
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

CHAR_WIDTH_PX = 7.2
CELL_PADDING_PX = 6
MIN_WIDTH_PX = 90
MAX_WIDTH_PX = 420
# Keep wrapped cells compact while giving prose columns enough room to remain
# readable.  Profiled sheets are widened further below when their actual
# content would exceed this target.
TARGET_LINES = 10
MAX_TARGET_LINES = 10
SCREEN_BUDGET_PX = 1780
VERTICAL_PADDING_PX = 4
TEXT_LINE_HEIGHT_PX = 17
MAX_ROW_HEIGHT_PX = 800
WORD_WIDTH_SAFETY_MARGIN_PX = 10

# Standard Traffic Light Palette
COLOR_RED_BG = {"red": 0.988, "green": 0.910, "blue": 0.902}      # #FCE8E6
COLOR_RED_TEXT = {"red": 0.773, "green": 0.133, "blue": 0.122}    # #C5221F

COLOR_YELLOW_BG = {"red": 0.996, "green": 0.969, "blue": 0.878}   # #FEF7E0
COLOR_YELLOW_TEXT = {"red": 0.690, "green": 0.376, "blue": 0.0}   # #B06000

COLOR_GREEN_BG = {"red": 0.902, "green": 0.957, "blue": 0.918}    # #E6F4EA
COLOR_GREEN_TEXT = {"red": 0.075, "green": 0.451, "blue": 0.200}  # #137333

COLOR_GRAY_BG = {"red": 0.945, "green": 0.953, "blue": 0.957}     # #F1F3F4
COLOR_GRAY_TEXT = {"red": 0.373, "green": 0.388, "blue": 0.408}   # #5F6368

COLOR_BLUE_BG = {"red": 0.910, "green": 0.941, "blue": 0.996}     # #E8F0FE
COLOR_BLUE_TEXT = {"red": 0.102, "green": 0.451, "blue": 0.910}   # #1A73E8

HEADER_BG = {"red": 0.95, "green": 0.95, "blue": 0.95}


# Explicit Formatting Profiles
PROFILES: dict[str, dict[str, Any]] = {
    "_project_registry": {
        # Give the long risk header enough horizontal room to avoid a clipped
        # third line, while preserving the executive layout budget.
        "widths": [120, 150, 130, 350, 180, 260, 280, 160, 280, 120, 100],
        "freeze_rows": 1,
        "conditional_rules": [
            # Col C (idx 2): Общий уровень риска
            {"col_start": 2, "col_end": 3, "type": "TEXT_EQ", "val": "Высокий", "bg": COLOR_RED_BG, "fg": COLOR_RED_TEXT},
            {"col_start": 2, "col_end": 3, "type": "TEXT_EQ", "val": "Средний", "bg": COLOR_YELLOW_BG, "fg": COLOR_YELLOW_TEXT},
            {"col_start": 2, "col_end": 3, "type": "TEXT_EQ", "val": "Низкий", "bg": COLOR_GREEN_BG, "fg": COLOR_GREEN_TEXT},
            # Col I (idx 8): People requiring attention
            {"col_start": 7, "col_end": 8, "type": "TEXT_CONTAINS", "val": "[Stale: review required]", "bg": COLOR_YELLOW_BG, "fg": COLOR_YELLOW_TEXT},
        ],
    },
    "project_metrics": {
        "widths": [110, 80, 200, 100, 120, 100, 100, 110, 110, 400, 80, 90],
        "freeze_rows": 1,
        "conditional_rules": [
            # Col I (idx 8): Data Confidence
            {"col_start": 8, "col_end": 9, "type": "TEXT_EQ", "val": "Высокая", "bg": COLOR_GREEN_BG, "fg": COLOR_GREEN_TEXT},
            {"col_start": 8, "col_end": 9, "type": "TEXT_EQ", "val": "Средняя", "bg": COLOR_YELLOW_BG, "fg": COLOR_YELLOW_TEXT},
            {"col_start": 8, "col_end": 9, "type": "TEXT_EQ", "val": "Низкая", "bg": COLOR_RED_BG, "fg": COLOR_RED_TEXT},
            # Col L (idx 11): Тренд
            {"col_start": 11, "col_end": 12, "type": "TEXT_EQ", "val": "Позитивный", "bg": COLOR_GREEN_BG, "fg": COLOR_GREEN_TEXT},
            {"col_start": 11, "col_end": 12, "type": "TEXT_EQ", "val": "Смешанный", "bg": COLOR_YELLOW_BG, "fg": COLOR_YELLOW_TEXT},
            {"col_start": 11, "col_end": 12, "type": "TEXT_EQ", "val": "Негативный", "bg": COLOR_RED_BG, "fg": COLOR_RED_TEXT},
        ],
    },
    "project_risk_summary": {
        "widths": [110, 90, 130, 90, 220, 120, 90, 90, 110, 110, 220, 100, 80, 80],
        "freeze_rows": 1,
        "conditional_rules": [
            # Col C (idx 2:3): Общий уровень риска
            {"col_start": 2, "col_end": 3, "type": "TEXT_EQ", "val": "Высокий", "bg": COLOR_RED_BG, "fg": COLOR_RED_TEXT},
            {"col_start": 2, "col_end": 3, "type": "TEXT_EQ", "val": "Средний", "bg": COLOR_YELLOW_BG, "fg": COLOR_YELLOW_TEXT},
            {"col_start": 2, "col_end": 3, "type": "TEXT_EQ", "val": "Низкий", "bg": COLOR_GREEN_BG, "fg": COLOR_GREEN_TEXT},
            # Col F (idx 5:6): Статус прогнозирования
            {"col_start": 5, "col_end": 6, "type": "TEXT_EQ", "val": "Detected Early", "bg": COLOR_GREEN_BG, "fg": COLOR_GREEN_TEXT},
            {"col_start": 5, "col_end": 6, "type": "TEXT_EQ", "val": "Detected Late", "bg": COLOR_RED_BG, "fg": COLOR_RED_TEXT},
            {"col_start": 5, "col_end": 6, "type": "TEXT_EQ", "val": "Not Reviewed", "bg": COLOR_GRAY_BG, "fg": COLOR_GRAY_TEXT},
            {"col_start": 5, "col_end": 6, "type": "TEXT_EQ", "val": "Not Detectable", "bg": COLOR_GRAY_BG, "fg": COLOR_GRAY_TEXT},
            # Cols G-J (indices 6:10): 4 Risk dimensions (delivery, QA process, staffing/continuity, communication/client)
            {"col_start": 6, "col_end": 10, "type": "TEXT_EQ", "val": "Высокий", "bg": COLOR_RED_BG, "fg": COLOR_RED_TEXT},
            {"col_start": 6, "col_end": 10, "type": "TEXT_EQ", "val": "Средний", "bg": COLOR_YELLOW_BG, "fg": COLOR_YELLOW_TEXT},
            {"col_start": 6, "col_end": 10, "type": "TEXT_EQ", "val": "Низкий", "bg": COLOR_GREEN_BG, "fg": COLOR_GREEN_TEXT},
            # Col L (idx 11:12): Уверенность в данных
            {"col_start": 11, "col_end": 12, "type": "TEXT_EQ", "val": "Высокая", "bg": COLOR_GREEN_BG, "fg": COLOR_GREEN_TEXT},
            {"col_start": 11, "col_end": 12, "type": "TEXT_EQ", "val": "Средняя", "bg": COLOR_YELLOW_BG, "fg": COLOR_YELLOW_TEXT},
            {"col_start": 11, "col_end": 12, "type": "TEXT_EQ", "val": "Низкая", "bg": COLOR_RED_BG, "fg": COLOR_RED_TEXT},
        ],
    },
    "project_risk_items": {
        "widths": [80, 100, 250, 110, 90, 90, 90, 110, 90, 90, 100, 100, 120, 220, 140, 110, 140, 220, 80, 90],
        "freeze_rows": 1,
        "conditional_rules": [
            # Col E (idx 4): Уровень риска (Severity)
            {"col_start": 4, "col_end": 5, "type": "TEXT_EQ", "val": "Высокий", "bg": COLOR_RED_BG, "fg": COLOR_RED_TEXT},
            {"col_start": 4, "col_end": 5, "type": "TEXT_EQ", "val": "Средний", "bg": COLOR_YELLOW_BG, "fg": COLOR_YELLOW_TEXT},
            {"col_start": 4, "col_end": 5, "type": "TEXT_EQ", "val": "Низкий", "bg": COLOR_GREEN_BG, "fg": COLOR_GREEN_TEXT},
            # Col M (idx 12): Статус прогнозирования
            {"col_start": 12, "col_end": 13, "type": "TEXT_EQ", "val": "Detected Early", "bg": COLOR_GREEN_BG, "fg": COLOR_GREEN_TEXT},
            {"col_start": 12, "col_end": 13, "type": "TEXT_EQ", "val": "Detected Late", "bg": COLOR_RED_BG, "fg": COLOR_RED_TEXT},
            {"col_start": 12, "col_end": 13, "type": "TEXT_EQ", "val": "Not Reviewed", "bg": COLOR_GRAY_BG, "fg": COLOR_GRAY_TEXT},
            {"col_start": 12, "col_end": 13, "type": "TEXT_EQ", "val": "Not Detectable", "bg": COLOR_GRAY_BG, "fg": COLOR_GRAY_TEXT},
            # Col T (idx 19): Текущий статус
            {"col_start": 19, "col_end": 20, "type": "TEXT_EQ", "val": "Closed", "bg": COLOR_GRAY_BG, "fg": COLOR_GRAY_TEXT},
            {"col_start": 19, "col_end": 20, "type": "TEXT_EQ", "val": "Materialized", "bg": COLOR_RED_BG, "fg": COLOR_RED_TEXT},
            {"col_start": 19, "col_end": 20, "type": "TEXT_EQ", "val": "Mitigating", "bg": COLOR_YELLOW_BG, "fg": COLOR_YELLOW_TEXT},
            {"col_start": 19, "col_end": 20, "type": "TEXT_EQ", "val": "Open", "bg": COLOR_BLUE_BG, "fg": COLOR_BLUE_TEXT},
        ],
    },
}


def resolve_profile_for_tab(sheet_name: str, tab_title: str) -> dict[str, Any] | None:
    """Find matching formatting profile by sheet name and tab title."""
    if sheet_name == "_project_registry" or tab_title == "_project_registry":
        return PROFILES["_project_registry"]
    if sheet_name == "project_metrics" or tab_title == "project_metrics":
        return PROFILES["project_metrics"]
    if sheet_name == "project_risk" or "риск" in sheet_name.casefold():
        if tab_title == "Risk Items" or "items" in tab_title.casefold():
            return PROFILES["project_risk_items"]
        return PROFILES["project_risk_summary"]
    if tab_title == "Summary":
        return PROFILES["project_risk_summary"]
    if tab_title == "Risk Items":
        return PROFILES["project_risk_items"]
    return None


def call_with_retry(request: Callable[[], Any]) -> Any:
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


def row_height(lines: int) -> int:
    return min(MAX_ROW_HEIGHT_PX, VERTICAL_PADDING_PX + TEXT_LINE_HEIGHT_PX * max(1, lines))


def cell_line_count(text: str, width_px: int) -> int:
    if not text:
        return 1
    chars_per_line = max(1, int((width_px - CELL_PADDING_PX) / CHAR_WIDTH_PX))
    lines = 0
    for segment in text.split("\n"):
        lines += max(1, -(-len(segment) // chars_per_line))
    return max(1, lines)


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


def longest_word_width(values: list[str]) -> int:
    longest = max((len(w) for v in values for w in v.split() if w), default=0)
    if not longest:
        return MIN_WIDTH_PX
    return min(MAX_WIDTH_PX, int(longest * CHAR_WIDTH_PX + CELL_PADDING_PX) + WORD_WIDTH_SAFETY_MARGIN_PX)


def width_for_line_limit(values: list[str], line_limit: int = MAX_TARGET_LINES) -> int:
    """Return a width that fits the longest logical line within line_limit."""
    longest = max((len(segment) for value in values for segment in value.split("\n")), default=0)
    if not longest:
        return MIN_WIDTH_PX
    return min(MAX_WIDTH_PX, int((longest / line_limit) * CHAR_WIDTH_PX + CELL_PADDING_PX))


def build_conditional_rule_requests(sheet_id: int, rules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build Sheets API AddConditionalFormatRuleRequest payloads."""
    requests: list[dict[str, Any]] = []
    for r in rules:
        cond_type = r["type"]
        val = r["val"]
        cond: dict[str, Any] = {"type": cond_type, "values": [{"userEnteredValue": val}]}
        format_spec: dict[str, Any] = {"backgroundColor": r["bg"]}
        if "fg" in r:
            format_spec["textFormat"] = {"foregroundColor": r["fg"]}

        rule_req = {
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [
                        {
                            "sheetId": sheet_id,
                            "startRowIndex": 1,
                            "endRowIndex": 500,
                            "startColumnIndex": r["col_start"],
                            "endColumnIndex": r["col_end"],
                        }
                    ],
                    "booleanRule": {
                        "condition": cond,
                        "format": format_spec,
                    },
                },
                "index": 0,
            }
        }
        requests.append(rule_req)
    return requests


def build_tab_formatting_requests(
    grid_id: int,
    row_count: int,
    col_count: int,
    values: list[list[str]],
    profile: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], dict[int, int]]:
    """Pure builder for formatting batchUpdate requests for one tab."""
    requests: list[dict[str, Any]] = []
    num_cols = max((len(r) for r in values), default=0)
    col_values: list[list[str]] = [[] for _ in range(num_cols)]
    for row in values:
        for i in range(num_cols):
            col_values[i].append(row[i] if i < len(row) else "")

    non_empty_cols = [i for i in range(num_cols) if any(v.strip() for v in col_values[i])]
    widths: dict[int, int] = {}

    if profile and "widths" in profile:
        prof_widths = profile["widths"]
        for i in range(min(num_cols, len(prof_widths))):
            widths[i] = prof_widths[i]
        for i in range(len(prof_widths), num_cols):
            widths[i] = column_width(col_values[i])
        # Profile widths are the baseline, not a reason to leave long values
        # clipped. Widen columns as far as practical when their actual text
        # would wrap beyond the ten-line readability target.
        for i in range(num_cols):
            widths[i] = max(widths.get(i, MIN_WIDTH_PX), width_for_line_limit(col_values[i]))
    else:
        min_widths = {i: column_width(col_values[i]) for i in non_empty_cols}
        ideal_widths = {i: column_width(col_values[i], target_lines=1) for i in non_empty_cols}
        total_min = sum(min_widths.values())
        total_ideal = sum(ideal_widths.values())

        if total_ideal <= SCREEN_BUDGET_PX:
            widths = ideal_widths
        elif total_min <= SCREEN_BUDGET_PX:
            widths = dict(min_widths)
            slack = SCREEN_BUDGET_PX - total_min
            wants = {i: ideal_widths[i] - min_widths[i] for i in non_empty_cols}
            total_want = sum(wants.values())
            if total_want > 0:
                for i in non_empty_cols:
                    grow = int(slack * (wants[i] / total_want))
                    widths[i] = min(ideal_widths[i], min_widths[i] + grow)
        else:
            widths = dict(min_widths)
            over_min = {i: w for i, w in widths.items() if w > MIN_WIDTH_PX}
            shrinkable_total = sum(over_min.values())
            excess = total_min - SCREEN_BUDGET_PX
            if shrinkable_total > 0:
                for i in over_min:
                    reduction = int(excess * (widths[i] / shrinkable_total))
                    widths[i] = max(MIN_WIDTH_PX, widths[i] - reduction)

        for i in non_empty_cols:
            widths[i] = max(widths[i], longest_word_width(col_values[i]))

    full_range = {
        "sheetId": grid_id,
        "startRowIndex": 0,
        "endRowIndex": row_count,
        "startColumnIndex": 0,
        "endColumnIndex": col_count,
    }
    # Base cell styling
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
                "fields": "userEnteredFormat(wrapStrategy,horizontalAlignment,verticalAlignment,backgroundColor,textFormat.foregroundColor)",
            }
        }
    )
    # Clear borders
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
    # Header styling (Row 0)
    header_range = {
        "sheetId": grid_id,
        "startRowIndex": 0,
        "endRowIndex": 1,
        "startColumnIndex": 0,
        "endColumnIndex": col_count,
    }
    requests.append(
        {
            "repeatCell": {
                "range": header_range,
                "cell": {
                    "userEnteredFormat": {
                        "textFormat": {"bold": True},
                        "backgroundColor": HEADER_BG,
                    }
                },
                "fields": "userEnteredFormat(textFormat.bold,backgroundColor)",
            }
        }
    )
    # Freeze header row if profile sets it
    if profile and profile.get("freeze_rows"):
        requests.append(
            {
                "updateSheetProperties": {
                    "properties": {
                        "sheetId": grid_id,
                        "gridProperties": {"frozenRowCount": profile["freeze_rows"]},
                    },
                    "fields": "gridProperties.frozenRowCount",
                }
            }
        )

    # Column widths
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

    # Un-collapse rows
    requests.append(
        {
            "updateDimensionProperties": {
                "range": {"sheetId": grid_id, "dimension": "ROWS", "startIndex": 0, "endIndex": row_count},
                "properties": {"hiddenByUser": False},
                "fields": "hiddenByUser",
            }
        }
    )

    # Row heights
    row_heights = [
        row_height(max((cell_line_count(col_values[i][row_idx], widths.get(i, MIN_WIDTH_PX)) for i in range(num_cols)), default=1))
        for row_idx in range(len(values))
    ]
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

    # Conditional formatting rules from profile
    if profile and "conditional_rules" in profile:
        cond_reqs = build_conditional_rule_requests(grid_id, profile["conditional_rules"])
        requests.extend(cond_reqs)

    return requests, widths


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

        profile = resolve_profile_for_tab(name, title)
        tab_reqs, widths = build_tab_formatting_requests(grid_id, row_count, col_count, values, profile=profile)
        requests.extend(tab_reqs)
        log_parts.append(f"{title}: {len(widths)} cols, total_width={sum(widths.values())}px")

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
