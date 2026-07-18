"""Refresh `_timeline_looker_view` - a Looker-Studio-friendly flattening of
`_timeline` (20_M2_Project_Management) and `_m1_timeline`
(10_M1_People_Management), same spirit as sync_timeline_to_calendar.py but
producing a Sheet instead of Calendar events, for a Looker Studio report to
connect to directly (live, no snapshot step on Looker Studio's side - only
this Sheet needs periodic regeneration).

Why not point Looker Studio at `_timeline` directly: its `Дата события`
column mixes ISO (YYYY-MM-DD) and DD.MM.YYYY in the same column (see
sync_timeline_to_calendar.py's parse_mixed_date docstring) - Looker
Studio's date-type auto-detection needs one consistent format. This view
also precomputes `Status` (Просрочено/Скоро/Позже) so a Looker Studio
chart can color/filter by it without a calculated field.

Living view, fully regenerated every run - same discipline as
`_m1_pr_calendar`/the Calendar sync. Closed rows (Статус != Открыто) are
excluded, same as the Calendar sync.

    python refresh_timeline_looker_view.py            # dry run
    python refresh_timeline_looker_view.py --apply
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))
from google_api_smoke_test import ensure_utf8_stdout
from pipeline_common import get_services, reformat_sheet
from show_project_state import find_folder
from sync_m2_source_docs_to_sheets import ROOT_FOLDER_ID, find_or_create_folder, find_sheet_in_folder, read_sheet_values, upsert_sheet

VIEW_TITLE = "_timeline_looker_view"
# "Дата (конец)" = "Дата (начало)" + 1 day - the same exclusive-end
# convention Google Calendar itself uses for all-day events (see
# sync_timeline_to_calendar.py: an all-day event's API "end.date" is the
# next day). Every row here is a single-point deadline/event, not a
# multi-day task, so there is no genuine multi-day span to report - this
# is not a fabricated duration, it is "this item occupies its one day,"
# which a zero-length start=end bar renders as invisible in Data Studio's
# Timeline chart.
VIEW_HEADER = ["Дата (начало)", "Дата (конец)", "Проект", "Scope", "Тип", "Что нужно сделать", "Owner", "Статус", "Источник", "Комментарии"]
DUE_SOON_DAYS = 7


def parse_mixed_date(value: str) -> dt.date | None:
    value = (value or "").strip()
    if not value:
        return None
    try:
        return dt.date.fromisoformat(value)
    except ValueError:
        pass
    match = re.match(r"^(\d{1,2})\.(\d{1,2})\.(\d{4})$", value)
    if match:
        day, month, year = (int(x) for x in match.groups())
        try:
            return dt.date(year, month, day)
        except ValueError:
            return None
    return None


def status_of(event_date: dt.date, today: dt.date) -> str:
    diff = (event_date - today).days
    if diff < 0:
        return "Просрочено"
    if diff <= DUE_SOON_DAYS:
        return "Скоро"
    return "Позже"


def collect_rows(services: dict[str, Any], today: dt.date) -> list[list[str]]:
    drive = services["drive"]
    rows_out: list[list[str]] = []

    m2_root = find_or_create_folder(drive, ROOT_FOLDER_ID, "20_M2_Project_Management")
    m2_timeline = find_sheet_in_folder(drive, m2_root["id"], "_timeline")
    if m2_timeline:
        for row in read_sheet_values(services, m2_timeline["id"])[1:]:
            if len(row) < 5 or row[4].strip() != "Открыто":
                continue
            event_date = parse_mixed_date(row[1])
            if event_date is None:
                continue
            rows_out.append(
                [event_date.isoformat(), (event_date + dt.timedelta(days=1)).isoformat(), row[0], "M2", row[2], row[3],
                 row[5] if len(row) > 5 else "", status_of(event_date, today),
                 row[6] if len(row) > 6 else "", row[7] if len(row) > 7 else ""]
            )

    m1_root = find_folder(drive, ROOT_FOLDER_ID, "10_M1_People_Management")
    if m1_root:
        m1_timeline = find_sheet_in_folder(drive, m1_root["id"], "_m1_timeline")
        if m1_timeline:
            for row in read_sheet_values(services, m1_timeline["id"])[1:]:
                if len(row) < 5 or row[4].strip() != "Открыто":
                    continue
                event_date = parse_mixed_date(row[1])
                if event_date is None:
                    continue
                rows_out.append(
                    [event_date.isoformat(), (event_date + dt.timedelta(days=1)).isoformat(), row[0], "M1", row[2], row[3],
                     row[5] if len(row) > 5 else "", status_of(event_date, today),
                     row[6] if len(row) > 6 else "", row[7] if len(row) > 7 else ""]
                )

    rows_out.sort(key=lambda r: r[0])
    return rows_out


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="Write the view Sheet (default: dry run, prints only).")
    parser.add_argument("--credentials", default=".local/google/credentials.json")
    parser.add_argument("--token", default=".local/google/token.json")
    return parser.parse_args()


def main() -> int:
    ensure_utf8_stdout()
    args = parse_args()
    services = get_services(args.credentials, args.token)
    today = dt.date.today()

    rows = collect_rows(services, today)
    print(f"{len(rows)} open row(s) with a parseable date.")
    for row in rows[:10]:
        print(" ", row[:7])
    if len(rows) > 10:
        print(f"  ... and {len(rows) - 10} more")

    if not args.apply:
        print("\nDry run - rerun with --apply to write the view Sheet.")
        return 0

    drive = services["drive"]
    m2_root = find_or_create_folder(drive, ROOT_FOLDER_ID, "20_M2_Project_Management")
    sheet = upsert_sheet(services, m2_root["id"], VIEW_TITLE, [VIEW_HEADER] + rows)
    reformat_sheet(services, sheet["id"], VIEW_TITLE)
    print(f"\nWrote {len(rows)} row(s) to '{VIEW_TITLE}' (id={sheet['id']}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
