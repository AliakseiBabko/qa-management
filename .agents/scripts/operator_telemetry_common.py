"""Shared schema/constants for the Phase 11 operator-telemetry scripts
(measure_operator_outputs.py, finalize_operator_run.py, check_operator_csv.py,
extract_agent_telemetry.py, record_agent_session.py).

Modeled on the erp-web-tests benchmark-playwright-debugging skill's
methodology (canonical append-only CSV, finalizer/extractor split,
deterministic derived metrics, diff-guarded rewrites) but stripped down to
what this repo's read-only operator commands need: measuring whether
dashboard/guide/classify/pack/triage/search/show_project_state reduce
output size and token usage versus older full-read workflows. There is no
fix/patch/EQA/IRR concept here - this is a pure output/token measurement
layer, not a debugging benchmark.

The CSV must never contain real command output, source previews, or real
names/projects (see the module docstring on CSV_HEADER below and
check_operator_csv.py's leak guard). Only counts and redacted command
labels are stored.

Two separate CSVs, two separate questions
------------------------------------------
`operator-runs.csv` (CSV_HEADER below) answers "how large was this
command's output?" - one row per measured read-only command invocation.
`agent-sessions.csv` (AGENT_SESSION_CSV_HEADER below) answers "how many
model tokens did this agent session actually consume?" - one row per
extracted/recorded agent runtime session, which commonly spans MANY
operator-runs.csv rows (a single long conversation can run many measured
commands). They are intentionally not the same table: a session's token
total cannot be honestly attributed back to any one command within it, so
operator-runs.csv's `actual_*` fields stay blank unless a row genuinely
was its own dedicated one-command session (rare) - see agent-sessions.csv's
`linked_operator_run_ids` for the (many-rows -> one session) relationship
instead. Neither CSV's append/diff-guard functions ever rewrite an existing
row of the OTHER CSV, or of their own.
"""

from __future__ import annotations

import csv
import re
import subprocess
from pathlib import Path

TELEMETRY_ROOT = Path(__file__).resolve().parent.parent / "telemetry"
CSV_PATH = TELEMETRY_ROOT / "operator-runs.csv"
TEMPLATE_PATH = TELEMETRY_ROOT / "templates" / "operator-run-note.md"
AGENT_SESSION_CSV_PATH = TELEMETRY_ROOT / "agent-sessions.csv"

# One row per measured command invocation. Every column here is either a
# count, a boolean-ish yes/no, an enum, or a redacted label - never raw
# command output or source text.
CSV_HEADER = [
    "case_id",
    "run_id",
    "date",
    "runtime",
    "model_label",
    "command_name",
    "command_args_redacted",
    "json_mode",
    "status",
    "elapsed_ms",
    "stdout_bytes",
    "stderr_bytes",
    "output_chars",
    "preview_chars",
    "result_count",
    "truncated",
    "approximate_input_tokens",
    "approximate_output_tokens",
    "actual_input_tokens",
    "actual_cache_creation_tokens",
    "actual_cache_read_tokens",
    "actual_output_tokens",
    "actual_reasoning_tokens",
    "total_tokens",
    "estimated_cost_usd",
    "baseline_command",
    "reduction_ratio_vs_baseline",
    "notes_file",
    "notes",
]

# Fields that must always be non-blank on any row.
REQUIRED_FIELDS = [
    "case_id", "run_id", "date", "runtime", "command_name",
    "command_args_redacted", "json_mode", "status", "elapsed_ms",
    "stdout_bytes", "stderr_bytes", "output_chars", "truncated",
]

# Fields that, when non-blank, must parse as a number (int or float).
NUMERIC_FIELDS = [
    "elapsed_ms", "stdout_bytes", "stderr_bytes", "output_chars",
    "preview_chars", "result_count", "approximate_input_tokens",
    "approximate_output_tokens", "actual_input_tokens",
    "actual_cache_creation_tokens", "actual_cache_read_tokens",
    "actual_output_tokens", "actual_reasoning_tokens", "total_tokens",
    "estimated_cost_usd", "reduction_ratio_vs_baseline",
]

VALID_RUNTIME = {"Codex", "Claude Code", "Antigravity", "manual_script"}
VALID_YES_NO = {"yes", "no"}
VALID_STATUS = {"ok", "error"}

