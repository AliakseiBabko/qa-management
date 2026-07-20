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
                              completed | failed | historical

    stages within processing: analysis -> apply -> closure

`historical` is the terminal state for sources that were already processed
before the queue existed (with evidence) - being pre-queue is not a
processing failure. `failed` may be corrected to `historical` when
migration evidence turns up.

Source identity is (path, content hash): a changed file at a known path is
rediscovered as a new run (noting what it supersedes); identical content at
a new path is recorded as a duplicate rather than silently skipped.

Commands (all support --json for machine-readable output):

    scan                          discover new/changed source files (the
                                  only write scan performs is appending
                                  newly discovered rows)
    status                        queue overview (read-only)
    next                          the single most actionable run + what the
                                  graph says about it (read-only)
    start <run-id> --source-type T [--variant V]
          [--project P --person X] [--scope "P|X" ...]
                                  agent-supplied classification; validates
                                  type/variant against the graph. Scopes are
                                  explicit (project, person) tuples - never
                                  a Cartesian product, never defaulted
                                  silently (missing scope => needs_scope)
    record-analysis <run-id> --summary "..."
                                  short operational summary of the analysis
                                  (never analysis bodies); stage -> apply
    record-apply <run-id> [--project P --person X]
          --updated d1,d2 [--no-change "d3=reason;d4=reason"]
          [--not-applicable "d5=reason"]
                                  per-scope outcome for every route entry
                                  document; only updated entries seed the
                                  cascade; stage -> closure
    resolve-edge <run-id> --source A --target B --outcome X [--reason ...]
                                  records a closure outcome via
                                  closure_outcomes (shared validation)
    block <run-id> --reason "..." mark waiting on a gate/answer
    resume <run-id> [--continue]  exact unfinished stage + what remains;
                                  --continue reactivates a blocked run
    complete <run-id>             verification gate: every entry document
                                  has a per-scope outcome, strict closure
                                  per scope, a `run:<run-id>` token in
                                  _skill_invocations, and a clean mirror
                                  snapshot newer than the run's last
                                  mutation (its SHA is persisted); then the
                                  terminal queue state itself is exported
                                  into the mirror as a follow-up commit
    fail <run-id> --reason "..."  give up explicitly (kept in history)
    historical <run-id> --evidence "..."
                                  terminal: processed before the queue
                                  existed; evidence required

Queue rows hold operational metadata and short summaries only - full
transcripts and analysis content never enter the queue.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import io
import json
import subprocess
import sys
from pathlib import Path

import yaml

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent))

GRAPH_PATH = Path(__file__).resolve().parent.parent / "document_graph.yaml"
DATA_ROOT = Path(r"G:\My Drive\QA_Management")
MIRROR = Path.home() / "Documents" / "qa-drive-mirror"
SCAN_DIRS = [
    "02_Transcripts_Inbox",
    r"00_Source_Docs\01_Meeting_Transcripts",
    r"00_Source_Docs\02_Chats_and_Emails",
    r"00_Source_Docs\03_Source_Documents",
]
SCAN_EXTS = {".txt", ".md", ".docx", ".doc", ".pdf", ".csv", ".xlsx"}

QUEUE_SHEET = "_intake_queue"
HEADER = ["Run ID", "Source", "Source hash", "Source type", "Route variant",
          "Project", "Person", "Scopes", "Status", "Stage", "Skills",
          "Entries", "Discovered", "Started", "Last mutation", "Completed",
          "Snapshot", "Reason", "Summary"]

STATES = {"discovered", "needs_scope", "ready", "processing", "blocked",
          "finalizing", "completed", "failed", "historical"}
TRANSITIONS = {
    "discovered": {"needs_scope", "ready", "processing", "failed", "historical"},
    "needs_scope": {"ready", "processing", "failed", "historical"},
    "ready": {"processing", "failed", "historical"},
    "processing": {"blocked", "finalizing", "failed", "historical"},
    "blocked": {"processing", "failed", "historical"},
    # All verification passed; only the terminal mirror bookkeeping remains.
    # Retryable: a failed export leaves the run here, complete re-runs it.
    "finalizing": {"completed", "failed"},
    "completed": set(),
    # A failed mark may later turn out to be pre-queue history - correcting
    # the record is allowed; nothing else leaves a terminal state.
    "failed": {"historical"},
    "historical": set(),
}
STAGES = ["analysis", "apply", "closure", "done"]
ENTRY_OUTCOMES = {"updated", "no_change", "not_applicable"}
ENTRY_REASON_REQUIRED = {"no_change", "not_applicable"}

