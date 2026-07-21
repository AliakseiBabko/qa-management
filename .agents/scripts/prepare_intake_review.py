"""Intake assistant: find new/changed source files, extract and classify them,
log them to evidence_log, and produce a review bundle for M2 to read.

Scope, deliberately stopped short of judgment (see m2-role-rules.md,
Project-Level Rollups and Pipeline Architecture):

- scans 00_Inbox recursively for files not yet seen
- reuses an existing extraction by sha256 (checks every
  90_Storage/_System/extracts/source/*/manifest.csv) instead of re-extracting
- classifies each new file by project (folder-based under
  03_Source_Documents, filename-matched against _project_registry /
  _people_registry under 01/02) using substring matching only — genuinely
  ambiguous files are left unclassified, not guessed
- appends evidence_log rows (mechanical trace, not a judgment call)
- writes a local review bundle markdown file summarizing what's new

It does NOT touch project_risk, project_development_plan, project_metrics,
qa_process_metrics, m2_input, or individual documents. Read the review
bundle, then start the normal preliminary-analysis round in m2_input for any
project the bundle flags — that step still needs a human/conversational
pass, this script only gets the raw material ready for it.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))
from qa_source_extract import docx_to_markdown, extract_xlsx, safe_name, sha256_file
from google_api_smoke_test import build_services, ensure_utf8_stdout, load_credentials
from pipeline_common import get_people_registry_sheet, reformat_sheet
from sync_m2_source_docs_to_sheets import (
    ROOT_FOLDER_ID,
    find_or_create_folder,
    find_sheet_in_folder,
    merge_evidence,
    read_sheet_values,
)

DEFAULT_ROOT = Path(r"G:\My Drive\QA_Management")
INBOX_ROOT = "00_Inbox"
EXTRACT_ROOT = DEFAULT_ROOT / "90_Storage" / "_System" / "extracts" / "source"
REVIEW_ROOT = DEFAULT_ROOT / "90_Storage" / "_System" / "reviews" / "intake"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(DEFAULT_ROOT))
    parser.add_argument("--credentials", default=".local/google/credentials.json")
    parser.add_argument("--token", default=".local/google/token.json")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Scan and classify only; do not write evidence_log or the review bundle.",
    )
    return parser.parse_args()


def known_sha256_map(extract_root: Path) -> dict[str, dict[str, str]]:
    known: dict[str, dict[str, str]] = {}
    if not extract_root.exists():
        return known
    for manifest_path in extract_root.glob("*/manifest.csv"):
        with manifest_path.open(encoding="utf-8-sig") as fh:
            for row in csv.DictReader(fh):
                if row.get("sha256"):
                    known[row["sha256"]] = {
                        "extract_file": str(manifest_path.parent / row["extract_file"]) if row.get("extract_file") else "",
                        "manifest": str(manifest_path),
                    }
    return known


def source_tail(path_str: str) -> str:
    # Compare on the last two path segments (project-folder/filename) so a
    # folder reorg (for example, a historical category directory landing
    # and <Project>) doesn't make an already-logged file look new just
    # because its full relative path changed.
    parts = Path(path_str.replace("\\", "/")).parts
    return "/".join(parts[-2:]) if len(parts) >= 2 else path_str


def already_logged_sources(evidence_rows: list[list[str]]) -> set[str]:
    return {source_tail(row[1]) for row in evidence_rows[1:] if len(row) > 1}


def load_known_names(services: dict[str, Any]) -> tuple[list[str], dict[str, list[str]]]:
    drive = services["drive"]
    m2_root = find_or_create_folder(drive, ROOT_FOLDER_ID, "20_M2_Project_Management")
    projects = [
        f["name"]
        for f in drive.files()
        .list(
            q=f"'{m2_root['id']}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false",
            fields="files(name)",
        )
        .execute()
        .get("files", [])
        if not f["name"].startswith("_")
    ]

    person_to_projects: dict[str, list[str]] = {}
    people_sheet = get_people_registry_sheet(services)
    if people_sheet:
        rows = read_sheet_values(services, people_sheet["id"])
        project_col = rows[0].index("Project(s)") if rows and "Project(s)" in rows[0] else 8
        for row in rows[1:]:
            if len(row) < 2:
                continue
            names = [n for n in (row[0], row[1]) if n]
            person_projects = [p.strip() for p in row[project_col].split(",")] if len(row) > project_col and row[project_col] else []
            for name in names:
                if name:
                    person_to_projects[name] = person_projects
    return projects, person_to_projects


def classify(filename: str, projects: list[str], person_to_projects: dict[str, list[str]]) -> tuple[str, str]:
    lowered = filename.casefold()
    for project in projects:
        if project.casefold() in lowered:
            return project, f"filename matches project '{project}'"
    for person, person_projects in person_to_projects.items():
        if person.casefold() in lowered:
            if person_projects:
                return person_projects[0], f"filename matches person '{person}' -> project '{person_projects[0]}'"
            return "", f"filename matches person '{person}', but they have no project(s) on record"
    return "", "no project or known person name found in filename"


def extract_office_file(path: Path, relative: Path, out_dir: Path) -> str:
    role = "unknown"
    out_dir.mkdir(parents=True, exist_ok=True)
    if path.suffix.casefold() == ".docx":
        out_file = out_dir / "docx" / f"{safe_name(path.stem)}.md"
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(docx_to_markdown(path, str(relative), role), encoding="utf-8")
        return str(out_file)
    if path.suffix.casefold() == ".xlsx":
        xlsx_out = out_dir / "xlsx" / safe_name(path.stem)
        extract_xlsx(path, xlsx_out, str(relative), role)
        return str(xlsx_out / f"{safe_name(path.stem)}.json")
    return ""


def main() -> int:
    ensure_utf8_stdout()
    args = parse_args()
    root = Path(args.root)
    today = dt.date.today().isoformat()

    creds = load_credentials(Path(args.credentials), Path(args.token))
    services = build_services(creds)
    drive = services["drive"]

    projects, person_to_projects = load_known_names(services)
    known_hashes = known_sha256_map(EXTRACT_ROOT)

    m2_root = find_or_create_folder(drive, ROOT_FOLDER_ID, "20_M2_Project_Management")
    evidence_by_project: dict[str, list[list[str]]] = {}
    for project in projects:
        pf = find_or_create_folder(drive, m2_root["id"], project)
        sheet = find_sheet_in_folder(drive, pf["id"], "evidence_log")
        evidence_by_project[project] = read_sheet_values(services, sheet["id"]) if sheet else [
            ["date", "source", "source_type", "project", "routed_to", "notes"]
        ]
    all_logged_sources = {
        src for rows in evidence_by_project.values() for src in already_logged_sources(rows)
    }

    found: list[dict[str, str]] = []

    inbox_path = root / INBOX_ROOT
    if inbox_path.exists():
        for path in sorted(inbox_path.rglob("*")):
            if not path.is_file():
                continue
            relative = path.relative_to(root)
            if source_tail(str(relative)) in all_logged_sources:
                continue
            project, reason = classify(path.name, projects, person_to_projects)
            extract_file = ""
            if path.suffix.casefold() in (".docx", ".xlsx"):
                h = sha256_file(path)
                if h in known_hashes:
                    extract_file = known_hashes[h]["extract_file"]
                else:
                    out_dir = EXTRACT_ROOT / today / safe_name(project or "_unclassified")
                    extract_file = extract_office_file(path, relative, out_dir)
            source_type = "strategy_chat" if "_strategy" in path.stem.casefold() else "source_document"
            found.append({
                "path": str(relative),
                "source_type": source_type,
                "project": project,
                "reason": reason,
                "extract_file": extract_file,
            })

    if not found:
        print("No new source files found.")
        return 0

    print(f"Found {len(found)} new file(s).")
    if args.dry_run:
        for item in found:
            print(f"  [{item['project'] or 'UNCLASSIFIED'}] {item['path']} — {item['reason']}")
        return 0

    for item in found:
        project = item["project"]
        row = [today, item["path"], item["source_type"], project or "UNCLASSIFIED", "pending M2 review", item["reason"]]
        if project in evidence_by_project:
            evidence_by_project[project] = merge_evidence(evidence_by_project[project], [row])
        else:
            evidence_by_project.setdefault("_unclassified", [["date", "source", "source_type", "project", "routed_to", "notes"]])
            evidence_by_project["_unclassified"] = merge_evidence(evidence_by_project["_unclassified"], [row])

    logged_projects: list[str] = []
    for project in projects:
        pf = find_or_create_folder(drive, m2_root["id"], project)
        sheet = find_sheet_in_folder(drive, pf["id"], "evidence_log")
        if sheet and any(item["project"] == project for item in found):
            services["sheets"].spreadsheets().values().clear(
                spreadsheetId=sheet["id"], range="A1:F5000"
            ).execute()
            services["sheets"].spreadsheets().values().update(
                spreadsheetId=sheet["id"], range="A1", valueInputOption="RAW",
                body={"values": evidence_by_project[project]},
            ).execute()
            reformat_sheet(services, sheet["id"], "evidence_log")
            logged_projects.append(project)

    REVIEW_ROOT.mkdir(parents=True, exist_ok=True)
    bundle_path = REVIEW_ROOT / f"{today}.md"
    lines = [f"# Intake review — {today}", ""]
    by_project: dict[str, list[dict[str, str]]] = {}
    for item in found:
        by_project.setdefault(item["project"] or "UNCLASSIFIED", []).append(item)
    for project, items in sorted(by_project.items()):
        lines.append(f"## {project}")
        for item in items:
            extract_note = f" — extract: `{item['extract_file']}`" if item["extract_file"] else ""
            lines.append(f"- `{item['path']}` ({item['source_type']}, {item['reason']}){extract_note}")
        lines.append("")
    lines.append(
        "Next step: read the flagged files above (and their extracts, where present), then — "
        "if they change the picture for a project — start a new preliminary-analysis round in "
        "that project's `m2_input` (see m2-role-rules.md, Project-Level Rollups). This script "
        "does not write m2_input, project_risk, project_development_plan, project_metrics, or "
        "status reports; UNCLASSIFIED items need manual routing before anything else happens "
        "with them."
    )
    bundle_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Review bundle: {bundle_path}")
    if logged_projects:
        print(f"evidence_log updated for: {', '.join(sorted(logged_projects))}")
    if "UNCLASSIFIED" in by_project:
        print(
            f"{len(by_project['UNCLASSIFIED'])} file(s) UNCLASSIFIED — not written to any "
            "evidence_log, needs manual routing (see review bundle)."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
