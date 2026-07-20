"""Intake queue and run state machine - the durable-state layer of the
intake workflow.

The agent session owns the workflow and every judgment call (classification
confidence, evidence analysis, what to write); this tool owns durable state
and deterministic transitions, so a repeated run produces no duplicates and
a failed run resumes from its exact unfinished stage. It never analyzes a
source and never writes a business document.

State model (per run, in the workspace `_intake_queue` Sheet):

    discovered -> needs_scope -> ready ------.
        |             ^                      v
        '-------------+----------------> processing <-> blocked
                                             |
                                             v
                                     completed | failed

    stages within processing: analysis -> apply -> closure

Commands (all support --json for machine-readable output):

    scan                          discover new source files (hash-idempotent;
                                  the only write scan performs is appending
                                  newly discovered rows)
    status                        queue overview (read-only)
    next                          the single most actionable run + what the
                                  graph says about it (read-only)
    start <run-id> --source-type T [--variant V] [--project P] [--person X]
                                  agent-supplied classification; validates
                                  type/variant against the graph and scope
                                  against the route's entry documents -
                                  missing required scope => needs_scope,
                                  never a silent default
    record-analysis <run-id> --summary "..." --touched d1,d2
                                  short operational summary (never analysis
                                  bodies) + which documents were written
    resolve-edge <run-id> --source A --target B --outcome X [--reason ...]
                                  records a closure outcome via
                                  closure_outcomes (shared validation, no
                                  duplication), tagged with the run's scope
    block <run-id> --reason "..." mark waiting on a gate/answer
    resume <run-id> [--continue]  exact unfinished stage + what remains;
                                  --continue reactivates a blocked run
    complete <run-id>             verification gate: route entry documents
                                  all touched, strict closure per every
                                  scope seen in the run, _skill_invocations
                                  row present, mirror snapshot tagged with
                                  the run id - only then completed
    fail <run-id> --reason "..."  give up explicitly (kept in history)

Queue rows hold operational metadata and short summaries only - full
transcripts and analysis content never enter the queue.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

import yaml

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent))

GRAPH_PATH = Path(__file__).resolve().parent.parent / "document_graph.yaml"
DATA_ROOT = Path(r"G:\My Drive\QA_Management")
SCAN_DIRS = [
    "02_Transcripts_Inbox",
    r"00_Source_Docs\01_Meeting_Transcripts",
    r"00_Source_Docs\02_Chats_and_Emails",
    r"00_Source_Docs\03_Source_Documents",
]
SCAN_EXTS = {".txt", ".md", ".docx", ".doc", ".pdf", ".csv", ".xlsx"}

QUEUE_SHEET = "_intake_queue"
HEADER = ["Run ID", "Source", "Source hash", "Source type", "Route variant",
          "Project", "Person", "Status", "Stage", "Skills", "Touched",
          "Discovered", "Started", "Completed", "Reason", "Summary"]

STATES = {"discovered", "needs_scope", "ready", "processing", "blocked",
          "completed", "failed"}
TRANSITIONS = {
    "discovered": {"needs_scope", "ready", "processing", "failed"},
    "needs_scope": {"ready", "processing", "failed"},
    "ready": {"processing", "failed"},
    "processing": {"blocked", "completed", "failed"},
    "blocked": {"processing", "failed"},
    "completed": set(),
    "failed": set(),
}
STAGES = ["analysis", "apply", "closure", "done"]

# Mechanical folder -> pre-classification label (agent refines via start).
FOLDER_PRECLASS = {
    "02_Transcripts_Inbox": "raw_transcript",
    "01_Meeting_Transcripts": "raw_transcript",
    "02_Chats_and_Emails": "raw_chat",
    "03_Source_Documents": "source_document",
}


def now() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M")


# ---------- pure helpers (unit-tested) ----------

def validate_transition(current: str, target: str) -> None:
    if current not in STATES or target not in STATES:
        raise SystemExit(f"Unknown state: {current!r} -> {target!r}")
    if target not in TRANSITIONS[current]:
        raise SystemExit(f"Invalid transition {current!r} -> {target!r} "
                         f"(allowed from {current!r}: {sorted(TRANSITIONS[current]) or 'none'})")


def mint_run_id(source_path: str, source_hash: str, date: str | None = None) -> str:
    stem = Path(source_path).stem.lower()
    slug = "".join(c if c.isalnum() else "-" for c in stem)
    slug = "-".join(p for p in slug.split("-") if p)[:40]
    return f"{date or dt.date.today().strftime('%Y%m%d')}-{slug}-{source_hash[:6]}"


def resolve_route(graph: dict, source_type: str, variant: str) -> dict:
    """The graph's skills/entry for a source type (+ variant when the type
    has route variants). Raises with the valid options on a mismatch."""
    sources = graph.get("sources") or {}
    spec = sources.get(source_type)
    if spec is None:
        raise SystemExit(f"source_type {source_type!r} has no route in document_graph.yaml "
                         f"(routed types: {sorted(sources)})")
    if "routes" in spec:
        routes = spec["routes"] or {}
        if not variant:
            raise SystemExit(f"source_type {source_type!r} needs --variant "
                             f"(one of: {sorted(routes)})")
        if variant not in routes:
            raise SystemExit(f"Unknown variant {variant!r} for {source_type!r} "
                             f"(one of: {sorted(routes)})")
        return routes[variant]
    if variant:
        raise SystemExit(f"source_type {source_type!r} has no route variants - drop --variant")
    return spec


def needed_scopes(graph: dict, entry_docs: list[str]) -> set[str]:
    """Which scope fields the route's entry documents demand."""
    docs = graph.get("documents") or {}
    return {(docs.get(d) or {}).get("scope") for d in entry_docs} & {"project", "person"}


