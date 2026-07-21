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
                       completed | failed | historical | ignored

    stages within processing: analysis -> apply -> closure

`historical` is the terminal state for sources that were already processed
before the queue existed (with evidence) - being pre-queue is not a
processing failure. `failed` may be corrected to `historical` when
migration evidence turns up. `ignored` (with a category:
non_intake_course_material / reference_material / duplicate_data_quality /
other) is for sources that are not intake at all - distinct from
historical, which asserts prior processing. Subtrees that are categorically
non-intake are additionally excluded from discovery via SCAN_EXCLUDE.

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
    add-scope <run-id> --project P --person X
                                  declare a scope the analysis discovered;
                                  explicit scope args elsewhere must name a
                                  declared tuple (a typo cannot silently
                                  create a scope)
    block <run-id> --reason "..." mark waiting on a gate/answer
    resume <run-id> [--continue]  exact unfinished stage + what remains;
                                  --continue reactivates a blocked run
    archive-source <run-id>       move the closure-stage original from
                                  00_Inbox to its run-specific processed
                                  archive before taking the final snapshot
    complete <run-id>             verification gate: every entry document
                                  has a per-scope outcome, strict closure
                                  per scope, a `run:<run-id>` token in
                                  _skill_invocations, and a clean mirror
                                  snapshot newer than the run's last
                                  mutation (its SHA is persisted). The
                                  intended terminal state is committed to
                                  the mirror (verified, bundle refreshed)
                                  BEFORE the final Drive transition; any
                                  failure leaves the run retryable in
                                  finalizing - never a false success
    fail <run-id> --reason "..."  give up explicitly (kept in history)
    ignore <run-id> --category C [--reason "..."]
                                  terminal: not an intake source at all
    historical <run-id> --evidence "..."
                                  terminal: processed before the queue
                                  existed; evidence required
    dashboard [--limit N] [--include-completed] [--include-ignored]
          [--project P] [--person X]
                                  read-only operator summary: actionable
                                  runs grouped by what's next (start /
                                  record-analysis / record-apply /
                                  resolve-edge / commit_workspace_state /
                                  complete), blocked runs, finalizing
                                  retries, integrity issues found by
                                  reusing the same review/evaluate logic
                                  (bounded by --limit so it stays cheap),
                                  plus a read-only 00_Inbox/90_Storage
                                  filesystem summary. Never creates,
                                  writes, or mutates anything.
    guide <run-id>                read-only deterministic next-steps for
                                  ONE selected run (dashboard says what
                                  needs attention across the queue; guide
                                  drills into a single run_id): identity,
                                  the graph route's interpretation
                                  (skills/entry docs/scopes), a
                                  stage-specific checklist with exact
                                  command templates (start/needs_scope
                                  scope requirements, record-analysis,
                                  per-scope record-apply gaps, per-edge
                                  resolve-edge, commit_workspace_state.py,
                                  complete, resume, historical), and only
                                  the guardrails relevant to that stage.
                                  Reuses review/evaluate_run exclusively;
                                  never creates, writes, or mutates
                                  anything.

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
import re
import subprocess
import sys
from pathlib import Path
import contextlib
import traceback
from dataclasses import dataclass, field

@dataclass
class EvaluationResult:
    ready_for_completion: bool
    entry_problems: list[str]
    unresolved_edges: list[str]
    warnings: list[str]
    snapshot_sha: str | None
    snapshot_problem: str
    invocation_present: bool | None

    @property
    def all_problems(self) -> list[str]:
        p = list(self.entry_problems)
        p.extend(self.unresolved_edges)
        if self.snapshot_problem:
            p.append(self.snapshot_problem)
        if self.invocation_present is False:
            p.append("Missing invocation token")
        return p

import yaml
from export_source_text import source_text_requirement

from mirror_common import mirror_git, mirror_git_bytes, assert_private_mirror

if (isinstance(sys.stdout, io.TextIOWrapper) and sys.stdout.encoding
        and sys.stdout.encoding.lower() not in ("utf-8", "utf8")):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent))

GRAPH_PATH = Path(__file__).resolve().parent.parent / "document_graph.yaml"
DATA_ROOT = Path(r"G:\My Drive\QA_Management")
MIRROR = Path.home() / "Documents" / "qa-drive-mirror"
SCAN_DIRS = [
    "00_Inbox",
]
SCAN_EXCLUDE: list[str] = []
SCAN_EXTS = {".txt", ".md", ".docx", ".doc", ".pdf", ".csv", ".xlsx"}

QUEUE_SHEET = "_intake_queue"
HEADER = ["Run ID", "Source", "Source hash", "Current source", "Source disposition",
          "Source type", "Route variant",
          "Project", "Person", "Scopes", "Status", "Stage", "Skills",
          "Entries", "Discovered", "Started", "Last mutation", "Completed",
          "Snapshot", "Reason", "Summary", "Source text version"]

STATES = {"discovered", "needs_scope", "ready", "processing", "blocked",
          "finalizing", "completed", "failed", "historical", "ignored"}
TRANSITIONS = {
    "discovered": {"needs_scope", "ready", "processing", "failed", "historical", "ignored"},
    "needs_scope": {"ready", "processing", "failed", "historical", "ignored"},
    "ready": {"processing", "failed", "historical", "ignored"},
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
    # Not intake at all (course material, template/rule sources, duplicate
    # artifacts) - distinct from historical, which means "was processed".
    "ignored": set(),
}
IGNORE_CATEGORIES = {"non_intake_course_material", "reference_material",
                     "duplicate_data_quality", "other"}
STAGES = ["analysis", "apply", "closure", "done"]
ENTRY_OUTCOMES = {"updated", "no_change", "not_applicable"}
ENTRY_REASON_REQUIRED = {"no_change", "not_applicable"}

# Mechanical folder -> pre-classification label (agent refines via start).
FOLDER_PRECLASS = {
    "00_Inbox": "source_document",
}

# dashboard: how many rows per section get an (expensive) evaluate_run()
# integrity pass, and how many rows are listed per section - keeps the
# command cheap regardless of queue size.
DEFAULT_DASHBOARD_LIMIT = 20


def now() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M")


def parse_ts(text: str) -> float:
    try:
        return dt.datetime.strptime(text.strip(), "%Y-%m-%d %H:%M").timestamp()
    except ValueError:
        return 0.0


# ---------- pure helpers (unit-tested) ----------


def check_source_text_snapshot(sha: str, row: dict) -> list[str]:
    v = str(row.get("Source text version", "")).strip()
    req = source_text_requirement(row)

    if v == "1" and req != "required":
        return [f"Integrity error: row has Source text version 1 but requirement is {req}"]

    if req == "required" and v == "1":
        res = mirror_git_bytes(MIRROR, "show", f"{sha}:_source_text_manifest.json")
        if res.returncode != 0:
            return ["_source_text_manifest.json not found in snapshot"]
        try:
            import json
            manifest = json.loads(res.stdout.decode("utf-8"))
        except Exception as e:
            return [f"Malformed _source_text_manifest.json: {e}"]

        key = f"{row.get('Run ID', '')}:v1"
        if key not in manifest:
            return [f"Run {key} missing from _source_text_manifest.json"]

        entry = manifest[key]

        from export_source_text import validate_manifest, verify_manifest_entry
        try:
            validate_manifest({key: entry})
        except Exception as e:
            return [f"Manifest integrity failed: {e}"]

        def blob_loader(path: str) -> bytes:
            blob_res = mirror_git_bytes(MIRROR, "show", f"{sha}:{path}")
            if blob_res.returncode != 0:
                raise RuntimeError(f"Blob {path} not found in snapshot")
            return blob_res.stdout

        errs = verify_manifest_entry(row, entry, blob_loader, raw_source_resolver=None)
        return errs

    return []

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


def is_excluded(rel: str) -> bool:
    """True when the path sits in a SCAN_EXCLUDE subtree."""
    norm = rel.replace("/", "\\").casefold()
    return any(norm.startswith(prefix.casefold() + "\\") or norm == prefix.casefold()
               for prefix in SCAN_EXCLUDE)


def discovery_action(rel: str, digest: str, by_pair: set[tuple[str, str]],
                     by_path: dict[str, str], by_hash: dict[str, str]) -> tuple[str, str]:
    """Identity is (path, hash). Returns (action, related_run_id):
    skip (exact pair known), changed (known path, new content - supersedes),
    duplicate (known content at a new path), or new."""
    rel = rel.replace("\\", "/")
    if (rel, digest) in by_pair:
        return "skip", ""
    if rel in by_path:
        return "changed", by_path[rel]
    if digest in by_hash:
        return "duplicate", by_hash[digest]
    return "new", ""


def queue_discovery_indexes(
    rows: list[dict],
) -> tuple[set[tuple[str, str]], dict[str, str], dict[str, str]]:
    by_pair: set[tuple[str, str]] = set()
    by_path: dict[str, str] = {}
    by_hash: dict[str, str] = {}
    for row in rows:
        digest = str(row.get("Source hash", ""))
        run_id = str(row.get("Run ID", ""))
        paths = {
            str(row.get("Source", "")).strip(),
            str(row.get("Current source", "")).strip(),
        }
        for path in paths - {""}:
            normalized = path.replace("\\", "/")
            by_pair.add((normalized, digest))
            by_path[normalized] = run_id
        if digest:
            by_hash[digest] = run_id
    return by_pair, by_path, by_hash


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


def missing_scope_fields(need: set[str], project: str, person: str) -> list[str]:
    """Which of the route's required scope fields this tuple fails to
    carry. Shared by start and add-scope so a later-added scope can't
    bypass the validation start enforces."""
    return sorted(s for s in need
                  if not (project if s == "project" else person).strip())


