#!/usr/bin/env python3
"""Sync source-aligned M2 project files from 00_Source_Docs into Google Sheets.

This script uses extracted DOCX/XLSX content from 80_Exports/source_extracts and
updates the canonical project-based M2 workspace in Google Drive:

- 20_M2_Project_Management/<Project>/project_metrics
- 20_M2_Project_Management/<Project>/project_risk
- 20_M2_Project_Management/<Project>/evidence_log
- 20_M2_Project_Management/<Project>/people/<Person>/individual_metrics

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

from google_api_smoke_test import build_services, load_credentials, move_file_to_folder
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
        default=rf"G:\My Drive\QA_Management\80_Exports\source_extracts\{today}",
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
    value = value.strip().strip("_").strip()
    value = re.sub(r"^(План развития|Метрики)\s+", "", value, flags=re.IGNORECASE)
    value = re.sub(r"\s*-\s*план развития.*$", "", value, flags=re.IGNORECASE)
    value = re.sub(r"\s*-\s*метрики.*$", "", value, flags=re.IGNORECASE)
    value = re.sub(r"\s+", " ", value)
    return value.strip(" -_")


def normalize_name_tokens(value: str) -> str:
    words = re.findall(r"[A-Za-zА-Яа-яЁё0-9]+", value.casefold())
    return " ".join(sorted(words))


def resolve_existing_person_dir(project: str, person: str) -> str:
    people_root = M2_ROOT / project / "people"
    people_root.mkdir(parents=True, exist_ok=True)
    wanted = normalize_name_tokens(person)
    for child in people_root.iterdir():
        if child.is_dir() and normalize_name_tokens(child.name) == wanted:
            return child.name
    return person


def drive_query(drive: Any, query: str, fields: str = "id,name,mimeType,parents,webViewLink") -> list[dict[str, Any]]:
    files: list[dict[str, Any]] = []
    token = None
    while True:
        response = (
            drive.files()
            .list(
                q=query,
                fields=f"nextPageToken,files({fields})",
                pageSize=1000,
                pageToken=token,
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
            )
            .execute()
        )
        files.extend(response.get("files", []))
        token = response.get("nextPageToken")
        if not token:
            return files


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
    return matches[0] if matches else None


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
    return existing


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
                "Synced from 00_Source_Docs extract.",
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
    metadata = services["sheets"].spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    title = metadata["sheets"][0]["properties"]["title"]
    return (
        services["sheets"]
        .spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range=f"'{title}'")
        .execute()
        .get("values", [])
    )


def ensure_project_local_dirs(project: str, person_names: set[str]) -> None:
    project_root = M2_ROOT / project
    for folder in ["people", "status_reports"]:
        (project_root / folder).mkdir(parents=True, exist_ok=True)
    for person in person_names:
        folder_name = resolve_existing_person_dir(project, person)
        (project_root / "people" / folder_name).mkdir(parents=True, exist_ok=True)


def main() -> int:
    args = parse_args()
    extract_root = Path(args.extract_root)
    if not (extract_root / "manifest.csv").exists():
        raise SystemExit(f"Missing manifest.csv under {extract_root}")

    manifest = read_manifest(extract_root)
    manifest = [item for item in manifest if item["project"] not in IGNORED_PROJECTS]
    snapshot_date = dt.date.today().isoformat()

    project_metrics_header = read_template_header("метрики_проекта_qa.csv")
    project_risk_header = read_template_header("светофор_рисков_проекта.csv")
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

        if project in project_metrics:
            meta = upsert_sheet(
                services,
                project_folder["id"],
                "project_metrics",
                [project_metrics_header, *project_metrics[project]],
            )
            results.append(f"{project}: {meta['name']}")

        if project in project_risks:
            meta = upsert_sheet(
                services,
                project_folder["id"],
                "project_risk",
                [project_risk_header, *project_risks[project]],
            )
            results.append(f"{project}: {meta['name']}")

        evidence_sheet = find_sheet_in_folder(drive, project_folder["id"], "evidence_log")
        existing_evidence = read_sheet_values(services, evidence_sheet["id"]) if evidence_sheet else [evidence_header]
        merged_evidence = merge_evidence(existing_evidence, evidence_entries.get(project, []))
        upsert_sheet(services, project_folder["id"], "evidence_log", merged_evidence)

        people_folder = find_or_create_folder(drive, project_folder["id"], "people")
        for person in sorted(project_people.get(project, set())):
            folder_name = resolve_existing_person_dir(project, person)
            person_folder = find_or_create_folder(drive, people_folder["id"], folder_name)
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
