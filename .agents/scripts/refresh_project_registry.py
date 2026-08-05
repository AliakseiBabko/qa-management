"""Refresh `_project_registry` from each project's already-curated `project_metrics`.

This is the mechanical step referenced in
qa-management-roles/references/google-workspace/pipeline-architecture.md:
it copies dashboard values across with no
interpretation of its own — it does not compute Статус, Вклад в проект,
Горизонт, Бизнес-риск, or Качество QA-процесса, only aggregates what
`project_metrics` already says. Writing those values in `project_metrics`
in the first place is still a judgment step done in conversation.

Статус (Активен/Не активен - exactly two states, see
Templates/метрики_проекта_qa.md §1.0) is manual-only in project_metrics -
this script never sets or clears it. Активен copies through normally; Не
активен excludes the project from the rebuilt registry entirely - the
concrete mechanism for "not currently active, for whatever reason"
projects (pause or official stop alike - see google-workspace/m2-layout.md).
Reactivation happens by M2 flipping project_metrics back to Активен
directly; the next run of this script picks that up like any other
mirrored field.

Aggregation for "Наименьший вклад в проект" is worst-known-status, not an
average (see m2-role/m2-metrics-attribution.md, Registry Data-Gap Semantics): among named
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

# Values that legitimately mean "no judgment yet" - never warned about, just
# folded into the unknown bucket per the Registry Data-Gap Semantics rule
# above (see m2-role/m2-metrics-attribution.md).
MISSING_CONTRIBUTION_VALUES = {"", "Неизвестно"}

PROJECT_STATUS_VALUES = {"Активен", "Не активен"}
INACTIVE_STATUS_VALUE = "Не активен"


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


def project_status_warning(project: str, status: str) -> str | None:
    """Return a warning string if `status` ('Статус проекта') isn't one of
    PROJECT_STATUS_VALUES, or None if it's canonical. `dashboard_value`'s
    own default ("Активен") means `status` is never blank here - anything
    else is a value that slipped past the manual-only Активен/Не активен
    convention (see Templates/метрики_проекта_qa.md §1.0) and would
    otherwise be copied into the registry unnoticed."""
    if status in PROJECT_STATUS_VALUES:
        return None
    return (
        f"{project}: 'Статус проекта' has a non-canonical value {status!r} "
        f"(expected one of {sorted(PROJECT_STATUS_VALUES)}) - copied as-is, not normalized."
    )


def contribution_summary(rows: list[list[str]], project: str = "") -> tuple[str, list[str], list[str]]:
    # project_metrics is meant to hold at most one current "Вклад в
    # проект: <Имя>" row per person (see m2-role/m2-cascading-updates.md, Cascading
    # Updates - update in place, don't append a new dated row per pass).
    # A stale duplicate can still slip in upstream, though (this happened
    # on a real project once); dedupe defensively here by name, keeping
    # only the latest-dated row per person, so a duplicate never renders
    # as "<Имя>, <Имя>" in the registry even if project_metrics itself
    # temporarily has two rows for the same key.
    #
    # A value that isn't exactly one of STATUS_ORDER and isn't a
    # recognized missing-data marker (blank / "Неизвестно") - e.g. a
    # suffixed variant like "Позитивный (по самоотчёту)" - falls into the
    # same `unknown` bucket as genuinely missing data below. That's the
    # right *registry* behavior (never guess a verdict), but it silently
    # hides a project_metrics value that doesn't match the documented
    # enum (see метрики_проекта_qa.md) - a real one went unnoticed this
    # way until a manual diff caught it. `warnings` surfaces that case
    # for the operator without changing the aggregation itself; this
    # function never normalizes a fuzzy value to a canonical one - that
    # stays a human edit in project_metrics.
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
    warnings: list[str] = []
    for name in order:
        status = latest_by_name[name][1]
        if status in known:
            known[status].append(name)
        else:
            unknown.append(name)
            if status not in MISSING_CONTRIBUTION_VALUES:
                where = f"{project}: " if project else ""
                warnings.append(
                    f"{where}'Вклад в проект: {name}' has a non-canonical value {status!r} "
                    f"(expected one of {STATUS_ORDER} or a missing-data marker "
                    f"{sorted(MISSING_CONTRIBUTION_VALUES)!r}) - treated as unknown/missing data in "
                    "the registry, not auto-normalized. Fix the value in project_metrics directly."
                )
    people = [n for names in known.values() for n in names] + unknown
    worst = next((status for status in STATUS_ORDER if known[status]), None)
    if worst is None:
        if unknown:
            return f"Неизвестно (данных недостаточно по {', '.join(unknown)})", people, warnings
        return "", people, warnings
    label = f"{worst} ({', '.join(known[worst])})"
    if unknown:
        label += f" — данных нет по {', '.join(unknown)}"
    return label, people, warnings


def build_registry_row(project: str, pm_rows: list[list[str]]) -> tuple[list[str] | None, list[str]]:
    """Build one `_project_registry` row from a project's `project_metrics`
    rows, or return `(None, warnings)` if the project is currently `Не
    активен` - excluded from the registry entirely (see
    Templates/метрики_проекта_qa.md §1.0). Pure function, no Google API
    calls, so the inactive-exclusion behavior is directly unit-testable
    without mocking `main()`'s Drive/Sheets calls.

    `warnings` covers both a non-canonical `Статус проекта` value and any
    non-canonical `Вклад в проект` values surfaced by `contribution_summary()`
    - the caller is responsible for printing them."""
    status = dashboard_value(pm_rows, "Статус проекта", default="Активен")
    warnings: list[str] = []
    status_warning = project_status_warning(project, status)
    if status_warning:
        warnings.append(status_warning)
    if status == INACTIVE_STATUS_VALUE:
        return None, warnings
    horizon = dashboard_value(pm_rows, "Горизонт совместной работы")
    biz_risk = dashboard_value(pm_rows, "Бизнес-риск продукта клиента (оценка M2)")
    qa_quality = dashboard_value(pm_rows, "Качество QA-процесса")
    contribution, people, contribution_warnings = contribution_summary(pm_rows, project)
    warnings.extend(contribution_warnings)
    row = [project, ", ".join(people), status, horizon, biz_risk, contribution, qa_quality]
    return row, warnings


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
        row, warnings = build_registry_row(project, pm_rows)
        for warning in warnings:
            print(f"WARNING: {warning}")
        if row is None:
            print(f"{project}: Статус проекта = Не активен - excluded from registry")
            continue
        rows.append(row)
        people_count = len(row[1].split(", ")) if row[1] else 0
        print(f"{project}: refreshed ({people_count} people, status={row[2]})")

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
