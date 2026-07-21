"""Shared schema/constants for the Phase 11 operator-telemetry scripts
(measure_operator_outputs.py, finalize_operator_run.py, check_operator_csv.py,
extract_agent_telemetry.py).

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
"""

from __future__ import annotations

import csv
import re
import subprocess
from pathlib import Path

TELEMETRY_ROOT = Path(__file__).resolve().parent.parent / "telemetry"
CSV_PATH = TELEMETRY_ROOT / "operator-runs.csv"
TEMPLATE_PATH = TELEMETRY_ROOT / "templates" / "operator-run-note.md"

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


def redact_argv(argv: list[str], target_placeholder: str = "<target>") -> str:
    """Render an argv list as a redacted, space-joined label - substituting
    any resolved target value back to a generic placeholder token so the
    live value is never persisted. Callers pass the already-redacted argv
    (with {target} still literal, or already replaced) - this just joins and
    normalizes for storage."""
    return " ".join(argv)


def read_rows() -> tuple[list[str], list[dict]]:
    """Read the CSV, returning (header, rows). Creates no file as a side
    effect - callers that need the file to exist should check CSV_PATH."""
    if not CSV_PATH.exists():
        return list(CSV_HEADER), []
    with open(CSV_PATH, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        header = list(reader.fieldnames or CSV_HEADER)
        rows = list(reader)
    return header, rows


def validate_row(row: dict) -> list[str]:
    """Return a list of validation error strings; empty means valid."""
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
        val = str(row.get(field, ""))
        if val and not is_ascii_safe(val):
            errors.append(
                f"field '{field}' failed the ASCII-safe leak guard (possible real-data leak): {val!r}"
            )
    return errors


def append_row(row: dict) -> None:
    """Append exactly one validated row to operator-runs.csv, creating the
    file with the canonical header if it does not exist yet. Never rewrites
    an existing row - this is a pure append. Raises ValueError on any
    validation failure (required/numeric/enum/leak-guard), writing nothing."""
    errors = validate_row(row)
    if errors:
        raise ValueError("Row failed validation:\n  " + "\n  ".join(errors))

    header, existing_rows = read_rows()
    if header != CSV_HEADER:
        raise ValueError(
            f"CSV header does not match canonical schema.\n  expected: {CSV_HEADER}\n  found:    {header}"
        )
    run_id = row.get("run_id")
    if any(r.get("run_id") == run_id for r in existing_rows):
        raise ValueError(f"run_id '{run_id}' already exists in the CSV - refusing to duplicate.")

    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    write_header = not CSV_PATH.exists()
    with open(CSV_PATH, "a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADER)
        if write_header:
            writer.writeheader()
        writer.writerow({k: row.get(k, "") for k in CSV_HEADER})


def diff_guard_new_row_only(run_id: str, ref: str = "HEAD", repo_root: Path | None = None) -> tuple[bool, list[str]]:
    """Compare the working-tree CSV against `ref` (default HEAD) and assert
    that the only difference is the addition of `run_id`'s row. Any other
    added/removed/modified row, or a header change, is a violation - this is
    the diff-guard pattern from the erp-web-tests benchmark skill's
    check_csv.py, adapted for a pure-append (no in-place row update) model.
    Returns (ok, violations)."""
    root = repo_root or CSV_PATH.parent.parent.parent
    try:
        rel = CSV_PATH.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        rel = CSV_PATH.name

    committed = subprocess.run(
        ["git", "-C", str(root), "show", f"{ref}:{rel}"],
        capture_output=True, text=True, encoding="utf-8",
    )
    if committed.returncode != 0:
        return True, []  # no baseline (new file) - nothing to guard against

    import io
    base_reader = csv.DictReader(io.StringIO(committed.stdout))
    base_header = list(base_reader.fieldnames or [])
    base_rows = {r.get("run_id"): r for r in base_reader}

    work_header, work_rows_list = read_rows()
    work_rows = {r.get("run_id"): r for r in work_rows_list}

    violations = []
    if base_header != work_header:
        violations.append(f"Header changed.\n    {ref}: {base_header}\n    work: {work_header}")

    for rid in base_rows:
        if rid not in work_rows:
            violations.append(f"Row removed since {ref}: '{rid}'.")
        elif base_rows[rid] != work_rows[rid]:
            violations.append(f"Unrelated row '{rid}' was modified since {ref}.")

    for rid in work_rows:
        if rid not in base_rows and rid != run_id:
            violations.append(f"Row added that is not the target: '{rid}'.")

    return (len(violations) == 0), violations