# Mechanical folder -> pre-classification label (agent refines via start).
FOLDER_PRECLASS = {
    "02_Transcripts_Inbox": "raw_transcript",
    "01_Meeting_Transcripts": "raw_transcript",
    "02_Chats_and_Emails": "raw_chat",
    "03_Source_Documents": "source_document",
}


def now() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M")


def parse_ts(text: str) -> float:
    try:
        return dt.datetime.strptime(text.strip(), "%Y-%m-%d %H:%M").timestamp()
    except ValueError:
        return 0.0


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
    # Identity is (path, hash): identical content under the same filename in
    # two directories is two runs, so the id carries a path digest too.
    path_digest = hashlib.sha256(
        source_path.replace("\\", "/").casefold().encode("utf-8")).hexdigest()[:4]
    return (f"{date or dt.date.today().strftime('%Y%m%d')}-{slug}-"
            f"{source_hash[:6]}{path_digest}")


def discovery_action(rel: str, digest: str, by_pair: set[tuple[str, str]],
                     by_path: dict[str, str], by_hash: dict[str, str]) -> tuple[str, str]:
    """Identity is (path, hash). Returns (action, related_run_id):
    skip (exact pair known), changed (known path, new content - supersedes),
    duplicate (known content at a new path), or new."""
    if (rel, digest) in by_pair:
        return "skip", ""
    if rel in by_path:
        return "changed", by_path[rel]
    if digest in by_hash:
        return "duplicate", by_hash[digest]
    return "new", ""


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


def needed_scopes(graph: dict, route: dict) -> set[str]:
    """Which scope fields the route demands: derived from its entry
    documents' graph scope, plus the route's own explicit `scope_required`
    (a source can be person-centric even when its entry documents are
    workspace-scoped - e.g. people_case_chat)."""
    docs = graph.get("documents") or {}
    entry_docs = route.get("entry") or []
    derived = {(docs.get(d) or {}).get("scope") for d in entry_docs}
    return (derived | set(route.get("scope_required") or [])) & {"project", "person"}


def scope_key(project: str, person: str) -> str:
    return f"{project.strip()}|{person.strip()}"


def parse_scopes_cell(cell: str) -> list[tuple[str, str]]:
    """Explicit (project, person) tuples - never a cross product."""
    if not cell.strip():
        return []
    return [tuple(s) for s in json.loads(cell)]


def parse_entries_cell(cell: str) -> dict[str, dict[str, list[str]]]:
    """{scope_key: {doc: [outcome, reason]}}."""
    return json.loads(cell) if cell.strip() else {}


def scope_component_matches(stored: str, wanted: str) -> bool:
    stored, wanted = stored.strip(), wanted.strip()
    if not stored:
        return True          # workspace-level record applies to any scope
    if not wanted:
        return False         # scoped record needs the explicit scope
    return stored.casefold() == wanted.casefold()


def entries_for_scope(entries: dict[str, dict[str, list[str]]],
                      project: str, person: str) -> dict[str, list[str]]:
    """Entry outcomes applying to one (project, person) scope - same
    wildcard rule as closure rows: empty stored component matches any,
    a scoped record never matches a different or omitted scope. Merge
    order is by specificity, wildcards first, so an exact scoped outcome
    always wins over a workspace wildcard regardless of insertion order."""
    matching: list[tuple[int, str, dict[str, list[str]]]] = []
    for key, docs in entries.items():
        sp, _, spe = key.partition("|")
        if scope_component_matches(sp, project) and scope_component_matches(spe, person):
            specificity = sum(1 for c in (sp, spe) if c.strip())
            matching.append((specificity, key, docs))
    out: dict[str, list[str]] = {}
    for _, _, docs in sorted(matching, key=lambda m: (m[0], m[1])):
        out.update(docs)
    return out


def validate_entry_outcomes(route_entry: list[str],
                            scoped: dict[str, list[str]]) -> list[str]:
    """Every route entry document needs an outcome; reasons are mandatory
    for no_change/not_applicable. Returns problem strings."""
    problems = []
    for doc in route_entry:
        rec = scoped.get(doc)
        if rec is None:
            problems.append(f"entry document {doc!r} has no recorded outcome "
                            "(record-apply --updated/--no-change/--not-applicable)")
            continue
        outcome, reason = rec[0], rec[1] if len(rec) > 1 else ""
        if outcome not in ENTRY_OUTCOMES:
            problems.append(f"entry document {doc!r}: unknown outcome {outcome!r}")
        elif outcome in ENTRY_REASON_REQUIRED and not reason.strip():
            problems.append(f"entry document {doc!r}: {outcome} requires a reason")
    return problems