def enumerate_run_scopes(outcome_rows: list[dict], row: dict) -> list[tuple[str, str, str]]:
    """Every (project, person, variant) scope the run touched: declared on
    the queue row (comma-separated multi-values allowed) plus every scope
    seen in recorded outcomes. Each is strict-closure-checked separately."""
    scopes: set[tuple[str, str, str]] = set()
    projects = [p.strip() for p in row.get("Project", "").split(",") if p.strip()] or [""]
    persons = [p.strip() for p in row.get("Person", "").split(",") if p.strip()] or [""]
    variant = row.get("Route variant", "").strip()
    for proj in projects:
        for pers in persons:
            scopes.add((proj, pers, variant))
    for rec in outcome_rows:
        scopes.add((rec.get("Project", "").strip(), rec.get("Person", "").strip(),
                    rec.get("Route variant", "").strip()))
    return sorted(scopes)


# ---------- queue sheet I/O ----------

def load_graph() -> dict:
    return yaml.safe_load(GRAPH_PATH.read_text(encoding="utf-8"))


def get_services_cached():
    from pipeline_common import get_services
    return get_services()


def find_queue(services):
    from sync_m2_source_docs_to_sheets import ROOT_FOLDER_ID, find_sheet_in_folder
    return find_sheet_in_folder(services["drive"], ROOT_FOLDER_ID, QUEUE_SHEET)


def get_or_create_queue(services):
    from sync_m2_source_docs_to_sheets import ROOT_FOLDER_ID, create_sheet
    sheet = find_queue(services)
    if sheet:
        return sheet
    return create_sheet(services, QUEUE_SHEET, ROOT_FOLDER_ID, [HEADER])


def read_queue(services, sheet) -> list[dict]:
    from sync_m2_source_docs_to_sheets import read_sheet_values
    rows = read_sheet_values(services, sheet["id"])
    out = []
    for row in rows[1:]:
        padded = list(row) + [""] * (len(HEADER) - len(row))
        out.append(dict(zip(HEADER, padded)))
    return out


def write_queue(services, sheet, rows: list[dict]) -> None:
    from pipeline_common import reformat_sheet
    title = services["sheets"].spreadsheets().get(
        spreadsheetId=sheet["id"]).execute()["sheets"][0]["properties"]["title"]
    values = [HEADER] + [[r.get(h, "") for h in HEADER] for r in rows]
    services["sheets"].spreadsheets().values().clear(
        spreadsheetId=sheet["id"], range=f"'{title}'").execute()
    services["sheets"].spreadsheets().values().update(
        spreadsheetId=sheet["id"], range=f"'{title}'!A1", valueInputOption="RAW",
        body={"values": values}).execute()
    reformat_sheet(services, sheet["id"], QUEUE_SHEET)


def get_run(rows: list[dict], run_id: str) -> dict:
    for row in rows:
        if row["Run ID"] == run_id:
            return row
    raise SystemExit(f"No queue row with Run ID {run_id!r} - see qa_manage.py status.")


# ---------- output ----------

