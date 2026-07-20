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
import contextlib
import datetime as dt
import io
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

PROJECT_DOCS = {"project_metrics", "project_risk", "evidence_log", "qa_process_metrics", "action_items", "project_development_plan", "m2_input"}
PERSON_DOCS = {"individual_metrics", "individual_metrics_internal", "individual_development_plan"}
REGISTRY_DOCS = {"_people_registry", "_project_registry", "_timeline"}

DATE_COLS = {
    "evidence_log": 0,
    "action_items": 1,
    "project_risk": 1,
    "_timeline": 1,
}

class ParserError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)

def build_json_envelope(ok: bool, cmd: str, data: dict[str, Any], warnings: list[str], errors: list[str]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "ok": ok,
        "command": cmd,
        "data": data,
        "warnings": warnings,
        "errors": errors
    }

class ThrowingArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        raise ParserError(message)

@contextlib.contextmanager
def stdout_redirected(to=sys.stderr):
    original_stdout = sys.stdout
    sys.stdout = to
    try:
        yield
    finally:
        sys.stdout = original_stdout

def parse_args() -> argparse.Namespace:
    parser = ThrowingArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--project", help="Project name under 20_M2_Project_Management, e.g. <ProjectName>")
    parser.add_argument("--registries", action="store_true", help="Also/instead dump _people_registry and _project_registry")
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Print a one-liner per project instead of a full dump.",
    )
    parser.add_argument(
        "--evidence-tail",
        type=int,
        default=10,
        help="Show only the last N evidence_log rows. Pass 0 for full log.",
    )

    parser.add_argument("--document", action="append", default=[], help="Specific document names to fetch")
    parser.add_argument("--person", help="Person name for individual document scope")
    parser.add_argument("--since", help="Filter rows >= this YYYY-MM-DD date")
    parser.add_argument("--limit", type=int, help="Limit returned rows/paragraphs. Defaults to 20 when --document is used. Range: 1..1000")
    parser.add_argument("--json", action="store_true", help="Output strict JSON envelope")

    parser.add_argument("--credentials", default=".local/google/credentials.json")
    parser.add_argument("--token", default=".local/google/token.json")

    args = parser.parse_args()

    if args.since:
        try:
            dt.date.fromisoformat(args.since)
        except ValueError:
            parser.error(f"Invalid --since date format: '{args.since}'. Expected YYYY-MM-DD.")

    if args.limit is not None:
        if args.limit < 1 or args.limit > 1000:
            parser.error(f"Invalid --limit: {args.limit}. Must be between 1 and 1000.")

    targeted_only_flags = []
    if args.person: targeted_only_flags.append("--person")
    if args.since: targeted_only_flags.append("--since")
    if args.limit is not None: targeted_only_flags.append("--limit")
    if targeted_only_flags and not args.document:
        parser.error(f"Targeted options {', '.join(targeted_only_flags)} require --document")

    num_modes = sum([
        bool(args.document),
        bool(args.summary),
        bool(args.registries),
        bool(not args.document and not args.summary and not args.registries and args.project)
    ])
    if num_modes > 1:
        if not (args.registries and args.project and not args.document and not args.summary):
            parser.error("Incompatible options: cannot combine targeted reads (--document), summary mode (--summary), registries (--registries), or legacy full-dump mode.")

    if args.document:
        for doc_name in args.document:
            if doc_name in PROJECT_DOCS:
                if not args.project:
                    parser.error(f"Document {doc_name} requires --project")
                if args.person:
                    parser.error(f"Document {doc_name} does not accept --person")
            elif doc_name in PERSON_DOCS:
                if not args.project or not args.person:
                    parser.error(f"Document {doc_name} requires both --project and --person")
            elif doc_name in REGISTRY_DOCS:
                if args.project or args.person:
                    parser.error(f"Document {doc_name} does not accept --project or --person")
            else:
                parser.error(f"Unknown canonical document name: {doc_name}")

            if args.since and doc_name not in DATE_COLS and not doc_name.endswith("_plan") and doc_name != "m2_input":
                parser.error(f"Document {doc_name} does not support --since filtering")
            if args.since and (doc_name.endswith("_plan") or doc_name == "m2_input"):
                parser.error(f"Document {doc_name} (Docs) does not support --since filtering")

    return args

def find_folder(drive: Any, parent_id: str, name: str) -> dict[str, Any] | None:
    matches = drive_query(
        drive,
        f"'{parent_id}' in parents and name = '{q_escape(name)}' and mimeType = '{FOLDER_MIME}' and trashed = false",
        fields="id,name",
    )
    return matches[0] if matches else None

