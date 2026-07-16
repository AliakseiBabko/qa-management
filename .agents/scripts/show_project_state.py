"""Read-only dump of a project's (or the workspace registries') current
canonical documents - the thing every conversational M2 update needs to look
at first, before touching anything.

Prints, for --project <Name>:
- project_metrics, project_risk, evidence_log, qa_process_metrics,
  action_items (Sheets)
- project_development_plan, m2_input (Docs)
- for every person under people/<Person>/: individual_metrics,
  individual_metrics_internal (Sheets), individual_development_plan (Doc)

Prints, for --registries:
- _m2_people_registry, _project_registry, _timeline (Sheets)

--summary (alone, or with --project) skips the full dump and prints a cheap
one-liner per project instead: People count (from _project_registry),
current risk level + snapshot date (from project_risk's latest row),
evidence_log's most recent entry date, whether the project's m2_input
has a round still waiting on an answer, and open action_items counts (overdue
vs due within 7 days, from today's date) so nothing gets missed without
opening the full timeline. Meant for triage before pulling a full project's
documents - e.g. deciding whether a strategy chat that reads as mostly
non-QA content is worth a full dump at all.

This makes no writes and creates nothing - unlike find_or_create_folder (used
by the sync scripts), a missing project/folder here is reported as missing,
not created, so a typo'd --project name can't leave a stray empty folder
behind.
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))
from google_api_smoke_test import ensure_utf8_stdout
from pipeline_common import get_last_round_status, get_pending_round_questions, get_services
from scaffold_project_dashboard import EMPTY_ROUND_PLACEHOLDER
from sync_m2_source_docs_to_sheets import ROOT_FOLDER_ID, drive_query, find_sheet_in_folder, q_escape, read_sheet_values

FOLDER_MIME = "application/vnd.google-apps.folder"
DOC_MIME = "application/vnd.google-apps.document"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--project", help="Project name under 20_M2_Project_Management, e.g. <ProjectName>")
    parser.add_argument("--registries", action="store_true", help="Also/instead dump _m2_people_registry and _project_registry")
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Print a one-liner per project (People count, risk level, last evidence_log date) instead of "
        "a full dump. Combine with --project to summarize just that one.",
    )
    parser.add_argument(
        "--evidence-tail",
        type=int,
        default=10,
        help="Show only the last N evidence_log rows in the full dump (default 10; header row doesn't "
        "count). evidence_log grows without bound by design (append-only audit trail) and reading it in "
        "full every time gets expensive as a project accumulates history. Pass 0 for the full log.",
    )
    parser.add_argument("--credentials", default=".local/google/credentials.json")
    parser.add_argument("--token", default=".local/google/token.json")
    return parser.parse_args()


def find_folder(drive: Any, parent_id: str, name: str) -> dict[str, Any] | None:
    matches = drive_query(
        drive,
        f"'{parent_id}' in parents and name = '{q_escape(name)}' and mimeType = '{FOLDER_MIME}' and trashed = false",
        fields="id,name",
    )
    return matches[0] if matches else None


def dump_sheet(services: dict[str, Any], folder_id: str, title: str, tail: int = 0) -> None:
    sheet = find_sheet_in_folder(services["drive"], folder_id, title)
    if not sheet:
        print(f"--- {title}: not found ---")
        return
    rows = read_sheet_values(services, sheet["id"])
    header, body = (rows[0], rows[1:]) if rows else ([], [])
    omitted = 0
    if tail and len(body) > tail:
        omitted = len(body) - tail
        body = body[-tail:]
    suffix = f" (showing last {tail} of {tail + omitted} rows; pass --evidence-tail 0 for all)" if omitted else ""
    print(f"--- {title} ({sheet['id']}){suffix} ---")
    if header:
        print(header)
    for row in body:
        print(row)
    print()


def find_doc(services: dict[str, Any], folder_id: str, title: str) -> dict[str, Any] | None:
    matches = drive_query(
        services["drive"],
        f"'{folder_id}' in parents and name = '{q_escape(title)}' and mimeType = '{DOC_MIME}' and trashed = false",
        fields="id,name",
    )
    return matches[0] if matches else None


def dump_doc(services: dict[str, Any], folder_id: str, title: str) -> None:
    match = find_doc(services, folder_id, title)
    if not match:
        print(f"--- {title} (doc): not found ---")
        return
    doc = services["docs"].documents().get(documentId=match["id"]).execute()
    print(f"--- {title} (doc, {match['id']}) ---")
    text = []
    for element in doc["body"]["content"]:
        if "paragraph" in element:
            for run in element["paragraph"]["elements"]:
                if "textRun" in run:
                    text.append(run["textRun"]["content"])
    print("".join(text))
    print()


def dump_project(services: dict[str, Any], m2_root_id: str, project: str, evidence_tail: int = 0) -> None:
    project_folder = find_folder(services["drive"], m2_root_id, project)
    if not project_folder:
        print(f"No such project folder: {project}")
        return

    print(f"===== {project}: project_metrics =====")
    dump_sheet(services, project_folder["id"], "project_metrics")
    print(f"===== {project}: project_risk =====")
    dump_sheet(services, project_folder["id"], "project_risk")
    print(f"===== {project}: evidence_log =====")
    dump_sheet(services, project_folder["id"], "evidence_log", tail=evidence_tail)
    print(f"===== {project}: qa_process_metrics =====")
    dump_sheet(services, project_folder["id"], "qa_process_metrics")
    print(f"===== {project}: action_items =====")
    dump_sheet(services, project_folder["id"], "action_items")
    print(f"===== {project}: project_development_plan =====")
    dump_doc(services, project_folder["id"], "project_development_plan")

    m2_input_folder = find_folder(services["drive"], project_folder["id"], "m2_input")
    if m2_input_folder:
        print(f"===== {project}: m2_input =====")
        dump_doc(services, m2_input_folder["id"], "m2_input")

    people_folder = find_folder(services["drive"], project_folder["id"], "people")
    if not people_folder:
        return
    print(f"===== {project}: people =====")
    for person in drive_query(
        services["drive"],
        f"'{people_folder['id']}' in parents and mimeType = '{FOLDER_MIME}' and trashed = false",
        fields="id,name",
    ):
        print(f"--- person: {person['name']} ---")
        dump_sheet(services, person["id"], "individual_metrics")
        dump_sheet(services, person["id"], "individual_metrics_internal")
        dump_doc(services, person["id"], "individual_development_plan")


def project_people_counts(services: dict[str, Any], m2_root_id: str) -> dict[str, str]:
    """Project -> People cell, straight from _project_registry (already-curated, cheap to read once)."""
    sheet = find_sheet_in_folder(services["drive"], m2_root_id, "_project_registry")
    if not sheet:
        return {}
    rows = read_sheet_values(services, sheet["id"])
    return {row[0]: row[1] if len(row) > 1 else "" for row in rows[1:] if row}


def summarize_project(services: dict[str, Any], m2_root_id: str, project: str, people_cell: str) -> str:
    project_folder = find_folder(services["drive"], m2_root_id, project)
    if not project_folder:
        return f"{project}: folder not found"

    qa_count = len([p for p in people_cell.split(",") if p.strip()]) if people_cell else 0

    risk_level, risk_date = "н/д", ""
    risk_sheet = find_sheet_in_folder(services["drive"], project_folder["id"], "project_risk")
    if risk_sheet:
        rows = read_sheet_values(services, risk_sheet["id"])
        if len(rows) > 1:
            last = rows[-1]
            risk_date = last[1] if len(last) > 1 else ""
            risk_level = last[2] if len(last) > 2 and last[2] else "н/д"

    last_touched = "н/д"
    evidence_sheet = find_sheet_in_folder(services["drive"], project_folder["id"], "evidence_log")
    if evidence_sheet:
        rows = read_sheet_values(services, evidence_sheet["id"])
        dates = [row[0] for row in rows[1:] if row and row[0]]
        if dates:
            last_touched = max(dates)

    m2_input_note = ""
    m2_input_folder = find_folder(services["drive"], project_folder["id"], "m2_input")
    if m2_input_folder:
        m2_input_doc = find_doc(services, m2_input_folder["id"], "m2_input")
        if m2_input_doc:
            status = get_last_round_status(services["docs"], m2_input_doc["id"])
            if status["pending"]:
                pending_text = get_pending_round_questions(services["docs"], m2_input_doc["id"])
                if pending_text.strip() == EMPTY_ROUND_PLACEHOLDER:
                    m2_input_note = f", m2_input: пустой раунд-заглушка ({status['round_date']})"
                else:
                    m2_input_note = f", m2_input: раунд {status['round_date']} ожидает ответа M2"
            elif status["pending"] is False:
                m2_input_note = f", m2_input: раунд {status['round_date']} отвечен"

    action_items_note = ""
    action_items_sheet = find_sheet_in_folder(services["drive"], project_folder["id"], "action_items")
    if action_items_sheet:
        rows = read_sheet_values(services, action_items_sheet["id"])
        today = dt.date.today().isoformat()
        overdue = due_soon = 0
        for row in rows[1:]:
            if len(row) <= 4 or row[4].strip() != "Открыто":
                continue
            due = row[1] if len(row) > 1 else ""
            if due and due < today:
                overdue += 1
            elif due and due <= (dt.date.today() + dt.timedelta(days=7)).isoformat():
                due_soon += 1
        if overdue or due_soon:
            action_items_note = f", action_items: {overdue} просрочено, {due_soon} в ближайшие 7 дн."

    return (
        f"{project}: {qa_count} чел. (People), риск={risk_level} (на {risk_date or 'н/д'}), "
        f"evidence_log обновлён {last_touched}{m2_input_note}{action_items_note}"
    )


def main() -> int:
    ensure_utf8_stdout()
    args = parse_args()
    if not args.project and not args.registries and not args.summary:
        print("Nothing to do: pass --project <Name>, --registries, and/or --summary.")
        return 1

    services = get_services(args.credentials, args.token)
    drive = services["drive"]
    m2_root = find_folder(drive, ROOT_FOLDER_ID, "20_M2_Project_Management")
    if not m2_root:
        print("20_M2_Project_Management folder not found under the workspace root.")
        return 1

    if args.summary:
        people_by_project = project_people_counts(services, m2_root["id"])
        projects = [args.project] if args.project else sorted(people_by_project)
        for project in projects:
            print(summarize_project(services, m2_root["id"], project, people_by_project.get(project, "")))
        return 0

    if args.registries:
        print("===== _m2_people_registry =====")
        dump_sheet(services, m2_root["id"], "_m2_people_registry")
        print("===== _project_registry =====")
        dump_sheet(services, m2_root["id"], "_project_registry")
        print("===== _timeline =====")
        dump_sheet(services, m2_root["id"], "_timeline")

    if args.project:
        dump_project(services, m2_root["id"], args.project, evidence_tail=args.evidence_tail)

    return 0


if __name__ == "__main__":
    sys.exit(main())