def emit(payload: dict, as_json: bool, human_lines: list[str]) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=1))
    else:
        for line in human_lines:
            print(line)


def row_brief(row: dict) -> str:
    scope = " / ".join(x for x in (row["Project"], row["Person"]) if x)
    return (f"{row['Run ID']}  [{row['Status']}"
            + (f":{row['Stage']}" if row["Stage"] else "") + "]  "
            + (f"{row['Source type']}" if row["Source type"] else "unclassified")
            + (f"({row['Route variant']})" if row["Route variant"] else "")
            + (f"  {scope}" if scope else "")
            + (f"  reason: {row['Reason']}" if row["Reason"] and
               row["Status"] in ("blocked", "needs_scope", "failed") else ""))


# ---------- commands ----------

def cmd_scan(args) -> int:
    services = get_services_cached()
    sheet = get_or_create_queue(services)
    rows = read_queue(services, sheet)
    known_hashes = {r["Source hash"] for r in rows if r["Source hash"]}
    known_sources = {r["Source"] for r in rows}

    discovered = []
    for rel_dir in SCAN_DIRS:
        base = DATA_ROOT / rel_dir
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in SCAN_EXTS:
                continue
            digest = hashlib.sha256(path.read_bytes()).hexdigest()[:16]
            rel = str(path.relative_to(DATA_ROOT))
            if digest in known_hashes or rel in known_sources:
                continue
            preclass = FOLDER_PRECLASS.get(path.parent.name,
                                           FOLDER_PRECLASS.get(Path(rel_dir).name, "source_document"))
            row = dict.fromkeys(HEADER, "")
            row.update({"Run ID": mint_run_id(rel, digest), "Source": rel,
                        "Source hash": digest, "Source type": preclass,
                        "Status": "discovered", "Discovered": now()})
            discovered.append(row)
            known_hashes.add(digest)

    if discovered:
        write_queue(services, sheet, rows + discovered)
    payload = {"discovered": [{"run_id": r["Run ID"], "source": r["Source"],
                               "preclass": r["Source type"]} for r in discovered]}
    emit(payload, args.json,
         [f"{len(discovered)} new source(s) discovered:"] +
         [f"  {r['Run ID']}  {r['Source']}  ({r['Source type']})" for r in discovered]
         if discovered else ["No new sources."])
    return 0


def cmd_status(args) -> int:
    services = get_services_cached()
    sheet = find_queue(services)
    rows = read_queue(services, sheet) if sheet else []
    open_rows = [r for r in rows if r["Status"] not in ("completed", "failed")]
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["Status"]] = counts.get(r["Status"], 0) + 1
    payload = {"counts": counts, "open": [{h.lower().replace(" ", "_"): r[h] for h in HEADER
                                          if h != "Summary"} for r in open_rows]}
    emit(payload, args.json,
         [f"Queue: " + ", ".join(f"{k}={v}" for k, v in sorted(counts.items())) if counts
          else "Queue is empty (run scan first)."] +
         [f"  {row_brief(r)}" for r in open_rows])
    return 0


def cmd_next(args) -> int:
    services = get_services_cached()
    sheet = find_queue(services)
    rows = read_queue(services, sheet) if sheet else []
    priority = ["processing", "ready", "needs_scope", "discovered", "blocked"]
    pick = None
    for status in priority:
        cands = [r for r in rows if r["Status"] == status]
        if cands:
            pick = cands[0]
            break
    if not pick:
        emit({"next": None}, args.json, ["Nothing actionable - queue is clear."])
        return 0

    lines = [row_brief(pick), f"  source: {pick['Source']}"]
    info: dict = {"run_id": pick["Run ID"], "status": pick["Status"], "stage": pick["Stage"],
                  "source": pick["Source"], "source_type": pick["Source type"],
                  "variant": pick["Route variant"], "project": pick["Project"],
                  "person": pick["Person"]}
    graph = load_graph()
    if pick["Status"] == "discovered":
        spec = (graph.get("sources") or {}).get(pick["Source type"])
        lines.append("  unfinished: classification - read the source, then "
                     "`start` with --source-type (and --variant/--project/--person).")
        if spec is None:
            routed = sorted((graph.get("sources") or {}))
            lines.append(f"  routed source types: {', '.join(routed)}")
            info["routed_types"] = routed
    elif pick["Status"] == "needs_scope":
        lines.append(f"  unfinished: scope - {pick['Reason']}")
    elif pick["Status"] in ("ready", "processing", "blocked"):
        try:
            route = resolve_route(graph, pick["Source type"], pick["Route variant"])
            info["skills"] = route.get("skills") or []
            info["entry"] = route.get("entry") or []
            lines.append(f"  skills: {', '.join(info['skills']) or '(graph: shared rules only)'}")
            lines.append(f"  entry documents: {', '.join(info['entry'])}")
        except SystemExit as exc:
            lines.append(f"  route problem: {exc}")
        lines.append(f"  unfinished stage: {pick['Stage'] or 'analysis'}"
                     + (f" (blocked: {pick['Reason']})" if pick["Status"] == "blocked" else ""))
    info["unfinished"] = pick["Stage"] or pick["Status"]
    emit({"next": info}, args.json, lines)
    return 0