# Session rows use extractor/runtime keys, not the display labels used by
# operator-runs.csv. `record_agent_session.py` normalizes accepted aliases
# before writing, so the persisted CSV stays consistent.
AGENT_SESSION_VALID_RUNTIME = {"claude", "codex", "cline", "antigravity", "manual"}
# Kept valid for historical rows already appended before runtime alias
# normalization existed. New rows should be written with canonical values.
AGENT_SESSION_LEGACY_RUNTIME = {"claude-code"}

# One row per recorded agent-runtime session (see the module docstring's
# "Two separate CSVs" section for why this is not just another
# operator-runs.csv column).
AGENT_SESSION_CSV_HEADER = [
    "session_run_id",
    "date",
    "runtime",
    "model_label",
    "session_id",
    "linked_operator_run_ids",
    "objective",
    "started_at",
    "ended_at",
    "elapsed_min",
    "actual_input_tokens",
    "actual_cache_creation_tokens",
    "actual_cache_read_tokens",
    "actual_output_tokens",
    "actual_reasoning_tokens",
    "total_tokens",
    "estimated_cost_usd",
    "extraction_method",
    "confidence",
    "notes",
]

AGENT_SESSION_REQUIRED_FIELDS = [
    "session_run_id", "date", "runtime", "session_id", "objective",
    "extraction_method", "confidence",
]

AGENT_SESSION_NUMERIC_FIELDS = [
    "elapsed_min", "actual_input_tokens", "actual_cache_creation_tokens",
    "actual_cache_read_tokens", "actual_output_tokens", "actual_reasoning_tokens",
    "total_tokens", "estimated_cost_usd",
]

VALID_EXTRACTION_METHOD = {
    "claude_log", "codex_log", "antigravity_cli", "antigravity_db",
    "cline_history", "manual",
}
# "manual" is a 4th confidence bucket beyond high/medium/low, deliberately -
# a manually-entered figure (read off a runtime's own usage UI, typed in by
# a person) has a different trust profile than any of the three automatic-
# extraction confidence levels, and conflating it with one of them would
# overstate or understate it depending on which was picked.
VALID_CONFIDENCE = {"high", "medium", "low", "manual"}

# Case catalog: case_id -> command template. `{target}` is substituted from
# --target at measurement time and is REDACTED back to a placeholder before
# anything is written to the CSV or a committed note - the live value never
# reaches a committed artifact. Commands with no {target} placeholder don't
# require --target. All commands here are read-only by construction (no
# qa_manage.py verb here mutates state - see MUTATING_VERBS below, checked
# defensively in measure_operator_outputs.py).
CASES: dict[str, dict] = {
    "dashboard_overview": {
        "command_name": "qa_manage.py dashboard",
        "argv": ["qa_manage.py", "dashboard", "--json"],
        "json_mode": True,
        "baseline_of": None,
    },
    "guide_discovered": {
        "command_name": "qa_manage.py guide",
        "argv": ["qa_manage.py", "guide", "{target}", "--json"],
        "json_mode": True,
        "baseline_of": "show_project_state_full_project",
        "requires_target": "run_id",
    },
    "classify_discovered": {
        "command_name": "qa_manage.py classify",
        "argv": ["qa_manage.py", "classify", "{target}", "--json"],
        "json_mode": True,
        "baseline_of": "show_project_state_full_project",
        "requires_target": "run_id",
    },
    "pack_discovered": {
        "command_name": "qa_manage.py pack",
        "argv": ["qa_manage.py", "pack", "{target}", "--json"],
        "json_mode": True,
        "baseline_of": "show_project_state_full_project",
        "requires_target": "run_id",
    },
    "completed_run_review": {
        "command_name": "qa_manage.py review",
        "argv": ["qa_manage.py", "review", "{target}", "--json"],
        "json_mode": True,
        "baseline_of": None,
        "requires_target": "run_id",
    },
    "triage_overview": {
        "command_name": "qa_manage.py triage",
        "argv": ["qa_manage.py", "triage", "--json"],
        "json_mode": True,
        "baseline_of": None,
    },
    "triage_one": {
        "command_name": "qa_manage.py triage-one",
        "argv": ["qa_manage.py", "triage-one", "{target}", "--json"],
        "json_mode": True,
        "baseline_of": None,
        "requires_target": "run_id",
    },
    "search_current": {
        "command_name": "search_workspace.py search",
        "argv": ["search_workspace.py", "search", "{target}", "--json"],
        "json_mode": True,
        "baseline_of": None,
        "requires_target": "query",
    },
    "search_history": {
        "command_name": "search_workspace.py history",
        "argv": ["search_workspace.py", "history", "{target}", "--json"],
        "json_mode": True,
        "baseline_of": None,
        "requires_target": "query",
    },
    "show_project_state_targeted": {
        "command_name": "show_project_state.py --document",
        "argv": ["show_project_state.py", "--project", "{target}",
                 "--document", "m2_input", "--limit", "20", "--json"],
        "json_mode": True,
        "baseline_of": "show_project_state_full_project",
        "requires_target": "project",
    },
    "show_project_state_full_project": {
        "command_name": "show_project_state.py --project (full)",
        "argv": ["show_project_state.py", "--project", "{target}", "--json"],
        "json_mode": True,
        "baseline_of": None,
        "requires_target": "project",
    },
}

