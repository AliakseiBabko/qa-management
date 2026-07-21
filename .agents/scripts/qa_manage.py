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
processing failure. It is only reachable from a pre-processing state
(`discovered`/`needs_scope`/`ready`) or as a correction from `failed` -
never from `processing`/`blocked`, since by the time a run has actually
started, "this predates the queue" is no longer a truthful claim. `ignored`
(with a category:
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
    ignore <run-id> --category C --reason "..." [--evidence "..."]
                                  terminal: not an intake source at all;
                                  only reachable from a pre-processing
                                  state; --reason is required (a category
                                  alone is not a reason); leaves the
                                  source file where it is - its (path,
                                  hash) identity keeps `scan` from
                                  rediscovering it
    mark-historical <run-id> --evidence "..."
                                  terminal: processed before the queue
                                  existed; only reachable from a
                                  pre-processing state or as a correction
                                  of a mistaken `fail` - never from
                                  `processing`/`blocked`; --evidence must
                                  name something concrete (an
                                  evidence_log row, a _skill_invocations
                                  date, a document revision), never a
                                  vague reason or unverified memory
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
    classify <run-id> [--max-preview-chars N]
                                  read-only pre-`start` helper for a
                                  `discovered` run needing a source_type/
                                  variant/scope judgment call: reads
                                  Current source (falling back to Source),
                                  reports deterministic format signals
                                  (line count, speaker/chat-header/
                                  datetime/email marker counts - no AI/LLM
                                  call), and lists unranked `candidate_routes`
                                  (source_type, variant, required scope,
                                  skills, entry documents, and the exact
                                  signal that produced each one) plus
                                  `guide`/`start`/`ignore` command
                                  templates. Never chooses a final route,
                                  never calls `start`, never writes
                                  anywhere - the classification decision
                                  stays with the agent after reading the
                                  actual source. The preview excerpt
                                  returned is capped (small, to avoid
                                  token waste); nothing here is ever
                                  written into the queue or this repo.
    pack <run-id> [--max-preview-chars N]
                                  read-only cross-agent handoff/resume
                                  packet for one run - compact enough to
                                  paste into a fresh session and continue.
                                  Combines: identity (status/stage, Source
                                  vs Current source, source_type/variant,
                                  scopes, source hash, source text
                                  version, Snapshot SHA, disposition);
                                  dashboard's category for this run;
                                  guide's stage-specific checklist and
                                  guardrails; review/evaluate_run's
                                  unresolved edges/entry problems/
                                  invocation/snapshot status; a
                                  classify-style signals+candidate_routes
                                  block only when the route isn't resolved
                                  yet; graph context (skills/entry docs/
                                  required scope, plus downstream closure
                                  expectations when already at the
                                  closure stage); a capped source preview
                                  (Current source preferred, metadata-only
                                  for non-text files); and a short
                                  `agent_handoff` prose block naming what
                                  to read first, which skill(s) to load,
                                  the exact next command, and what not to
                                  do. Reuses dashboard/guide/classify/
                                  review exclusively; never creates,
                                  writes, or mutates anything, and never
                                  includes full source text - only the
                                  same capped preview `classify` returns.
    triage [--limit N] [--project P] [--person X]
          [--category discovered|needs_scope|blocked|all]
                                  read-only backlog overview across
                                  discovered/needs_scope/blocked (or all
                                  three): per-candidate recommended
                                  command plus the exact terminal-action
                                  commands (`ignore`/`mark-historical`)
                                  TRANSITIONS actually allows from each
                                  row's status - never a suggestion to
                                  auto-apply one. Never creates, writes,
                                  or mutates anything.
    triage-one <run-id> [--max-preview-chars N]
                                  read-only detailed triage view for one
                                  run: source access + age, classify-style
                                  signals/candidate_routes, a capped
                                  preview, and the exact terminal-action
                                  commands available from its current
                                  status. Never creates, writes, or
                                  mutates anything, and never infers
                                  ignore/mark-historical from filename or
                                  extension alone - only ever a hint,
                                  applied explicitly and separately via
                                  `ignore`/`mark-historical`.

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
    # historical is deliberately NOT reachable from processing/blocked - by
    # the time a run has started, "this was already processed before the
    # queue existed" is no longer a truthful claim (that's what `historical`
    # asserts). A run that needs to stop mid-processing goes to `failed`
    # instead; `failed` can still be corrected to `historical` below, for
    # the narrow case where the failed mark itself was the mistake (the
    # source was never real live work in the first place).
    "processing": {"blocked", "finalizing", "failed"},
    "blocked": {"processing", "failed"},
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

# classify: default cap on the preview excerpt returned to the caller -
# small enough to avoid token waste, large enough to see the shape of the
# source. The full file is still read locally to compute deterministic
# signals (line count, speaker/date/chat/email markers); only the
# returned preview text itself is capped.
DEFAULT_MAX_PREVIEW_CHARS = 2000

# classify: extensions cheap/safe to read as plain text for signal
# detection. Binary formats (.docx/.doc/.pdf/.xlsx) are reported by
# filename/extension only - never decoded here.
TEXT_READABLE_EXTS = {".txt", ".md", ".csv"}


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
            commands.append(f'mark-historical {run_id} --evidence "..."')

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


# ---------- classify (read-only, one run) ----------

# "Name:" alone on its own line - the speaker-turn shape seen in this
# workspace's own 1:1/meeting transcripts (e.g. "Алексе Бобко:" followed by
# the message on the next line). Deliberately narrow (short, no trailing
# text) so it doesn't fire on ordinary prose lines that happen to end in a
# colon.
_SPEAKER_LINE_RE = re.compile(r"^([^\n:]{1,60}):\s*$")
# Generic date/time markers (ISO dates, HH:MM[:SS] [AM/PM], D/M/Y) - a
# coarse density signal, distinct from the stricter Google-Chat header
# shape detect_strategy_chats.is_header_line looks for.
_DATETIME_MARKER_RE = re.compile(
    r"\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM|am|pm)?\b|\b\d{1,2}/\d{1,2}/\d{2,4}\b"
)
_EMAIL_HEADER_RE = re.compile(r"^(?:From|To|Subject|Sent|Cc|Bcc):\s", re.IGNORECASE | re.MULTILINE)
# Bracketed turn/header markers - some transcript exports (e.g. auto-
# generated diarization) label turns as "[Speaker 1]", "[Speaker A]",
# a bare "[00:01:23]" timestamp, or a combined "[Speaker 1 00:01:23]",
# each alone on its own line. Only the "Speaker <id>" shape identifies
# WHO is speaking; a bare bracketed timestamp only marks a turn boundary,
# not an identity - see _BRACKET_SPEAKER_LABEL_RE below.
_BRACKETED_TURN_RE = re.compile(
    r"^\[\s*(?P<content>Speaker\s+\w+(?:\s+(?:\d{1,2}:)?\d{1,2}:\d{2}(?::\d{2})?)?"
    r"|(?:\d{1,2}:)?\d{1,2}:\d{2}(?::\d{2})?)\s*\]\s*$",
    re.IGNORECASE,
)
_BRACKET_SPEAKER_LABEL_RE = re.compile(r"^Speaker\s+(\w+)", re.IGNORECASE)
# Unbracketed timestamp-prefixed turn markers: "00:01:23 Name:" or
# "00:01 Name" alone on their own line (a name, not a duration/timestamp
# repeated - excludes a line that's just another timestamp).
_TIMESTAMP_TURN_RE = re.compile(
    r"^(?:\d{1,2}:)?\d{1,2}:\d{2}(?::\d{2})?\s+(?P<name>[^\s\d:][^\n:]{0,40})\s*:?\s*$"
)

_EMPTY_SIGNALS = {
    "text_readable": False,
    "line_count": None,
    "distinct_speaker_prefixes": 0,
    "chat_header_line_count": 0,
    "datetime_marker_count": 0,
    "email_marker_count": 0,
    "bracketed_speaker_marker_count": 0,
    "timestamp_turn_marker_count": 0,
    "distinct_turn_identities": 0,
    "paragraph_turn_density": 0.0,
    "likely_transcript": False,
    "likely_chat": False,
    "likely_email": False,
    "likely_binary_document": False,
}


def _extract_turn_identities(lines: list[str]) -> set[str]:
    """WHO-is-speaking identities deterministically recoverable from turn
    markers, merged across the three shapes this function understands.
    A bare bracketed timestamp ("[00:01:23]") marks a turn boundary but
    names no one, so it never contributes an identity - callers must not
    infer a 1:1 from turn *count* alone, only from identity count."""
    identities: set[str] = set()
    for line in lines:
        stripped = line.strip()
        m = _SPEAKER_LINE_RE.match(stripped)
        if m and m.group(1).strip():
            identities.add(m.group(1).strip().casefold())
            continue
        m = _BRACKETED_TURN_RE.match(stripped)
        if m:
            label = _BRACKET_SPEAKER_LABEL_RE.match(m.group("content").strip())
            if label:
                identities.add(f"speaker {label.group(1)}".casefold())
            continue
        m = _TIMESTAMP_TURN_RE.match(stripped)
        if m and m.group("name").strip():
            identities.add(m.group("name").strip().casefold())
    return identities


def detect_format_signals(text: str | None, extension: str) -> dict:
    """Deterministic, content-independent-of-semantics signal detection -
    no AI/LLM call, just line-shape/regex counting. `text` is the full
    file content (already read by the caller); this function only counts,
    it never decides a classification."""
    if extension not in TEXT_READABLE_EXTS or text is None:
        return dict(_EMPTY_SIGNALS, likely_binary_document=extension not in TEXT_READABLE_EXTS)

    from detect_strategy_chats import is_header_line

    lines = text.splitlines()
    speakers: set[str] = set()
    speaker_line_matches = 0
    for line in lines:
        m = _SPEAKER_LINE_RE.match(line.strip())
        if m and m.group(1).strip():
            speakers.add(m.group(1).strip())
            speaker_line_matches += 1
    chat_header_count = sum(1 for line in lines if is_header_line(line))
    datetime_count = len(_DATETIME_MARKER_RE.findall(text))
    email_count = len(_EMAIL_HEADER_RE.findall(text))
    bracketed_count = sum(1 for line in lines if _BRACKETED_TURN_RE.match(line.strip()))
    timestamp_turn_count = sum(1 for line in lines if _TIMESTAMP_TURN_RE.match(line.strip()))
    turn_identities = _extract_turn_identities(lines)

    non_empty_lines = sum(1 for line in lines if line.strip())
    turn_line_count = speaker_line_matches + bracketed_count + timestamp_turn_count
    turn_density = round(turn_line_count / non_empty_lines, 3) if non_empty_lines else 0.0

    return {
        "text_readable": True,
        "line_count": len(lines),
        "distinct_speaker_prefixes": len(speakers),
        "chat_header_line_count": chat_header_count,
        "datetime_marker_count": datetime_count,
        "email_marker_count": email_count,
        "bracketed_speaker_marker_count": bracketed_count,
        "timestamp_turn_marker_count": timestamp_turn_count,
        "distinct_turn_identities": len(turn_identities),
        "paragraph_turn_density": turn_density,
        "likely_transcript": len(speakers) >= 2 or bracketed_count >= 2 or timestamp_turn_count >= 2,
        "likely_chat": chat_header_count >= 3,
        "likely_email": email_count >= 2,
        "likely_binary_document": False,
    }


def classify_candidate_routes(graph: dict, signals: dict, row: dict) -> list[dict]:
    """Candidate (source_type, variant) hints from signals + route
    metadata only - never a final choice, never semantic content
    interpretation. Each candidate names the exact deterministic signal
    that produced it so the agent can judge it, not just trust it."""
    candidates: list[dict] = []
    added: set[tuple[str, str]] = set()

    def add(source_type: str, variant: str, reason: str) -> None:
        key = (source_type, variant)
        if key in added:
            return
        sources = graph.get("sources") or {}
        if source_type not in sources:
            return
        try:
            route = resolve_route(graph, source_type, variant)
        except SystemExit:
            return
        added.add(key)
        candidates.append({
            "source_type": source_type,
            "variant": variant,
            "required_scope": sorted(needed_scopes(graph, route)),
            "skills": route.get("skills") or [],
            "entry_documents": route.get("entry") or [],
            "route_description": route.get("description", ""),
            "reason": reason,
        })

    if not signals.get("text_readable") or "duplicate content of" in str(row.get("Reason", "")):
        return candidates

    # Plain "Name:" speaker lines - exactly 2 distinct names is treated as
    # a tight 1:1 signal; 3+ falls back to the broader meeting_transcript
    # bucket. Gated on this signal's OWN count (not the shared
    # likely_transcript flag, which also fires from bracket/timestamp
    # turns below) - otherwise a bracket-only transcript with zero plain
    # "Name:" lines would wrongly claim "0 distinct speaker-like prefixes
    # ... typical of a multi-person meeting" as its reason.
    speakers = signals.get("distinct_speaker_prefixes", 0)
    if speakers >= 2:
        if speakers == 2:
            for variant in ("m1", "m2", "mixed"):
                add("qa_1to1", variant,
                    f"{speakers} distinct speaker-like prefixes detected - typical of a 1:1 conversation")
        else:
            for variant in ("multi_project", "single_project"):
                add("meeting_transcript", variant,
                    f"{speakers} distinct speaker-like prefixes detected - typical of a multi-person meeting")

    # Bracketed ("[Speaker 1]") or unbracketed-timestamped ("00:01:23
    # Name:") turn markers - a different transcript export shape than
    # plain "Name:" lines. A strong count of either always suggests
    # meeting_transcript (safe default when speaker identity may be
    # unclear); qa_1to1 is added additionally only when exactly 2 distinct
    # identities were actually recoverable from those markers - never
    # inferred from turn *count* alone, since a bare "[00:01:23]" marks a
    # boundary but names no one.
    bracketed = signals.get("bracketed_speaker_marker_count", 0)
    timestamped = signals.get("timestamp_turn_marker_count", 0)
    turn_identities = signals.get("distinct_turn_identities", 0)
    if bracketed >= 2 or timestamped >= 2:
        for variant in ("multi_project", "single_project"):
            add("meeting_transcript", variant,
                f"{bracketed} bracketed and {timestamped} timestamped turn marker(s) detected - "
                "transcript-like turn structure")
        if turn_identities == 2:
            for variant in ("m1", "m2", "mixed"):
                add("qa_1to1", variant,
                    "exactly 2 distinct speaker identities recovered from bracketed/timestamped turn "
                    "markers - consistent with a 1:1")

    if signals.get("likely_chat"):
        add("strategy_chat", "",
            f"{signals.get('chat_header_line_count', 0)} Google-Chat-style message headers detected")

    if signals.get("likely_email"):
        add("admin_note", "",
            f"{signals.get('email_marker_count', 0)} email-header marker(s) detected - short pasted notes "
            "often route here")
        add("people_case_chat", "",
            f"{signals.get('email_marker_count', 0)} email-header marker(s) detected - person-specific "
            "incident chats often route here")

    return candidates


def classify_commands(run_id: str, candidates: list[dict], ignore_suggestion: dict | None) -> list[str]:
    commands = [f'guide {run_id}']
    for c in candidates:
        variant_flag = f' --variant {c["variant"]}' if c["variant"] else ""
        scope_flag = ' --scope "Project|Person"' if c["required_scope"] else ""
        scope_note = f'  (requires scope: {", ".join(c["required_scope"])})' if c["required_scope"] else ""
        commands.append(f'start {run_id} --source-type {c["source_type"]}{variant_flag}{scope_flag}{scope_note}')
    if ignore_suggestion:
        commands.append(f'ignore {run_id} --category {ignore_suggestion["category"]} --reason "..."')
    if not candidates:
        commands.append(f'start {run_id} --source-type <type> [--variant <variant>] --scope "Project|Person"'
                        '  (manual classification required - no strong deterministic signal fired)')
    return commands


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
    """Terminal: not an intake source at all. Explicit mutation, only
    reachable from a pre-processing state (see TRANSITIONS) - never
    auto-inferred from a filename or extension. Requires a concrete
    --reason (not just a category); leaves the source file exactly where
    it is - a queue row's (path, hash) identity keeps it from being
    rediscovered by a later `scan`, so no move/delete is needed to keep it
    out of the backlog."""
    reason = (args.reason or "").strip()
    if not reason:
        raise SystemExit("ignore requires --reason with a concrete reason - not blank, "
                         "not just repeating the --category.")

    def mutate(row: dict) -> None:
        validate_transition(row["Status"], "ignored")
        row["Status"] = "ignored"
        evidence = (getattr(args, "evidence", "") or "").strip()
        row["Reason"] = (f"ignored ({args.category}): {reason}"
                         + (f"  [evidence: {evidence}]" if evidence else ""))
    row = _update_run(args, mutate)
    return CommandResult(
        ok=True,
        data={"run_id": row["Run ID"], "status": "ignored", "category": args.category,
              "reason": reason},
        human_lines=[row_brief(row)],
        exit_code=0
    )


def cmd_mark_historical(args) -> CommandResult:
    """Terminal: processed before the queue existed. Explicit mutation,
    only reachable from a pre-processing state or as a correction of a
    mistaken `fail` (see TRANSITIONS) - never from `processing`/`blocked`,
    since a run that has actually started is not "pre-queue" by
    definition. Requires concrete --evidence (a specific evidence_log row,
    _skill_invocations date, document revision, etc.) - never a vague
    reason or "I remember doing this"."""
    evidence = (args.evidence or "").strip()
    if not evidence:
        raise SystemExit("mark-historical requires --evidence naming something concrete "
                         "(an evidence_log row, a _skill_invocations date, a document revision) - "
                         "not a vague reason or unverified memory.")

    def mutate(row: dict) -> None:
        validate_transition(row["Status"], "historical")
        row["Status"] = "historical"
        row["Reason"] = f"pre-queue history: {evidence}"
    row = _update_run(args, mutate)
    return CommandResult(
        ok=True,
        data={"run_id": row["Run ID"], "status": "historical", "evidence": evidence},
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
        "route_description": route.get("description", ""),
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
    if interpretation["route_description"]:
        lines.append(f"  route: {interpretation['route_description']}")
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


def resolve_source_path(row: dict) -> tuple[str, str]:
    """(path_used, path_field_used) - Current source preferred, Source
    fallback (Current source tracks the live file location; Source is the
    immutable discovery identity and can go stale after a move/archive -
    see guide's discovered-stage checklist). Raises only when the row
    records neither at all (a queue data-integrity issue, not a normal
    missing-file case)."""
    current_source = str(row.get("Current source", "")).strip()
    source = str(row.get("Source", "")).strip()
    if current_source:
        return current_source, "current_source"
    if source:
        return source, "source"
    raise SystemExit(f"Run {row.get('Run ID', '')!r} has neither Current source nor Source recorded - "
                     "nothing to read.")


def resolve_source_file_path(path_used: str) -> Path:
    normalized = path_used.replace("\\", "/").strip("/")
    parts = [p for p in normalized.split("/") if p]
    if not parts or ".." in parts:
        raise SystemExit(f"Unsafe source path recorded: {path_used!r}")
    return DATA_ROOT.joinpath(*parts)


def build_source_preview(row: dict, max_chars: int) -> tuple[dict, str | None, list[str]]:
    """Read-only source access + capped preview, shared by `classify` and
    `pack`. Unlike `classify` (which is useless without the file and fails
    outright), this degrades gracefully: a missing file becomes a warning,
    not an exception, since callers like `pack` are still useful without a
    preview (identity/operator-state/graph-context don't need the file).
    Returns (output-safe preview dict, full text or None - for internal
    signal detection only, NEVER put in output/queue/repo, warnings)."""
    path_used, path_field_used = resolve_source_path(row)
    preview: dict = {
        "source_path_used": path_used,
        "source_path_field_used": path_field_used,
        "file_exists": False,
        "extension": "",
        "size_bytes": None,
        "text_readable": False,
        "line_count": None,
        "preview": "",
        "preview_max_chars": max_chars,
        "preview_truncated": False,
    }
    warnings: list[str] = []
    try:
        file_path = resolve_source_file_path(path_used)
    except SystemExit as exc:
        warnings.append(str(exc))
        return preview, None, warnings

    preview["extension"] = file_path.suffix.lower()
    if not file_path.is_file():
        warnings.append(f"Source file not found on disk: {file_path} (read from {path_field_used}={path_used!r})")
        return preview, None, warnings

    preview["file_exists"] = True
    preview["size_bytes"] = file_path.stat().st_size
    text = None
    if preview["extension"] in TEXT_READABLE_EXTS:
        text = file_path.read_text(encoding="utf-8", errors="replace")
        preview["text_readable"] = True
        preview["line_count"] = len(text.splitlines())
    preview["preview"] = text[:max_chars] if text is not None else ""
    preview["preview_truncated"] = text is not None and len(text) > max_chars
    return preview, text, warnings


def cmd_classify(args) -> CommandResult:
    """Read-only pre-`start` helper: deterministic signals + candidate
    route hints for one discovered run. Never chooses a final source_type/
    variant/scope, never calls `start`, never writes anywhere - the
    classification decision stays with the agent, made after reading the
    actual source content this command points at."""
    services = get_services_cached()
    sheet = find_queue(services)
    rows = read_queue(services, sheet) if sheet else []
    row = get_run(rows, args.run_id)

    path_used, path_field_used = resolve_source_path(row)
    current_source = str(row.get("Current source", "")).strip()
    source = str(row.get("Source", "")).strip()

    file_path = resolve_source_file_path(path_used)
    if not file_path.is_file():
        raise SystemExit(f"Source file not found on disk: {file_path} (read from {path_field_used}={path_used!r})")

    extension = file_path.suffix.lower()
    size_bytes = file_path.stat().st_size
    max_chars = (args.max_preview_chars if getattr(args, "max_preview_chars", None)
                 and args.max_preview_chars > 0 else DEFAULT_MAX_PREVIEW_CHARS)

    text = None
    if extension in TEXT_READABLE_EXTS:
        text = file_path.read_text(encoding="utf-8", errors="replace")

    signals = detect_format_signals(text, extension)
    preview = text[:max_chars] if text is not None else ""
    preview_truncated = text is not None and len(text) > max_chars

    graph = load_graph()
    candidates = classify_candidate_routes(graph, signals, row)
    routed_source_types = sorted((graph.get("sources") or {}).keys())
    confidence = "signals_detected" if candidates else "low"

    reason_field = str(row.get("Reason", ""))
    ignore_suggestion = None
    if "duplicate content of" in reason_field:
        ignore_suggestion = {"category": "duplicate_data_quality", "reason_hint": reason_field}

    commands = classify_commands(args.run_id, candidates, ignore_suggestion)

    guardrails = [
        "This is a signals-only preview, not a classification - the final source_type/variant/scope "
        "decision is the agent's, made after reading the full source.",
        "candidate_routes are unranked hints, not a recommendation - do not `start` on one without reading "
        "the source content first.",
        "Never write the preview text, full source content, or full analysis into the queue, "
        "_skill_invocations, evidence_log, or this repo - only short operational summaries belong there.",
    ]

    data = {
        "run_id": args.run_id,
        "source_path_used": path_used,
        "source_path_field_used": path_field_used,
        "source": source,
        "current_source": current_source,
        "extension": extension,
        "size_bytes": size_bytes,
        "preview_max_chars": max_chars,
        "preview_truncated": preview_truncated,
        "preview": preview,
        "signals": signals,
        "confidence": confidence,
        "candidate_routes": candidates,
        "routed_source_types": routed_source_types,
        "ignore_suggestion": ignore_suggestion,
        "commands": commands,
        "guardrails": guardrails,
    }

    lines = [f"Classify preview for {args.run_id}",
             f"  source path used: {path_used}  (from {path_field_used})",
             f"  extension: {extension}  size: {size_bytes} bytes"]
    if signals.get("text_readable"):
        lines.append(f"  lines: {signals['line_count']}  speakers~: {signals['distinct_speaker_prefixes']}"
                     f"  chat headers~: {signals['chat_header_line_count']}"
                     f"  datetime markers~: {signals['datetime_marker_count']}"
                     f"  email markers~: {signals['email_marker_count']}")
    else:
        lines.append("  not text-readable - binary/unsupported format, filename/extension only")
    lines.append(f"  confidence: {confidence}")
    lines.append("  candidate_routes:")
    lines += [f"    - {c['source_type']}" + (f"/{c['variant']}" if c["variant"] else "")
              + f"  ({c['reason']})"
              + (f"\n      {c['route_description']}" if c.get("route_description") else "")
              for c in candidates] or ["    (none - manual classification required)"]
    if ignore_suggestion:
        lines.append(f"  ignore_suggestion: {ignore_suggestion['category']} - {ignore_suggestion['reason_hint']}")
    lines.append("  commands:")
    lines += [f"    $ {c}" for c in commands]
    lines.append("  guardrails:")
    lines += [f"    ! {g}" for g in guardrails]

    return CommandResult(ok=True, data=data, human_lines=lines, exit_code=0)


# ---------- pack (read-only cross-agent handoff, one run) ----------

def dashboard_category_for_row(row: dict) -> str:
    """Same section a run would land in under `dashboard` - lets `pack`
    tell a receiving agent "this is what dashboard would call it" without
    re-scanning the whole queue."""
    status = row.get("Status", "")
    if status in ("discovered", "needs_scope", "processing"):
        return "action_required"
    if status == "blocked":
        return "blocked"
    if status == "finalizing":
        return "finalizing"
    if status == "completed":
        return "completed"
    if status in ("ignored", "historical", "failed"):
        return "terminal"
    return "unknown"


def build_closure_expectations(graph: dict, entry_documents: list[str]) -> list[dict]:
    """Each entry document's own immediate downstream cascade edges, read
    straight out of document_graph.yaml - lets a receiving agent see what
    will eventually need resolving without re-deriving it."""
    docs = graph.get("documents") or {}
    expectations: list[dict] = []
    for doc in entry_documents:
        for edge in (docs.get(doc) or {}).get("downstream") or []:
            expectations.append({"from": doc, "to": edge.get("to"), "kind": edge.get("kind")})
    return expectations


def build_agent_handoff(run_id: str, identity: dict, interpretation: dict,
                        commands: list[str], classify_block: dict | None) -> str:
    """Concise prose block for a receiving agent in another session - what
    to read first, what to load, what to run next, what not to do. Every
    fact in it is already present elsewhere in the pack; this just orders
    it for a cold start."""
    read_first = identity["current_source"] or identity["source"] or "(no source path recorded on this run)"
    if interpretation["skills"]:
        skill_line = f"Load skill(s): {', '.join(interpretation['skills'])}."
    elif classify_block and classify_block["candidate_routes"]:
        hinted = sorted({s for c in classify_block["candidate_routes"] for s in c["skills"]})
        skill_line = ("Route not yet chosen - skills depend on it. Candidate routes hint at: "
                      f"{', '.join(hinted) if hinted else '(none)'}. Read the source and classify before "
                      "assuming any of these.")
    else:
        skill_line = "Route not yet known - read and classify the source before any skill can be named."
    next_cmd = commands[0] if commands else "(none - see checklist/guardrails)"
    lines = [
        f"Handoff for run {run_id} [{identity['status']}" + (f":{identity['stage']}" if identity["stage"] else "") + "]",
        f"Read first: {read_first}",
        skill_line,
        f"Run next: {next_cmd}",
        "Do not: start on an unread/unclassified source, default a missing project/person scope, write full "
        "transcript/source text or full analysis into the queue or this repo, or hand-edit a completed run's "
        "own Snapshot/queue row.",
        "Guardrails: prefer Current source over Source for live file access (Source may be historical); "
        "put the exact token run:<run-id> in _skill_invocations before completing; commit_workspace_state.py's "
        "message must include the run id in brackets, e.g. [<run-id>]; real business data belongs only in "
        "Drive/the private mirror, never this public repo.",
    ]
    return "\n".join(lines)


def cmd_pack(args) -> CommandResult:
    """Read-only cross-agent handoff/resume packet for one run - compact
    enough to paste into a fresh session and continue. Reuses dashboard/
    guide/classify/review logic exclusively; never creates, writes, or
    mutates _intake_queue, _closure_outcomes, _skill_invocations, mirror
    files, or the public repo. Never includes full source text - only a
    preview capped by --max-preview-chars."""
    services = get_services_cached()
    sheet = find_queue(services)
    rows = read_queue(services, sheet) if sheet else []
    row = get_run(rows, args.run_id)

    graph = load_graph()
    try:
        route = resolve_route(graph, row.get("Source type", ""), row.get("Route variant", ""))
    except SystemExit:
        route = {}

    ctx = load_review_context(services, args.run_id, rows=rows)
    eval_res = evaluate_run(ctx)

    max_chars = (args.max_preview_chars if getattr(args, "max_preview_chars", None)
                 and args.max_preview_chars > 0 else DEFAULT_MAX_PREVIEW_CHARS)
    preview, text, preview_warnings = build_source_preview(row, max_chars)

    identity = {
        "run_id": row.get("Run ID", ""),
        "status": row.get("Status", ""),
        "stage": row.get("Stage", ""),
        "source": row.get("Source", ""),
        "current_source": row.get("Current source", ""),
        "source_path_used": preview["source_path_used"],
        "source_path_field_used": preview["source_path_field_used"],
        "source_type": row.get("Source type", ""),
        "route_variant": row.get("Route variant", ""),
        "scopes": parse_scopes_cell(row.get("Scopes", "")),
        "source_hash": row.get("Source hash", ""),
        "source_text_version": row.get("Source text version", ""),
        "snapshot_sha": row.get("Snapshot", ""),
        "source_disposition": row.get("Source disposition", ""),
    }
    interpretation = {
        "skills": route.get("skills") or [],
        "entry_documents": route.get("entry") or [],
        "route_description": route.get("description", ""),
        "declared_scopes": parse_scopes_cell(row.get("Scopes", "")),
        "source_disposition": row.get("Source disposition", ""),
        "source_still_in_inbox": row.get("Source disposition", "") != "archived",
        "route_resolved": bool(route),
    }

    checklist, guide_commands, guide_extra = guide_stage_details(row, graph, route, eval_res, ctx)
    guardrails = guide_guardrails(row, interpretation)
    dashboard_category = dashboard_category_for_row(row)

    classify_block = None
    if not route:
        signals = detect_format_signals(text, preview["extension"])
        candidates = classify_candidate_routes(graph, signals, row)
        reason_field = str(row.get("Reason", ""))
        ignore_suggestion = None
        if "duplicate content of" in reason_field:
            ignore_suggestion = {"category": "duplicate_data_quality", "reason_hint": reason_field}
        classify_block = {
            "signals": signals,
            "confidence": "signals_detected" if candidates else "low",
            "candidate_routes": candidates,
            "routed_source_types": sorted((graph.get("sources") or {}).keys()),
            "ignore_suggestion": ignore_suggestion,
            "commands": classify_commands(args.run_id, candidates, ignore_suggestion),
        }

    commands = classify_block["commands"] if classify_block else guide_commands

    # evaluate_run always appends "Run cannot be completed from state X"
    # for any non-processing/closure status (discovered, blocked,
    # completed, ...) - true and expected, never an actual finding (same
    # filter `guide`/`dashboard` already apply to completed rows), so it
    # never belongs in the curated "problems" summary regardless of status.
    review_problems = [p for p in eval_res.all_problems if "Run cannot be completed from state" not in p]
    review_summary = {
        "unresolved_edges": eval_res.unresolved_edges,
        "entry_problems": eval_res.entry_problems,
        "problems": review_problems,
        "warnings": eval_res.warnings,
        "invocation_present": eval_res.invocation_present,
        "snapshot_sha": eval_res.snapshot_sha,
        "snapshot_problem": eval_res.snapshot_problem,
        "ready_for_completion": eval_res.ready_for_completion,
    }

    if route:
        graph_context = {
            "route_resolved": True,
            "route_description": interpretation["route_description"],
            "skills": interpretation["skills"],
            "entry_documents": interpretation["entry_documents"],
            "required_scope": sorted(needed_scopes(graph, route)),
        }
        if row.get("Stage") == "closure":
            graph_context["closure_expectations"] = build_closure_expectations(graph, interpretation["entry_documents"])
    else:
        graph_context = {
            "route_resolved": False,
            "candidate_source_types": sorted({c["source_type"]
                                             for c in (classify_block or {}).get("candidate_routes", [])}),
            "routed_source_types": (classify_block or {}).get("routed_source_types",
                                                               sorted((graph.get("sources") or {}).keys())),
        }

    agent_handoff = build_agent_handoff(args.run_id, identity, interpretation, commands, classify_block)

    data = {
        "run_id": args.run_id,
        "identity": identity,
        "interpretation": interpretation,
        "dashboard_category": dashboard_category,
        "checklist": checklist,
        "commands": commands,
        "guardrails": guardrails,
        "review_summary": review_summary,
        "classify": classify_block,
        "graph_context": graph_context,
        "source_preview": preview,
        "agent_handoff": agent_handoff,
    }

    stage_label = identity["status"] + (f":{identity['stage']}" if identity["stage"] else "")
    lines = [f"Pack for {args.run_id}  [{stage_label}]  ({dashboard_category})",
             f"  source: {preview['source_path_used']}  (from {preview['source_path_field_used']})"]
    if preview["text_readable"]:
        lines.append(f"  lines: {preview['line_count']}  size: {preview['size_bytes']} bytes"
                     f"  preview_truncated: {preview['preview_truncated']}")
    elif preview["file_exists"]:
        lines.append(f"  size: {preview['size_bytes']} bytes  (binary/unsupported - metadata only)")
    else:
        lines.append("  (source file not found on disk - see warnings)")
    if interpretation.get("route_description"):
        lines.append(f"  route: {interpretation['route_description']}")
    lines.append("  commands:")
    lines += [f"    $ {c}" for c in commands] or ["    (none)"]
    lines.append("  guardrails:")
    lines += [f"    ! {g}" for g in guardrails]
    lines.append("  agent_handoff:")
    lines += [f"    {line}" for line in agent_handoff.splitlines()]

    return CommandResult(ok=True, data=data, warnings=preview_warnings, human_lines=lines, exit_code=0)


# ---------- triage (read-only backlog overview + explicit terminal actions) ----------

def allowed_terminal_actions_for_status(status: str) -> list[str]:
    """Which of the two explicit triage terminal actions (`ignore`,
    `mark-historical`) TRANSITIONS actually allows from this status - read
    straight from the same table `start`/`complete` validate against, so
    triage can never suggest an action the state machine would reject."""
    reachable = TRANSITIONS.get(status, set())
    actions: list[str] = []
    if "ignored" in reachable:
        actions.append("ignore")
    if "historical" in reachable:
        actions.append("mark-historical")
    return actions


def triage_terminal_action_commands(run_id: str, allowed: list[str]) -> list[str]:
    commands: list[str] = []
    if "ignore" in allowed:
        commands.append(f'ignore {run_id} --category <non_intake_course_material|reference_material|'
                        f'duplicate_data_quality|other> --reason "..." [--evidence "..."]')
    if "mark-historical" in allowed:
        commands.append(f'mark-historical {run_id} --evidence "..."')
    return commands


def cmd_triage(args) -> CommandResult:
    """Read-only backlog overview, built from the same dashboard/classify
    helpers - never a new source of truth, never an auto-classification.
    Lists candidates in discovered/needs_scope/blocked (or all three) with
    the exact terminal-action commands TRANSITIONS actually allows for
    each; applying one is always a separate, explicit `ignore`/
    `mark-historical` call."""
    services = get_services_cached()
    sheet = find_queue(services)
    rows = read_queue(services, sheet) if sheet else []

    project, person = (args.project or "").strip(), (args.person or "").strip()
    if project or person:
        rows = [r for r in rows if row_matches_scope_filter(r, project, person)]

    category = (args.category or "discovered").strip().lower()
    valid_categories = {"discovered", "needs_scope", "blocked", "all"}
    if category not in valid_categories:
        raise SystemExit(f"--category must be one of {sorted(valid_categories)} (got {category!r})")
    statuses = {"discovered", "needs_scope", "blocked"} if category == "all" else {category}

    candidate_rows = [r for r in rows if r.get("Status") in statuses]
    limit = args.limit if getattr(args, "limit", None) and args.limit > 0 else DEFAULT_DASHBOARD_LIMIT

    items = []
    for row in candidate_rows[:limit]:
        status = row.get("Status", "")
        path_used, path_field_used, file_exists = "", "", None
        try:
            path_used, path_field_used = resolve_source_path(row)
            file_exists = resolve_source_file_path(path_used).is_file()
        except SystemExit:
            pass
        allowed = allowed_terminal_actions_for_status(status)
        items.append({
            **dashboard_row_summary(row),
            "current_source": row.get("Current source", ""),
            "source_path_used": path_used,
            "source_path_field_used": path_field_used,
            "file_exists": file_exists,
            "recommended_command": dashboard_recommended_command(row),
            "allowed_terminal_actions": allowed,
            "terminal_action_commands": triage_terminal_action_commands(row["Run ID"], allowed),
        })

    counts = {s: sum(1 for r in rows if r.get("Status") == s) for s in ("discovered", "needs_scope", "blocked")}

    data = {
        "category": category,
        "counts": counts,
        "total_candidates": len(candidate_rows),
        "items": items,
        "limit": limit,
        "guardrails": [
            "Never infer a terminal action (ignore/mark-historical) from filename or extension alone - "
            "read the source (`classify`/`triage-one`) first.",
            "ignore requires a concrete --reason; mark-historical requires concrete --evidence - neither "
            "accepts a blank or vague value.",
            "This command never mutates anything - apply ignore/mark-historical explicitly, one run at a time.",
        ],
    }

    lines = [f"Triage ({category}): {len(items)} of {len(candidate_rows)} candidate(s) shown "
             f"(discovered={counts['discovered']}, needs_scope={counts['needs_scope']}, "
             f"blocked={counts['blocked']})"]
    for item in items:
        lines.append(f"  {item['run_id']}  [{item['status']}]  {item['source']}")
        lines.append(f"    -> {item['recommended_command']}")
        lines += [f"    ! {c}" for c in item["terminal_action_commands"]]
    if not items:
        lines.append("  (none)")

    return CommandResult(ok=True, data=data, human_lines=lines, exit_code=0)


def cmd_triage_one(args) -> CommandResult:
    """Read-only detailed triage view for one run: source access/age,
    classify-style signals and candidate routes, a capped preview, and the
    exact terminal-action commands actually available from its current
    status per TRANSITIONS - never a suggestion to auto-apply one."""
    services = get_services_cached()
    sheet = find_queue(services)
    rows = read_queue(services, sheet) if sheet else []
    row = get_run(rows, args.run_id)

    max_chars = (args.max_preview_chars if getattr(args, "max_preview_chars", None)
                 and args.max_preview_chars > 0 else DEFAULT_MAX_PREVIEW_CHARS)
    preview, text, preview_warnings = build_source_preview(row, max_chars)

    graph = load_graph()
    signals = detect_format_signals(text, preview["extension"])
    candidates = classify_candidate_routes(graph, signals, row)
    reason_field = str(row.get("Reason", ""))
    ignore_suggestion = None
    if "duplicate content of" in reason_field:
        ignore_suggestion = {"category": "duplicate_data_quality", "reason_hint": reason_field}
    classify_block = {
        "signals": signals,
        "confidence": "signals_detected" if candidates else "low",
        "candidate_routes": candidates,
        "routed_source_types": sorted((graph.get("sources") or {}).keys()),
        "ignore_suggestion": ignore_suggestion,
    }

    status = row.get("Status", "")
    allowed = allowed_terminal_actions_for_status(status)
    terminal_commands = triage_terminal_action_commands(args.run_id, allowed)
    if ignore_suggestion and "ignore" in allowed:
        terminal_commands.insert(0, f'ignore {args.run_id} --category {ignore_suggestion["category"]} '
                                    f'--reason "..."  (row Reason already flags: '
                                    f'{ignore_suggestion["reason_hint"]})')
    process_commands = [f'classify {args.run_id}', f'guide {args.run_id}', f'pack {args.run_id}']

    identity = dashboard_row_summary(row)
    identity["current_source"] = row.get("Current source", "")
    identity["source_hash"] = row.get("Source hash", "")
    age_days = None
    discovered_ts = parse_ts(row.get("Discovered", ""))
    if discovered_ts:
        age_days = round((dt.datetime.now().timestamp() - discovered_ts) / 86400, 2)
    identity["age_days"] = age_days

    guardrails = [
        "Never infer a terminal action from filename or extension alone - the preview/signals below are "
        "hints, not a decision; read the source before choosing.",
        "ignore requires a concrete --reason; mark-historical requires concrete --evidence.",
        "This command never mutates anything.",
    ]

    data = {
        "run_id": args.run_id,
        "identity": identity,
        "source_preview": preview,
        "classify": classify_block,
        "allowed_terminal_actions": allowed,
        "terminal_action_commands": terminal_commands,
        "process_commands": process_commands,
        "guardrails": guardrails,
    }

    lines = [f"Triage detail for {args.run_id}  [{status}]",
             f"  source: {preview['source_path_used']}  (from {preview['source_path_field_used']})",
             f"  age: {age_days} day(s) since discovered" if age_days is not None else "  age: unknown"]
    if preview["text_readable"]:
        lines.append(f"  lines: {preview['line_count']}  confidence: {classify_block['confidence']}")
    lines.append("  candidate_routes:")
    lines += [f"    - {c['source_type']}" + (f"/{c['variant']}" if c["variant"] else "")
              + f"  ({c['reason']})" for c in candidates] or ["    (none - manual review required)"]
    lines.append("  allowed terminal actions: " + (", ".join(allowed) or "(none from this status)"))
    lines.append("  commands:")
    lines += [f"    $ {c}" for c in terminal_commands + process_commands]
    lines.append("  guardrails:")
    lines += [f"    ! {g}" for g in guardrails]

    return CommandResult(ok=True, data=data, warnings=preview_warnings, human_lines=lines, exit_code=0)


# ---------- gates (read-only M2 gate dashboard, Phase 12) ----------

GATES_EMPTY_ROUND_CHAR_THRESHOLD = 60
GATES_STALE_AGE_DAYS = 2


def parse_round_date(value: str | None) -> dt.date | None:
    if not value:
        return None
    try:
        return dt.datetime.strptime(value.strip(), "%Y-%m-%d").date()
    except ValueError:
        return None


def row_projects(row: dict) -> set[str]:
    """Every project this queue row is scoped to - declared Scopes tuples
    first, falling back to the semicolon-joined Project field for rows that
    never declared an explicit scope yet (discovered/needs_scope), same
    fallback rule as row_matches_scope_filter."""
    projects = {p.strip() for p, _ in parse_scopes_cell(row.get("Scopes", "")) if p.strip()}
    if not projects:
        raw = str(row.get("Project", "")).strip()
        if raw:
            projects = {x.strip() for x in raw.split(";") if x.strip()}
    return projects


def compute_recommended_action(block_chars: int, has_open_queue_run: bool, age_days: int | None) -> str:
    """Deterministic-only recommendation - no content judgment, no semantic
    reading of the question text itself:
    - an effectively empty round (no real question text ever added) needs
      no action yet;
    - a project with an open (not yet completed/terminal) queue run may
      already have its answer sitting in that unprocessed source - process
      it first rather than asking the user to re-derive the same answer;
    - an old enough round with real content and no pending source is a
      genuine ask for M2/the user;
    - anything else (fresh round, ambiguous) falls back to manual review."""
    if block_chars <= GATES_EMPTY_ROUND_CHAR_THRESHOLD:
        return "no action yet"
    if has_open_queue_run:
        return "process existing source first"
    if age_days is not None and age_days >= GATES_STALE_AGE_DAYS:
        return "ask M2/user for answers"
    return "manual review required"


def build_gate_row(project: str, round_summary: dict, has_open_queue_run: bool, today: dt.date) -> dict | None:
    """One gates row from a project's get_pending_round_summary() result, or
    None if that project's m2_input has no round currently pending (nothing
    to gate on). Never includes question/addendum text - only counts and
    the first addendum heading label (see get_pending_round_summary)."""
    if not round_summary.get("pending"):
        return None
    round_date_str = round_summary.get("round_date")
    round_date = parse_round_date(round_date_str)
    age_days = (today - round_date).days if round_date else None
    block_chars = round_summary.get("block_chars", 0)
    return {
        "project": project,
        "round_date": round_date_str,
        "age_days": age_days,
        "addenda_count": round_summary.get("addenda_count", 0),
        "first_heading": round_summary.get("first_heading"),
        "block_chars": block_chars,
        "gated_documents": ["project_risk", "project_development_plan"],
        "gated_documents_secondary": ["action_items"],
        "recommended_action": compute_recommended_action(block_chars, has_open_queue_run, age_days),
    }


def sort_and_filter_gates(rows: list[dict], project_filter: str = "", min_age_days: int = 0,
                           limit: int = 0) -> list[dict]:
    """Oldest-first sort (missing age sorts last, never crashes), then
    project/min-age filters, then limit. A pure function so gates' grouping/
    sorting/filtering is unit-testable without live Drive access."""
    out = list(rows)
    project_filter = (project_filter or "").strip()
    if project_filter:
        out = [r for r in out if r["project"].casefold() == project_filter.casefold()]
    if min_age_days:
        out = [r for r in out if (r["age_days"] if r["age_days"] is not None else -1) >= min_age_days]
    out.sort(key=lambda r: r["age_days"] if r["age_days"] is not None else -1, reverse=True)
    if limit and limit > 0:
        out = out[:limit]
    return out


def cmd_gates(args) -> CommandResult:
    """Read-only M2 gate dashboard: every project with a currently pending
    m2_input round, and what it's gating. Never answers a question, never
    writes project_risk/project_development_plan/action_items, never
    records a closure outcome - purely Drive/Sheets *reads* (find_folder_path,
    list_children, find_document, docs().get(), read_queue) plus the pure
    helpers above. No qa_manage.py verb here mutates _intake_queue -
    write_queue/export_queue_terminal are never called."""
    from pipeline_common import get_pending_round_summary
    from m2_workspace_layout import DOC_MIME, FOLDER_MIME, find_document, find_folder_path, list_children
    from sync_m2_source_docs_to_sheets import ROOT_FOLDER_ID

    services = get_services_cached()
    drive, docs = services["drive"], services["docs"]

    sheet = find_queue(services)
    rows = read_queue(services, sheet) if sheet else []
    open_statuses = {"discovered", "needs_scope", "processing", "blocked"}
    projects_with_open_runs = {
        p.casefold() for row in rows if row.get("Status") in open_statuses for p in row_projects(row)
    }

    m2_root = find_folder_path(drive, ROOT_FOLDER_ID, ["20_M2_Project_Management"])
    project_folders: list[tuple[str, str]] = []
    if m2_root:
        for item in list_children(drive, m2_root["id"]):
            name = str(item.get("name", ""))
            if item.get("mimeType") == FOLDER_MIME and not name.startswith("_"):
                project_folders.append((name, item["id"]))
    project_folders.sort(key=lambda t: t[0].casefold())

    today = dt.date.today()
    gate_rows: list[dict] = []
    for name, folder_id in project_folders:
        doc = find_document(drive, folder_id, "m2_input", "m2_input", DOC_MIME)
        if not doc:
            continue
        summary = get_pending_round_summary(docs, doc["id"])
        row = build_gate_row(name, summary, name.casefold() in projects_with_open_runs, today)
        if row:
            gate_rows.append(row)

    limit = args.limit if getattr(args, "limit", None) else 0
    min_age_days = args.min_age_days if getattr(args, "min_age_days", None) else 0
    result_rows = sort_and_filter_gates(gate_rows, args.project or "", min_age_days, limit)

    data = {
        "generated_date": today.isoformat(),
        "projects_scanned": len(project_folders),
        "pending_rounds_total": len(gate_rows),
        "gates": result_rows,
    }

    lines = [f"M2 gates (oldest first) - {len(result_rows)} of {len(gate_rows)} pending round(s), "
             f"{len(project_folders)} project(s) scanned"]
    if not result_rows:
        lines.append("  (none)")
    for r in result_rows:
        age = f"{r['age_days']}d" if r["age_days"] is not None else "unknown age"
        lines.append(f"  - {r['project']}: round {r['round_date']}  ({age}, {r['addenda_count']} addenda)")
        lines.append(f"      gates: {', '.join(r['gated_documents'])}"
                     f"  (secondary: {', '.join(r['gated_documents_secondary'])})")
        if r["first_heading"]:
            lines.append(f"      first addendum: {r['first_heading']}")
        lines.append(f"      next action: {r['recommended_action']}")

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
    p.add_argument("--reason", required=True, help="concrete reason - required, not just the category")
    p.add_argument("--evidence", default="", help="optional supporting evidence for the audit trail")

    p = sub.add_parser("mark-historical", help="terminal: processed before the queue existed",
                       parents=[parent])
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

    p = sub.add_parser("classify", help="read-only signals + candidate route hints for one "
                                        "discovered run, before start", parents=[parent])
    p.add_argument("run_id")
    p.add_argument("--max-preview-chars", type=int, default=DEFAULT_MAX_PREVIEW_CHARS,
                   help=f"cap on the returned preview excerpt (default {DEFAULT_MAX_PREVIEW_CHARS})")

    p = sub.add_parser("pack", help="read-only cross-agent handoff/resume packet for one run",
                       parents=[parent])
    p.add_argument("run_id")
    p.add_argument("--max-preview-chars", type=int, default=DEFAULT_MAX_PREVIEW_CHARS,
                   help=f"cap on the returned source preview excerpt (default {DEFAULT_MAX_PREVIEW_CHARS})")

    p = sub.add_parser("triage", help="read-only backlog overview (discovered/needs_scope/blocked)",
                       parents=[parent])
    p.add_argument("--limit", type=int, default=DEFAULT_DASHBOARD_LIMIT,
                   help=f"candidates listed (default {DEFAULT_DASHBOARD_LIMIT})")
    p.add_argument("--project", default="", help="filter to one project")
    p.add_argument("--person", default="", help="filter to one person")
    p.add_argument("--category", default="discovered",
                   choices=["discovered", "needs_scope", "blocked", "all"],
                   help="which backlog bucket to list (default discovered)")

    p = sub.add_parser("triage-one", help="read-only detailed triage view for one run",
                       parents=[parent])
    p.add_argument("run_id")
    p.add_argument("--max-preview-chars", type=int, default=DEFAULT_MAX_PREVIEW_CHARS,
                   help=f"cap on the returned preview excerpt (default {DEFAULT_MAX_PREVIEW_CHARS})")

    p = sub.add_parser("gates", help="read-only M2 gate dashboard: pending m2_input rounds and "
                                      "what they gate", parents=[parent])
    p.add_argument("--project", default="", help="filter to one project")
    p.add_argument("--limit", type=int, default=0, help="cap the number of gates listed (0 = no cap)")
    p.add_argument("--min-age-days", type=int, default=0,
                   help="only list rounds at least this many days old")

    args = parser.parse_args()

    commands = {
        "scan": cmd_scan, "status": cmd_status, "next": cmd_next,
        "start": cmd_start, "record-analysis": cmd_record_analysis,
        "record-apply": cmd_record_apply, "resolve-edge": cmd_resolve_edge,
        "add-scope": cmd_add_scope,
        "block": cmd_block, "fail": cmd_fail, "ignore": cmd_ignore,
        "mark-historical": cmd_mark_historical, "archive-source": cmd_archive_source,
        "resume": cmd_resume, "complete": cmd_complete, "review": cmd_review,
        "dashboard": cmd_dashboard, "guide": cmd_guide, "classify": cmd_classify,
        "pack": cmd_pack, "triage": cmd_triage, "triage-one": cmd_triage_one,
        "gates": cmd_gates,
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