def dedup_scopes(scopes: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Order-preserving, case-insensitive dedup (first spelling wins) -
    membership checks are casefold, so dedup must be too."""
    seen: set[tuple[str, str]] = set()
    out: list[tuple[str, str]] = []
    for proj, pers in scopes:
        key = (proj.strip().casefold(), pers.strip().casefold())
        if key not in seen:
            seen.add(key)
            out.append((proj.strip(), pers.strip()))
    return out


def needed_scopes(graph: dict, route: dict) -> set[str]:
    """Which scope fields the route demands: derived from its entry
    documents' graph scope, plus the route's own explicit `scope_required`
    (a source can be person-centric even when its entry documents are
    workspace-scoped - e.g. people_case_chat)."""
    docs = graph.get("documents") or {}
    entry_docs = route.get("entry") or []
    needed: set[str] = set()
    for doc in entry_docs:
        scope = (docs.get(doc) or {}).get("scope")
        if isinstance(scope, str) and scope in ("project", "person"):
            needed.add(scope)
    for scope in route.get("scope_required") or []:
        if isinstance(scope, str) and scope in ("project", "person"):
            needed.add(scope)
    return needed


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


def check_snapshot(log_entries: list[tuple[str, float, str]], row: dict,
                   last_mutation_ts: float, dirty: bool) -> tuple[str, str]:
    """Verify a mirror snapshot for the run: (sha, "") on success, else
    ("", problem). A qualifying commit mentions the run id and is not older
    than the run's last recorded mutation; the mirror must be clean."""
    run_id = row.get("Run ID", "")
    req = source_text_requirement(row)
    v1 = str(row.get("Source text version", "")).strip() == "1"

    # If finalizing, we use the stored snapshot exclusively, if it exists
    is_finalizing = row.get("Status") == "finalizing"
    if is_finalizing:
        if dirty:
            return "", "mirror worktree is dirty - run commit_workspace_state.py first"
        snapshot = row.get("Snapshot", "")
        sha = snapshot if isinstance(snapshot, str) else ""
        if not sha:
            return "", "run is finalizing but missing Snapshot SHA"
        # Validate that the snapshot exists in logs
        found = any(s == sha for s, _, _ in log_entries)
        if not found:
            return "", f"Snapshot {sha} not found in log"
    else:
        if dirty:
            return "", "mirror worktree is dirty - run commit_workspace_state.py first"
        candidates = [(s, ts) for s, ts, subject in log_entries if run_id in subject]
        if not candidates:
            if req == "required" and v1:
                return "", "required_pending_snapshot"
            return "", (f"no mirror commit mentions {run_id} - run "
                        f"commit_workspace_state.py -m \"<skill>: <source> [{run_id}]\"")
        sha, ts = max(candidates, key=lambda c: c[1])
        if ts + 60 < last_mutation_ts:
            if req == "required" and v1:
                return "", "required_pending_snapshot"
            return "", (f"mirror commit {sha[:8]} mentioning {run_id} predates the run's "
                        "last mutation - re-run commit_workspace_state.py")

    # Now we have a specific SHA. Verify source text if required.
    st_errors = check_source_text_snapshot(sha, row)
    if st_errors:
        return "", "\n  ".join(st_errors)

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
    must name a DECLARED scope tuple (a typo would otherwise silently
    create a new scope through entries/outcomes - use `add-scope` when
    analysis legitimately discovers one); a single-scope run defaults to
    its one declared tuple; a run with no declared scope is
    workspace-scoped ("", ""); a multi-scope run REQUIRES explicit args -
    defaulting there would collapse the record into a wildcard that
    satisfies every scope."""
    scopes = parse_scopes_cell(row["Scopes"])
    if project or person:
        wanted = (project.strip(), person.strip())
        declared = {(p.strip().casefold(), pe.strip().casefold()) for p, pe in scopes}
        if (wanted[0].casefold(), wanted[1].casefold()) not in declared:
            raise SystemExit(
                f"{cmd}: scope {wanted} is not declared on run {row['Run ID']} "
                f"(declared: {scopes or '[workspace]'}). If the analysis genuinely "
                "surfaced a new scope, declare it first: qa_manage.py add-scope "
                f"{row['Run ID']} --project ... --person ...")
        return wanted
    if len(scopes) == 1:
        return scopes[0]
    if not scopes:
        return "", ""
    raise SystemExit(f"{cmd}: run {row['Run ID']} declares {len(scopes)} scopes "
                     f"{scopes} - pass --project/--person explicitly so the record "
                     "attaches to one scope instead of becoming a wildcard.")


def is_queue_only_dirt(porcelain: str) -> bool:
    """True when every dirty path in the mirror belongs to the queue's own
    export (a half-finished terminal commit): the finalizing recovery path
    may proceed through such dirt, anything else is real dirt."""
    lines = [line for line in porcelain.splitlines() if line.strip()]
    if not lines:
        return False
    for line in lines:
        path = line[3:].strip().strip('"')
        name = path.replace("\\", "/").rsplit("/", 1)[-1]
        if not (name.startswith(f"{QUEUE_SHEET}.") or name == "_manifest.json"):
            return False
    return True




def export_queue_terminal(services, sheet, terminal_rows: list[dict], run_id: str) -> tuple[str, list[str]]:
    assert_private_mirror(MIRROR, DATA_ROOT)
    """Commit the run's INTENDED terminal queue state to the mirror -
    called before the final Drive transition, so the mirror always carries
    the terminal representation the moment the run becomes terminal (and a
    failure here leaves the run retryable in finalizing, never a false
    success).

    Idempotent: files are rewritten in place; if nothing changed and no
    dirt is staged, the previously verified commit is located and its SHA
    returned. Writes the diff+values restore layers (same names the full
    exporter uses), updates _manifest.json, drops the now-stale queue xlsx
    (the next full export's change gate regenerates a missing xlsx), and
    refreshes the Drive bundle after committing - same guarantees as a
    full export, minus the untouched other documents."""
    title = queue_tab_title(services, sheet)
    values = [HEADER] + [[r.get(h, "") for h in HEADER] for r in terminal_rows]
    buf = io.StringIO()
    csv.writer(buf, lineterminator="\n").writerows(values)
    (MIRROR / f"{QUEUE_SHEET}.{title}.csv").write_text(buf.getvalue(), encoding="utf-8")
    (MIRROR / f"{QUEUE_SHEET}.values.json").write_text(
        json.dumps({title: values}, ensure_ascii=False, indent=1), encoding="utf-8")
    manifest_path = MIRROR / "_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    manifest[f"{QUEUE_SHEET}.values.json"] = {"fileId": sheet["id"], "name": QUEUE_SHEET,
                                              "kind": "spreadsheet-values"}
    # The pre-terminal xlsx is stale the moment the terminal rows land; a
    # missing xlsx is regenerated by the full exporter's change gate.
    manifest.pop(f"{QUEUE_SHEET}.xlsx", None)
    (MIRROR / f"{QUEUE_SHEET}.xlsx").unlink(missing_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=1, sort_keys=True),
                             encoding="utf-8")

    res = mirror_git(MIRROR, "add", "-A")
    if res.returncode != 0:
        raise SystemExit(f"mirror git add failed: {res.stderr.strip()}")
    msg = f"queue: {run_id} completed [{run_id}]"
    if not mirror_git(MIRROR, "status", "--porcelain").stdout.strip():
        # Nothing to commit - a previous attempt already landed it; verify,
        # and refresh the bundle too (the earlier attempt may have crashed
        # between its commit and its bundle refresh).
        for line in mirror_git(MIRROR, "log", "-20", "--format=%H|%s").stdout.splitlines():
            sha, _, subject = line.partition("|")
            if subject.strip() == msg:
                from commit_workspace_state import refresh_bundle
                bundle_msg = refresh_bundle(MIRROR)
                return sha, [bundle_msg] if "FAILED" in bundle_msg else []
        raise SystemExit("mirror is clean but no terminal queue commit for "
                         f"{run_id} exists - inspect the mirror before retrying.")
    res = mirror_git(MIRROR, "commit", "-m", msg)
    if res.returncode != 0:
        raise SystemExit(f"mirror commit failed: {res.stderr.strip() or res.stdout.strip()}")
    head = mirror_git(MIRROR, "log", "-1", "--format=%H|%s").stdout.strip()
    sha, _, subject = head.partition("|")
    if run_id not in subject:
        raise SystemExit(f"mirror HEAD {sha[:8]} is not the queue commit just made "
                         f"({subject!r}) - inspect the mirror before retrying.")
    from commit_workspace_state import refresh_bundle
    bundle_msg = refresh_bundle(MIRROR)
    return sha, [bundle_msg] if "FAILED" in bundle_msg else []


# ---------- output ----------

@dataclass
class CommandResult:
    ok: bool = True
    data: dict = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    human_lines: list[str] = field(default_factory=list)
    exit_code: int = 0


def build_json_envelope(ok: bool, command: str, data: dict, warnings: list[str], errors: list[str]) -> dict:
    return {
        "schema_version": 1,
        "ok": ok,
        "command": command,
        "data": data,
        "warnings": warnings,
        "errors": errors
    }

class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        if "--json" in sys.argv:
            cmd = next((arg for arg in sys.argv[1:] if not arg.startswith("-")), "unknown")
            envelope = build_json_envelope(False, cmd, {}, [], [message])
            print(json.dumps(envelope, ensure_ascii=False, indent=1))
            sys.exit(1)
        else:
            super().error(message)


@contextlib.contextmanager
def stdout_redirected(to=sys.stderr):
    original_stdout = sys.stdout
    sys.stdout = to
    try:
        yield
    finally:
        sys.stdout = original_stdout


def row_brief(row: dict) -> str:
    scope = " / ".join(x for x in (row["Project"], row["Person"]) if x)
    return (f"{row['Run ID']}  [{row['Status']}"
            + (f":{row['Stage']}" if row["Stage"] else "") + "]  "
            + (f"{row['Source type']}" if row["Source type"] else "unclassified")
            + (f"({row['Route variant']})" if row["Route variant"] else "")
            + (f"  {scope}" if scope else "")
            + (f"  reason: {row['Reason']}" if row["Reason"] and
               row["Status"] in ("blocked", "needs_scope", "failed", "historical",
                                 "ignored") else ""))


# ---------- dashboard (read-only) ----------


def row_matches_scope_filter(row: dict, project: str, person: str) -> bool:
    """True when a row belongs to the requested (project, person) filter.
    Prefers the declared Scopes tuples (accurate for multi-scope runs);
    falls back to the semicolon-joined Project/Person fields for rows that
    never declared an explicit scope (discovered/needs_scope). An empty
    filter matches everything."""
    project, person = project.strip(), person.strip()
    if not project and not person:
        return True
    scopes = parse_scopes_cell(row.get("Scopes", ""))
    if scopes:
        return any(
            (not project or p.strip().casefold() == project.casefold())
            and (not person or pe.strip().casefold() == person.casefold())
            for p, pe in scopes
        )
    proj_list = [x.strip().casefold() for x in str(row.get("Project", "")).split(";") if x.strip()]
    pers_list = [x.strip().casefold() for x in str(row.get("Person", "")).split(";") if x.strip()]
    if project and project.casefold() not in proj_list:
        return False
    if person and person.casefold() not in pers_list:
        return False
    return True


def dashboard_recommended_command(row: dict, eval_res: "EvaluationResult | None" = None) -> str:
    """Deterministic next CLI command for a queue row - mirrors
    get_recommended_action's state-machine mapping but names the actual
    command (and, for the closure stage, picks between resolve-edge and
    commit_workspace_state/complete using the same evaluate_run() problem
    categories `review` already reports). Never a judgment call - purely a
    function of (status, stage, eval_res)."""
    status = row.get("Status", "")
    stage = row.get("Stage", "")
    run_id = row.get("Run ID", "")

    if status == "discovered":
        return (f'start {run_id} --source-type <type> [--variant <variant>] '
                f'[--scope "Project|Person"]  (read + classify the source first)')
    if status == "needs_scope":
        src_type = row.get("Source type") or "<type>"
        return (f'start {run_id} --source-type {src_type} --scope "Project|Person"  '
                f'({row.get("Reason") or "missing required scope"})')
    if status == "blocked":
        return f'resume {run_id} --continue  ({row.get("Reason", "")})'
    if status == "finalizing":
        return f'complete {run_id}'
    if status == "processing":
        if stage in ("", "analysis"):
            return f'record-analysis {run_id} --summary "..."'
        if stage == "apply":
            return f'record-apply {run_id} --project <P> --person <X> --updated d1,d2'
        if stage == "closure":
            if eval_res is None:
                return f'review {run_id} --json  (evaluate before deciding the next command)'
            if any("archive-source" in p for p in eval_res.entry_problems):
                return f'archive-source {run_id}'
            if any("entry document" in p for p in eval_res.entry_problems):
                return f'record-apply {run_id} --project <P> --person <X> --updated d1,d2'
            if eval_res.unresolved_edges:
                return (f'resolve-edge {run_id} --source <A> --target <B> '
                        f'--outcome <updated|no_change|gated|regenerated>')
            if eval_res.invocation_present is False or eval_res.snapshot_problem:
                return f'commit_workspace_state.py -m "<skill>: <source> [{run_id}]"'
            if eval_res.ready_for_completion:
                return f'complete {run_id}'
            return f'review {run_id} --json  (unresolved warning - inspect before completing)'
    if status in ("completed", "failed", "historical", "ignored"):
        return "none"
    return "unknown"


def dashboard_row_summary(row: dict) -> dict:
    return {
        "run_id": row.get("Run ID", ""),
        "status": row.get("Status", ""),
        "stage": row.get("Stage", ""),
        "source": row.get("Source", ""),
        "source_type": row.get("Source type", ""),
        "route_variant": row.get("Route variant", ""),
        "project": row.get("Project", ""),
        "person": row.get("Person", ""),
        "reason": row.get("Reason", ""),
        "discovered": row.get("Discovered", ""),
        "started": row.get("Started", ""),
        "completed": row.get("Completed", ""),
    }


def inbox_snapshot(data_root: Path, rows: list[dict]) -> dict:
    """Read-only count of currently actionable files sitting in 00_Inbox,
    grouped by whatever classification the queue already recorded for that
    exact path (never guesses a classification for a file the queue
    hasn't seen - that's what `scan` + `start` are for). Pure filesystem
    read: no file is created, moved, or deleted."""
    classified: dict[str, str] = {}
    for row in rows:
        current = str(row.get("Current source", "")).strip().replace("\\", "/")
        if current and row.get("Source disposition", "inbox") == "inbox":
            classified[current] = row.get("Source type") or "unclassified"

    by_type: dict[str, int] = {}
    total = 0
    inbox_root = data_root / "00_Inbox"
    if inbox_root.exists():
        for path in sorted(inbox_root.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in SCAN_EXTS:
                continue
            rel = path.relative_to(data_root).as_posix()
            if is_excluded(rel):
                continue
            total += 1
            label = classified.get(rel, "undiscovered (run scan)")
            by_type[label] = by_type.get(label, 0) + 1
    return {"total_files": total, "by_source_type": by_type}


def storage_snapshot(data_root: Path) -> dict:
    """Read-only count of already-processed sources under
    90_Storage/Processed_Sources/<year>/<month>/<run-id>, grouped by
    year-month. Pure filesystem read: no directory is created or moved."""
    root = data_root / "90_Storage" / "Processed_Sources"
    by_month: dict[str, int] = {}
    total = 0
    if root.exists():
        for year_dir in sorted(p for p in root.iterdir() if p.is_dir()):
            for month_dir in sorted(p for p in year_dir.iterdir() if p.is_dir()):
                count = sum(1 for p in month_dir.iterdir() if p.is_dir())
                if count:
                    by_month[f"{year_dir.name}-{month_dir.name}"] = count
                    total += count
    return {"total_processed_runs": total, "by_month": by_month}


# ---------- guide (read-only, one run) ----------

# These two patterns parse evaluate_run()'s own problem-string format back
# into structured fields - the format is owned by evaluate_run/
# check_cascade_closure.walk (see their f-string construction), never
# reverse-engineered from free text. A non-match returns None rather than
# guessing, so a future wording change fails closed (no command shown)
# instead of emitting a wrong command.
_UNRESOLVED_EDGE_RE = re.compile(
    r"^scope \((?P<project>.*?), (?P<person>.*?), (?P<variant>.*?)\): "
    r"unresolved edge (?P<source>\S+) -> (?P<target>\S+) \[(?P<kind>\w+)\]$"
)
_MISSING_ENTRY_RE = re.compile(
    r"^scope \((?P<project>.*?), (?P<person>.*?), (?P<variant>.*?)\): "
    r"entry document '(?P<doc>[^']+)' has no recorded outcome"
)


def _scope_placeholder_to_empty(value: str) -> str:
    return "" if value == "-" else value


def parse_unresolved_edge_entry(entry: str) -> dict | None:
    """One evaluate_run() unresolved_edges string -> structured fields for
    an exact resolve-edge command. None if the string doesn't match this
    exact shape (never guess)."""
    m = _UNRESOLVED_EDGE_RE.match(entry)
    if not m:
        return None
    d = m.groupdict()
    return {"project": _scope_placeholder_to_empty(d["project"]),
            "person": _scope_placeholder_to_empty(d["person"]),
            "variant": _scope_placeholder_to_empty(d["variant"]),
            "source": d["source"], "target": d["target"], "kind": d["kind"]}


def parse_missing_entry_document(entry: str) -> dict | None:
    """One evaluate_run() entry_problems string for a missing record-apply
    outcome -> structured fields. None if it doesn't match this exact
    shape (e.g. it's the archive-source hint instead)."""
    m = _MISSING_ENTRY_RE.match(entry)
    if not m:
        return None
    d = m.groupdict()
    return {"project": _scope_placeholder_to_empty(d["project"]),
            "person": _scope_placeholder_to_empty(d["person"]),
            "variant": _scope_placeholder_to_empty(d["variant"]), "doc": d["doc"]}


def guide_scope_cli_args(project: str, person: str) -> str:
    """Both flags together whenever either side is non-empty, so the CLI's
    own exact-tuple scope matching (resolve_scope_args) is unambiguous -
    passing only one side of a declared (project, person) tuple would not
    match it."""
    if not project and not person:
        return ""
    return f' --project "{project}" --person "{person}"'


def guide_stage_details(row: dict, graph: dict, route: dict,
                        eval_res: EvaluationResult, ctx: "ReviewContext") -> tuple[list[str], list[str], dict]:
    """(checklist, commands, extra_data) for one run's current
    status/stage - the deterministic "what do I do next" logic guide
    exists for. Pure given (row, graph, route, eval_res, ctx); no I/O."""
    status = row.get("Status", "")
    stage = row.get("Stage", "")
    run_id = row.get("Run ID", "")
    checklist: list[str] = []
    commands: list[str] = []
    extra: dict = {}

    if status == "discovered":
        routed_types = sorted((graph.get("sources") or {}).keys())
        current_source = str(row.get("Current source", "")).strip()
        source = str(row.get("Source", "")).strip()
        if current_source:
            # Current source tracks the live file location and is updated on
            # every move (e.g. archive-source); Source is the immutable
            # (path, hash) discovery identity and can point at a stale/
            # legacy path once a run's file has moved - reading it directly
            # once caused an agent to try opening a nonexistent file.
            read_step = f"Read the source at Current source: {current_source}"
        else:
            read_step = f"Current source is blank; read original Source: {source}"
        checklist = [
            read_step,
            "Classify source_type and route variant from the CONTENT, not the filename.",
            f"Routed source types: {', '.join(routed_types)}.",
            "Determine the (project, person) scope the chosen route requires.",
        ]
        commands = [f'start {run_id} --source-type <type> [--variant <variant>] '
                    f'--scope "Project|Person" [--scope "Project|Person" ...]']
        extra["routed_source_types"] = routed_types

    elif status == "needs_scope":
        need = needed_scopes(graph, route) if route else set()
        scopes = parse_scopes_cell(row.get("Scopes", ""))
        if scopes:
            missing = sorted({m for proj, pers in scopes for m in missing_scope_fields(need, proj, pers)})
        else:
            missing = sorted(need)
        checklist = [
            f"Missing required scope field(s): {', '.join(missing) or '(see Reason)'}.",
            f"Reason on file: {row.get('Reason', '')}",
            "Re-run start with a corrected --scope tuple that carries every required field.",
        ]
        commands = [f'start {run_id} --source-type {row.get("Source type") or "<type>"} '
                    f'--scope "Project|Person"  (must carry: {", ".join(missing) or "see Reason"})']
        extra["missing_scope_fields"] = missing

    elif status == "processing" and stage in ("", "analysis"):
        checklist = [
            f"Apply the route skills: {', '.join(route.get('skills') or []) or '(none listed)'}.",
            f"Update the entry documents: {', '.join(route.get('entry') or []) or '(none listed)'}.",
            "Record a short OPERATIONAL summary (not the full analysis body).",
        ]
        commands = [f'record-analysis {run_id} --summary "..."']

    elif status == "processing" and stage == "apply":
        entries = parse_entries_cell(row.get("Entries", ""))
        entry_docs = route.get("entry") or []
        scopes = enumerate_run_scopes(ctx.all_rows, parse_scopes_cell(row.get("Scopes", "")),
                                      entries, row.get("Route variant", ""))
        per_scope_missing = []
        for proj, pers, variant in scopes:
            scoped = entries_for_scope(entries, proj, pers)
            missing_docs = [d for d in entry_docs if d not in scoped]
            per_scope_missing.append({"project": proj, "person": pers, "variant": variant,
                                      "missing_documents": missing_docs})
            if missing_docs:
                commands.append(f'record-apply {run_id}{guide_scope_cli_args(proj, pers)} '
                                f'--updated {",".join(missing_docs)}'
                                f'  (or --no-change/--not-applicable "doc=reason" per doc)')
        checklist = [f"Entry documents required by the route: {', '.join(entry_docs) or '(none)'}."]
        scope_lines = [
            f"scope ({m['project'] or '-'}, {m['person'] or '-'}): "
            f"missing outcome for {', '.join(m['missing_documents'])}"
            for m in per_scope_missing if m["missing_documents"]
        ]
        checklist += scope_lines or ["All entry documents already have an outcome for every scope."]
        extra["missing_entry_documents_by_scope"] = per_scope_missing

    elif status == "processing" and stage == "closure":
        archive_needed = any("archive-source" in p for p in eval_res.entry_problems)
        missing_entries = [m for m in (parse_missing_entry_document(p) for p in eval_res.entry_problems) if m]
        unresolved = [u for u in (parse_unresolved_edge_entry(e) for e in eval_res.unresolved_edges) if u]

        if archive_needed:
            checklist.append("Source is still in 00_Inbox - archive it before taking the closure snapshot.")
            commands.append(f'archive-source {run_id}')
        if missing_entries:
            checklist.append(f"{len(missing_entries)} entry document(s) still have no recorded outcome.")
            for m in missing_entries:
                commands.append(f'record-apply {run_id}{guide_scope_cli_args(m["project"], m["person"])} '
                                f'--updated {m["doc"]}  (or --no-change/--not-applicable "{m["doc"]}=reason")')
        if unresolved:
            checklist.append(f"{len(unresolved)} cascade edge(s) unresolved.")
            for u in unresolved:
                commands.append(f'resolve-edge {run_id} --source {u["source"]} --target {u["target"]} '
                                f'--outcome <updated|no_change|gated|regenerated> [--reason "..."]'
                                f'{guide_scope_cli_args(u["project"], u["person"])}')
        if not archive_needed and not missing_entries and not unresolved:
            if eval_res.invocation_present is False or eval_res.snapshot_problem:
                checklist.append("Cascade closed, but the mirror snapshot/invocation token is missing or stale.")
                commands.append(f'commit_workspace_state.py -m "<skill>: <source> [{run_id}]"')
            elif eval_res.ready_for_completion:
                checklist.append("Everything verified - ready to complete.")
                commands.append(f'complete {run_id}')
            else:
                checklist.append("Unresolved warning(s) reported by review - inspect before completing.")
                commands.append(f'review {run_id} --json')

        extra.update({
            "unresolved_edges": unresolved,
            "missing_entry_documents": missing_entries,
            "existing_outcomes": ctx.all_rows,
            "snapshot_problem": eval_res.snapshot_problem,
            "invocation_present": eval_res.invocation_present,
            "ready_for_completion": eval_res.ready_for_completion,
        })

    elif status == "blocked":
        checklist = [f"Blocked: {row.get('Reason', '')}",
                     "Resolve the underlying gate/question, then reactivate the run."]
        commands = [f'resume {run_id} --continue']

    elif status == "finalizing":
        checklist = ["Verification already passed; only the terminal mirror bookkeeping is unfinished.",
                     "Re-run complete to retry it - the terminal transition is idempotent by design."]
        commands = [f'complete {run_id}']
        extra["snapshot_problem"] = eval_res.snapshot_problem
        extra["invocation_present"] = eval_res.invocation_present

    elif status == "completed":
        real_problems = [p for p in eval_res.all_problems if "Run cannot be completed from state" not in p]
        if real_problems or eval_res.warnings:
            checklist = [
                "This completed run has an integrity problem - do NOT edit its terminal Snapshot/queue row.",
                "Investigate with review/search_workspace.py, then repair with a NEW dated pass "
                "(evidence_log entry + a fresh commit_workspace_state.py snapshot) - same as any other "
                "data-quality repair, never by mutating this run's own completed row.",
            ]
            commands = [f'review {run_id} --json  (see problems below)']
            extra["problems"] = real_problems
            extra["warnings"] = eval_res.warnings
        else:
            checklist = ["Completed and healthy - no operational action needed."]
        extra["snapshot_sha"] = eval_res.snapshot_sha
        extra["invocation_present"] = eval_res.invocation_present

    elif status in ("historical", "ignored", "failed"):
        checklist = [f"Terminal state ({status}) - not part of normal processing.",
                     f"Reason on file: {row.get('Reason', '')}"]
        if status == "failed":
            checklist.append("A failed run may later be corrected to historical if migration evidence turns up.")
            commands.append(f'historical {run_id} --evidence "..."')

    else:
        checklist = [f"Unrecognized status {status!r}."]

    return checklist, commands, extra


def guide_guardrails(row: dict, interpretation: dict) -> list[str]:
    """Guardrails relevant to this run's current status/stage only - never
    the full generic list, so the operator sees what actually applies."""
    status = row.get("Status", "")
    stage = row.get("Stage", "")
    guardrails: list[str] = []
    if status in ("discovered", "needs_scope"):
        guardrails.append("Never default a missing project/person scope - a route that needs it must land in "
                          "needs_scope, not a silently-defaulted scope.")
        guardrails.append("Use Current source for live file access; Source is the immutable discovery identity "
                          "and may be historical.")
    if status == "discovered" or (status == "processing" and stage in ("", "analysis")):
        guardrails.append("Queue rows must contain short summaries/status only, never full transcript text or "
                          "full analysis.")
    if status == "processing" and stage == "apply":
        guardrails.append("no_change/not_applicable entry outcomes require a reason.")
    if status == "processing" and stage == "closure":
        guardrails.append("no_change/gated cascade outcomes require a reason.")
        guardrails.append("Put the exact token `run:<run-id>` in _skill_invocations before completing.")
        guardrails.append("commit_workspace_state.py's message must include the run id in brackets, e.g. [<run-id>].")
        if interpretation.get("source_still_in_inbox"):
            guardrails.append("archive-source must run BEFORE the closure snapshot is taken, not after.")
    if status == "finalizing":
        guardrails.append("complete is safe to retry here - the terminal transition is idempotent by design.")
    if status == "completed":
        guardrails.append("A completed run's recorded Snapshot is immutable evidence - a later repair needs its "
                          "own new evidence_log entry and mirror commit, never editing this run's own row.")
    return guardrails


# ---------- commands ----------

def cmd_scan(args) -> CommandResult:
    services = get_services_cached()
    sheet = get_or_create_queue(services)
    rows = read_queue(services, sheet)
    by_pair, by_path, by_hash = queue_discovery_indexes(rows)

    discovered = []
    for rel_dir in SCAN_DIRS:
        base = DATA_ROOT / rel_dir
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in SCAN_EXTS:
                continue
            rel = path.relative_to(DATA_ROOT).as_posix()
            if is_excluded(rel):
                continue
            digest = hashlib.sha256(path.read_bytes()).hexdigest()[:16]
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
                        "Source hash": digest, "Current source": rel,
                        "Source disposition": "inbox", "Source type": preclass,
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
    return CommandResult(
        ok=True,
        data=payload,
        human_lines=[f"{len(discovered)} new source(s) discovered:"] +
                    [f"  {r['Run ID']}  {r['Source']}  ({r['Source type']})"
                     + (f"  [{r['Reason']}]" if r["Reason"] else "") for r in discovered]
                    if discovered else ["No new sources."],
        exit_code=0
    )


def cmd_status(args) -> CommandResult:
    services = get_services_cached()
    sheet = find_queue(services)
    rows = read_queue(services, sheet) if sheet else []
    terminal = ("completed", "failed", "historical", "ignored")
    open_rows = [r for r in rows if r["Status"] not in terminal]
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["Status"]] = counts.get(r["Status"], 0) + 1
    payload = {"counts": counts, "open": [{h.lower().replace(" ", "_"): r[h] for h in HEADER
                                          if h not in ("Summary", "Entries")} for r in open_rows]}
    return CommandResult(
        ok=True,
        data=payload,
        human_lines=[f"Queue: " + ", ".join(f"{k}={v}" for k, v in sorted(counts.items())) if counts
                     else "Queue is empty (run scan first)."] +
                    [f"  {row_brief(r)}" for r in open_rows],
        exit_code=0
    )


def cmd_next(args) -> CommandResult:
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
        return CommandResult(ok=True, data={"next": None}, human_lines=["Nothing actionable - queue is clear."], exit_code=0)

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
    return CommandResult(ok=True, data={"next": info}, human_lines=lines, exit_code=0)


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


def cmd_start(args) -> CommandResult:
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
    scopes = dedup_scopes(scopes)

    def mutate(row: dict) -> None:
        row["Source type"] = args.source_type
        row["Route variant"] = args.variant or ""
        row["Scopes"] = json.dumps(scopes, ensure_ascii=False) if scopes else ""
        row["Project"] = "; ".join(dict.fromkeys(p for p, _ in scopes if p))
        row["Person"] = "; ".join(dict.fromkeys(p for _, p in scopes if p))
        row["Skills"] = ", ".join(route.get("skills") or [])
        if scopes:
            missing = sorted({m for proj, pers in scopes
                              for m in missing_scope_fields(need, proj, pers)})
        else:
            missing = sorted(need)
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

        row["Source text version"] = "1" if source_text_requirement(row) == "required" else ""

    row = _update_run(args, mutate)
    ok = row["Status"] == "processing"
    return CommandResult(
        ok=ok,
        data={"run_id": row["Run ID"], "status": row["Status"], "stage": row["Stage"],
              "skills": row["Skills"], "entry": entry, "scopes": scopes,
              "reason": row["Reason"]},
        human_lines=[row_brief(row)] +
         ([f"  load skills: {row['Skills'] or '(shared rules per graph note)'}",
           f"  entry documents to update: {', '.join(entry)}",
           f"  scopes: {scopes}"]
          if ok else [f"  {row['Reason']}"]),
        exit_code=0 if ok else 1
    )


def cmd_record_analysis(args) -> CommandResult:
    def mutate(row: dict) -> None:
        if row["Status"] != "processing":
            raise SystemExit(f"record-analysis requires status=processing (is {row['Status']!r}).")
        if row["Stage"] not in ("analysis", ""):
            raise SystemExit(f"record-analysis belongs to the analysis stage "
                             f"(run is at {row['Stage']!r}).")
        row["Stage"] = "apply"
        row["Summary"] = (row["Summary"] + " | " if row["Summary"] else "") + args.summary.strip()

    row = _update_run(args, mutate)
    return CommandResult(
        ok=True,
        data={"run_id": row["Run ID"], "stage": row["Stage"]},
        human_lines=[row_brief(row),
                     "  next: apply the documents, then record-apply per scope."],
        exit_code=0
    )


def cmd_record_apply(args) -> CommandResult:
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
    return CommandResult(
        ok=True,
        data={"run_id": row["Run ID"], "stage": row["Stage"],
              "entries": parse_entries_cell(row["Entries"])},
        human_lines=[row_brief(row),
                     "  next: resolve every cascade edge (resolve-edge), snapshot, complete."],
        exit_code=0
    )


def cmd_resolve_edge(args) -> CommandResult:
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
    return CommandResult(
        ok=True,
        data={"run_id": args.run_id, "edge": f"{args.source}->{args.target}",
              "kind": kind, "outcome": args.outcome,
              "scope": [project, person, variant]},
        human_lines=[f"Recorded: {args.source} -> {args.target} [{kind}] = {args.outcome}"
                     + (f" ({args.reason})" if args.reason else "")
                     + (f"  @{project}/{person}" if project or person else "")],
        exit_code=0
    )


def cmd_add_scope(args) -> CommandResult:
    if not (args.project or args.person):
        raise SystemExit("add-scope needs --project and/or --person.")
    graph = load_graph()

    def mutate(row: dict) -> None:
        if row["Status"] != "processing":
            raise SystemExit(f"add-scope requires status=processing (is {row['Status']!r}).")
        # Same validation start enforces - a later-declared scope must carry
        # every field the route requires, or a project-only/person-only
        # tuple would sneak past start's gate.
        route = resolve_route(graph, row["Source type"], row["Route variant"])
        missing = missing_scope_fields(needed_scopes(graph, route),
                                       args.project, args.person)
        if missing:
            raise SystemExit(f"add-scope: this route requires {'/'.join(missing)} - "
                             f"the new scope must carry --{' and --'.join(missing)}.")
        scopes = parse_scopes_cell(row["Scopes"])
        new = (args.project.strip(), args.person.strip())
        if len(dedup_scopes(scopes + [new])) == len(scopes):
            raise SystemExit(f"scope {new} is already declared on {row['Run ID']} "
                             "(case-insensitive).")
        scopes.append(new)
        row["Scopes"] = json.dumps(scopes, ensure_ascii=False)
        row["Project"] = "; ".join(dict.fromkeys(p for p, _ in scopes if p))
        row["Person"] = "; ".join(dict.fromkeys(p for _, p in scopes if p))

    row = _update_run(args, mutate)
    return CommandResult(
        ok=True,
        data={"run_id": row["Run ID"], "scopes": parse_scopes_cell(row["Scopes"])},
        human_lines=[row_brief(row),
                     f"  scopes now: {parse_scopes_cell(row['Scopes'])} - record-apply and "
                     "resolve-edge for the new scope need explicit --project/--person."],
        exit_code=0
    )


def cmd_block(args) -> CommandResult:
    def mutate(row: dict) -> None:
        validate_transition(row["Status"], "blocked")
        row["Status"], row["Reason"] = "blocked", args.reason
    row = _update_run(args, mutate)
    return CommandResult(
        ok=True,
        data={"run_id": row["Run ID"], "status": "blocked", "reason": row["Reason"]},
        human_lines=[row_brief(row)],
        exit_code=0
    )


def cmd_fail(args) -> CommandResult:
    def mutate(row: dict) -> None:
        validate_transition(row["Status"], "failed")
        row["Status"], row["Reason"] = "failed", args.reason
    row = _update_run(args, mutate)
    return CommandResult(
        ok=True,
        data={"run_id": row["Run ID"], "status": "failed"},
        human_lines=[row_brief(row)],
        exit_code=0
    )


def cmd_ignore(args) -> CommandResult:
    def mutate(row: dict) -> None:
        validate_transition(row["Status"], "ignored")
        row["Status"] = "ignored"
        row["Reason"] = (f"ignored ({args.category})"
                         + (f": {args.reason}" if args.reason else ""))
    row = _update_run(args, mutate)
    return CommandResult(
        ok=True,
        data={"run_id": row["Run ID"], "status": "ignored", "category": args.category},
        human_lines=[row_brief(row)],
        exit_code=0
    )


def cmd_historical(args) -> CommandResult:
    def mutate(row: dict) -> None:
        validate_transition(row["Status"], "historical")
        row["Status"] = "historical"
        row["Reason"] = f"pre-queue history: {args.evidence}"
    row = _update_run(args, mutate)
    return CommandResult(
        ok=True,
        data={"run_id": row["Run ID"], "status": "historical", "evidence": args.evidence},
        human_lines=[row_brief(row)],
        exit_code=0
    )


def find_drive_item_by_path(drive, relative_path: str) -> dict:
    from m2_workspace_layout import find_folder_path, list_children
    from sync_m2_source_docs_to_sheets import ROOT_FOLDER_ID

    normalized = relative_path.replace("\\", "/").strip("/")
    parts = [part for part in normalized.split("/") if part]
    if not parts or ".." in parts:
        raise SystemExit(f"Unsafe current source path: {relative_path!r}")
    parent = find_folder_path(drive, ROOT_FOLDER_ID, parts[:-1])
    if not parent:
        raise SystemExit(f"Source parent not found in Drive: {'/'.join(parts[:-1])}")
    matches = [item for item in list_children(drive, str(parent["id"])) if item.get("name") == parts[-1]]
    if len(matches) != 1:
        raise SystemExit(
            f"Expected exactly one Drive item at {normalized!r}, found {len(matches)}"
        )
    return matches[0]


def cmd_archive_source(args) -> CommandResult:
    from m2_workspace_layout import ensure_folder_path, list_children, move_item
    from sync_m2_source_docs_to_sheets import ROOT_FOLDER_ID
    from workspace_root_layout import processed_run_destination

    services = get_services_cached()
    sheet = find_queue(services)
    if not sheet:
        raise SystemExit("No _intake_queue sheet yet - run scan first.")
    rows = read_queue(services, sheet)
    row = get_run(rows, args.run_id)
    if row.get("Status") != "processing" or row.get("Stage") != "closure":
        raise SystemExit("archive-source requires a processing run at the closure stage")
    if row.get("Source disposition") == "archived":
        return CommandResult(
            ok=True,
            data={"run_id": args.run_id, "current_source": row.get("Current source", ""),
                  "source_disposition": "archived"},
            human_lines=[f"{args.run_id}: source already archived."],
            exit_code=0,
        )

    current = str(row.get("Current source") or row.get("Source") or "")
    filename = Path(current.replace("\\", "/")).name
    destination = processed_run_destination(args.run_id, filename, dt.date.today().isoformat())
    drive = services["drive"]
    target_parent = ensure_folder_path(drive, ROOT_FOLDER_ID, destination[:-1])

    existing = [
        item for item in list_children(drive, str(target_parent["id"]))
        if item.get("name") == destination[-1]
    ]
    if len(existing) > 1:
        raise SystemExit(f"Multiple archived source items exist for run {args.run_id}")
    if existing:
        item = existing[0]
    else:
        item = find_drive_item_by_path(drive, current)
        move_item(drive, str(item["id"]), str(target_parent["id"]))

    row["Current source"] = "/".join(destination)
    row["Source disposition"] = "archived"
    row["Last mutation"] = now()
    write_queue(services, sheet, rows)
    return CommandResult(
        ok=True,
        data={"run_id": args.run_id, "item_id": str(item["id"]),
              "current_source": row["Current source"], "source_disposition": "archived"},
        human_lines=[f"{args.run_id}: source archived; create a fresh workspace snapshot before complete."],
        exit_code=0,
    )


def cmd_resume(args) -> CommandResult:
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
    return CommandResult(
        ok=True,
        data={"run_id": row["Run ID"], "status": row["Status"], "stage": row["Stage"],
              "entries": entries, "outcomes": len(outcome_rows),
              "scopes": [list(s) for s in scopes]},
        human_lines=lines,
        exit_code=0
    )


@dataclass
class ReviewContext:
    row: dict
    graph: dict
    all_rows: list[dict]
    inv_rows: list[list[str]]
    dirty: bool
    log_entries: list[tuple[str, float, str]]

def load_review_context(services, run_id: str, rows: list[dict] | None = None) -> ReviewContext:
    """`rows` lets a caller that already read the queue (e.g. dashboard,
    iterating many runs in one pass) skip re-reading the whole Sheet per
    run; omit it (the default) to read fresh, as review/complete do."""
    from closure_outcomes import fetch_outcomes
    from sync_m2_source_docs_to_sheets import ROOT_FOLDER_ID, find_sheet_in_folder, read_sheet_values
    from pipeline_common import SKILL_INVOCATIONS_SHEET

    if rows is None:
        sheet = find_queue(services)
        rows = read_queue(services, sheet) if sheet else []
    row = get_run(rows, run_id)
    graph = load_graph()

    all_rows = fetch_outcomes(services, run_id, all_scopes=True)

    inv_sheet = find_sheet_in_folder(services["drive"], ROOT_FOLDER_ID, SKILL_INVOCATIONS_SHEET)
    inv_rows = read_sheet_values(services, inv_sheet["id"]) if inv_sheet else []

    porcelain = mirror_git(MIRROR, "status", "--porcelain").stdout
    dirty = bool(porcelain.strip())
    if dirty and row["Status"] == "finalizing" and is_queue_only_dirt(porcelain):
        dirty = False

    log_raw = mirror_git(MIRROR, "log", "-50", "--format=%H|%ct|%s").stdout
    log_entries = []
    for line in log_raw.splitlines():
        sha, _, rest = line.partition("|")
        ts, _, subject = rest.partition("|")
        try:
            log_entries.append((sha, float(ts), subject))
        except ValueError:
            continue

    return ReviewContext(row, graph, all_rows, inv_rows, dirty, log_entries)

def evaluate_run(ctx: ReviewContext) -> EvaluationResult:
    from check_cascade_closure import build_resolved, walk
    from closure_outcomes import row_matches_scope
    row = ctx.row
    graph = ctx.graph
    status = row.get("Status") or "discovered"
    stage = row.get("Stage") or ""

    res = EvaluationResult(False, [], [], [], "", "", True)  # Default invocation_present to True until proven otherwise

    if status in ("discovered", "needs_scope", "ready", "blocked", "failed", "historical", "ignored", "completed"):
        res.ready_for_completion = False
        res.entry_problems.append(f"Run cannot be completed from state {status!r}.")
        if status == "completed":
            snapshot = row.get("Snapshot", "")
            snapshot_sha = snapshot if isinstance(snapshot, str) else ""
            res.snapshot_sha = snapshot_sha
            token = f"run:{row.get('Run ID', '')}"
            res.invocation_present = any(token in " | ".join(r) for r in ctx.inv_rows[1:])
            st_errors = check_source_text_snapshot(snapshot_sha, row)
            if st_errors:
                res.snapshot_problem = "\n  ".join(st_errors)
        else:
            res.invocation_present = None
            res.snapshot_sha = None
        return res

    if status == "processing" and stage in ("analysis", "apply", ""):
        res.ready_for_completion = False
        res.entry_problems.append(f"Stage is {stage!r} (must be closure).")
        res.invocation_present = None # irrelevant for these states
        res.snapshot_sha = None
        return res

    route = resolve_route(graph, row["Source type"], row["Route variant"])
    entry_docs = route.get("entry") or []
    entries = parse_entries_cell(row["Entries"])
    scopes = enumerate_run_scopes(ctx.all_rows, parse_scopes_cell(row["Scopes"]),
                                  entries, row["Route variant"])

    current_source = str(row.get("Current source", "")).strip()
    if current_source and row.get("Source disposition") != "archived":
        res.entry_problems.append("Source original is still in 00_Inbox; run archive-source before snapshotting.")

    last_outcome_ts = max(parse_ts(row["Started"]), parse_ts(row["Last mutation"]))
    for proj, pers, variant in scopes:
        label = f"scope ({proj or '-'!s}, {pers or '-'!s}, {variant or '-'!s})"
        scoped_entries = entries_for_scope(entries, proj, pers)
        res.entry_problems.extend(f"{label}: {p}" for p in validate_entry_outcomes(entry_docs, scoped_entries))
        seeds = seeds_for_scope(scoped_entries)
        scoped_rows = [r for r in ctx.all_rows if row_matches_scope(r, proj, pers, variant)]
        for rec in scoped_rows:
            last_outcome_ts = max(last_outcome_ts, parse_ts(rec.get("Timestamp", "")))
        resolved, warns = build_resolved(scoped_rows, graph)
        res.warnings.extend(f"{label}: {w}" for w in warns)
        open_items: list[str] = []
        lines: list[str] = []
        visited_req = set(seeds)
        for node in sorted(seeds):
            walk(graph, node, seeds, visited_req, set(), 0, False, True,
                 resolved, open_items, lines)
        res.unresolved_edges.extend(f"{label}: unresolved edge {item}" for item in open_items)

    token = f"run:{row['Run ID']}"
    res.invocation_present = any(token in " | ".join(r) for r in ctx.inv_rows[1:])

    sha, snap_problem = check_snapshot(ctx.log_entries, row, last_outcome_ts, ctx.dirty)
    res.snapshot_sha = sha
    res.snapshot_problem = snap_problem

    res.ready_for_completion = (not res.entry_problems and not res.unresolved_edges
                                and res.invocation_present and not res.snapshot_problem
                                and not res.warnings)
    return res


def get_recommended_action(status: str, stage: str, ready: bool) -> str:
    if status in ("discovered", "needs_scope", "ready"):
        return "start"
    if status == "blocked":
        return "resume --continue"
    if status == "finalizing":
        return "complete" if ready else "retry complete"
    if status in ("completed", "failed", "historical", "ignored"):
        return "none"
    if status == "processing":
        if stage == "analysis": return "record-analysis"
        if stage == "apply": return "record-apply"
        if stage == "closure":
            return "complete" if ready else "resolve unmet requirements"
    return "unknown"

def cmd_review(args) -> CommandResult:
    services = get_services_cached()
    ctx = load_review_context(services, args.run_id)
    eval_res = evaluate_run(ctx)
    row = ctx.row
    try:
        route = resolve_route(ctx.graph, row.get("Source type", ""), row.get("Route variant", ""))
    except SystemExit:
        route = {}

    all_problems = eval_res.all_problems

    rec_action = get_recommended_action(row.get("Status", "discovered"), row.get("Stage", ""), eval_res.ready_for_completion)

    return CommandResult(
        ok=True,
        data={
            "run_id": args.run_id,
            "source": row.get("Source", ""),
            "source_hash": row.get("Source hash", ""),
            "status": row.get("Status", ""),
            "stage": row.get("Stage", ""),
            "scopes": parse_scopes_cell(row.get("Scopes", "")),
            "skills": route.get("skills", []),
            "entries": parse_entries_cell(row.get("Entries", "")),
            "outcomes": ctx.all_rows,
            "unresolved_edges": eval_res.unresolved_edges,
            "snapshot_sha": eval_res.snapshot_sha,
            "snapshot_problem": eval_res.snapshot_problem,
            "invocation_present": eval_res.invocation_present,
            "mirror_cleanliness": not ctx.dirty,
            "ready_for_completion": eval_res.ready_for_completion,
            "recommended_action": rec_action
        },
        warnings=eval_res.warnings,
        human_lines=[f"Review for {args.run_id}:"] + (
            [f"  - {p}" for p in all_problems] + [f"  - WARNING: {w}" for w in eval_res.warnings]
            if all_problems or eval_res.warnings else ["  All clear. Ready for complete."]
        ),
        exit_code=0
    )


def cmd_complete(args) -> CommandResult:
    services = get_services_cached()
    sheet = find_queue(services)
    if not sheet:
        raise SystemExit(f"Queue sheet {QUEUE_SHEET!r} not found.")
    rows = read_queue(services, sheet)

    ctx = load_review_context(services, args.run_id)
    eval_res = evaluate_run(ctx)
    sha = eval_res.snapshot_sha

    row = get_run(rows, args.run_id)

    if not eval_res.ready_for_completion:
        problems = eval_res.all_problems + eval_res.warnings
        return CommandResult(
            ok=False,
            data={"run_id": args.run_id, "completed": False, "problems": problems},
            errors=["Run is not ready for completion"],
            human_lines=[f"NOT completed - {len(problems)} unmet requirement(s):"] +
                        [f"  - {p}" for p in problems],
            exit_code=1
        )

    if not sha:
        return CommandResult(
            ok=False,
            data={"run_id": args.run_id, "completed": False,
                  "problems": ["Completion evaluation returned no snapshot SHA"]},
            errors=["Missing snapshot SHA"],
            human_lines=["NOT completed - completion evaluation returned no snapshot SHA."],
            exit_code=1,
        )

    # Verify that the mirror commit contains the exact token in _skill_invocations.values.json
    token = f"run:{args.run_id}"
    res_git = mirror_git(MIRROR, "show", f"{sha}:_skill_invocations.values.json")
    if res_git.returncode != 0 or token not in res_git.stdout:
        problems = [f"Mirror commit {sha[:8]} does not contain {token} in _skill_invocations.values.json"]
        return CommandResult(
            ok=False,
            data={"run_id": args.run_id, "completed": False, "problems": problems},
            errors=["Missing mirror invocation token"],
            human_lines=[f"NOT completed - 1 unmet requirement(s):"] +
                        [f"  - {p}" for p in problems],
            exit_code=1
        )

    # Verification passed. Two-phase terminal transition so a mirror
    # bookkeeping failure never yields a false success or a stuck terminal
    # row: (1) finalizing is written to Drive with the verified snapshot
    # SHA; (2) the INTENDED terminal representation is committed to the
    # mirror (idempotent, verified, bundle refreshed); (3) only after that
    # commit exists does Drive get the completed state - with the very
    # timestamps already in the mirror. A failure anywhere before (3)
    # leaves the run in finalizing and complete re-runs from there; there
    # is no post-terminal step left to fail.
    if row["Status"] == "processing":
        validate_transition(row["Status"], "finalizing")
        # The intended completion timestamp is fixed here and reused on
        # every retry - otherwise a retry in a later minute would produce a
        # second, differing terminal commit instead of recognizing the one
        # already landed. Last mutation is deliberately NOT bumped: this
        # transition is the queue's own bookkeeping, not a business
        # mutation, and bumping it would make the already-verified snapshot
        # look stale on every retry.
        row["Status"], row["Snapshot"] = "finalizing", sha
        row["Completed"] = now()
        write_queue(services, sheet, rows)

    completed_ts = row["Completed"] or now()
    stored_snapshot = row.get("Snapshot", "")
    final_snapshot = stored_snapshot if isinstance(stored_snapshot, str) and stored_snapshot else sha
    terminal_rows = [dict(r) for r in rows]
    terminal_row = next(r for r in terminal_rows if r["Run ID"] == args.run_id)
    terminal_row.update({"Status": "completed", "Stage": "done",
                         "Completed": completed_ts,
                         "Snapshot": final_snapshot})
    queue_sha, warnings = export_queue_terminal(services, sheet, terminal_rows, args.run_id)

    validate_transition("finalizing", "completed")
    row.update({"Status": "completed", "Stage": "done", "Completed": completed_ts,
                "Snapshot": final_snapshot})
    write_queue(services, sheet, rows)
    return CommandResult(
        ok=True,
        data={"run_id": args.run_id, "completed": True, "snapshot": final_snapshot,
              "terminal_commit": queue_sha},
        warnings=warnings,
        human_lines=[f"{args.run_id} completed: entry outcomes valid, closure strict-CLOSED per "
                     f"scope, invocation token present, snapshot {final_snapshot[:8]} verified; "
                     f"terminal state committed to the mirror ({queue_sha[:8]}) before the Drive "
                     "transition."],
        exit_code=0
    )


def cmd_dashboard(args) -> CommandResult:
    """Read-only operator summary. Never creates, writes, or mutates
    _intake_queue, _closure_outcomes, _skill_invocations, mirror files, or
    the public repo - reuses find/read helpers (read_queue, fetch_outcomes
    via load_review_context, evaluate_run) exclusively."""
    services = get_services_cached()
    sheet = find_queue(services)
    rows = read_queue(services, sheet) if sheet else []

    project, person = (args.project or "").strip(), (args.person or "").strip()
    if project or person:
        rows = [r for r in rows if row_matches_scope_filter(r, project, person)]

    limit = args.limit if getattr(args, "limit", None) else DEFAULT_DASHBOARD_LIMIT
    if limit <= 0:
        limit = DEFAULT_DASHBOARD_LIMIT

    action_required: list[dict] = []
    blocked: list[dict] = []
    finalizing: list[dict] = []
    integrity_issues: list[dict] = []
    recent_completed: list[dict] = []
    ignored_historical_counts: dict[str, int] = {}

    eval_cache: dict[str, EvaluationResult] = {}

    def evaluated(row: dict) -> EvaluationResult:
        run_id = row["Run ID"]
        if run_id not in eval_cache:
            ctx = load_review_context(services, run_id, rows=rows)
            eval_cache[run_id] = evaluate_run(ctx)
        return eval_cache[run_id]

    def integrity_record(row: dict, eval_res: EvaluationResult) -> dict | None:
        problems = eval_res.all_problems
        if row.get("Status") == "completed":
            # evaluate_run's early-return branch always appends "Run cannot
            # be completed from state 'completed'." for a terminal run -
            # true and expected, not a finding. Only genuine snapshot/
            # invocation problems are worth surfacing for an already-
            # completed run; filter the boilerplate so it doesn't drown out
            # real issues (found live: every completed row otherwise showed
            # up here even when perfectly healthy).
            problems = [p for p in problems if "Run cannot be completed from state" not in p]
        if not problems and not eval_res.warnings:
            return None
        return {**dashboard_row_summary(row), "problems": problems, "warnings": eval_res.warnings}

    for row in rows:
        status, stage = row.get("Status", ""), row.get("Stage", "")
        if status in ("discovered", "needs_scope"):
            if len(action_required) < limit:
                action_required.append({**dashboard_row_summary(row),
                                        "recommended_command": dashboard_recommended_command(row)})
        elif status == "processing":
            if stage in ("", "analysis", "apply"):
                if len(action_required) < limit:
                    action_required.append({**dashboard_row_summary(row),
                                            "recommended_command": dashboard_recommended_command(row)})
            elif stage == "closure" and len(action_required) < limit:
                # Listing and the (expensive) evaluate_run() pass share one
                # budget - a row that wouldn't be listed doesn't need
                # evaluating either; raise --limit to see/evaluate more.
                eval_res = evaluated(row)
                action_required.append({**dashboard_row_summary(row),
                                        "recommended_command":
                                            dashboard_recommended_command(row, eval_res)})
                rec = integrity_record(row, eval_res)
                if rec:
                    integrity_issues.append(rec)
        elif status == "blocked":
            if len(blocked) < limit:
                blocked.append({**dashboard_row_summary(row),
                                "recommended_command": dashboard_recommended_command(row)})
        elif status == "finalizing":
            if len(finalizing) < limit:
                eval_res = evaluated(row)
                finalizing.append({**dashboard_row_summary(row),
                                   "recommended_command": dashboard_recommended_command(row, eval_res)})
                rec = integrity_record(row, eval_res)
                if rec:
                    integrity_issues.append(rec)
        elif status in ("ignored", "historical", "failed"):
            ignored_historical_counts[status] = ignored_historical_counts.get(status, 0) + 1

    completed_rows = sorted(
        (r for r in rows if r.get("Status") == "completed"),
        key=lambda r: parse_ts(r.get("Completed", "")),
        reverse=True,
    )
    for row in completed_rows[:limit]:
        eval_res = evaluated(row)
        rec = integrity_record(row, eval_res)
        if rec:
            integrity_issues.append(rec)
        if args.include_completed:
            recent_completed.append(dashboard_row_summary(row))

    ignored_historical: list[dict] = []
    if args.include_ignored:
        ignored_historical = [
            dashboard_row_summary(r) for r in rows
            if r.get("Status") in ("ignored", "historical", "failed")
        ][:limit]

    inbox = inbox_snapshot(DATA_ROOT, rows)
    storage = storage_snapshot(DATA_ROOT)

    recommendations: list[str] = []
    if action_required:
        recommendations.append(f"{len(action_required)} run(s) need the next agent action - see action_required")
    if blocked:
        recommendations.append(f"{len(blocked)} run(s) blocked - see blocked")
    if finalizing:
        recommendations.append(f"{len(finalizing)} run(s) stuck in finalizing - retry `complete <run-id>`")
    if integrity_issues:
        recommendations.append(f"{len(integrity_issues)} integrity issue(s) found - see integrity_issues")
    if inbox["total_files"] and not action_required:
        recommendations.append(f"{inbox['total_files']} file(s) in 00_Inbox not yet actioned - run `scan`")
    if not recommendations:
        recommendations.append("Nothing actionable - queue is clear.")

    data = {
        "action_required": action_required,
        "blocked": blocked,
        "finalizing": finalizing,
        "integrity_issues": integrity_issues,
        "recent_completed": recent_completed,
        "ignored_historical_counts": ignored_historical_counts if args.include_ignored else {},
        "ignored_historical": ignored_historical,
        "inbox_summary": inbox,
        "storage_summary": storage,
        "recommendations": recommendations,
        "limit": limit,
    }

    lines = ["QA management dashboard:",
             f"  action_required: {len(action_required)}"]
    lines += [f"    {i['run_id']}  [{i['status']}" + (f":{i['stage']}" if i['stage'] else "")
              + f"]  -> {i['recommended_command']}" for i in action_required]
    lines.append(f"  blocked: {len(blocked)}")
    lines += [f"    {i['run_id']}  reason: {i['reason']}  -> {i['recommended_command']}" for i in blocked]
    lines.append(f"  finalizing: {len(finalizing)}")
    lines += [f"    {i['run_id']}  -> {i['recommended_command']}" for i in finalizing]
    lines.append(f"  integrity_issues: {len(integrity_issues)}")
    lines += [f"    {i['run_id']}: {'; '.join(i['problems'][:2]) or '; '.join(i['warnings'][:2])}"
              for i in integrity_issues]
    lines.append(f"  inbox: {inbox['total_files']} actionable file(s)"
                 + (f"  {inbox['by_source_type']}" if inbox["by_source_type"] else ""))
    lines.append(f"  storage: {storage['total_processed_runs']} processed run(s) archived")
    if args.include_completed:
        lines.append(f"  recent_completed: {len(recent_completed)}")
    if args.include_ignored:
        lines.append(f"  ignored/historical/failed: {ignored_historical_counts}")
    lines.append("  recommendations:")
    lines += [f"    - {r}" for r in recommendations]

    return CommandResult(ok=True, data=data, human_lines=lines, exit_code=0)


def cmd_guide(args) -> CommandResult:
    """Read-only deterministic "what do I do next for THIS run" - dashboard
    answers "what needs attention" across the queue; guide drills into one
    selected run_id. Reuses review/evaluate_run exclusively; never creates,
    writes, or mutates _intake_queue, _closure_outcomes,
    _skill_invocations, mirror files, or the public repo."""
    services = get_services_cached()
    sheet = find_queue(services)
    rows = read_queue(services, sheet) if sheet else []
    row = get_run(rows, args.run_id)  # raises SystemExit for an unknown run_id, same as every other command

    graph = load_graph()
    try:
        route = resolve_route(graph, row.get("Source type", ""), row.get("Route variant", ""))
    except SystemExit:
        route = {}

    ctx = load_review_context(services, args.run_id, rows=rows)
    eval_res = evaluate_run(ctx)

    identity = {
        "run_id": row.get("Run ID", ""),
        "status": row.get("Status", ""),
        "stage": row.get("Stage", ""),
        "source": row.get("Source", ""),
        "current_source": row.get("Current source", ""),
        "source_type": row.get("Source type", ""),
        "route_variant": row.get("Route variant", ""),
        "scopes": parse_scopes_cell(row.get("Scopes", "")),
        "source_text_version": row.get("Source text version", ""),
        "snapshot_sha": row.get("Snapshot", ""),
    }
    interpretation = {
        "skills": route.get("skills") or [],
        "entry_documents": route.get("entry") or [],
        "declared_scopes": parse_scopes_cell(row.get("Scopes", "")),
        "source_disposition": row.get("Source disposition", ""),
        "source_still_in_inbox": row.get("Source disposition", "") != "archived",
        "route_resolved": bool(route),
    }

    checklist, commands, extra = guide_stage_details(row, graph, route, eval_res, ctx)
    guardrails = guide_guardrails(row, interpretation)

    data = {
        "run_id": args.run_id,
        "identity": identity,
        "interpretation": interpretation,
        "checklist": checklist,
        "commands": commands,
        "guardrails": guardrails,
        **extra,
    }

    stage_label = identity["status"] + (f":{identity['stage']}" if identity["stage"] else "")
    lines = [f"Guide for {args.run_id}  [{stage_label}]",
             f"  source: {identity['source']}"]
    if identity["current_source"] and identity["current_source"] != identity["source"]:
        lines.append(f"  current source: {identity['current_source']}")
    if interpretation["skills"]:
        lines.append(f"  skills: {', '.join(interpretation['skills'])}")
    if interpretation["entry_documents"]:
        lines.append(f"  entry documents: {', '.join(interpretation['entry_documents'])}")
    lines.append("  next steps:")
    lines += [f"    - {c}" for c in checklist] or ["    (none)"]
    lines.append("  commands:")
    lines += [f"    $ {c}" for c in commands] or ["    (none)"]
    if guardrails:
        lines.append("  guardrails:")
        lines += [f"    ! {g}" for g in guardrails]

    return CommandResult(ok=True, data=data, human_lines=lines, exit_code=0)


def main() -> int:
    parent = JsonArgumentParser(add_help=False)
    parent.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    parent.add_argument("--debug", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)

    module_doc = __doc__ or "QA management intake state machine"
    parser = JsonArgumentParser(description=module_doc.splitlines()[0])
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument("--debug", action="store_true", help="print full traceback on unexpected error")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("scan", help="discover new/changed source files", parents=[parent])
    sub.add_parser("status", help="queue overview", parents=[parent])
    sub.add_parser("next", help="most actionable run", parents=[parent])

    p = sub.add_parser("start", help="classify + activate a run", parents=[parent])
    p.add_argument("run_id")
    p.add_argument("--source-type", required=True)
    p.add_argument("--variant", default="")
    p.add_argument("--project", default="")
    p.add_argument("--person", default="")
    p.add_argument("--scope", action="append", default=[],
                   metavar="PROJECT|PERSON",
                   help="explicit scope tuple; repeat for multi-scope runs")

    p = sub.add_parser("record-analysis", help="analysis summary (stage -> apply)", parents=[parent])
    p.add_argument("run_id")
    p.add_argument("--summary", required=True)

    p = sub.add_parser("record-apply", help="per-scope entry outcomes (stage -> closure)", parents=[parent])
    p.add_argument("run_id")
    p.add_argument("--project", default="")
    p.add_argument("--person", default="")
    p.add_argument("--updated", default="", help="comma-separated documents actually written")
    p.add_argument("--no-change", dest="no_change", default="",
                   help="';'-separated doc=reason pairs")
    p.add_argument("--not-applicable", dest="not_applicable", default="",
                   help="';'-separated doc=reason pairs")

    p = sub.add_parser("resolve-edge", help="record one closure outcome", parents=[parent])
    p.add_argument("run_id")
    p.add_argument("--source", required=True)
    p.add_argument("--target", required=True)
    p.add_argument("--outcome", required=True)
    p.add_argument("--reason", default="")
    p.add_argument("--project", default="")
    p.add_argument("--person", default="")
    p.add_argument("--variant", default="")
    p.add_argument("--actor", default="agent")

    p = sub.add_parser("add-scope", help="declare a scope discovered during analysis", parents=[parent])
    p.add_argument("run_id")
    p.add_argument("--project", default="")
    p.add_argument("--person", default="")

    p = sub.add_parser("block", help="mark run waiting on a gate", parents=[parent])
    p.add_argument("run_id")
    p.add_argument("--reason", required=True)

    p = sub.add_parser("fail", help="give up on a run explicitly", parents=[parent])
    p.add_argument("run_id")
    p.add_argument("--reason", required=True)

    p = sub.add_parser("ignore", help="terminal: not an intake source at all", parents=[parent])
    p.add_argument("run_id")
    p.add_argument("--category", required=True, choices=sorted(IGNORE_CATEGORIES))
    p.add_argument("--reason", default="")

    p = sub.add_parser("historical", help="terminal: processed before the queue existed", parents=[parent])
    p.add_argument("run_id")
    p.add_argument("--evidence", required=True,
                   help="where the pre-queue processing is recorded "
                        "(_skill_invocations date, evidence_log row, ...)")

    p = sub.add_parser("archive-source", help="move a closure-stage source from inbox to processed archive", parents=[parent])
    p.add_argument("run_id")

    p = sub.add_parser("review", help="read-only run evaluation", parents=[parent])
    p.add_argument("run_id")

    p = sub.add_parser("resume", help="unfinished stage + what remains", parents=[parent])
    p.add_argument("run_id")
    p.add_argument("--continue", dest="cont", action="store_true",
                   help="reactivate a blocked run")

    p = sub.add_parser("complete", help="verification gate -> completed", parents=[parent])
    p.add_argument("run_id")

    p = sub.add_parser("dashboard", help="read-only operator summary: actionable/blocked/"
                                          "finalizing runs, integrity issues, inbox/storage counts",
                       parents=[parent])
    p.add_argument("--limit", type=int, default=DEFAULT_DASHBOARD_LIMIT,
                   help=f"rows evaluated/listed per section (default {DEFAULT_DASHBOARD_LIMIT})")
    p.add_argument("--include-completed", action="store_true",
                   help="list the newest completed runs (they're still integrity-checked either way)")
    p.add_argument("--include-ignored", action="store_true",
                   help="list ignored/historical/failed runs (counts always excluded unless passed)")
    p.add_argument("--project", default="", help="filter to one project")
    p.add_argument("--person", default="", help="filter to one person")

    p = sub.add_parser("guide", help="read-only deterministic next-steps for one selected run",
                       parents=[parent])
    p.add_argument("run_id")

    args = parser.parse_args()

    commands = {
        "scan": cmd_scan, "status": cmd_status, "next": cmd_next,
        "start": cmd_start, "record-analysis": cmd_record_analysis,
        "record-apply": cmd_record_apply, "resolve-edge": cmd_resolve_edge,
        "add-scope": cmd_add_scope,
        "block": cmd_block, "fail": cmd_fail, "ignore": cmd_ignore,
        "historical": cmd_historical, "archive-source": cmd_archive_source,
        "resume": cmd_resume, "complete": cmd_complete, "review": cmd_review,
        "dashboard": cmd_dashboard, "guide": cmd_guide
    }

    if not args.json:
        result = commands[args.cmd](args)
        if isinstance(result, CommandResult):
            for line in result.human_lines:
                print(line)
            return result.exit_code
        return result

    with stdout_redirected(sys.stderr):
        try:
            result = commands[args.cmd](args)
        except SystemExit as exc:
            msg = str(exc)
            if msg == "0" or not msg:
                result = CommandResult(ok=True)
            else:
                result = CommandResult(ok=False, errors=[msg], exit_code=1)
        except Exception as exc:
            if args.debug:
                traceback.print_exc()
            else:
                print(f"Internal error: {type(exc).__name__}", file=sys.stderr)
            result = CommandResult(ok=False, errors=["Internal error"], exit_code=1)

    if not isinstance(result, CommandResult):
        # Fallback if something returned an int
        result = CommandResult(ok=(result == 0), exit_code=result)

    envelope = build_json_envelope(result.ok, args.cmd, result.data, result.warnings, result.errors)
    print(json.dumps(envelope, ensure_ascii=False, indent=1))
    return result.exit_code


if __name__ == "__main__":
    sys.exit(main())