# qa_manage.py verbs that mutate state - measure_operator_outputs.py refuses
# to run any case whose argv contains one of these, defense-in-depth on top
# of the case catalog above only listing read-only verbs.
MUTATING_VERBS = {
    "start", "record-analysis", "record-apply", "resolve-edge", "add-scope",
    "block", "fail", "ignore", "mark-historical", "archive-source", "resume",
    "complete", "next",
}

# ASCII-only allowlist for command_args_redacted / notes / notes_file - a
# structural guard against accidental real-name leakage. This repo's business
# names are predominantly Cyrillic; requiring pure ASCII here catches those.
# It is a defense-in-depth backstop, not the primary safeguard - the primary
# safeguard is that measure_operator_outputs.py substitutes {target} back to
# a placeholder token before writing anything, so a live --target value never
# reaches a written field in the first place. {}/() are allowlisted because
# every {target}-templated case's own redacted command string (e.g.
# "qa_manage.py review {target} --json") legitimately contains the literal
# placeholder braces - excluding them meant no {target} case could ever
# actually be --append-csv'd (found live: only the two no-target cases,
# dashboard_overview/triage_overview, had ever produced a row).
_ASCII_SAFE_RE = re.compile(r"^[A-Za-z0-9_\-\.\s/:,<>=\[\]{}()]*$")


def is_ascii_safe(value: str) -> bool:
    return bool(_ASCII_SAFE_RE.match(value or ""))


# Email addresses are already rejected by is_ascii_safe (the '@' character
# isn't in its allowlist), but that rejection is incidental and produces a
# vague "ASCII-safe leak guard" message. This dedicated check runs first so
# a caller gets a precise reason instead - found live: an agent-session
# `notes` field is exactly the kind of free text a real email is most
# likely to slip into (e.g. quoting a person-card verbatim).
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def contains_email_address(value: str) -> bool:
    return bool(_EMAIL_RE.search(value or ""))


def contains_watch_string(text: str, watch) -> list[str]:
    """Return every entry in `watch` that appears as a literal substring of
    `text`. Pure and registry-agnostic - the caller supplies the watch-list
    (e.g. check_sensitive_data.load_watch_strings()'s live Drive fetch, or a
    synthetic set in a test); this function never loads anything itself, so
    it never needs network/Drive access to be exercised in tests."""
    if not text or not watch:
        return []
    return [w for w in watch if w and w in text]


def redact_argv(argv: list[str], target_placeholder: str = "<target>") -> str:
    """Render an argv list as a redacted, space-joined label - substituting
    any resolved target value back to a generic placeholder token so the
    live value is never persisted. Callers pass the already-redacted argv
    (with {target} still literal, or already replaced) - this just joins and
    normalizes for storage."""
    return " ".join(argv)


