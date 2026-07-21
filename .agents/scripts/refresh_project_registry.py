"""Refresh `_project_registry` from each project's already-curated `project_metrics`.

This is the mechanical step referenced in google-workspace-rules.md,
Pipeline Architecture: it copies dashboard values across with no
interpretation of its own — it does not compute Статус, Вклад в проект,
Горизонт, Бизнес-риск, or Качество QA-процесса, only aggregates what
`project_metrics` already says. Writing those values in `project_metrics`
in the first place is still a judgment step done in conversation.

Статус (Активен/На паузе, see Templates/метрики_проекта_qa.md §1.0) is
manual-only in project_metrics - this script never sets or clears it, it
just copies whatever's there. Reactivation happens by M2 editing
project_metrics directly; the next run of this script picks that up like
any other mirrored field.

Aggregation for "Наименьший вклад в проект" is worst-known-status, not an
average (see m2-role-rules.md, Registry Data-Gap Semantics): among named
people with an actual Позитивный/Смешанный/Негативный judgment, report the
worst one and who is at it; people with no judgment yet (blank or
"Неизвестно") are named separately, never folded into the worst-case label.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from m2_workspace_layout import SHEET_MIME, find_document

from google_api_smoke_test import build_services, ensure_utf8_stdout, load_credentials
from pipeline_common import reformat_sheet
from sync_m2_source_docs_to_sheets import ROOT_FOLDER_ID, find_or_create_folder, find_sheet_in_folder, read_sheet_values

REGISTRY_HEADER = [
    "Проект",
    "People",
    "Статус",
    "Горизонт совместной работы",
    "Бизнес-риск продукта клиента",
    "Наименьший вклад в проект",
    "Качество QA-процесса",
]

STATUS_ORDER = ["Негативный", "Смешанный", "Позитивный"]
CONTRIBUTION_PREFIX = "Вклад в проект: "


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--credentials", default=".local/google/credentials.json")
    parser.add_argument("--token", default=".local/google/token.json")
    return parser.parse_args()


def dashboard_value(rows: list[list[str]], metric: str, default: str = "") -> str:
    for row in rows:
        if len(row) > 2 and row[2] == metric:
            value = row[3] if len(row) > 3 else ""
            return value or default
    return default


def contribution_summary(rows: list[list[str]]) -> tuple[str, list[str]]:
    # project_metrics is meant to hold at most one current "Вклад в
    # проект: <Имя>" row per person (see m2-role-rules.md, Cascading
    # Updates - update in place, don't append a new dated row per pass).
    # A stale duplicate can still slip in upstream, though (this happened
    # on a real project once); dedupe defensively here by name, keeping
    # only the latest-dated row per person, so a duplicate never renders
    # as "<Имя>, <Имя>" in the registry even if project_metrics itself
    # temporarily has two rows for the same key.
    latest_by_name: dict[str, tuple[str, str]] = {}  # name -> (date, status)
    order: list[str] = []
    for row in rows:
        if len(row) <= 3 or not row[2].startswith(CONTRIBUTION_PREFIX):
            continue
        name = row[2][len(CONTRIBUTION_PREFIX):].strip()
        date = row[1].strip() if len(row) > 1 else ""
        status = row[3].strip()
        if name not in latest_by_name:
            order.append(name)
        elif date >= latest_by_name[name][0]:
            pass  # newer or equal (later row wins ties) - falls through to overwrite below
        else:
            continue  # existing entry has a strictly later date - keep it
        latest_by_name[name] = (date, status)

    known: dict[str, list[str]] = {status: [] for status in STATUS_ORDER}
    unknown: list[str] = []
    for name in order:
        status = latest_by_name[name][1]
        if status in known:
            known[status].append(name)
        else:
            unknown.append(name)
    people = [n for names in known.values() for n in names] + unknown
    worst = next((status for status in STATUS_ORDER if known[status]), None)
    if worst is None:
        if unknown:
            return f"Неизвестно (данных недостаточно по {', '.join(unknown)})", people
        return "", people
    label = f"{worst} ({', '.join(known[worst])})"
    if unknown:
        label += f" — данных нет по {', '.join(unknown)}"
    return label, people


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

    registry_sheet = find_sheet_in_folder(drive, m2_root["id"], "_project_registry")
    if not registry_sheet:
        raise SystemExit("_project_registry Sheet not found under 20_M2_Project_Management")

    rows = [REGISTRY_HEADER]
    for folder in sorted(project_folders, key=lambda f: f["name"]):
        project = folder["name"]
        pm_sheet = find_document(
            drive, folder["id"], "project_metrics", "project_metrics", SHEET_MIME
        )
        if not pm_sheet:
            print(f"{project}: no project_metrics yet, skipped")
            continue
        pm_rows = read_sheet_values(services, pm_sheet["id"])
        status = dashboard_value(pm_rows, "Статус проекта", default="Активен")
        horizon = dashboard_value(pm_rows, "Горизонт совместной работы")
        biz_risk = dashboard_value(pm_rows, "Бизнес-риск продукта клиента")
        qa_quality = dashboard_value(pm_rows, "Качество QA-процесса")
        contribution, people = contribution_summary(pm_rows)
        rows.append([project, ", ".join(people), status, horizon, biz_risk, contribution, qa_quality])
        print(f"{project}: refreshed ({len(people)} people, status={status})")

    services["sheets"].spreadsheets().values().clear(
        spreadsheetId=registry_sheet["id"], range="A1:G200"
    ).execute()
    services["sheets"].spreadsheets().values().update(
        spreadsheetId=registry_sheet["id"], range="A1", valueInputOption="RAW", body={"values": rows}
    ).execute()
    reformat_sheet(services, registry_sheet["id"], "_project_registry")
    print(f"_project_registry: {len(rows) - 1} project rows written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
