"""Sync open `_timeline` (20_M2_Project_Management) and `_m1_timeline`
(10_M1_People_Management) rows into a dedicated Google Calendar, so
upcoming/overdue events are visible sorted-by-date in a real calendar view
instead of a 30+ row unsorted Sheet table with mixed date formats.

Scope, deliberately mechanical (same spirit as refresh_timeline_registry.py/
refresh_m1_pr_calendar.py): this does not decide what belongs on the
timeline - `_timeline`/`_m1_timeline` are still the source of truth,
already curated by their own refresh scripts. This only projects their
currently-open rows onto a calendar as a more visual read.

The target calendar (default title "QA Management Timeline") is a
dedicated calendar, not the user's primary one, and is treated as a fully
regenerated rollup on every run - same living-artifact discipline as
`_m1_pr_calendar`. Every event previously created by this script is
deleted and recreated from current data, so no fragile diffing/matching
logic is needed and stale/closed items always disappear on the next run.
Only events this script created are touched (tagged via
extendedProperties.private.source=qa-timeline-sync) - anything a human
adds to this calendar by hand is left alone.

Closed rows (Статус != Открыто) are skipped - a calendar cluttered with
finished items defeats the point.

    python sync_timeline_to_calendar.py            # dry run - prints what would sync
    python sync_timeline_to_calendar.py --apply     # actually writes to Calendar
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
from pipeline_common import get_services
from show_project_state import find_folder
from sync_m2_source_docs_to_sheets import ROOT_FOLDER_ID, find_or_create_folder, find_sheet_in_folder, read_sheet_values

CALENDAR_TITLE = "QA Management Timeline"
SOURCE_TAG = "qa-timeline-sync"

# colorId values from the Calendar API's fixed event-color palette (colors().get()) -
# not arbitrary numbers, these are Google Calendar's own IDs (11=Tomato/red,
# 5=Banana/yellow, 10=Basil/green).
COLOR_OVERDUE = "11"
COLOR_DUE_SOON = "5"
COLOR_LATER = "10"
DUE_SOON_DAYS = 7


def parse_mixed_date(value: str) -> dt.date | None:
    """`_timeline` mixes ISO (YYYY-MM-DD) and DD.MM.YYYY in the same column
    (the exact problem this script exists to paper over visually) - accept
    both rather than erroring on whichever one wasn't expected."""
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="Write to Calendar (default: dry run, prints only).")
    parser.add_argument("--calendar-title", default=CALENDAR_TITLE)
    parser.add_argument("--credentials", default=".local/google/credentials.json")
    parser.add_argument("--token", default=".local/google/token.json")
    return parser.parse_args()


def get_or_create_calendar(calendar_service: Any, title: str) -> str:
    page_token = None
    while True:
        response = calendar_service.calendarList().list(pageToken=page_token).execute()
        for entry in response.get("items", []):
            if entry.get("summary") == title:
                return entry["id"]
        page_token = response.get("nextPageToken")
        if not page_token:
            break
    created = calendar_service.calendars().insert(body={"summary": title}).execute()
    return created["id"]


def delete_previous_events(calendar_service: Any, calendar_id: str) -> int:
    deleted = 0
    page_token = None
    while True:
        response = (
            calendar_service.events()
            .list(calendarId=calendar_id, privateExtendedProperty=f"source={SOURCE_TAG}", pageToken=page_token)
            .execute()
        )
        for event in response.get("items", []):
            calendar_service.events().delete(calendarId=calendar_id, eventId=event["id"]).execute()
            deleted += 1
        page_token = response.get("nextPageToken")
        if not page_token:
            break
    return deleted


