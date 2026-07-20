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
- _people_registry, _project_registry, _timeline (Sheets)

Targeted queries:
Use --document <Name> (can be passed multiple times) along with --since <Date>
and --limit <N> to fetch specific documents with a strict JSON contract.
This enforces read-only semantics (no folder/sheet/doc creation).
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
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

# Scope mapping
PROJECT_DOCS = {"project_metrics", "project_risk", "evidence_log", "qa_process_metrics", "action_items", "project_development_plan", "m2_input", "m2_monthly_report"}
PERSON_DOCS = {"individual_metrics", "individual_metrics_internal", "individual_development_plan", "m1_people_1to1", "m2_people_1to1"}
REGISTRY_DOCS = {"_people_registry", "_project_registry", "_timeline", "_m1_timeline"}

# Date column mapping for --since filtering
DATE_COLS = {
    "evidence_log": 0,
    "action_items": 1,
    "project_risk": 1,
    "_timeline": 0,
    "_m1_timeline": 0
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--project", help="Project name under 20_M2_Project_Management, e.g. <ProjectName>")
    parser.add_argument("--registries", action="store_true", help="Also/instead dump _people_registry and _project_registry")
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
        help="Show only the last N evidence_log rows in the full dump (default 10). Pass 0 for the full log.",
    )

    # New phase 3 targeted reads
    parser.add_argument("--document", action="append", default=[], help="Specific document names to fetch")
    parser.add_argument("--person", help="Person name for individual document scope")
    parser.add_argument("--since", help="Filter rows >= this YYYY-MM-DD date")
    parser.add_argument("--limit", type=int, help="Limit returned rows/paragraphs. Defaults to 20 when --document is used.")
    parser.add_argument("--json", action="store_true", help="Output strict JSON envelope")

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


def read_doc_paragraphs(services: dict[str, Any], doc_id: str) -> list[str]:
    doc = services["docs"].documents().get(documentId=doc_id).execute()
    text = []
    for element in doc.get("body", {}).get("content", []):
        if "paragraph" in element:
            for run in element["paragraph"].get("elements", []):
                if "textRun" in run:
                    text.append(run["textRun"]["content"])
    return text


def dump_sheet(services: dict[str, Any], folder_id: str, title: str, tail: int = 0) -> None:
    sheet = find_sheet_in_folder(services["drive"], folder_id, title)
    if not sheet:
        print(f"--- {title}: not found ---", file=sys.stdout)
        return
    rows = read_sheet_values(services, sheet["id"])
    header, body = (rows[0], rows[1:]) if rows else ([], [])
    omitted = 0
    if tail and len(body) > tail:
        omitted = len(body) - tail
        body = body[-tail:]
    suffix = f" (showing last {tail} of {tail + omitted} rows; pass --evidence-tail 0 for all)" if omitted else ""
    print(f"--- {title} ({sheet['id']}){suffix} ---", file=sys.stdout)
    if header:
        print(header, file=sys.stdout)
    for row in body:
        print(row, file=sys.stdout)
    print(file=sys.stdout)


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
        print(f"--- {title} (doc): not found ---", file=sys.stdout)
        return
    text = read_doc_paragraphs(services, match["id"])
    print(f"--- {title} (doc, {match['id']}) ---", file=sys.stdout)
    print("".join(text), file=sys.stdout)
    print(file=sys.stdout)