def _update_run(args, mutate) -> tuple[dict, list[dict], object, object]:
    services = get_services_cached()
    sheet = find_queue(services)
    if not sheet:
        raise SystemExit("No _intake_queue sheet yet - run scan first.")
    rows = read_queue(services, sheet)
    row = get_run(rows, args.run_id)
    mutate(row)
    write_queue(services, sheet, rows)
    return row, rows, services, sheet


def cmd_start(args) -> int:
    graph = load_graph()
    from pipeline_common import SKILL_INVOCATION_SOURCE_TYPES
    if args.source_type not in SKILL_INVOCATION_SOURCE_TYPES:
        raise SystemExit(f"source_type {args.source_type!r} is not canonical "
                         f"({sorted(SKILL_INVOCATION_SOURCE_TYPES)})")
    route = resolve_route(graph, args.source_type, args.variant or "")
    entry = route.get("entry") or []
    need = needed_scopes(graph, entry)

    def mutate(row: dict) -> None:
        row["Source type"] = args.source_type
        row["Route variant"] = args.variant or ""
        row["Project"] = args.project or row["Project"]
        row["Person"] = args.person or row["Person"]
        row["Skills"] = ", ".join(route.get("skills") or [])
        missing = [s for s in sorted(need)
                   if not row["Project" if s == "project" else "Person"].strip()]
        if missing:
            validate_transition(row["Status"], "needs_scope")
            row["Status"] = "needs_scope"
            row["Reason"] = (f"route entry documents are {'/'.join(missing)}-scoped - "
                             f"re-run start with --{' and --'.join(missing)} "
                             "(never defaulted silently)")
        else:
            validate_transition(row["Status"], "processing")
            row["Status"], row["Stage"] = "processing", "analysis"
            row["Started"], row["Reason"] = now(), ""

    row, *_ = _update_run(args, mutate)
    emit({"run_id": row["Run ID"], "status": row["Status"], "stage": row["Stage"],
          "skills": row["Skills"], "entry": entry, "reason": row["Reason"]},
         args.json,
         [row_brief(row)] +
         ([f"  load skills: {row['Skills'] or '(shared rules per graph note)'}",
           f"  entry documents to update: {', '.join(entry)}"]
          if row["Status"] == "processing" else [f"  {row['Reason']}"]))
    return 0 if row["Status"] == "processing" else 1


def cmd_record_analysis(args) -> int:
    from check_cascade_closure import build_alias_map, normalize
    graph = load_graph()
    alias_map = build_alias_map(graph)
    touched, unknown = [], []
    for name in (t.strip() for t in args.touched.split(",") if t.strip()):
        canon = normalize(name, alias_map)
        (touched if canon else unknown).append(canon or name)
    if unknown:
        raise SystemExit(f"Unknown touched document(s): {', '.join(unknown)} - "
                         "use canonical graph node names (or add aliases).")

    def mutate(row: dict) -> None:
        if row["Status"] != "processing":
            raise SystemExit(f"record-analysis requires status=processing (is {row['Status']!r}).")
        row["Stage"] = "closure"
        row["Touched"] = ", ".join(sorted(set(touched) |
                                          {t for t in row["Touched"].split(", ") if t}))
        row["Summary"] = (row["Summary"] + " | " if row["Summary"] else "") + args.summary.strip()

    row, *_ = _update_run(args, mutate)
    emit({"run_id": row["Run ID"], "stage": row["Stage"], "touched": row["Touched"]},
         args.json,
         [row_brief(row), f"  touched: {row['Touched']}",
          "  next: resolve every edge (resolve-edge), then complete."])
    return 0


