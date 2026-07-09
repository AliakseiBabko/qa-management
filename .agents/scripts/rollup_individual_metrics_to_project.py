#!/usr/bin/env python3
"""DEPRECATED — do not run this against project_metrics.

The "Команда: ..." statistical-distribution rollup (grade-fit/feedback/
workload breakdown across the team) is redundant with the per-person
`Вклад в проект: <Имя>` rows in project_metrics (see
Templates\\метрики_проекта_qa.md §1.3) — one row per QA engineer showing an
actual judgment (Позитивный/Смешанный/Негативный), not a mechanical
distribution. `main()` below refuses to run; the aggregation logic is kept
only for reference.
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from google_api_smoke_test import build_services, load_credentials
from sync_m2_source_docs_to_sheets import (
    ROOT_FOLDER_ID,
    IGNORED_PROJECTS,
    drive_query,
    find_or_create_folder,
    find_sheet_in_folder,
    read_sheet_values,
    upsert_sheet,
)

ROLLUP_PREFIX = "Команда: "

QUALITATIVE_LEVELS: dict[str, list[str]] = {
    "Обратная связь клиента/команды": ["Позитивная", "Нейтральная", "Негативная"],
    "Соответствие ожиданиям клиента (грейд)": ["Соответствует", "Требует поддержки", "Превышает"],
    "Нагрузка": ["Комфортная", "Повышенная", "Критическая"],
}
# "Вклад в проект" is deliberately excluded from Core rollup: it's M2's
# private per-person conclusion, tracked directly in project_metrics, not
# derived from individual_metrics (which the employee can see).

QUANTITATIVE_CORE_METRICS = [
    "Перформанс",
    "Баги на проде",
    "Bug leakage rate",
    "Regression/smoke coverage критичных сценариев",
]

CORE_METRICS = [*QUANTITATIVE_CORE_METRICS, *QUALITATIVE_LEVELS.keys()]

PROJECT_METRICS_HEADER = [
    "Проект",
    "Период",
    "Метрика",
    "Показатель",
    "Пояснение",
    "Owner",
    "Тренд",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Roll up team Core individual metrics into project_metrics.")
    parser.add_argument(
        "--credentials",
        default=".local/google/credentials.json",
        help="OAuth desktop client JSON path.",
    )
    parser.add_argument(
        "--token",
        default=".local/google/token.json",
        help="OAuth token cache path.",
    )
    return parser.parse_args()


def latest_person_metrics(rows: list[list[str]]) -> dict[str, tuple[str, str]]:
    """From one person's individual_metrics rows, return {metric: (показатель, дата)}
    using only that metric's most recent date."""
    body = rows[1:] if rows else []
    latest: dict[str, tuple[str, str]] = {}
    for row in body:
        if len(row) < 6:
            continue
        date, metric, indicator = row[2], row[4], row[5]
        if metric not in CORE_METRICS:
            continue
        prev = latest.get(metric)
        if prev is None or date >= prev[1]:
            latest[metric] = (indicator, date)
    return latest


def build_rollup_rows(project: str, team_values: dict[str, list[tuple[str, str]]]) -> list[list[str]]:
    """team_values: {metric: [(person, показатель), ...]}"""
    snapshot_date = dt.date.today().isoformat()
    rows: list[list[str]] = []
    for metric, entries in team_values.items():
        if not entries:
            continue
        total = len(entries)
        if metric in QUALITATIVE_LEVELS:
            counts = defaultdict(int)
            for _, value in entries:
                counts[value] += 1
            indicator = ", ".join(f"{counts[level]}/{total} {level}" for level in QUALITATIVE_LEVELS[metric] if counts[level])
            evidence = "; ".join(f"{person}: {value}" for person, value in entries)
        else:
            indicator = f"{total} чел. с данными"
            evidence = "; ".join(f"{person}: {value}" for person, value in entries)
        rows.append(
            [
                project,
                snapshot_date,
                f"{ROLLUP_PREFIX}{metric}",
                indicator,
                evidence,
                "M2",
                "",
            ]
        )
    return rows


def merge_rollup(existing: list[list[str]], rollup_rows: list[list[str]]) -> list[list[str]]:
    header = existing[0] if existing else PROJECT_METRICS_HEADER
    body = [row for row in existing[1:] if row and not row[2].startswith(ROLLUP_PREFIX)] if existing else []
    return [header, *body, *rollup_rows]


def main() -> int:
    print(
        "This script is deprecated — project_metrics uses per-person Вклад в "
        "проект rows instead of Команда: ... rollup rows. Not running. See "
        "the module docstring.",
        file=sys.stderr,
    )
    return 1

    args = parse_args()  # noqa: unreachable — kept for reference only
    creds = load_credentials(Path(args.credentials), Path(args.token))
    services = build_services(creds)
    drive = services["drive"]

    m2_folder = find_or_create_folder(drive, ROOT_FOLDER_ID, "20_M2_Project_Management")
    projects = drive_query(
        drive,
        f"'{m2_folder['id']}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false",
    )

    results: list[str] = []
    for project_folder in projects:
        project = project_folder["name"]
        if project in IGNORED_PROJECTS:
            continue
        people_matches = drive_query(
            drive,
            f"'{project_folder['id']}' in parents and name='people' and mimeType='application/vnd.google-apps.folder'",
        )
        if not people_matches:
            continue
        people = drive_query(
            drive,
            f"'{people_matches[0]['id']}' in parents and mimeType='application/vnd.google-apps.folder'",
        )

        team_values: dict[str, list[tuple[str, str]]] = defaultdict(list)
        for person in people:
            metrics_sheet = find_sheet_in_folder(drive, person["id"], "individual_metrics")
            if not metrics_sheet:
                continue
            rows = read_sheet_values(services, metrics_sheet["id"])
            for metric, (indicator, _date) in latest_person_metrics(rows).items():
                team_values[metric].append((person["name"], indicator))

        if not team_values:
            continue

        rollup_rows = build_rollup_rows(project, team_values)
        metrics_sheet = find_sheet_in_folder(drive, project_folder["id"], "project_metrics")
        existing = read_sheet_values(services, metrics_sheet["id"]) if metrics_sheet else [PROJECT_METRICS_HEADER]
        merged = merge_rollup(existing, rollup_rows)
        meta = upsert_sheet(services, project_folder["id"], "project_metrics", merged)
        results.append(f"{project}: {len(rollup_rows)} rollup row(s) in {meta['name']}")

    sys.stdout.buffer.write(("\n".join(results) + "\n").encode("utf-8", errors="replace"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