def seeds_for_scope(scoped: dict[str, list[str]]) -> set[str]:
    """Only actually-updated documents seed the cascade."""
    return {doc for doc, rec in scoped.items() if rec and rec[0] == "updated"}


def parse_outcome_args(updated: str, no_change: str, not_applicable: str) -> dict[str, list[str]]:
    """CLI lists -> {doc: [outcome, reason]}. Reasoned lists are
    ';'-separated 'doc=reason' pairs (reasons may contain commas)."""
    out: dict[str, list[str]] = {}
    for doc in (d.strip() for d in updated.split(",") if d.strip()):
        out[doc] = ["updated", ""]
    for label, blob in (("no_change", no_change), ("not_applicable", not_applicable)):
        for pair in (p.strip() for p in blob.split(";") if p.strip()):
            doc, eq, reason = pair.partition("=")
            if not eq or not reason.strip():
                raise SystemExit(f"--{label.replace('_', '-')} items need 'doc=reason' "
                                 f"(got {pair!r})")
            out[doc.strip()] = [label, reason.strip()]
    return out


def enumerate_run_scopes(outcome_rows: list[dict], scopes: list[tuple[str, str]],
                         entries: dict[str, dict], variant: str) -> list[tuple[str, str, str]]:
    """Every (project, person, variant) scope the run declared or actually
    used - explicit tuples only, no combination is invented. A run with no
    scope anywhere is a workspace-scoped run, checked as ("", "", variant):
    the enumeration is never empty, so complete can never do zero
    iterations."""
    result: set[tuple[str, str, str]] = set()
    for proj, pers in scopes:
        result.add((proj.strip(), pers.strip(), variant.strip()))
    for key in entries:
        sp, _, spe = key.partition("|")
        result.add((sp.strip(), spe.strip(), variant.strip()))
    for rec in outcome_rows:
        result.add((rec.get("Project", "").strip(), rec.get("Person", "").strip(),
                    rec.get("Route variant", "").strip()))
    if not result:
        result.add(("", "", variant.strip()))
    return sorted(result)


def check_snapshot(log_entries: list[tuple[str, float, str]], run_id: str,
                   last_mutation_ts: float, dirty: bool) -> tuple[str, str]:
    """Verify a mirror snapshot for the run: (sha, "") on success, else
    ("", problem). A qualifying commit mentions the run id and is not older
    than the run's last recorded mutation; the mirror must be clean."""
    if dirty:
        return "", "mirror worktree is dirty - run commit_workspace_state.py first"
    candidates = [(sha, ts) for sha, ts, subject in log_entries if run_id in subject]
    if not candidates:
        return "", (f"no mirror commit mentions {run_id} - run "
                    f"commit_workspace_state.py -m \"<skill>: <source> [{run_id}]\"")
    sha, ts = max(candidates, key=lambda c: c[1])
    # Minute-precision timestamps on both sides - allow the same minute.
    if ts + 60 < last_mutation_ts:
        return "", (f"mirror commit {sha[:8]} mentioning {run_id} predates the run's "
                    "last mutation - re-run commit_workspace_state.py")
    return sha, ""


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
    """Rows as dicts keyed by the CURRENT header - mapped via the sheet's
    own header row, so a schema migration (new columns) reads old rows
    correctly instead of zipping values against the wrong names."""
    from sync_m2_source_docs_to_sheets import read_sheet_values
    rows = read_sheet_values(services, sheet["id"])
    if not rows:
        return []
    sheet_header = rows[0]
    out = []
    for row in rows[1:]:
        by_old = dict(zip(sheet_header, list(row) + [""] * (len(sheet_header) - len(row))))
        out.append({h: by_old.get(h, "") for h in HEADER})
    return out


def write_queue(services, sheet, rows: list[dict]) -> None:
    from pipeline_common import reformat_sheet
    title = queue_tab_title(services, sheet)
    values = [HEADER] + [[r.get(h, "") for h in HEADER] for r in rows]
    services["sheets"].spreadsheets().values().clear(
        spreadsheetId=sheet["id"], range=f"'{title}'").execute()
    services["sheets"].spreadsheets().values().update(
        spreadsheetId=sheet["id"], range=f"'{title}'!A1", valueInputOption="RAW",
        body={"values": values}).execute()
    reformat_sheet(services, sheet["id"], QUEUE_SHEET)


def queue_tab_title(services, sheet) -> str:
    return services["sheets"].spreadsheets().get(
        spreadsheetId=sheet["id"]).execute()["sheets"][0]["properties"]["title"]