def cmd_resolve_edge(args) -> int:
    import closure_outcomes as co
    services = get_services_cached()
    sheet = find_queue(services)
    rows = read_queue(services, sheet) if sheet else []
    row = get_run(rows, args.run_id)
    if row["Status"] != "processing":
        raise SystemExit(f"resolve-edge requires status=processing (is {row['Status']!r}).")

    project = args.project or row["Project"] if "," not in row["Project"] else args.project or ""
    person = args.person or row["Person"] if "," not in row["Person"] else args.person or ""
    variant = args.variant or row["Route variant"]
    kind = co.edge_kind(args.source, args.target)
    co.validate(kind, args.outcome, args.reason)
    co.require_scope(args.source, args.target, project, person)
    out_sheet = co.get_or_create_sheet(services)
    services["sheets"].spreadsheets().values().append(
        spreadsheetId=out_sheet["id"], range="A1", valueInputOption="RAW",
        body={"values": [[args.run_id, now(), project, person, variant,
                          args.source, args.target, kind, args.outcome,
                          args.reason, args.actor]]}).execute()
    emit({"run_id": args.run_id, "edge": f"{args.source}->{args.target}",
          "kind": kind, "outcome": args.outcome},
         args.json,
         [f"Recorded: {args.source} -> {args.target} [{kind}] = {args.outcome}"
          + (f" ({args.reason})" if args.reason else "")])
    return 0


def cmd_block(args) -> int:
    def mutate(row: dict) -> None:
        validate_transition(row["Status"], "blocked")
        row["Status"], row["Reason"] = "blocked", args.reason
    row, *_ = _update_run(args, mutate)
    emit({"run_id": row["Run ID"], "status": "blocked", "reason": row["Reason"]},
         args.json, [row_brief(row)])
    return 0


def cmd_fail(args) -> int:
    def mutate(row: dict) -> None:
        validate_transition(row["Status"], "failed")
        row["Status"], row["Reason"] = "failed", args.reason
    row, *_ = _update_run(args, mutate)
    emit({"run_id": row["Run ID"], "status": "failed"}, args.json, [row_brief(row)])
    return 0


def cmd_resume(args) -> int:
    services = get_services_cached()
    sheet = find_queue(services)
    rows = read_queue(services, sheet) if sheet else []
    row = get_run(rows, args.run_id)

    from closure_outcomes import fetch_outcomes
    outcome_rows = fetch_outcomes(services, args.run_id, all_scopes=True)
    scopes = enumerate_run_scopes(outcome_rows, row)

    if args.cont:
        if row["Status"] != "blocked":
            raise SystemExit(f"--continue only reactivates a blocked run (is {row['Status']!r}).")
        validate_transition("blocked", "processing")
        row["Status"], row["Reason"] = "processing", ""
        write_queue(services, sheet, rows)

    lines = [row_brief(row),
             f"  source: {row['Source']}",
             f"  touched so far: {row['Touched'] or '(none recorded)'}",
             f"  outcomes recorded: {len(outcome_rows)} across {len(scopes)} scope(s)",
             f"  unfinished stage: {row['Stage'] or row['Status']} - completed writes are "
             "recorded above; do not repeat them, continue from here."]
    emit({"run_id": row["Run ID"], "status": row["Status"], "stage": row["Stage"],
          "touched": row["Touched"], "outcomes": len(outcome_rows),
          "scopes": [list(s) for s in scopes]}, args.json, lines)
    return 0


