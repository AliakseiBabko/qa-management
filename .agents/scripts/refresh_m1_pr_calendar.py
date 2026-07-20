"""Refresh `_m1_pr_calendar` from `_people_registry` - a PR-only view,
same mechanical-rollup spirit as `refresh_project_registry.py`/
`refresh_timeline_registry.py`: no judgment of its own, just recomputes
the expected next-PR window for every internal person on record and
writes it out sorted by how soon it opens.

This does NOT duplicate `Дата последнего PR` as an independently-editable
fact anywhere - `_people_registry` stays the single source of truth for
that; this Sheet is fully regenerated from it every run, so it can never
drift out of sync the way a second hand-maintained sheet could (see
performance-review-rules.md, "Deriving the Expected Next PR Window").

Also applies the workspace's standard formatting (wrap, left/top align,
column widths - see format_all_sheets.py) after every write, the same way
scaffold_project_dashboard.py-created Sheets are expected to eventually be
formatted. A fully-rewritten Sheet has no reason to ever sit unformatted
between runs.

Safe to rerun anytime after a `_people_registry` update. Unlike
scan_m1_events.py, there is no --write/dry-run split here - there's no
candidate to review, just a recomputation, so it always writes.
"""

from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))
from format_all_sheets import format_sheet
from google_api_smoke_test import ensure_utf8_stdout
from pipeline_common import get_people_registry_sheet, get_services
from scan_m1_events import (
    REGISTRY_HIRE_DATE_COL,
    REGISTRY_LAST_PR_COL,
    REGISTRY_NAME_EN_COL,
    REGISTRY_NAME_RU_COL,
    expected_pr_window,
    parse_iso_date,
)
from show_project_state import find_folder
from sync_m2_source_docs_to_sheets import ROOT_FOLDER_ID, find_sheet_in_folder, read_sheet_values, upsert_sheet

CALENDAR_HEADER = [
    "Сотрудник",
    "Основание расчёта",
    "Дата последнего PR / трудоустройства",
    "Окно начала",
    "Окно окончания",
    "Статус",
    "Комментарий",
]


def compute_row(name_ru: str, name_en: str, hire: dt.date | None, last_pr: dt.date | None) -> list[str]:
    person = name_ru or name_en
    window_open, window_close, basis = expected_pr_window(hire, last_pr)

    if window_open is None or window_close is None:
        return [person, "нет данных", "", "", "", "Нет данных", "Нужна «Дата трудоустройства» в _people_registry"]

    anchor = last_pr if last_pr is not None else hire
    today = dt.date.today()
    if today < window_open:
        status = "Не скоро"
    elif today <= window_close:
        status = "В окне"
    else:
        status = "Просрочено"

    return [
        person,
        basis,
        anchor.isoformat() if anchor else "",
        window_open.isoformat(),
        window_close.isoformat(),
        status,
        "",
    ]


def main() -> int:
    ensure_utf8_stdout()
    services = get_services()
    drive = services["drive"]

    m1_root = find_folder(drive, ROOT_FOLDER_ID, "10_M1_People_Management")
    if not m1_root:
        print("10_M1_People_Management folder not found under the workspace root.")
        return 1
    registry_sheet = get_people_registry_sheet(services)

    registry_rows = read_sheet_values(services, registry_sheet["id"])
    rows: list[list[str]] = []
    for row in registry_rows[1:]:
        if not row:
            continue

        def cell(idx: int) -> str:
            return row[idx].strip() if len(row) > idx and row[idx] else ""

        name_ru, name_en = cell(REGISTRY_NAME_RU_COL), cell(REGISTRY_NAME_EN_COL)
        hire = parse_iso_date(cell(REGISTRY_HIRE_DATE_COL))
        last_pr = parse_iso_date(cell(REGISTRY_LAST_PR_COL))
        if hire is None and last_pr is None:
            continue  # nothing to compute - not a data gap worth a row for every registry entry
        rows.append(compute_row(name_ru, name_en, hire, last_pr))

    rows.sort(key=lambda r: r[3] or "9999-99-99")  # soonest-opening window first; no-window rows sort last

    sheet = upsert_sheet(services, m1_root["id"], "_m1_pr_calendar", [CALENDAR_HEADER] + rows)
    print(f"_m1_pr_calendar: {len(rows)} people written.")
    for r in rows:
        print(f"  [{r[5]}] {r[0]}: window {r[3]}–{r[4]} ({r[1]})")

    print(format_sheet(services["sheets"], sheet["id"], "_m1_pr_calendar"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