def _read_csv_rows(csv_path: Path, default_header: list[str]) -> tuple[list[str], list[dict]]:
    """Read a CSV, returning (header, rows). Creates no file as a side
    effect - callers that need the file to exist should check the path."""
    if not csv_path.exists():
        return list(default_header), []
    with open(csv_path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        header = list(reader.fieldnames or default_header)
        rows = list(reader)
    return header, rows


def _append_csv_row(csv_path: Path, header: list[str], id_field: str, row: dict,
                    read_fn) -> None:
    """Append exactly one row to a canonical-header CSV, creating it with
    that header if it does not exist yet. Never rewrites an existing row -
    a pure append, keyed on `id_field`. Raises ValueError (writing nothing)
    if `id_field`'s value already exists or the on-disk header has drifted
    from `header`."""
    existing_header, existing_rows = read_fn()
    if existing_header != header:
        raise ValueError(
            f"CSV header does not match canonical schema.\n  expected: {header}\n  found:    {existing_header}"
        )
    key = row.get(id_field)
    if any(r.get(id_field) == key for r in existing_rows):
        raise ValueError(f"{id_field} '{key}' already exists in the CSV - refusing to duplicate.")

    csv_path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not csv_path.exists()
    with open(csv_path, "a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        if write_header:
            writer.writeheader()
        writer.writerow({k: row.get(k, "") for k in header})


def _diff_guard_new_row_only(csv_path: Path, id_field: str, target_id: str, read_fn,
                             ref: str = "HEAD", repo_root: Path | None = None) -> tuple[bool, list[str]]:
    """Compare the working-tree CSV against `ref` (default HEAD) and assert
    that the only difference is the addition of `target_id`'s row (matched
    on `id_field`). Any other added/removed/modified row, or a header
    change, is a violation - the diff-guard pattern from the erp-web-tests
    benchmark skill's check_csv.py, adapted for a pure-append (no in-place
    row update) model. Returns (ok, violations)."""
    root = repo_root or csv_path.parent.parent.parent
    try:
        rel = csv_path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        rel = csv_path.name

    committed = subprocess.run(
        ["git", "-C", str(root), "show", f"{ref}:{rel}"],
        capture_output=True, text=True, encoding="utf-8",
    )
    if committed.returncode != 0:
        return True, []  # no baseline (new file) - nothing to guard against

    import io
    base_reader = csv.DictReader(io.StringIO(committed.stdout))
    base_header = list(base_reader.fieldnames or [])
    base_rows = {r.get(id_field): r for r in base_reader}

    work_header, work_rows_list = read_fn()
    work_rows = {r.get(id_field): r for r in work_rows_list}

    violations = []
    if base_header != work_header:
        violations.append(f"Header changed.\n    {ref}: {base_header}\n    work: {work_header}")

    for rid in base_rows:
        if rid not in work_rows:
            violations.append(f"Row removed since {ref}: '{rid}'.")
        elif base_rows[rid] != work_rows[rid]:
            violations.append(f"Unrelated row '{rid}' was modified since {ref}.")

    for rid in work_rows:
        if rid not in base_rows and rid != target_id:
            violations.append(f"Row added that is not the target: '{rid}'.")

    return (len(violations) == 0), violations


# ---------------------------------------------------------------------------
# operator-runs.csv (command-footprint rows)
# ---------------------------------------------------------------------------

def read_rows() -> tuple[list[str], list[dict]]:
    """Read operator-runs.csv, returning (header, rows). Creates no file as
    a side effect - callers that need the file to exist should check
    CSV_PATH."""
    return _read_csv_rows(CSV_PATH, CSV_HEADER)


def _check_free_text_field(field: str, val: str, watch) -> list[str]:
    """Shared leak-guard body for one free-text CSV field: email pattern,
    then the ASCII-safe structural check, then (if a watch-list was
    supplied) a literal-substring match against known real names/projects.
    Returns error strings for `field`; empty means clean. Order matters -
    the email check is tried first so a caller gets the precise reason
    instead of the vaguer ASCII-safe message (an email is already ASCII-
    unsafe today because '@' isn't allowlisted, but that overlap is
    incidental, not the intended signal)."""
    if not val:
        return []
    if contains_email_address(val):
        return [f"field '{field}' contains what looks like an email address (possible real-data leak): {val!r}"]
    if not is_ascii_safe(val):
        return [f"field '{field}' failed the ASCII-safe leak guard (possible real-data leak): {val!r}"]
    hits = contains_watch_string(val, watch)
    if hits:
        return [
            f"field '{field}' matches a known real name/project in the registry watch-list "
            f"{hits!r} (possible real-data leak) - use a placeholder instead"
        ]
    return []


def validate_row(row: dict, watch=None) -> list[str]:
    """Return a list of validation error strings; empty means valid. `watch`
    is an optional iterable of known real names/projects (e.g. from
    check_sensitive_data.load_watch_strings()) to additionally reject as a
    literal substring of any free-text field - omitted by default so
    existing callers/tests keep their current (registry-independent)
    behavior."""
    errors = []
    for field in REQUIRED_FIELDS:
        if not str(row.get(field, "")).strip():
            errors.append(f"required field '{field}' is blank")
    for field in NUMERIC_FIELDS:
        val = row.get(field, "")
        if val is None or str(val).strip() == "":
            continue
        try:
            float(val)
        except (TypeError, ValueError):
            errors.append(f"field '{field}' has non-numeric value {val!r}")
    runtime = row.get("runtime")
    if runtime and runtime not in VALID_RUNTIME:
        errors.append(f"field 'runtime' has invalid value {runtime!r} (allowed: {sorted(VALID_RUNTIME)})")
    json_mode = row.get("json_mode")
    if json_mode and json_mode not in VALID_YES_NO:
        errors.append(f"field 'json_mode' has invalid value {json_mode!r} (allowed: yes/no)")
    truncated = row.get("truncated")
    if truncated and truncated not in VALID_YES_NO:
        errors.append(f"field 'truncated' has invalid value {truncated!r} (allowed: yes/no)")
    status = row.get("status")
    if status and status not in VALID_STATUS:
        errors.append(f"field 'status' has invalid value {status!r} (allowed: ok/error)")
    for field in ("command_args_redacted", "notes", "notes_file"):
        errors.extend(_check_free_text_field(field, str(row.get(field, "")), watch))
    return errors


def append_row(row: dict) -> None:
    """Append exactly one validated row to operator-runs.csv, creating the
    file with the canonical header if it does not exist yet. Never rewrites
    an existing row - this is a pure append. Raises ValueError on any
    validation failure (required/numeric/enum/leak-guard), writing nothing."""
    errors = validate_row(row)
    if errors:
        raise ValueError("Row failed validation:\n  " + "\n  ".join(errors))
    _append_csv_row(CSV_PATH, CSV_HEADER, "run_id", row, read_rows)


def diff_guard_new_row_only(run_id: str, ref: str = "HEAD", repo_root: Path | None = None) -> tuple[bool, list[str]]:
    """diff-guard for operator-runs.csv - see _diff_guard_new_row_only."""
    return _diff_guard_new_row_only(CSV_PATH, "run_id", run_id, read_rows, ref=ref, repo_root=repo_root)


# ---------------------------------------------------------------------------
# agent-sessions.csv (session-level token telemetry)
# ---------------------------------------------------------------------------

def read_agent_session_rows() -> tuple[list[str], list[dict]]:
    """Read agent-sessions.csv, returning (header, rows). Creates no file as
    a side effect - callers that need the file to exist should check
    AGENT_SESSION_CSV_PATH."""
    return _read_csv_rows(AGENT_SESSION_CSV_PATH, AGENT_SESSION_CSV_HEADER)


def validate_agent_session_row(row: dict, watch=None) -> list[str]:
    """Return a list of validation error strings; empty means valid. `watch`
    is an optional iterable of known real names/projects (e.g. from
    check_sensitive_data.load_watch_strings()) to additionally reject as a
    literal substring of `objective`/`notes` - omitted by default so
    existing callers/tests keep their current (registry-independent)
    behavior. See record_agent_session.py's --check-registry flag, the
    only caller that currently supplies one."""
    errors = []
    for field in AGENT_SESSION_REQUIRED_FIELDS:
        if not str(row.get(field, "")).strip():
            errors.append(f"required field '{field}' is blank")
    for field in AGENT_SESSION_NUMERIC_FIELDS:
        val = row.get(field, "")
        if val is None or str(val).strip() == "":
            continue
        try:
            float(val)
        except (TypeError, ValueError):
            errors.append(f"field '{field}' has non-numeric value {val!r}")
    extraction_method = row.get("extraction_method")
    if extraction_method and extraction_method not in VALID_EXTRACTION_METHOD:
        errors.append(
            f"field 'extraction_method' has invalid value {extraction_method!r} "
            f"(allowed: {sorted(VALID_EXTRACTION_METHOD)})"
        )
    confidence = row.get("confidence")
    if confidence and confidence not in VALID_CONFIDENCE:
        errors.append(
            f"field 'confidence' has invalid value {confidence!r} (allowed: {sorted(VALID_CONFIDENCE)})"
        )
    runtime = row.get("runtime")
    allowed_runtimes = AGENT_SESSION_VALID_RUNTIME | AGENT_SESSION_LEGACY_RUNTIME
    if runtime and runtime not in allowed_runtimes:
        errors.append(
            f"field 'runtime' has invalid value {runtime!r} "
            f"(allowed: {sorted(allowed_runtimes)})"
        )
    for field in ("objective", "notes"):
        errors.extend(_check_free_text_field(field, str(row.get(field, "")), watch))
    return errors


def append_agent_session_row(row: dict) -> None:
    """Append exactly one validated row to agent-sessions.csv, creating the
    file with the canonical header if it does not exist yet. Never rewrites
    an existing row, and never touches operator-runs.csv. Raises ValueError
    on any validation failure, writing nothing."""
    errors = validate_agent_session_row(row)
    if errors:
        raise ValueError("Row failed validation:\n  " + "\n  ".join(errors))
    _append_csv_row(AGENT_SESSION_CSV_PATH, AGENT_SESSION_CSV_HEADER, "session_run_id", row,
                    read_agent_session_rows)


def diff_guard_agent_session_new_row_only(session_run_id: str, ref: str = "HEAD",
                                          repo_root: Path | None = None) -> tuple[bool, list[str]]:
    """diff-guard for agent-sessions.csv - see _diff_guard_new_row_only."""
    return _diff_guard_new_row_only(AGENT_SESSION_CSV_PATH, "session_run_id", session_run_id,
                                    read_agent_session_rows, ref=ref, repo_root=repo_root)


# ---------------------------------------------------------------------------
# task-outcomes.csv (derived pass closure facts & workload telemetry)
# ---------------------------------------------------------------------------

TASK_OUTCOME_CSV_PATH = TELEMETRY_ROOT / "task-outcomes.csv"

TASK_OUTCOME_CSV_HEADER = [
    "task_outcome_id",
    "date",
    "task_type",
    "runtime",
    "linked_session_run_id",
    "queue_run_hash",
    "lane",
    "source_type",
    "source_count",
    "source_blob_present",
    "source_chars",
    "source_estimated_tokens",
    "record_apply_updated_count",
    "record_apply_no_change_count",
    "record_apply_not_applicable_count",
    "closure_edges_count",
    "closure_edges_updated_count",
    "closure_edges_no_change_count",
    "closure_edges_gated_count",
    "mirror_export_mode",
    "status",
    "notes",
]

TASK_OUTCOME_REQUIRED_FIELDS = [
    "task_outcome_id", "date", "task_type", "runtime", "status",
]

TASK_OUTCOME_NUMERIC_FIELDS = [
    "source_count", "source_chars", "source_estimated_tokens",
    "record_apply_updated_count", "record_apply_no_change_count",
    "record_apply_not_applicable_count", "closure_edges_count",
    "closure_edges_updated_count", "closure_edges_no_change_count",
    "closure_edges_gated_count",
]

TASK_OUTCOME_VALID_TASK_TYPE = {
    "intake_run", "repo_maintenance", "retro_pass", "admin_pass", "quality_audit", "cleanup_pass",
}
TASK_OUTCOME_VALID_RUNTIME = {"antigravity", "claude", "codex", "cline", "manual"}
TASK_OUTCOME_VALID_LANE = {"m2_project_management", "project_knowledge", "m1_people_management", "workspace", ""}
TASK_OUTCOME_VALID_MIRROR_EXPORT_MODE = {"full", "scoped", "none", ""}
TASK_OUTCOME_VALID_STATUS = {"ok", "error", "gated"}
TASK_OUTCOME_VALID_YES_NO = {"yes", "no"}


def valid_source_types() -> set[str]:
    from pipeline_common import SKILL_INVOCATION_SOURCE_TYPES
    return set(SKILL_INVOCATION_SOURCE_TYPES) | {""}


def read_task_outcome_rows() -> tuple[list[str], list[dict]]:
    """Read task-outcomes.csv, returning (header, rows)."""
    return _read_csv_rows(TASK_OUTCOME_CSV_PATH, TASK_OUTCOME_CSV_HEADER)


def validate_task_outcome_row(row: dict, watch=None) -> list[str]:
    errors = []
    for field in TASK_OUTCOME_REQUIRED_FIELDS:
        if not str(row.get(field, "")).strip():
            errors.append(f"required field '{field}' is blank")

    for field in TASK_OUTCOME_NUMERIC_FIELDS:
        val = row.get(field, "")
        if val is None or str(val).strip() == "":
            continue
        try:
            int(val)
        except (TypeError, ValueError):
            errors.append(f"field '{field}' has non-integer value {val!r}")

    task_type = row.get("task_type")
    if task_type and task_type not in TASK_OUTCOME_VALID_TASK_TYPE:
        errors.append(
            f"field 'task_type' has invalid value {task_type!r} "
            f"(allowed: {sorted(TASK_OUTCOME_VALID_TASK_TYPE)})"
        )

    runtime = row.get("runtime")
    if runtime and runtime not in TASK_OUTCOME_VALID_RUNTIME:
        errors.append(
            f"field 'runtime' has invalid value {runtime!r} "
            f"(allowed: {sorted(TASK_OUTCOME_VALID_RUNTIME)})"
        )

    lane = row.get("lane")
    if lane and lane not in TASK_OUTCOME_VALID_LANE:
        errors.append(
            f"field 'lane' has invalid value {lane!r} "
            f"(allowed: {sorted(TASK_OUTCOME_VALID_LANE)})"
        )

    source_type = row.get("source_type")
    allowed_sources = valid_source_types()
    if source_type and source_type not in allowed_sources:
        errors.append(
            f"field 'source_type' has invalid value {source_type!r} "
            f"(allowed: {sorted(allowed_sources)})"
        )

    blob_present = row.get("source_blob_present")
    if blob_present and blob_present not in TASK_OUTCOME_VALID_YES_NO:
        errors.append(
            f"field 'source_blob_present' has invalid value {blob_present!r} (allowed: yes/no)"
        )

    export_mode = row.get("mirror_export_mode")
    if export_mode and export_mode not in TASK_OUTCOME_VALID_MIRROR_EXPORT_MODE:
        errors.append(
            f"field 'mirror_export_mode' has invalid value {export_mode!r} "
            f"(allowed: {sorted(TASK_OUTCOME_VALID_MIRROR_EXPORT_MODE)})"
        )

    status = row.get("status")
    if status and status not in TASK_OUTCOME_VALID_STATUS:
        errors.append(
            f"field 'status' has invalid value {status!r} "
            f"(allowed: {sorted(TASK_OUTCOME_VALID_STATUS)})"
        )

    # Non-zero workload guard: at least one count field must be > 0
    workload_counts = [row.get(f) for f in TASK_OUTCOME_NUMERIC_FIELDS]
    has_non_zero = False
    for c in workload_counts:
        if c is not None and str(c).strip().isdigit() and int(c) > 0:
            has_non_zero = True
            break
    if not has_non_zero:
        errors.append(
            "row failed non-zero workload guard: at least one count field "
            "(source_count, source_chars, record_apply_*, closure_edges_*) must be > 0"
        )

    for field in ("notes",):
        errors.extend(_check_free_text_field(field, str(row.get(field, "")), watch))

    return errors


def append_task_outcome_row(row: dict) -> None:
    """Append exactly one validated row to task-outcomes.csv, creating the file
    with the canonical header if it does not exist yet. Never rewrites an
    existing row. Raises ValueError on any validation failure, writing nothing."""
    errors = validate_task_outcome_row(row)
    if errors:
        raise ValueError("Row failed validation:\n  " + "\n  ".join(errors))
    _append_csv_row(TASK_OUTCOME_CSV_PATH, TASK_OUTCOME_CSV_HEADER, "task_outcome_id", row,
                    read_task_outcome_rows)


def diff_guard_task_outcome_new_row_only(task_outcome_id: str, ref: str = "HEAD",
                                         repo_root: Path | None = None) -> tuple[bool, list[str]]:
    """diff-guard for task-outcomes.csv - see _diff_guard_new_row_only."""
    return _diff_guard_new_row_only(TASK_OUTCOME_CSV_PATH, "task_outcome_id", task_outcome_id,
                                    read_task_outcome_rows, ref=ref, repo_root=repo_root)