def read_doc_paragraphs(services: dict[str, Any], doc_id: str) -> list[str]:
    doc = services["docs"].documents().get(documentId=doc_id).execute()
    paras = []
    for element in doc.get("body", {}).get("content", []):
        if "paragraph" in element:
            para_text = []
            for run in element["paragraph"].get("elements", []):
                if "textRun" in run:
                    para_text.append(run["textRun"]["content"])
            full_text = "".join(para_text)
            if full_text.strip():
                paras.append(full_text)
    return paras

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
    text = read_doc_paragraphs(services, match["id"])
    print(f"--- {title} (doc, {match['id']}) ---")
    for para in text:
        print(para, end="")
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
        doc_result = {
            "name": doc_name,
            "scope": {"project": args.project, "person": args.person},
            "missing": True,
            "content": [],
            "returned_count": 0,
            "total_count": 0,
            "truncated": False
        }

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
                if args.since and doc_name in DATE_COLS:
                    col = DATE_COLS[doc_name]
                    def parse_date(d_str):
                        try:
                            return dt.date.fromisoformat(d_str).isoformat()
                        except ValueError:
                            return None
                    since_iso = dt.date.fromisoformat(args.since).isoformat()
                    filtered_body = []
                    for r in body:
                        if len(r) > col:
                            d = parse_date(r[col])
                            if d and d >= since_iso:
                                filtered_body.append(r)
                    body = filtered_body

                doc_result["total_count"] = len(body)
                if limit and len(body) > limit:
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
            if limit and len(paras) > limit:
                paras = paras[:limit]
                doc_result["truncated"] = True

            doc_result["content"] = paras
            doc_result["returned_count"] = len(paras)

        doc_results.append(doc_result)

    return {"doc_results": doc_results, "errors": errors}

def do_run(args: argparse.Namespace) -> tuple[dict[str, Any] | None, int]:
    if not args.project and not args.registries and not args.summary and not args.document:
        msg = "Nothing to do: pass --project <Name>, --registries, --summary, and/or --document <Name>."
        return build_json_envelope(False, "show_project_state", {}, [], [msg]), 1

    try:
        services = get_services(args.credentials, args.token)
    except Exception as e:
        return build_json_envelope(False, "show_project_state", {}, [], [f"Failed to build services: {e}"]), 1

    drive = services["drive"]
    m2_root = find_folder(drive, ROOT_FOLDER_ID, "20_M2_Project_Management")
    if not m2_root:
        msg = "20_M2_Project_Management folder not found under the workspace root."
        return build_json_envelope(False, "show_project_state", {}, [], [msg]), 1

    if args.document:
        res = fetch_targeted_docs(services, args, m2_root["id"])
        envelope = build_json_envelope(len(res["errors"]) == 0, "show_project_state", {
            "selectors": {
                "project": args.project,
                "person": args.person,
                "since": args.since,
                "limit": args.limit if args.limit is not None else 20
            },
            "documents": res["doc_results"]
        }, [], res["errors"])

        if res["errors"]:
            if not args.json:
                for e in res["errors"]:
                    print(f"Error: {e}", file=sys.stderr)
            return envelope, 1

        if not args.json:
            for d in res["doc_results"]:
                print(f"--- {d['name']} ---")
                if d["missing"]:
                    print("Not found.")
                else:
                    for line in d["content"]:
                        print(line)
        return envelope, 0

    if args.summary:
        people_by_project = project_people_counts(services, m2_root["id"])
        projects = [args.project] if args.project else sorted(people_by_project)
        output = []
        for project in projects:
            summary = summarize_project(services, m2_root["id"], project, people_by_project.get(project, ""))
            if not args.json:
                print(summary)
            output.append(summary)
        return build_json_envelope(True, "show_project_state", {"output": output}, [], []), 0

    if args.registries or (args.project and not args.document and not args.summary):
        output_buffer = io.StringIO()
        with stdout_redirected(output_buffer if args.json else sys.stdout):
            if args.registries:
                print("===== _people_registry =====")
                people_root = find_folder(drive, ROOT_FOLDER_ID, "05_People_Management")
                if people_root:
                    dump_sheet(services, people_root["id"], "_people_registry")
                else:
                    print("--- _people_registry: not found (05_People_Management missing) ---")
                print("===== _project_registry =====")
                dump_sheet(services, m2_root["id"], "_project_registry")
                print("===== _timeline =====")
                dump_sheet(services, m2_root["id"], "_timeline")

            if args.project and not args.document and not args.summary:
                dump_project(services, m2_root["id"], args.project, evidence_tail=args.evidence_tail)

        return build_json_envelope(True, "show_project_state", {"output": output_buffer.getvalue() if args.json else ""}, [], []), 0

    return build_json_envelope(True, "show_project_state", {}, [], []), 0

def main() -> int:
    try:
        ensure_utf8_stdout()
    except Exception:
        pass

    is_json = "--json" in sys.argv

    try:
        args = parse_args()
    except ParserError as pe:
        if is_json:
            envelope = build_json_envelope(False, "show_project_state", {}, [], [pe.message])
            print(json.dumps(envelope, ensure_ascii=False, indent=1))
            return 1
        else:
            print(f"show_project_state.py: error: {pe.message}", file=sys.stderr)
            return 2
    except Exception as e:
        if is_json:
            envelope = build_json_envelope(False, "show_project_state", {}, [], [f"Unexpected error: {e}"])
            print(json.dumps(envelope, ensure_ascii=False, indent=1))
            return 1
        else:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    buffer = io.StringIO()
    if is_json:
        cm = stdout_redirected(buffer)
    else:
        cm = contextlib.nullcontext()

    with cm:
        try:
            res, code = do_run(args)
        except SystemExit as e:
            code = e.code if isinstance(e.code, int) else 1
            res = None
        except Exception as e:
            res = build_json_envelope(False, "show_project_state", {}, [], [f"Unexpected error: {e}"])
            code = 1

    if is_json:
        if res is not None:
            print(json.dumps(res, ensure_ascii=False, indent=1))
        else:
            envelope = build_json_envelope(False, "show_project_state", {}, [], [f"SystemExit {code}"])
            print(json.dumps(envelope, ensure_ascii=False, indent=1))

    return code

if __name__ == "__main__":
    sys.exit(main())