def collect_rows(services: dict[str, Any]) -> list[dict[str, str]]:
    drive = services["drive"]
    rows_out: list[dict[str, str]] = []

    m2_root = find_or_create_folder(drive, ROOT_FOLDER_ID, "20_M2_Project_Management")
    m2_timeline = find_sheet_in_folder(drive, m2_root["id"], "_timeline")
    if m2_timeline:
        rows = read_sheet_values(services, m2_timeline["id"])
        for row in rows[1:]:
            if len(row) < 5 or row[4].strip() != "Открыто":
                continue
            rows_out.append(
                {
                    "scope": "M2", "project": row[0], "date": row[1], "type": row[2],
                    "task": row[3], "owner": row[5] if len(row) > 5 else "",
                    "source": row[6] if len(row) > 6 else "", "comments": row[7] if len(row) > 7 else "",
                }
            )

    m1_root = find_folder(drive, ROOT_FOLDER_ID, "10_M1_People_Management")
    if m1_root:
        m1_timeline = find_sheet_in_folder(drive, m1_root["id"], "_m1_timeline")
        if m1_timeline:
            rows = read_sheet_values(services, m1_timeline["id"])
            for row in rows[1:]:
                # _m1_timeline header: Сотрудник, Дата события, Тип, Что нужно сделать, Статус, Owner, Источник, Комментарии
                if len(row) < 5 or row[4].strip() != "Открыто":
                    continue
                rows_out.append(
                    {
                        "scope": "M1", "project": row[0], "date": row[1], "type": row[2],
                        "task": row[3], "owner": row[5] if len(row) > 5 else "",
                        "source": row[6] if len(row) > 6 else "", "comments": row[7] if len(row) > 7 else "",
                    }
                )
    return rows_out


def build_event(item: dict[str, str], today: dt.date) -> dict[str, Any] | None:
    event_date = parse_mixed_date(item["date"])
    if event_date is None:
        return None
    if event_date < today:
        color = COLOR_OVERDUE
    elif (event_date - today).days <= DUE_SOON_DAYS:
        color = COLOR_DUE_SOON
    else:
        color = COLOR_LATER

    label = item["project"] or item["scope"]
    summary = f"[{label}] {item['type']}: {item['task'][:80]}"
    description_parts = [
        f"Полное описание: {item['task']}",
        f"Owner: {item['owner']}" if item["owner"] else "",
        f"Тип: {item['type']}",
        f"Источник: {item['source']}" if item["source"] else "",
        f"Комментарии: {item['comments']}" if item["comments"] else "",
    ]
    description = "\n".join(p for p in description_parts if p)

    return {
        "summary": summary,
        "description": description,
        "start": {"date": event_date.isoformat()},
        "end": {"date": event_date.isoformat()},
        "colorId": color,
        "extendedProperties": {"private": {"source": SOURCE_TAG}},
    }


def main() -> int:
    ensure_utf8_stdout()
    args = parse_args()
    services = get_services(args.credentials, args.token)
    calendar_service = services["calendar"]

    items = collect_rows(services)
    today = dt.date.today()
    events = []
    unparsed = []
    for item in items:
        event = build_event(item, today)
        if event is None:
            unparsed.append(item)
        else:
            events.append(event)

    events.sort(key=lambda e: e["start"]["date"])

    print(f"{len(items)} open row(s) found ({len(events)} with a parseable date, {len(unparsed)} without).")
    for item in unparsed:
        print(f"  SKIPPED (no parseable date): [{item['project']}] {item['task'][:60]!r} date={item['date']!r}")
    for event in events:
        print(f"  {event['start']['date']} [{event['colorId']}] {event['summary']}")

    if not args.apply:
        print("\nDry run - rerun with --apply to write these to Calendar.")
        return 0

    calendar_id = get_or_create_calendar(calendar_service, args.calendar_title)
    deleted = delete_previous_events(calendar_service, calendar_id)
    print(f"\nCleared {deleted} previously-synced event(s) from '{args.calendar_title}'.")
    for event in events:
        calendar_service.events().insert(calendarId=calendar_id, body=event).execute()
    print(f"Created {len(events)} event(s) in '{args.calendar_title}' (calendarId={calendar_id}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
