#!/usr/bin/env python3
"""Migrate every project's qa_process_metrics Sheet to the wide sprint-per-column layout.

The old shape was a long table - `Проект`, `Период`, `Метрика`, `Показатель`,
`Пояснение`, `Owner`, `Тренд` - with one row per (metric, period), so a single
metric's history was scattered down the sheet as unrelated-looking rows. The
new shape (2026-09-09, see
`.agents/skills/m2-project-qa-metrics-report/references/qa-process-metrics-schema.md`)
is `Метрика`, `Пояснение`, `Owner`, then one column appended per sprint, with
the Baseline 3 rows on top under a group label and the Core 6 below theirs.

What this preserves from an existing sheet:

- every `Пояснение` that has real text (it is project-tailored, and the schema
  requires it to stay that way);
- every non-empty `Owner`;
- every non-empty `Показатель`, placed in a column named after its old
  `Период` (or after `--period-label OLD=NEW`, which also merges several old
  period stamps into one column), in first-seen order;
- any non-canonical metric row (an Extended-catalog row someone added by hand),
  appended under its own group label rather than dropped.

The one thing it does not carry over is the `Тренд` column, which no longer
exists - any real text found there is printed instead of written, so nothing
disappears without being read.

A period column is created only if some metric actually has a value in that
period - an all-blank period is not worth a column, and the wide sheet is meant
to start with the sprint columns the team is really filling in.

The Sheet's file ID, link, and sharing are untouched: the migration clears the
grid and writes the new values into the same spreadsheet.

Default is a dry run that prints the planned result per project. Pass --apply
to write.

Examples:
  python .agents/scripts/migrate_qa_process_metrics_layout.py
  python .agents/scripts/migrate_qa_process_metrics_layout.py --project <Project>
  python .agents/scripts/migrate_qa_process_metrics_layout.py --apply --sprint "2026-S18 (01.09-14.09)"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from google_api_smoke_test import ensure_utf8_stdout
from m2_workspace_layout import SHEET_MIME, find_child_folder, find_document, list_children
from pipeline_common import execute_with_backoff, get_services, reformat_sheet
from scaffold_project_dashboard import (
    QA_PROCESS_FIXED_HEADER,
    QA_PROCESS_GROUPS,
    SPRINT_COLUMN_PLACEHOLDER,
)
from sync_m2_source_docs_to_sheets import ROOT_FOLDER_ID, read_sheet_values

M2_ROOT_NAME = "20_M2_Project_Management"
DOCUMENT = "qa_process_metrics"
# Not a project folder: the M2's own cross-project workspace.
NOT_A_PROJECT = frozenset({"M2"})

CARRIED_OVER_GROUP = "[Прочие метрики (перенесены из прошлого формата)]"

# Rows renamed with the layout change: the monthly cadence is gone from the
# metric's own name now that the column is the period.
RENAMED_METRICS = {"Количество автотестов (тренд)": "Количество автотестов"}

OLD_COLUMNS = ("Проект", "Период", "Метрика", "Показатель", "Пояснение", "Owner", "Тренд")

# Boilerplate wording inside an existing `Пояснение` that the layout change
# made wrong. These are applied as substring rewrites rather than by replacing
# the whole note, because real sheets have M2's own findings appended after the
# template prefix and those must survive untouched. Applied to already-wide
# sheets too, so a rerun fixes notes without touching anything else.
NOTE_REWRITES = (
    ("Общее число автотестов, помесячно -", "Общее число автотестов на конец спринта -"),
    ("Отдельно от снимка открытых багов ниже -", "Отдельно от снимка открытых багов выше -"),
    ("Сырое число, если трекер (Jira и т.п.) доступен",
     "Сырое число на конец спринта, если трекер (Jira и т.п.) доступен"),
)


def rewrite_note(note: str) -> str:
    for old, new in NOTE_REWRITES:
        note = note.replace(old, new)
    return note


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--project", action="append", default=[], dest="projects",
                        help="Limit to this project folder. Repeat for several; default is every project.")
    parser.add_argument("--sprint", default=SPRINT_COLUMN_PLACEHOLDER,
                        help="Header for the first sprint column when the old sheet carried no values at all, "
                             "e.g. \"2026-S18 (01.09-14.09)\". Defaults to a placeholder for the team to rename.")
    parser.add_argument("--period-label", action="append", default=[], dest="period_labels",
                        metavar="OLD=NEW",
                        help="Rename an old `Период` value to a column header, e.g. "
                             "\"2026-07-26=июль 2026\". Repeat; two old periods mapped to the same "
                             "header merge into one column (a value conflict keeps the first and warns).")
    parser.add_argument("--apply", action="store_true", help="Write the new layout. Without it, dry run only.")
    parser.add_argument("--credentials", default=".local/google/credentials.json")
    parser.add_argument("--token", default=".local/google/token.json")
    return parser.parse_args()


def column_index(header: list[str], name: str) -> int:
    return header.index(name) if name in header else -1


def is_group_label(metric: str) -> bool:
    return metric.startswith("[")


def canonical_metric_names() -> list[str]:
    return [metric for _, metrics in QA_PROCESS_GROUPS for metric, _ in metrics]


def parse_period_labels(pairs: list[str]) -> dict[str, str]:
    labels: dict[str, str] = {}
    for pair in pairs:
        if "=" not in pair:
            raise SystemExit(f"--period-label expects OLD=NEW, got {pair!r}")
        old, new = pair.split("=", 1)
        labels[old.strip()] = new.strip()
    return labels


def parse_old_sheet(values: list[list[str]], period_labels: dict[str, str]) -> dict[str, Any]:
    """Pull (metric -> period -> value), notes, owners, and period order out of the old shape."""
    header = [cell.strip() for cell in values[0]] if values else []
    idx_metric = column_index(header, "Метрика")
    idx_period = column_index(header, "Период")
    idx_value = column_index(header, "Показатель")
    idx_note = column_index(header, "Пояснение")
    idx_owner = column_index(header, "Owner")
    idx_trend = column_index(header, "Тренд")
    if idx_metric < 0:
        raise RuntimeError(f"No 'Метрика' column in header {header!r} - unrecognized layout, refusing to guess.")

    def cell(row: list[str], index: int) -> str:
        return row[index].strip() if 0 <= index < len(row) else ""

    values_by_metric: dict[str, dict[str, str]] = {}
    notes: dict[str, str] = {}
    owners: dict[str, str] = {}
    metric_order: list[str] = []
    period_order: list[str] = []
    dropped_trends: list[str] = []
    conflicts: list[str] = []
    for row in values[1:]:
        metric = cell(row, idx_metric)
        if not metric or is_group_label(metric):
            continue
        metric = RENAMED_METRICS.get(metric, metric)
        if metric not in values_by_metric:
            values_by_metric[metric] = {}
            metric_order.append(metric)
        period = cell(row, idx_period)
        value = cell(row, idx_value)
        note = cell(row, idx_note)
        owner = cell(row, idx_owner)
        if note and not notes.get(metric):
            notes[metric] = note
        if owner and not owners.get(metric):
            owners[metric] = owner
        trend = cell(row, idx_trend)
        if trend:
            # The Тренд column is gone (the trend is read across sprint columns
            # now). Report any real text in it rather than dropping it silently.
            dropped_trends.append(f"{metric} [{period}]: {trend}")
        if value:
            column = period_labels.get(period, period)
            # A period only earns a column once some metric has a value in it.
            if column and column not in period_order:
                period_order.append(column)
            previous = values_by_metric[metric].get(column)
            if previous and previous != value:
                conflicts.append(f"{metric} [{column}]: kept {previous!r}, discarded {value!r}")
            else:
                values_by_metric[metric][column] = value
    return {
        "values": values_by_metric,
        "notes": notes,
        "owners": owners,
        "metric_order": metric_order,
        "period_order": period_order,
        "dropped_trends": dropped_trends,
        "conflicts": conflicts,
    }


def build_wide_values(parsed: dict[str, Any], fallback_sprint: str) -> list[list[str]]:
    periods: list[str] = list(parsed["period_order"]) or [fallback_sprint]
    header = QA_PROCESS_FIXED_HEADER + periods

    owners = parsed["owners"]
    # Fall back to whatever owner the old sheet used most often - the schema
    # wants a named person per row, and a blank Owner column is what stops the
    # team from filling the sheet in.
    counts: dict[str, int] = {}
    for owner in owners.values():
        counts[owner] = counts.get(owner, 0) + 1
    default_owner = max(counts, key=lambda name: counts[name]) if counts else ""

    def metric_row(metric: str, template_note: str) -> list[str]:
        note = rewrite_note(parsed["notes"].get(metric) or template_note)
        row = [metric, note, owners.get(metric, default_owner)]
        by_period = parsed["values"].get(metric, {})
        row.extend(by_period.get(period, "") for period in periods)
        return row

    rows: list[list[str]] = [header]
    for label, metrics in QA_PROCESS_GROUPS:
        rows.append([label] + [""] * (len(header) - 1))
        rows.extend(metric_row(metric, note) for metric, note in metrics)

    canonical = set(canonical_metric_names())
    carried = [metric for metric in parsed["metric_order"] if metric not in canonical]
    if carried:
        rows.append([CARRIED_OVER_GROUP] + [""] * (len(header) - 1))
        rows.extend(metric_row(metric, "") for metric in carried)
    return rows


def refresh_notes_in_place(values: list[list[str]]) -> tuple[list[list[str]], list[str]]:
    """Apply NOTE_REWRITES to an already-wide sheet, leaving everything else alone."""
    rows = [list(row) for row in values]
    touched: list[str] = []
    for row in rows[1:]:
        if len(row) < 2 or not row[1]:
            continue
        updated = rewrite_note(row[1])
        if updated != row[1]:
            row[1] = updated
            touched.append(row[0])
    return rows, touched


def already_wide(values: list[list[str]]) -> bool:
    header = [cell.strip() for cell in values[0]] if values else []
    return header[: len(QA_PROCESS_FIXED_HEADER)] == QA_PROCESS_FIXED_HEADER


def write_wide_sheet(services: dict[str, Any], spreadsheet_id: str, values: list[list[str]]) -> None:
    sheets = services["sheets"]
    metadata = execute_with_backoff(sheets.spreadsheets().get(spreadsheetId=spreadsheet_id))
    title = metadata["sheets"][0]["properties"]["title"]
    execute_with_backoff(
        sheets.spreadsheets().values().clear(spreadsheetId=spreadsheet_id, range=f"'{title}'", body={})
    )
    execute_with_backoff(
        sheets.spreadsheets()
        .values()
        .update(
            spreadsheetId=spreadsheet_id,
            range=f"'{title}'!A1",
            valueInputOption="RAW",
            body={"values": values},
        )
    )


def summarize(project: str, parsed: dict[str, Any], rows: list[list[str]]) -> None:
    header = rows[0]
    filled = sum(1 for row in rows[1:] for cell in row[3:] if cell)
    carried = [metric for metric in parsed["metric_order"] if metric not in set(canonical_metric_names())]
    print(f"  columns: {len(header)} ({', '.join(header[3:])})")
    print(f"  rows: {len(rows) - 1} ({filled} value cells carried over)")
    if carried:
        print(f"  non-canonical rows kept: {', '.join(carried)}")
    missing_notes = [row[0] for row in rows[1:] if not is_group_label(row[0]) and not row[1]]
    if missing_notes:
        print(f"  rows still needing a Пояснение: {', '.join(missing_notes)}")
    for trend in parsed["dropped_trends"]:
        print(f"  Тренд text not carried over - {trend}")
    for conflict in parsed["conflicts"]:
        print(f"  merged-column conflict - {conflict}")


def main() -> int:
    ensure_utf8_stdout()
    args = parse_args()
    period_labels = parse_period_labels(args.period_labels)
    services = get_services(Path(args.credentials), Path(args.token))
    drive = services["drive"]

    m2_root = find_child_folder(drive, ROOT_FOLDER_ID, M2_ROOT_NAME)
    if not m2_root:
        raise SystemExit(f"{M2_ROOT_NAME} not found under the workspace root.")

    projects = args.projects or sorted(
        child["name"]
        for child in list_children(drive, m2_root["id"])
        if child["mimeType"].endswith("folder") and child["name"] not in NOT_A_PROJECT
    )

    print(f"{'Applying' if args.apply else 'Dry run'}: {DOCUMENT} wide-layout migration ({len(projects)} projects)")
    changed = skipped = 0
    for project in projects:
        project_folder = find_child_folder(drive, m2_root["id"], project)
        if not project_folder:
            print(f"{project}: project folder not found, skipped")
            continue
        sheet = find_document(drive, project_folder["id"], DOCUMENT, DOCUMENT, SHEET_MIME)
        if not sheet:
            print(f"{project}: no {DOCUMENT} Sheet, skipped")
            continue
        values = read_sheet_values(services, sheet["id"])
        print(f"{project}:")
        if already_wide(values):
            rows, touched = refresh_notes_in_place(values)
            if not touched:
                print("  already wide, nothing to change")
                skipped += 1
                continue
            print(f"  already wide; stale note wording in: {', '.join(touched)}")
            if args.apply:
                write_wide_sheet(services, sheet["id"], rows)
                reformat_sheet(services, sheet["id"], DOCUMENT)
                print(f"  notes updated: {sheet.get('webViewLink', sheet['id'])}")
            changed += 1
            continue
        parsed = parse_old_sheet(values, period_labels)
        rows = build_wide_values(parsed, args.sprint)
        summarize(project, parsed, rows)
        if args.apply:
            write_wide_sheet(services, sheet["id"], rows)
            # Widths/heights don't follow a values().update(), and this sheet
            # changed shape entirely - reformat it here instead of leaving the
            # whole workspace to a later format_all_sheets.py run.
            # Pass the document name so resolve_profile_for_tab finds the profile.
            reformat_sheet(services, sheet["id"], DOCUMENT)
            print(f"  written: {sheet.get('webViewLink', sheet['id'])}")
        changed += 1
    print(f"\n{changed} sheet(s) {'migrated' if args.apply else 'to migrate'}, {skipped} already wide")
    return 0


if __name__ == "__main__":
    sys.exit(main())