def get_run(rows: list[dict], run_id: str) -> dict:
    for row in rows:
        if row["Run ID"] == run_id:
            return row
    raise SystemExit(f"No queue row with Run ID {run_id!r} - see qa_manage.py status.")


def resolve_scope_args(row: dict, project: str, person: str, cmd: str) -> tuple[str, str]:
    """Which (project, person) a scoped record belongs to. Explicit args
    win; a single-scope run defaults to its one declared tuple; a run with
    no declared scope is workspace-scoped ("", ""); a multi-scope run
    REQUIRES explicit args - defaulting there would collapse the record
    into a wildcard that satisfies every scope."""
    if project or person:
        return project.strip(), person.strip()
    scopes = parse_scopes_cell(row["Scopes"])
    if len(scopes) == 1:
        return scopes[0]
    if not scopes:
        return "", ""
    raise SystemExit(f"{cmd}: run {row['Run ID']} declares {len(scopes)} scopes "
                     f"{scopes} - pass --project/--person explicitly so the record "
                     "attaches to one scope instead of becoming a wildcard.")


def mirror_git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(MIRROR), *args],
                          capture_output=True, text=True, encoding="utf-8")


def export_queue_to_mirror(services, sheet, rows: list[dict], run_id: str,
                           label: str) -> str:
    """Capture a queue transition in the mirror: rewrite the queue's mirror
    files (same names the full exporter uses, so its prune step recognizes
    them), commit, and VERIFY the commit exists. Returns the commit SHA
    ("" when there was nothing to commit); raises on any git failure so the
    caller can leave the run in a retryable state instead of reporting a
    success that didn't happen. Content-only follow-up - the verified
    business snapshot keeps its own SHA."""
    title = queue_tab_title(services, sheet)
    values = [HEADER] + [[r.get(h, "") for h in HEADER] for r in rows]
    buf = io.StringIO()
    csv.writer(buf, lineterminator="\n").writerows(values)
    (MIRROR / f"{QUEUE_SHEET}.{title}.csv").write_text(buf.getvalue(), encoding="utf-8")
    (MIRROR / f"{QUEUE_SHEET}.values.json").write_text(
        json.dumps({title: values}, ensure_ascii=False, indent=1), encoding="utf-8")
    res = mirror_git("add", "-A")
    if res.returncode != 0:
        raise SystemExit(f"mirror git add failed: {res.stderr.strip()}")
    if not mirror_git("status", "--porcelain").stdout.strip():
        return ""
    msg = f"queue: {run_id} {label} [{run_id}]"
    res = mirror_git("commit", "-m", msg)
    if res.returncode != 0:
        raise SystemExit(f"mirror commit failed: {res.stderr.strip() or res.stdout.strip()}")
    head = mirror_git("log", "-1", "--format=%H|%s").stdout.strip()
    sha, _, subject = head.partition("|")
    if run_id not in subject:
        raise SystemExit(f"mirror HEAD {sha[:8]} is not the queue commit just made "
                         f"({subject!r}) - inspect the mirror before retrying.")
    return sha


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
               row["Status"] in ("blocked", "needs_scope", "failed", "historical") else ""))


# ---------- commands ----------

def cmd_scan(args) -> int:
    services = get_services_cached()
    sheet = get_or_create_queue(services)
    rows = read_queue(services, sheet)
    by_pair = {(r["Source"], r["Source hash"]) for r in rows}
    by_path = {r["Source"]: r["Run ID"] for r in rows}
    by_hash = {r["Source hash"]: r["Run ID"] for r in rows if r["Source hash"]}

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
            action, related = discovery_action(rel, digest, by_pair, by_path, by_hash)
            if action == "skip":
                continue
            preclass = FOLDER_PRECLASS.get(path.parent.name,
                                           FOLDER_PRECLASS.get(Path(rel_dir).name, "source_document"))
            reason = {"changed": f"content changed - supersedes {related}",
                      "duplicate": f"duplicate content of {related}",
                      "new": ""}[action]
            row = dict.fromkeys(HEADER, "")
            row.update({"Run ID": mint_run_id(rel, digest), "Source": rel,
                        "Source hash": digest, "Source type": preclass,
                        "Status": "discovered", "Discovered": now(),
                        "Reason": reason})
            discovered.append(row)
            by_pair.add((rel, digest))
            by_path[rel] = row["Run ID"]
            by_hash.setdefault(digest, row["Run ID"])

    if discovered:
        write_queue(services, sheet, rows + discovered)
    payload = {"discovered": [{"run_id": r["Run ID"], "source": r["Source"],
                               "preclass": r["Source type"], "note": r["Reason"]}
                              for r in discovered]}
    emit(payload, args.json,
         [f"{len(discovered)} new source(s) discovered:"] +
         [f"  {r['Run ID']}  {r['Source']}  ({r['Source type']})"
          + (f"  [{r['Reason']}]" if r["Reason"] else "") for r in discovered]
         if discovered else ["No new sources."])
    return 0


