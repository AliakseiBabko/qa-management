"""Adapter: qa-management -> ai-telemetry (central) dual-write helper.

Phase 14 of ai-telemetry's own rollout (see that repo's README
"Roadmap"). qa-management's own local `.agents/telemetry/*.csv`
recording is UNCHANGED by this module - it is not read, not gated, not
replaced. This adapter only ever ADDS a second, best-effort write into
the shared ai-telemetry database, called explicitly by
`record_agent_session.py`/`record_task_outcome.py` after their own local
CSV append already succeeded (see those scripts' own `--dual-write-central`
flag).

Fail-soft by construction: every public function here returns a result
dict (`{"ok": True, ...}` or `{"ok": False, "reason": <short, generic
string>}`) and never raises - a missing/broken ai-telemetry checkout, a
missing database, a subprocess timeout, or any other central-write
problem is reported back to the caller as an `ok=False` result, never as
an exception a legacy closeout script would need to catch. Callers are
expected to print a warning and continue their own (fully unaffected)
local write either way - see the module docstring's Safety framing in
`closeout_telemetry.py` for the same "warn, never break the legacy path"
principle applied one level up.

This module is not a CLI (no `argparse`, no `__main__` block) - it is a
small set of functions the two record scripts import directly, so they
get typed return values (`ok`/`id`/`outcome`) instead of having to
re-parse another subprocess's stdout. It calls
`ai-telemetry\\scripts\\record_*.py` via subprocess with `--project-id
qa-management --source-system native --json` always injected - the same
`project_id`/`source_system` convention every other project's own
generated wrapper uses (see ai-telemetry's `scripts/generate_project_wrapper.py`
and its README "Recording native telemetry"). qa-management gets its own
hand-written adapter here rather than that generated wrapper verbatim
because these two callers need real return values, not just a printed
CLI result.

Central `tasks.linked_session_row_id` linking: `record_task()` accepts
`linked_session_source_ref` (qa-management's own local `session_run_id` -
the SAME value already passed as `record_session()`'s own `source_ref`
earlier) and, if given, calls `resolve_session_id()` to look up the
already-dual-written central `session_row_id` for that same
project_id='qa-management'/source_system='native'/source_ref, via a
targeted, read-only query against ai-telemetry's own database (reusing
that repo's own `report.py.connect_readonly()`/`db.py.DEFAULT_DB_PATH`
rather than opening the file directly here). If a match is found, it's
passed through as `--linked-session-row-id`; if not (session row not
dual-written yet, database unreachable, any other problem), the task is
still recorded, just without that link - `resolve_session_id()` fails
soft and returns `None`, never raises, and never prints the session id
or source_ref it looked up.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

DEFAULT_AI_TELEMETRY_PATH = Path(r"C:\Users\User\Documents\ai-telemetry")
PROJECT_ID = "qa-management"
SOURCE_SYSTEM = "native"
SUBPROCESS_TIMEOUT_SEC = 30


def _run_record_script(
    script_name: str, args: list[str], *, ai_telemetry_path: Path = DEFAULT_AI_TELEMETRY_PATH
) -> dict[str, Any]:
    """Runs one ai-telemetry `record_*.py` script with `--project-id`/
    `--source-system`/`--json` already injected. Never raises - see
    module docstring. `reason` (on failure) is always a short, generic,
    hardcoded-shape string - never raw subprocess stdout/stderr, which
    could in principle echo back caller-supplied text."""
    script_path = ai_telemetry_path / "scripts" / script_name
    if not script_path.exists():
        return {"ok": False, "reason": f"{script_name} not found under {ai_telemetry_path}"}
    argv = [
        sys.executable, str(script_path),
        "--project-id", PROJECT_ID, "--source-system", SOURCE_SYSTEM, "--json",
        *args,
    ]
    try:
        proc = subprocess.run(
            argv, capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=SUBPROCESS_TIMEOUT_SEC,
        )
    except Exception as exc:  # noqa: BLE001 - fail-soft by design, see module docstring
        return {"ok": False, "reason": f"{type(exc).__name__} running {script_name}"}
    if proc.returncode != 0:
        return {"ok": False, "reason": f"{script_name} exited {proc.returncode}"}
    try:
        result = json.loads(proc.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return {"ok": False, "reason": f"{script_name} produced unparseable output"}
    if not isinstance(result, dict):
        return {"ok": False, "reason": f"{script_name} produced a non-object JSON result"}
    result["ok"] = True
    return result


def _add_optional_flags(args: list[str], fields: dict[str, Any]) -> list[str]:
    """Appends `--<key-with-dashes> <value>` for every non-empty value in
    `fields` - shared by record_session/record_task below so each one's
    own optional-field list stays a plain dict literal at the call site."""
    for key, value in fields.items():
        if value is None or value == "":
            continue
        flag = "--" + key.replace("_", "-")
        args += [flag, str(value)]
    return args


def resolve_session_id(
    source_ref: str, *, ai_telemetry_path: Path = DEFAULT_AI_TELEMETRY_PATH
) -> str | None:
    """Best-effort lookup of the central `sessions.session_row_id` already
    dual-written for project_id='qa-management'/source_system='native'/
    this `source_ref`. Returns None on ANY problem - missing ai-telemetry
    checkout, missing database, no matching row, query error - never
    raises, and never prints anything (this function has no side
    effects at all; the caller decides whether/how to warn). Prefers
    ai-telemetry's own read helpers (`report.connect_readonly` +
    `db.DEFAULT_DB_PATH`) over opening the sqlite file directly, so this
    stays a genuinely read-only connection (an accidental write would
    raise, not silently succeed) and stays in sync with wherever
    ai-telemetry itself considers the database to live."""
    try:
        scripts_dir = ai_telemetry_path / "scripts"
        if str(scripts_dir) not in sys.path:
            sys.path.insert(0, str(scripts_dir))
        import db as ai_db  # type: ignore
        import report as ai_report  # type: ignore

        conn = ai_report.connect_readonly(ai_db.DEFAULT_DB_PATH)
        try:
            row = conn.execute(
                "SELECT session_row_id FROM sessions WHERE project_id = ? AND source_system = ? AND source_ref = ?",
                (PROJECT_ID, SOURCE_SYSTEM, source_ref),
            ).fetchone()
        finally:
            conn.close()
        return row["session_row_id"] if row else None
    except Exception:  # noqa: BLE001 - fail-soft by design, see docstring
        return None


def record_session(
    *, source_ref: str, runtime_id: str, session_id: str, date: str, **optional_fields: Any
) -> dict[str, Any]:
    """Dual-write one `sessions` row. `source_ref` should be
    qa-management's own local `session_run_id` (stable within
    project_id='qa-management', per ai-telemetry's own idempotency
    contract - rerunning with the same value is a safe no-op, not a
    duplicate). `optional_fields` may include any of record_session.py's
    own optional flags (objective, model_label, actual_input_tokens,
    total_tokens, estimated_cost_usd, extraction_method, confidence,
    notes, started_at, ended_at, elapsed_min, ...)."""
    args = ["--source-ref", source_ref, "--runtime-id", runtime_id,
            "--session-id", session_id, "--date", date]
    args = _add_optional_flags(args, optional_fields)
    return _run_record_script("record_session.py", args)


def record_task(
    *, source_ref: str, task_type: str, date: str, status_normalized: str = "unknown",
    linked_session_source_ref: str | None = None, **optional_fields: Any,
) -> dict[str, Any]:
    """Dual-write one `tasks` row. `source_ref` should be qa-management's
    own local `task_outcome_id`. `linked_session_source_ref`, if given,
    should be the local `session_run_id` a prior `record_session()` call
    already used as ITS OWN `source_ref` - this function resolves it to
    the matching central `session_row_id` (via `resolve_session_id()`)
    and passes that through as `--linked-session-row-id` when found.
    Never passed by the caller directly - `optional_fields` should NOT
    include `linked_session_row_id` itself. If resolution fails (no
    match, database unreachable, etc.), the row is still recorded, just
    without the link - the result dict's `link_resolved` key reports
    which happened (`True`/`False`/`None` if no `linked_session_source_ref`
    was given at all), so the caller can warn generically without this
    function ever printing anything itself.

    `optional_fields` may include any of record_task.py's own other
    optional flags (runtime_id, status_raw, workload_json, notes, ...)."""
    args = ["--source-ref", source_ref, "--task-type", task_type, "--date", date,
            "--status-normalized", status_normalized]
    link_resolved: bool | None = None
    if linked_session_source_ref:
        resolved_id = resolve_session_id(linked_session_source_ref)
        link_resolved = resolved_id is not None
        if resolved_id:
            args += ["--linked-session-row-id", resolved_id]
    args = _add_optional_flags(args, optional_fields)
    result = _run_record_script("record_task.py", args)
    result["link_resolved"] = link_resolved
    return result
