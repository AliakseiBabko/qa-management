#!/usr/bin/env python3
"""Sync source-aligned M2 project files from extracted reference material into Google Sheets.

This script uses extracted DOCX/XLSX content from 90_Storage/_System/extracts/source and
updates the canonical project-based M2 workspace in Google Drive:

- 20_M2_Project_Management/<Project>/private/project_metrics
- 20_M2_Project_Management/<Project>/private/project_risk (2-tab workbook: Summary + Risk Items)
- 20_M2_Project_Management/<Project>/private/evidence_log
- 20_M2_Project_Management/<Project>/people/<Person>/shared/individual_metrics

It updates values in place when a Sheet already exists, which preserves the
existing formatting of the Google Sheet.

Development plans (project_development_plan, individual_development_plan) are
narrative documents, not tabular records, and are synced separately as Google
Docs by sync_m2_plans_to_docs.py.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from google_api_smoke_test import build_services, ensure_utf8_stdout, load_credentials, move_file_to_folder
from pipeline_common import reformat_sheet
from m2_workspace_layout import (
    PERSON_SHARED_ROLES,
    PROJECT_PRIVATE_ROLES,
    PROJECT_TEAM_SHARED_ROLES,
    ensure_document_folder,
    find_child_folder,
)
from generate_m2_outputs import (
    clean_markdown,
    generate_metrics,
    generate_project_risk,
    read_manifest,
)


ROOT_FOLDER_ID = "1QtIOTEd0fVi4eAhCo_I0xqDSIUiEITRc"
DATA_ROOT = Path(r"G:\My Drive\QA_Management")
M2_ROOT = DATA_ROOT / "20_M2_Project_Management"
TEMPLATES_ROOT = Path("Templates")

FOLDER_MIME_TYPE = "application/vnd.google-apps.folder"
SHEET_MIME_TYPE = "application/vnd.google-apps.spreadsheet"
IGNORED_PROJECTS = {
    "_root",
    "M2_project_development_plan",
    "M2_personal_development_plan",
    "M2_role_vision",
}


def parse_args() -> argparse.Namespace:
    today = dt.date.today().isoformat()
    parser = argparse.ArgumentParser(description="Sync source-aligned M2 Sheets from extracted source docs.")
    parser.add_argument(
        "--extract-root",
        default=rf"G:\My Drive\QA_Management\90_Storage\_System\extracts\source\{today}",
        help="Dated extraction folder produced by qa_source_extract.py.",
    )
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


def read_csv(path: Path) -> list[list[str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.reader(handle))


def read_template_header(filename: str) -> list[str]:
    rows = read_csv(TEMPLATES_ROOT / filename)
    if not rows:
        raise SystemExit(f"Template is empty: {filename}")
    return rows[0]


def q_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


def clean_person_name(value: str) -> str:
    return value.replace("ё", "е").replace("Ё", "Е").strip()


def resolve_existing_person_dir(project: str, person_name: str) -> str:
    people_dir = M2_ROOT / project / "people"
    if not people_dir.exists():
        return person_name
    normalized_target = clean_person_name(person_name)
    for child in people_dir.iterdir():
        if child.is_dir() and clean_person_name(child.name) == normalized_target:
            return child.name
    return person_name


def drive_query(drive: Any, query: str, fields: str = "id,name,mimeType,webViewLink") -> list[dict[str, Any]]:
    from pipeline_common import execute_with_backoff
    results = []
    page_token = None
    while True:
        request = drive.files().list(
            q=query,
            fields=f"nextPageToken,files({fields})",
            pageToken=page_token,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        )
        response = execute_with_backoff(request)
        results.extend(response.get("files", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            break
    return results


def find_or_create_folder(drive: Any, parent_id: str, name: str) -> dict[str, Any]:
    matches = drive_query(
        drive,
        (
            f"'{parent_id}' in parents and name = '{q_escape(name)}' and "
            f"mimeType = '{FOLDER_MIME_TYPE}' and trashed = false"
        ),
    )
    if matches:
        return matches[0]
    return (
        drive.files()
        .create(
            body={"name": name, "mimeType": FOLDER_MIME_TYPE, "parents": [parent_id]},
            fields="id,name,webViewLink",
            supportsAllDrives=True,
        )
        .execute()
    )


def find_sheet_in_folder(drive: Any, folder_id: str, title: str) -> dict[str, Any] | None:
    matches = drive_query(
        drive,
        (
            f"'{folder_id}' in parents and name = '{q_escape(title)}' and "
            f"mimeType = '{SHEET_MIME_TYPE}' and trashed = false"
        ),
        fields="id,name,mimeType,webViewLink",
    )
    if matches:
        return matches[0]

    # Read compatibility for the visibility layout. Callers that still pass
    # a project or person root can find migrated Sheets; creation code must
    # still resolve the canonical target explicitly with ensure_document_folder.
    nested_name = None
    if title in PROJECT_PRIVATE_ROLES:
        nested_name = "private"
    elif title in PROJECT_TEAM_SHARED_ROLES:
        nested_name = "team_shared"
    elif title in PERSON_SHARED_ROLES:
        nested_name = "shared"
    if nested_name:
        nested = find_child_folder(drive, folder_id, nested_name)
        if nested:
            nested_matches = drive_query(
                drive,
                (
                    f"'{nested['id']}' in parents and name = '{q_escape(title)}' and "
                    f"mimeType = '{SHEET_MIME_TYPE}' and trashed = false"
                ),
                fields="id,name,mimeType,webViewLink",
            )
            if len(nested_matches) > 1:
                raise RuntimeError(f"Duplicate Sheets named {title!r} in {nested_name}")
            return nested_matches[0] if nested_matches else None
    return None


def col_label(index: int) -> str:
    result = []
    while index > 0:
        index, remainder = divmod(index - 1, 26)
        result.append(chr(65 + remainder))
    return "".join(reversed(result))


def first_sheet_range(sheets: Any, spreadsheet_id: str) -> tuple[str, str]:
    metadata = sheets.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    first = metadata["sheets"][0]["properties"]
    title = first["title"]
    rows = max(first.get("gridProperties", {}).get("rowCount", 1000), 1000)
    cols = max(first.get("gridProperties", {}).get("columnCount", 26), 26)
    return title, f"'{title}'!A1:{col_label(cols)}{rows}"


def create_sheet(services: dict[str, Any], title: str, folder_id: str, values: list[list[str]]) -> dict[str, Any]:
    spreadsheet = (
        services["sheets"]
        .spreadsheets()
        .create(body={"properties": {"title": title}}, fields="spreadsheetId,spreadsheetUrl")
        .execute()
    )
    spreadsheet_id = spreadsheet["spreadsheetId"]
    move_file_to_folder(services["drive"], spreadsheet_id, folder_id)
    services["sheets"].spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range="A1",
        valueInputOption="RAW",
        body={"values": values},
    ).execute()
    reformat_sheet(services, spreadsheet_id, title)
    return services["drive"].files().get(
        fileId=spreadsheet_id,
        fields="id,name,webViewLink",
        supportsAllDrives=True,
    ).execute()


def upsert_sheet(services: dict[str, Any], folder_id: str, title: str, values: list[list[str]]) -> dict[str, Any]:
    existing = find_sheet_in_folder(services["drive"], folder_id, title)
    if not existing:
        return create_sheet(services, title, folder_id, values)

    sheet_title, clear_range = first_sheet_range(services["sheets"], existing["id"])
    services["sheets"].spreadsheets().values().clear(
        spreadsheetId=existing["id"],
        range=clear_range,
        body={},
    ).execute()
    services["sheets"].spreadsheets().values().update(
        spreadsheetId=existing["id"],
        range=f"'{sheet_title}'!A1",
        valueInputOption="RAW",
        body={"values": values},
    ).execute()
    reformat_sheet(services, existing["id"], title)
    return existing


def create_multi_tab_sheet(
    services: dict[str, Any],
    title: str,
    folder_id: str,
    tabs_data: dict[str, list[list[str]]],
) -> dict[str, Any]:
    """Create a new Google Sheet with multiple named tabs."""
    tab_names = list(tabs_data.keys())
    first_tab = tab_names[0] if tab_names else "Sheet1"

    body = {
        "properties": {"title": title},
        "sheets": [{"properties": {"title": first_tab}}],
    }
    spreadsheet = (
        services["sheets"]
        .spreadsheets()
        .create(body=body, fields="spreadsheetId,spreadsheetUrl")
        .execute()
    )
    spreadsheet_id = spreadsheet["spreadsheetId"]
    move_file_to_folder(services["drive"], spreadsheet_id, folder_id)

    if len(tab_names) > 1:
        add_requests = [
            {"addSheet": {"properties": {"title": t_name}}}
            for t_name in tab_names[1:]
        ]
        services["sheets"].spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={"requests": add_requests},
        ).execute()

    for t_name, vals in tabs_data.items():
        if vals:
            services["sheets"].spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=f"'{t_name}'!A1",
                valueInputOption="RAW",
                body={"values": vals},
            ).execute()

    reformat_sheet(services, spreadsheet_id, title)
    return services["drive"].files().get(
        fileId=spreadsheet_id,
        fields="id,name,webViewLink",
        supportsAllDrives=True,
    ).execute()


def upsert_multi_tab_sheet(
    services: dict[str, Any],
    folder_id: str,
    title: str,
    tabs_data: dict[str, list[list[str]]],
) -> dict[str, Any]:
    """Upsert a multi-tab Google Sheet, updating tabs in place while preserving extra tabs."""
    existing = find_sheet_in_folder(services["drive"], folder_id, title)
    if not existing:
        return create_multi_tab_sheet(services, title, folder_id, tabs_data)

    spreadsheet_id = existing["id"]
    metadata = services["sheets"].spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    existing_tabs = {s["properties"]["title"]: s["properties"] for s in metadata.get("sheets", [])}

    add_requests = []
    for t_name in tabs_data:
        if t_name not in existing_tabs:
            add_requests.append({"addSheet": {"properties": {"title": t_name}}})
    if add_requests:
        services["sheets"].spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={"requests": add_requests},
        ).execute()

    for t_name, vals in tabs_data.items():
        grid = existing_tabs.get(t_name, {}).get("gridProperties", {})
        rows = max(grid.get("rowCount", 1000), 1000)
        cols = max(grid.get("columnCount", 26), 26)
        clear_range = f"'{t_name}'!A1:{col_label(cols)}{rows}"
        try:
            services["sheets"].spreadsheets().values().clear(
                spreadsheetId=spreadsheet_id,
                range=clear_range,
                body={},
            ).execute()
        except Exception:
            pass

        if vals:
            services["sheets"].spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=f"'{t_name}'!A1",
                valueInputOption="RAW",
                body={"values": vals},
            ).execute()

    reformat_sheet(services, spreadsheet_id, title)
    return existing


def build_project_risk_tabs_data(
    summary_header: list[str],
    items_header: list[str],
    summary_rows: list[list[str]],
    items_rows: list[list[str]] | None = None,
) -> dict[str, list[list[str]]]:
    """Assemble 2-tab data structure for project_risk workbook."""
    return {
        "Summary": [summary_header, *summary_rows],
        "Risk Items": [items_header, *(items_rows or [])],
    }


def markdown_for(extract_root: Path, item: dict[str, str]) -> str:
    path = extract_root / item["extract_file"]
    return clean_markdown(path.read_text(encoding="utf-8"))


def parse_person_from_heading(markdown: str, fallback: str) -> str:
    for line in markdown.splitlines():
        if line.startswith("## ") and " - " in line and "план развития" in line.casefold():
            return clean_person_name(line[3:].split(" - ", 1)[0])
    return clean_person_name(fallback)


def group_project_risk_rows(extract_root: Path, manifest: list[dict[str, str]], snapshot_date: str) -> dict[str, list[list[str]]]:
    rows = generate_project_risk(extract_root, manifest, snapshot_date)
    grouped: dict[str, list[list[str]]] = {}
    for row in rows:
        if row:
            grouped[row[0]] = [row]
    return grouped


def group_individual_metric_rows(extract_root: Path, manifest: list[dict[str, str]], snapshot_date: str) -> dict[tuple[str, str], list[list[str]]]:
    raw = generate_metrics(extract_root, manifest, "individual_metrics", snapshot_date)
    grouped: dict[tuple[str, str], list[list[str]]] = {}
    for key, rows in raw.items():
        project, person = key.split("__", 1)
        grouped[(project, clean_person_name(person))] = rows
    return grouped


def project_source_entries(manifest: list[dict[str, str]]) -> dict[str, list[list[str]]]:
    entries: dict[str, list[list[str]]] = defaultdict(list)
    for item in manifest:
        if item["status"] != "ok" or item["project"] in IGNORED_PROJECTS:
            continue
        routed_to = {
            "project_development_plan": "project_development_plan",
            "project_metrics": "project_metrics",
            "project_risk": "project_risk",
            "individual_development_plan": "people/*/individual_development_plan",
            "individual_metrics": "people/*/individual_metrics",
            "project_summary": "project_risk + project_development_plan context",
            "workbook_source": "context only",
        }.get(item["document_role"], "context only")
        entries[item["project"]].append(
            [
                dt.date.today().isoformat(),
                item["source_file"],
                item["document_role"],
                item["project"],
                routed_to,
                "Synced from reference-material extract.",
            ]
        )
    return entries


def merge_evidence(existing: list[list[str]], new_rows: list[list[str]]) -> list[list[str]]:
    header = ["date", "source", "source_type", "project", "routed_to", "notes"]
    body = existing[1:] if existing else []
    seen = {(tuple(row[:5])) for row in body if row}
    merged = [header, *body]
    for row in new_rows:
        key = tuple(row[:5])
        if key in seen:
            continue
        merged.append(row)
        seen.add(key)
    return merged


def merge_individual_metrics(existing: list[list[str]], new_rows: list[list[str]], header: list[str]) -> list[list[str]]:
    # individual_metrics is an append-only snapshot history, not a sheet that
    # gets overwritten each sync: Тренд is only meaningful if prior periods
    # are kept around to compare against. Dedup on (Проект, Сотрудник,
    # Период, Метрика) so re-running for the same day updates that day's row
    # instead of duplicating it, while a new day appends fresh rows.
    body = existing[1:] if existing else []
    seen = {(row[0], row[1], row[2], row[4]): idx for idx, row in enumerate(body) if len(row) > 4}
    merged = list(body)
    for row in new_rows:
        key = (row[0], row[1], row[2], row[4])
        if key in seen:
            merged[seen[key]] = row
        else:
            seen[key] = len(merged)
            merged.append(row)
    return [header, *merged]


def read_sheet_values(services: dict[str, Any], spreadsheet_id: str) -> list[list[str]]:
    from pipeline_common import execute_with_backoff
    metadata = execute_with_backoff(services["sheets"].spreadsheets().get(spreadsheetId=spreadsheet_id))
    title = metadata["sheets"][0]["properties"]["title"]
    res = execute_with_backoff(
        services["sheets"]
        .spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range=f"'{title}'")
    )
    return res.get("values", [])


def ensure_project_local_dirs(project: str, person_names: set[str]) -> None:
    project_root = M2_ROOT / project
    for folder in ["people", "status_reports"]:
        (project_root / folder).mkdir(parents=True, exist_ok=True)
    for person in person_names:
        folder_name = resolve_existing_person_dir(project, person)
        (project_root / "people" / folder_name).mkdir(parents=True, exist_ok=True)


def main() -> int:
    ensure_utf8_stdout()
    args = parse_args()
    extract_root = Path(args.extract_root)
    if not (extract_root / "manifest.csv").exists():
        raise SystemExit(f"Missing manifest.csv under {extract_root}")

    manifest = read_manifest(extract_root)
    manifest = [item for item in manifest if item["project"] not in IGNORED_PROJECTS]
    snapshot_date = dt.date.today().isoformat()

    project_metrics_header = read_template_header("метрики_проекта_qa.csv")
    project_risk_summary_header = read_template_header("светофор_рисков_проекта.csv")
    project_risk_items_header = read_template_header("project_risk_items.csv")
    individual_metrics_header = read_template_header("метрики_qa_по_проекту.csv")
    evidence_header = ["date", "source", "source_type", "project", "routed_to", "notes"]

    project_metrics = generate_metrics(extract_root, manifest, "project_metrics", snapshot_date)
    project_risks = group_project_risk_rows(extract_root, manifest, snapshot_date)
    individual_metrics = group_individual_metric_rows(extract_root, manifest, snapshot_date)
    evidence_entries = project_source_entries(manifest)

    project_people: dict[str, set[str]] = defaultdict(set)
    for item in manifest:
        if item["status"] != "ok" or item["document_role"] != "individual_development_plan":
            continue
        person = parse_person_from_heading(markdown_for(extract_root, item), Path(item["source_file"]).stem)
        project_people[item["project"]].add(person)
    for project, person in individual_metrics:
        project_people[project].add(person)

    creds = load_credentials(Path(args.credentials), Path(args.token))
    services = build_services(creds)
    drive = services["drive"]

    m2_folder = find_or_create_folder(drive, ROOT_FOLDER_ID, "20_M2_Project_Management")
    results: list[str] = []

    for project in sorted({*project_metrics, *project_risks, *project_people}):
        ensure_project_local_dirs(project, project_people.get(project, set()))
        project_folder = find_or_create_folder(drive, m2_folder["id"], project)

        # project_metrics and project_risk both require real M2 synthesis now (a
        # single coherent judgment per row/column), not the mechanical
        # label:value bullet extraction generate_metrics()/generate_project_risk()
        # do. upsert_sheet() clears and overwrites the whole sheet, so once a real
        # curated version exists, never touch it here — only bootstrap a brand-new
        # project that doesn't have one yet, and even then this is a rough first
        # pass to build on, not a finished document.
        private_folder = ensure_document_folder(drive, project_folder["id"], "project_metrics")
        if project in project_metrics:
            if find_sheet_in_folder(drive, project_folder["id"], "project_metrics"):
                results.append(f"{project}: project_metrics already exists, left untouched (needs M2 synthesis, not auto-sync)")
            else:
                meta = upsert_sheet(
                    services,
                    private_folder["id"],
                    "project_metrics",
                    [project_metrics_header, *project_metrics[project]],
                )
                results.append(f"{project}: {meta['name']} (rough first pass — still needs M2 synthesis)")

        if project in project_risks:
            if find_sheet_in_folder(drive, project_folder["id"], "project_risk"):
                results.append(f"{project}: project_risk already exists, left untouched (needs M2 synthesis, not auto-sync)")
            else:
                tabs_data = build_project_risk_tabs_data(
                    summary_header=project_risk_summary_header,
                    items_header=project_risk_items_header,
                    summary_rows=project_risks[project],
                )
                meta = upsert_multi_tab_sheet(
                    services,
                    private_folder["id"],
                    "project_risk",
                    tabs_data,
                )
                results.append(f"{project}: {meta['name']} (multi-tab 2-sheet rough first pass — still needs M2 synthesis)")

        evidence_sheet = find_sheet_in_folder(drive, project_folder["id"], "evidence_log")
        existing_evidence = read_sheet_values(services, evidence_sheet["id"]) if evidence_sheet else [evidence_header]
        merged_evidence = merge_evidence(existing_evidence, evidence_entries.get(project, []))
        upsert_sheet(services, private_folder["id"], "evidence_log", merged_evidence)

        for person in sorted(project_people.get(project, set())):
            folder_name = resolve_existing_person_dir(project, person)
            person_folder = ensure_document_folder(
                drive, project_folder["id"], "individual_metrics", folder_name
            )
            key = (project, person)

            metrics_sheet = find_sheet_in_folder(drive, person_folder["id"], "individual_metrics")
            existing_metrics = read_sheet_values(services, metrics_sheet["id"]) if metrics_sheet else [individual_metrics_header]
            merged_metrics = merge_individual_metrics(existing_metrics, individual_metrics.get(key, []), individual_metrics_header)
            meta = upsert_sheet(
                services,
                person_folder["id"],
                "individual_metrics",
                merged_metrics,
            )
            results.append(f"{project}/{folder_name}: {meta['name']}")

    sys.stdout.buffer.write(("\n".join(results) + "\n").encode("utf-8", errors="replace"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