def cmd_complete(args) -> int:
    import subprocess

    from check_cascade_closure import build_resolved, walk
    from closure_outcomes import fetch_outcomes
    from sync_m2_source_docs_to_sheets import read_sheet_values

    services = get_services_cached()
    sheet = find_queue(services)
    rows = read_queue(services, sheet) if sheet else []
    row = get_run(rows, args.run_id)
    if row["Status"] != "processing":
        raise SystemExit(f"complete requires status=processing (is {row['Status']!r}).")

    graph = load_graph()
    problems: list[str] = []

    # 1. Route entry documents must all be claimed as touched.
    route = resolve_route(graph, row["Source type"], row["Route variant"])
    touched = {t for t in (x.strip() for x in row["Touched"].split(",")) if t}
    for doc in route.get("entry") or []:
        if doc not in touched:
            problems.append(f"entry document {doc!r} not in Touched "
                            "(record-analysis --touched, or explain via fail/block)")

    # 2. Strict closure per scope - one check per (project, person, variant).
    all_rows = fetch_outcomes(services, args.run_id, all_scopes=True)
    for proj, pers, variant in enumerate_run_scopes(all_rows, row):
        scoped = fetch_outcomes(services, args.run_id, proj, pers, variant)
        resolved, warns = build_resolved(scoped, graph)
        problems.extend(f"scope ({proj or '-'}, {pers or '-'}, {variant or '-'}): {w}"
                        for w in warns)
        open_items: list[str] = []
        lines: list[str] = []
        visited_req = set(touched)
        for node in sorted(touched):
            walk(graph, node, touched, visited_req, set(), 0, False, True,
                 resolved, open_items, lines)
        for item in open_items:
            problems.append(f"scope ({proj or '-'}, {pers or '-'}, {variant or '-'}): "
                            f"unresolved edge {item}")

    # 3. A _skill_invocations row must reference this run.
    from pipeline_common import get_skill_invocations_sheet
    inv_rows = read_sheet_values(services, get_skill_invocations_sheet(services)["id"])
    if not any(args.run_id in " | ".join(r) or row["Source"] in " | ".join(r)
               for r in inv_rows[1:]):
        problems.append(f"no _skill_invocations row references run {args.run_id} "
                        f"or source {row['Source']} - log_skill_invocation() with the "
                        "run id in Notes")

    # 4. Mirror snapshot tagged with the run id.
    mirror = Path.home() / "Documents" / "qa-drive-mirror"
    log = subprocess.run(["git", "-C", str(mirror), "log", "-10", "--format=%s"],
                         capture_output=True, text=True, encoding="utf-8").stdout
    if args.run_id not in log:
        problems.append(f"no mirror commit mentions {args.run_id} - run "
                        f"commit_workspace_state.py -m \"<skill>: <source> [{args.run_id}]\"")

    if problems:
        emit({"run_id": args.run_id, "completed": False, "problems": problems},
             args.json,
             [f"NOT completed - {len(problems)} unmet requirement(s):"] +
             [f"  - {p}" for p in problems])
        return 1

    row["Status"], row["Stage"], row["Completed"] = "completed", "done", now()
    write_queue(services, sheet, rows)
    emit({"run_id": args.run_id, "completed": True}, args.json,
         [f"{args.run_id} completed: entry docs touched, closure strict-CLOSED per scope, "
          "invocation logged, mirror snapshot tagged."])
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("scan", help="discover new source files")
    sub.add_parser("status", help="queue overview")
    sub.add_parser("next", help="most actionable run")

    p = sub.add_parser("start", help="classify + activate a run")
    p.add_argument("run_id")
    p.add_argument("--source-type", required=True)
    p.add_argument("--variant", default="")
    p.add_argument("--project", default="")
    p.add_argument("--person", default="")

    p = sub.add_parser("record-analysis", help="summary + touched documents")
    p.add_argument("run_id")
    p.add_argument("--summary", required=True)
    p.add_argument("--touched", required=True)

    p = sub.add_parser("resolve-edge", help="record one closure outcome")
    p.add_argument("run_id")
    p.add_argument("--source", required=True)
    p.add_argument("--target", required=True)
    p.add_argument("--outcome", required=True)
    p.add_argument("--reason", default="")
    p.add_argument("--project", default="")
    p.add_argument("--person", default="")
    p.add_argument("--variant", default="")
    p.add_argument("--actor", default="agent")

    p = sub.add_parser("block", help="mark run waiting on a gate")
    p.add_argument("run_id")
    p.add_argument("--reason", required=True)

    p = sub.add_parser("fail", help="give up on a run explicitly")
    p.add_argument("run_id")
    p.add_argument("--reason", required=True)

    p = sub.add_parser("resume", help="unfinished stage + what remains")
    p.add_argument("run_id")
    p.add_argument("--continue", dest="cont", action="store_true",
                   help="reactivate a blocked run")

    p = sub.add_parser("complete", help="verification gate -> completed")
    p.add_argument("run_id")

    args = parser.parse_args()
    return {"scan": cmd_scan, "status": cmd_status, "next": cmd_next,
            "start": cmd_start, "record-analysis": cmd_record_analysis,
            "resolve-edge": cmd_resolve_edge, "block": cmd_block,
            "fail": cmd_fail, "resume": cmd_resume,
            "complete": cmd_complete}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