def cmd_status(args) -> int:
    services = get_services_cached()
    sheet = find_queue(services)
    rows = read_queue(services, sheet) if sheet else []
    terminal = ("completed", "failed", "historical")
    open_rows = [r for r in rows if r["Status"] not in terminal]
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["Status"]] = counts.get(r["Status"], 0) + 1
    payload = {"counts": counts, "open": [{h.lower().replace(" ", "_"): r[h] for h in HEADER
                                          if h not in ("Summary", "Entries")} for r in open_rows]}
    emit(payload, args.json,
         [f"Queue: " + ", ".join(f"{k}={v}" for k, v in sorted(counts.items())) if counts
          else "Queue is empty (run scan first)."] +
         [f"  {row_brief(r)}" for r in open_rows])
    return 0


def cmd_next(args) -> int:
    services = get_services_cached()
    sheet = find_queue(services)
    rows = read_queue(services, sheet) if sheet else []
    priority = ["finalizing", "processing", "ready", "needs_scope", "discovered", "blocked"]
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
                  "variant": pick["Route variant"],
                  "scopes": parse_scopes_cell(pick["Scopes"])}
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
    elif pick["Status"] == "finalizing":
        lines.append("  unfinished: verification passed but the terminal mirror "
                     "bookkeeping did not - re-run `complete` to retry it.")
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


def _update_run(args, mutate) -> dict:
    services = get_services_cached()
    sheet = find_queue(services)
    if not sheet:
        raise SystemExit("No _intake_queue sheet yet - run scan first.")
    rows = read_queue(services, sheet)
    row = get_run(rows, args.run_id)
    mutate(row)
    # Every queue transition counts as run activity - complete compares the
    # snapshot against this, not just Started/closure timestamps.
    row["Last mutation"] = now()
    write_queue(services, sheet, rows)
    return row


def cmd_start(args) -> int:
    graph = load_graph()
    from pipeline_common import SKILL_INVOCATION_SOURCE_TYPES
    if args.source_type not in SKILL_INVOCATION_SOURCE_TYPES:
        raise SystemExit(f"source_type {args.source_type!r} is not canonical "
                         f"({sorted(SKILL_INVOCATION_SOURCE_TYPES)})")
    route = resolve_route(graph, args.source_type, args.variant or "")
    entry = route.get("entry") or []
    need = needed_scopes(graph, route)

    scopes: list[tuple[str, str]] = []
    for blob in args.scope or []:
        proj, sep, pers = blob.partition("|")
        if not sep:
            raise SystemExit(f"--scope takes 'project|person' (got {blob!r}); "
                             "either side may be empty when not applicable")
        scopes.append((proj.strip(), pers.strip()))
    if args.project or args.person:
        scopes.append((args.project.strip(), args.person.strip()))
    # de-dup, preserve order
    scopes = list(dict.fromkeys(scopes))

    def mutate(row: dict) -> None:
        row["Source type"] = args.source_type
        row["Route variant"] = args.variant or ""
        row["Scopes"] = json.dumps(scopes, ensure_ascii=False) if scopes else ""
        row["Project"] = "; ".join(dict.fromkeys(p for p, _ in scopes if p))
        row["Person"] = "; ".join(dict.fromkeys(p for _, p in scopes if p))
        row["Skills"] = ", ".join(route.get("skills") or [])
        missing = sorted(
            s for s in need
            if not scopes or any(not (proj if s == "project" else pers).strip()
                                 for proj, pers in scopes))
        if missing:
            validate_transition(row["Status"], "needs_scope")
            row["Status"] = "needs_scope"
            row["Reason"] = (f"route entry documents are {'/'.join(missing)}-scoped - "
                             "every --scope tuple (or --project/--person) must carry "
                             f"{'/'.join(missing)} (never defaulted silently)")
        else:
            validate_transition(row["Status"], "processing")
            row["Status"], row["Stage"] = "processing", "analysis"
            row["Started"], row["Reason"] = now(), ""

    row = _update_run(args, mutate)
    emit({"run_id": row["Run ID"], "status": row["Status"], "stage": row["Stage"],
          "skills": row["Skills"], "entry": entry, "scopes": scopes,
          "reason": row["Reason"]},
         args.json,
         [row_brief(row)] +
         ([f"  load skills: {row['Skills'] or '(shared rules per graph note)'}",
           f"  entry documents to update: {', '.join(entry)}",
           f"  scopes: {scopes}"]
          if row["Status"] == "processing" else [f"  {row['Reason']}"]))
    return 0 if row["Status"] == "processing" else 1