def dump_project(services: dict[str, Any], m2_root_id: str, project: str, evidence_tail: int = 0) -> None:
    project_folder = find_folder(services["drive"], m2_root_id, project)
    if not project_folder:
        print(f"No such project folder: {project}", file=sys.stdout)
        return

    print(f"===== {project}: project_metrics =====", file=sys.stdout)
    dump_sheet(services, project_folder["id"], "project_metrics")
    print(f"===== {project}: project_risk =====", file=sys.stdout)
    dump_sheet(services, project_folder["id"], "project_risk")
    print(f"===== {project}: evidence_log =====", file=sys.stdout)
    dump_sheet(services, project_folder["id"], "evidence_log", tail=evidence_tail)
    print(f"===== {project}: qa_process_metrics =====", file=sys.stdout)
    dump_sheet(services, project_folder["id"], "qa_process_metrics")
    print(f"===== {project}: action_items =====", file=sys.stdout)
    dump_sheet(services, project_folder["id"], "action_items")
    print(f"===== {project}: project_development_plan =====", file=sys.stdout)
    dump_doc(services, project_folder["id"], "project_development_plan")

    m2_input_folder = find_folder(services["drive"], project_folder["id"], "m2_input")
    if m2_input_folder:
        print(f"===== {project}: m2_input =====", file=sys.stdout)
        dump_doc(services, m2_input_folder["id"], "m2_input")

    people_folder = find_folder(services["drive"], project_folder["id"], "people")
    if not people_folder:
        return
    print(f"===== {project}: people =====", file=sys.stdout)
    for person in drive_query(
        services["drive"],
        f"'{people_folder['id']}' in parents and mimeType = '{FOLDER_MIME}' and trashed = false",
        fields="id,name",
    ):
        print(f"--- person: {person['name']} ---", file=sys.stdout)
        dump_sheet(services, person["id"], "individual_metrics")
        dump_sheet(services, person["id"], "individual_metrics_internal")
        dump_doc(services, person["id"], "individual_development_plan")


def project_people_counts(services: dict[str, Any], m2_root_id: str) -> dict[str, str]:
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


def fetch_targeted_docs(services: dict[str, Any], args: argparse.Namespace, m2_root_id: str) -> dict[str, Any]:
    doc_results = []
    errors = []

    limit = args.limit if args.limit is not None else 20

    for doc_name in args.document:
        if doc_name in PROJECT_DOCS:
            if not args.project:
                errors.append(f"Document {doc_name} requires --project")
                continue
            if args.person:
                errors.append(f"Document {doc_name} does not accept --person")
                continue
        elif doc_name in PERSON_DOCS:
            if not args.project or not args.person:
                errors.append(f"Document {doc_name} requires both --project and --person")
                continue
        elif doc_name in REGISTRY_DOCS:
            if args.project or args.person:
                errors.append(f"Document {doc_name} does not accept --project or --person")
                continue
        else:
            errors.append(f"Unknown canonical document name: {doc_name}")
            continue

        if args.since and doc_name not in DATE_COLS and not doc_name.endswith("_plan") and doc_name != "m2_input":
            errors.append(f"Document {doc_name} does not support --since filtering")
            continue

        doc_result = {
            "name": doc_name,
            "scope": {"project": args.project, "person": args.person},
            "missing": True,
            "content": [],
            "returned_count": 0,
            "total_count": 0,
            "truncated": False
        }

        # Locate target folder
        target_folder_id = None
        if doc_name in REGISTRY_DOCS:
            if doc_name == "_people_registry":
                people_root = find_folder(services["drive"], ROOT_FOLDER_ID, "05_People_Management")
                target_folder_id = people_root["id"] if people_root else None
            else:
                target_folder_id = m2_root_id
        else:
            proj_folder = find_folder(services["drive"], m2_root_id, args.project)
            if not proj_folder:
                doc_results.append(doc_result)
                continue
            if doc_name == "m2_input":
                m2_in_folder = find_folder(services["drive"], proj_folder["id"], "m2_input")
                target_folder_id = m2_in_folder["id"] if m2_in_folder else None
            elif doc_name in PERSON_DOCS:
                people_folder = find_folder(services["drive"], proj_folder["id"], "people")
                if not people_folder:
                    doc_results.append(doc_result)
                    continue
                person_folder = find_folder(services["drive"], people_folder["id"], args.person)
                target_folder_id = person_folder["id"] if person_folder else None
            else:
                target_folder_id = proj_folder["id"]

        if not target_folder_id:
            doc_results.append(doc_result)
            continue

        is_sheet = not doc_name.endswith("_plan") and doc_name != "m2_input"

        if is_sheet:
            sheet = find_sheet_in_folder(services["drive"], target_folder_id, doc_name)
            if not sheet:
                doc_results.append(doc_result)
                continue

            doc_result["missing"] = False
            doc_result["kind"] = "sheet"
            doc_result["drive_id"] = sheet["id"]

            rows = read_sheet_values(services, sheet["id"])
            if rows:
                header, body = rows[0], rows[1:]

                # Apply since filter
                if args.since and doc_name in DATE_COLS:
                    col = DATE_COLS[doc_name]
                    body = [r for r in body if len(r) > col and r[col] >= args.since]

                doc_result["total_count"] = len(body)

                if limit and limit > 0 and len(body) > limit:
                    body = body[-limit:]
                    doc_result["truncated"] = True

                doc_result["content"] = [header] + body
                doc_result["returned_count"] = len(body)
        else:
            doc = find_doc(services, target_folder_id, doc_name)
            if not doc:
                doc_results.append(doc_result)
                continue

            doc_result["missing"] = False
            doc_result["kind"] = "doc"
            doc_result["drive_id"] = doc["id"]

            paras = read_doc_paragraphs(services, doc["id"])
            doc_result["total_count"] = len(paras)

            if limit and limit > 0 and len(paras) > limit:
                paras = paras[:limit]
                doc_result["truncated"] = True

            doc_result["content"] = paras
            doc_result["returned_count"] = len(paras)

        doc_results.append(doc_result)

    return {"doc_results": doc_results, "errors": errors}