def cmd_record_analysis(args) -> int:
    def mutate(row: dict) -> None:
        if row["Status"] != "processing":
            raise SystemExit(f"record-analysis requires status=processing (is {row['Status']!r}).")
        if row["Stage"] not in ("analysis", ""):
            raise SystemExit(f"record-analysis belongs to the analysis stage "
                             f"(run is at {row['Stage']!r}).")
        row["Stage"] = "apply"
        row["Summary"] = (row["Summary"] + " | " if row["Summary"] else "") + args.summary.strip()

    row = _update_run(args, mutate)
    emit({"run_id": row["Run ID"], "stage": row["Stage"]}, args.json,
         [row_brief(row),
          "  next: apply the documents, then record-apply per scope."])
    return 0


def cmd_record_apply(args) -> int:
    from check_cascade_closure import build_alias_map, normalize
    graph = load_graph()
    alias_map = build_alias_map(graph)
    outcomes = parse_outcome_args(args.updated, args.no_change, args.not_applicable)
    if not outcomes:
        raise SystemExit("record-apply needs at least one of --updated/--no-change/--not-applicable")
    canon_outcomes: dict[str, list[str]] = {}
    for doc, rec in outcomes.items():
        canon = normalize(doc, alias_map)
        if canon is None:
            raise SystemExit(f"Unknown document {doc!r} - use canonical graph node names.")
        canon_outcomes[canon] = rec

    def mutate(row: dict) -> None:
        if row["Status"] != "processing":
            raise SystemExit(f"record-apply requires status=processing (is {row['Status']!r}).")
        if row["Stage"] == "analysis":
            raise SystemExit("record-analysis first - the analysis stage hasn't been recorded.")
        project, person = resolve_scope_args(row, args.project, args.person, "record-apply")
        entries = parse_entries_cell(row["Entries"])
        key = scope_key(project, person)
        entries.setdefault(key, {}).update(canon_outcomes)
        row["Entries"] = json.dumps(entries, ensure_ascii=False)
        row["Stage"] = "closure"

    row = _update_run(args, mutate)
    emit({"run_id": row["Run ID"], "stage": row["Stage"],
          "entries": parse_entries_cell(row["Entries"])}, args.json,
         [row_brief(row),
          "  next: resolve every cascade edge (resolve-edge), snapshot, complete."])
    return 0


def cmd_resolve_edge(args) -> int:
    import closure_outcomes as co
    services = get_services_cached()
    sheet = find_queue(services)
    rows = read_queue(services, sheet) if sheet else []
    row = get_run(rows, args.run_id)
    if row["Status"] != "processing":
        raise SystemExit(f"resolve-edge requires status=processing (is {row['Status']!r}).")

    project, person = resolve_scope_args(row, args.project, args.person, "resolve-edge")
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
    row["Last mutation"] = now()
    write_queue(services, sheet, rows)
    emit({"run_id": args.run_id, "edge": f"{args.source}->{args.target}",
          "kind": kind, "outcome": args.outcome,
          "scope": [project, person, variant]},
         args.json,
         [f"Recorded: {args.source} -> {args.target} [{kind}] = {args.outcome}"
          + (f" ({args.reason})" if args.reason else "")
          + (f"  @{project}/{person}" if project or person else "")])
    return 0


def cmd_block(args) -> int:
    def mutate(row: dict) -> None:
        validate_transition(row["Status"], "blocked")
        row["Status"], row["Reason"] = "blocked", args.reason
    row = _update_run(args, mutate)
    emit({"run_id": row["Run ID"], "status": "blocked", "reason": row["Reason"]},
         args.json, [row_brief(row)])
    return 0


def cmd_fail(args) -> int:
    def mutate(row: dict) -> None:
        validate_transition(row["Status"], "failed")
        row["Status"], row["Reason"] = "failed", args.reason
    row = _update_run(args, mutate)
    emit({"run_id": row["Run ID"], "status": "failed"}, args.json, [row_brief(row)])
    return 0


def cmd_historical(args) -> int:
    def mutate(row: dict) -> None:
        validate_transition(row["Status"], "historical")
        row["Status"] = "historical"
        row["Reason"] = f"pre-queue history: {args.evidence}"
    row = _update_run(args, mutate)
    emit({"run_id": row["Run ID"], "status": "historical", "evidence": args.evidence},
         args.json, [row_brief(row)])
    return 0


def cmd_resume(args) -> int:
    services = get_services_cached()
    sheet = find_queue(services)
    rows = read_queue(services, sheet) if sheet else []
    row = get_run(rows, args.run_id)

    from closure_outcomes import fetch_outcomes
    outcome_rows = fetch_outcomes(services, args.run_id, all_scopes=True)
    entries = parse_entries_cell(row["Entries"])
    scopes = enumerate_run_scopes(outcome_rows, parse_scopes_cell(row["Scopes"]),
                                  entries, row["Route variant"])

    if args.cont:
        if row["Status"] != "blocked":
            raise SystemExit(f"--continue only reactivates a blocked run (is {row['Status']!r}).")
        validate_transition("blocked", "processing")
        row["Status"], row["Reason"] = "processing", ""
        write_queue(services, sheet, rows)

    lines = [row_brief(row),
             f"  source: {row['Source']}",
             f"  entry outcomes recorded: "
             + (json.dumps(entries, ensure_ascii=False) if entries else "(none)"),
             f"  cascade outcomes recorded: {len(outcome_rows)} across {len(scopes)} scope(s)",
             f"  unfinished stage: {row['Stage'] or row['Status']} - everything recorded "
             "above is done; do not repeat those writes, continue from here."]
    emit({"run_id": row["Run ID"], "status": row["Status"], "stage": row["Stage"],
          "entries": entries, "outcomes": len(outcome_rows),
          "scopes": [list(s) for s in scopes]}, args.json, lines)
    return 0