def main() -> int:
    ensure_utf8_stdout()
    args = parse_args()

    if args.json:
        # Redirect standard stdout to stderr to avoid polluting JSON
        sys.stdout = sys.stderr

    if not args.project and not args.registries and not args.summary and not args.document:
        msg = "Nothing to do: pass --project <Name>, --registries, --summary, and/or --document <Name>."
        if args.json:
            print(json.dumps({
                "schema_version": 1,
                "ok": False,
                "command": "show_project_state",
                "data": {},
                "warnings": [],
                "errors": [msg]
            }), file=sys.__stdout__)
        else:
            print(msg)
        return 1

    services = get_services(args.credentials, args.token)
    drive = services["drive"]
    m2_root = find_folder(drive, ROOT_FOLDER_ID, "20_M2_Project_Management")
    if not m2_root:
        msg = "20_M2_Project_Management folder not found under the workspace root."
        if args.json:
            print(json.dumps({
                "schema_version": 1,
                "ok": False,
                "command": "show_project_state",
                "data": {},
                "warnings": [],
                "errors": [msg]
            }), file=sys.__stdout__)
        else:
            print(msg)
        return 1

    if args.document:
        res = fetch_targeted_docs(services, args, m2_root["id"])
        if args.json:
            output = {
                "schema_version": 1,
                "ok": len(res["errors"]) == 0,
                "command": "show_project_state",
                "data": {
                    "selectors": {
                        "project": args.project,
                        "person": args.person,
                        "since": args.since,
                        "limit": args.limit if args.limit is not None else 20
                    },
                    "documents": res["doc_results"]
                },
                "warnings": [],
                "errors": res["errors"]
            }
            print(json.dumps(output), file=sys.__stdout__)
            return 1 if res["errors"] else 0
        else:
            if res["errors"]:
                for e in res["errors"]:
                    print(f"Error: {e}")
                return 1
            for d in res["doc_results"]:
                print(f"--- {d['name']} ---")
                if d["missing"]:
                    print("Not found.")
                else:
                    for line in d["content"]:
                        print(line)
            return 0

    if args.summary:
        people_by_project = project_people_counts(services, m2_root["id"])
        projects = [args.project] if args.project else sorted(people_by_project)
        for project in projects:
            print(summarize_project(services, m2_root["id"], project, people_by_project.get(project, "")), file=sys.__stdout__ if args.json else sys.stdout)
        return 0

    if args.registries:
        print("===== _people_registry =====", file=sys.__stdout__ if args.json else sys.stdout)
        people_root = find_folder(drive, ROOT_FOLDER_ID, "05_People_Management")
        if people_root:
            dump_sheet(services, people_root["id"], "_people_registry")
        else:
            print("--- _people_registry: not found (05_People_Management missing) ---", file=sys.__stdout__ if args.json else sys.stdout)
        print("===== _project_registry =====", file=sys.__stdout__ if args.json else sys.stdout)
        dump_sheet(services, m2_root["id"], "_project_registry")
        print("===== _timeline =====", file=sys.__stdout__ if args.json else sys.stdout)
        dump_sheet(services, m2_root["id"], "_timeline")

    if args.project:
        dump_project(services, m2_root["id"], args.project, evidence_tail=args.evidence_tail)

    return 0


if __name__ == "__main__":
    sys.exit(main())