def cmd_complete(args) -> int:
    from check_cascade_closure import build_resolved, walk
    from closure_outcomes import fetch_outcomes
    from sync_m2_source_docs_to_sheets import read_sheet_values

    services = get_services_cached()
    sheet = find_queue(services)
    rows = read_queue(services, sheet) if sheet else []
    row = get_run(rows, args.run_id)
    if row["Status"] not in ("processing", "finalizing"):
        raise SystemExit(f"complete requires status=processing or finalizing "
                         f"(is {row['Status']!r}).")
    if row["Status"] == "processing" and row["Stage"] != "closure":
        raise SystemExit(f"complete requires stage=closure (is {row['Stage'] or 'analysis'!r}) "
                         "- record-analysis and record-apply must run first, even for "
                         "workspace-only routes.")

    graph = load_graph()
    problems: list[str] = []
    route = resolve_route(graph, row["Source type"], row["Route variant"])
    entry_docs = route.get("entry") or []
    entries = parse_entries_cell(row["Entries"])
    all_rows = fetch_outcomes(services, args.run_id, all_scopes=True)
    scopes = enumerate_run_scopes(all_rows, parse_scopes_cell(row["Scopes"]),
                                  entries, row["Route variant"])

    # 1+2. Per scope: every entry document has a valid outcome; cascade from
    # the actually-updated ones must be strictly closed for that scope.
    last_outcome_ts = max(parse_ts(row["Started"]), parse_ts(row["Last mutation"]))
    for proj, pers, variant in scopes:
        label = f"scope ({proj or '-'}, {pers or '-'}, {variant or '-'})"
        scoped_entries = entries_for_scope(entries, proj, pers)
        problems.extend(f"{label}: {p}"
                        for p in validate_entry_outcomes(entry_docs, scoped_entries))
        seeds = seeds_for_scope(scoped_entries)
        scoped_rows = fetch_outcomes(services, args.run_id, proj, pers, variant)
        for rec in scoped_rows:
            last_outcome_ts = max(last_outcome_ts, parse_ts(rec.get("Timestamp", "")))
        resolved, warns = build_resolved(scoped_rows, graph)
        problems.extend(f"{label}: {w}" for w in warns)
        open_items: list[str] = []
        lines: list[str] = []
        visited_req = set(seeds)
        for node in sorted(seeds):
            walk(graph, node, seeds, visited_req, set(), 0, False, True,
                 resolved, open_items, lines)
        problems.extend(f"{label}: unresolved edge {item}" for item in open_items)

    # 3. A _skill_invocations row must carry the exact run token.
    from pipeline_common import get_skill_invocations_sheet
    token = f"run:{args.run_id}"
    inv_rows = read_sheet_values(services, get_skill_invocations_sheet(services)["id"])
    if not any(token in " | ".join(r) for r in inv_rows[1:]):
        problems.append(f"no _skill_invocations row carries the token '{token}' - "
                        "log_skill_invocation() with it in Notes")

    # 4. Clean mirror snapshot mentioning the run, not older than the run's
    # last recorded mutation; its SHA is persisted on the row.
    dirty = bool(mirror_git("status", "--porcelain").stdout.strip())
    log_raw = mirror_git("log", "-50", "--format=%H|%ct|%s").stdout
    log_entries = []
    for line in log_raw.splitlines():
        sha, _, rest = line.partition("|")
        ts, _, subject = rest.partition("|")
        try:
            log_entries.append((sha, float(ts), subject))
        except ValueError:
            continue
    sha, snap_problem = check_snapshot(log_entries, args.run_id, last_outcome_ts, dirty)
    if snap_problem:
        problems.append(snap_problem)

    if problems:
        emit({"run_id": args.run_id, "completed": False, "problems": problems},
             args.json,
             [f"NOT completed - {len(problems)} unmet requirement(s):"] +
             [f"  - {p}" for p in problems])
        return 1

    # Verification passed. Two-phase terminal transition so a mirror
    # bookkeeping failure never yields a false success or a stuck terminal
    # row: finalizing is written and exported first (verified commit),
    # completed only after that commit exists; a failure at any point
    # leaves the run in finalizing, and complete is re-runnable from there.
    if row["Status"] == "processing":
        validate_transition(row["Status"], "finalizing")
        row["Status"], row["Snapshot"] = "finalizing", sha
        row["Last mutation"] = now()
        write_queue(services, sheet, rows)
    export_queue_to_mirror(services, sheet, rows, args.run_id, "finalizing")

    validate_transition("finalizing", "completed")
    row["Status"], row["Stage"], row["Completed"] = "completed", "done", now()
    row["Snapshot"] = row["Snapshot"] or sha
    write_queue(services, sheet, rows)
    try:
        export_queue_to_mirror(services, sheet, rows, args.run_id, "completed")
        terminal_note = "terminal queue state exported to the mirror."
    except SystemExit as exc:
        # Completion itself is verified and recorded; only the final
        # bookkeeping commit failed - the next snapshot will carry it.
        terminal_note = (f"WARNING: terminal-state mirror commit failed ({exc}); "
                         "the next workspace snapshot will capture it.")
    emit({"run_id": args.run_id, "completed": True, "snapshot": row["Snapshot"]},
         args.json,
         [f"{args.run_id} completed: entry outcomes valid, closure strict-CLOSED per "
          f"scope, invocation token present, snapshot {row['Snapshot'][:8]} verified "
          f"and recorded; {terminal_note}"])
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("scan", help="discover new/changed source files")
    sub.add_parser("status", help="queue overview")
    sub.add_parser("next", help="most actionable run")

    p = sub.add_parser("start", help="classify + activate a run")
    p.add_argument("run_id")
    p.add_argument("--source-type", required=True)
    p.add_argument("--variant", default="")
    p.add_argument("--project", default="")
    p.add_argument("--person", default="")
    p.add_argument("--scope", action="append", default=[],
                   metavar="PROJECT|PERSON",
                   help="explicit scope tuple; repeat for multi-scope runs")

    p = sub.add_parser("record-analysis", help="analysis summary (stage -> apply)")
    p.add_argument("run_id")
    p.add_argument("--summary", required=True)

    p = sub.add_parser("record-apply", help="per-scope entry outcomes (stage -> closure)")
    p.add_argument("run_id")
    p.add_argument("--project", default="")
    p.add_argument("--person", default="")
    p.add_argument("--updated", default="", help="comma-separated documents actually written")
    p.add_argument("--no-change", dest="no_change", default="",
                   help="';'-separated doc=reason pairs")
    p.add_argument("--not-applicable", dest="not_applicable", default="",
                   help="';'-separated doc=reason pairs")

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

    p = sub.add_parser("historical", help="terminal: processed before the queue existed")
    p.add_argument("run_id")
    p.add_argument("--evidence", required=True,
                   help="where the pre-queue processing is recorded "
                        "(_skill_invocations date, evidence_log row, ...)")

    p = sub.add_parser("resume", help="unfinished stage + what remains")
    p.add_argument("run_id")
    p.add_argument("--continue", dest="cont", action="store_true",
                   help="reactivate a blocked run")

    p = sub.add_parser("complete", help="verification gate -> completed")
    p.add_argument("run_id")

    args = parser.parse_args()
    return {"scan": cmd_scan, "status": cmd_status, "next": cmd_next,
            "start": cmd_start, "record-analysis": cmd_record_analysis,
            "record-apply": cmd_record_apply, "resolve-edge": cmd_resolve_edge,
            "block": cmd_block, "fail": cmd_fail, "historical": cmd_historical,
            "resume": cmd_resume, "complete": cmd_complete}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
