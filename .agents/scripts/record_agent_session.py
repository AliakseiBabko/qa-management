"""Phase 11 operator telemetry: record one agent-session token-usage row.

Companion to operator-runs.csv's command-footprint rows (measured by
measure_operator_outputs.py / finalize_operator_run.py): this script
answers a different question - "how many model tokens did this agent
RUNTIME SESSION actually consume?" - and writes to a separate CSV,
.agents/telemetry/agent-sessions.csv, never operator-runs.csv.

Why a separate CSV instead of backfilling operator-runs.csv
-------------------------------------------------------------
extract_agent_telemetry.py returns a SESSION-WIDE token total. Several
operator-runs.csv rows commonly come from one long agent conversation/
session (one command measured, several more measured later in the same
chat) - there is no way to honestly slice a session's cumulative usage
back into "how much did just this one command cost". Writing the same
session total into multiple operator-runs.csv rows would duplicate and
overstate token use. So: operator-runs.csv rows keep their `actual_*`
fields blank unless a row genuinely was measured in its own dedicated
session; agent-sessions.csv instead records the session as its own unit,
with `linked_operator_run_ids` naming which operator-runs.csv rows (if
any) happened during it - a many-command-rows -> one-session-row
relationship, not a join key added to operator-runs.csv itself.

Usage
-----
  python .agents/scripts/record_agent_session.py \\
      --runtime claude --session-id <session-id> \\
      --model-label claude-sonnet-5 \\
      --objective "project knowledge source processing" \\
      --linked-operator-run-ids <id1>,<id2> \\
      --append-csv

  # Manual entry when automatic extraction isn't available for this runtime/session
  python .agents/scripts/record_agent_session.py \\
      --runtime antigravity --session-id <session-id> --manual \\
      --actual-input-tokens 12000 --actual-output-tokens 3400 \\
      --confidence manual --objective "..." --append-csv

  # Additionally reject a known real name/project pulled live from Drive
  python .agents/scripts/record_agent_session.py \\
      --runtime claude --session-id <session-id> --objective "..." \\
      --check-registry --append-csv

  # Task-scoped (windowed) row: derive the task's own [since, until] from
  # the queue run's Started/Completed timestamps and sum only that slice
  # of the session's usage - claude only today (see extract_agent_
  # telemetry.py's own windowing rollout notes). Produces an exact
  # per-task row instead of a whole-session total, for linking into
  # task-outcomes.csv's linked_session_run_id.
  python .agents/scripts/record_agent_session.py \\
      --runtime claude --session-id <session-id> --from-run <run-id> \\
      --objective "..." --append-csv

  # Explicit --since/--until always win over --from-run's derived window,
  # per field (e.g. supply --until yourself if Completed isn't set yet).
  python .agents/scripts/record_agent_session.py \\
      --runtime claude --session-id <session-id> \\
      --since 2026-07-23T09:00:00Z --until 2026-07-23T09:20:00Z \\
      --objective "..." --append-csv

  # Dry run - extract/compute and print, write nothing
  python .agents/scripts/record_agent_session.py \\
      --runtime claude --session-id <session-id> --objective "..." --dry-run

Confidence defaults (override with --confidence)
--------------------------------------------------
  claude_log, codex_log, cline_history, antigravity_cli  -> high
  antigravity_db (heuristic DB fallback)                 -> medium
  manual entry                                            -> manual

Runtime values in agent-sessions.csv
--------------------------------------
Accepted CLI aliases are normalized before writing. For example,
`--runtime claude-code` uses the Claude adapter but persists `runtime=claude`
and defaults the row id to `session-claude-...`, keeping the CSV grouped by
canonical runtime. Historical rows written before this rule may still contain
`claude-code` and remain valid for reading/validation.

Manual rows
--------------
`--manual` must include at least one `--actual-*-tokens` value. A manual row
with no token counts does not answer the session-telemetry question and is
therefore refused before writing.

Invalid --linked-operator-run-ids
------------------------------------
A listed id that isn't actually in operator-runs.csv is a WARNING, not a
failure - linking is informational cross-referencing, not a structural
guarantee, and a typo shouldn't block recording real session telemetry.
The warning is printed to stderr and the row is still appended.

Leak guard on --objective/--notes
------------------------------------
Every row's `objective`/`notes` fields are always checked for an email
address and for non-ASCII content (operator_telemetry_common.py's
ASCII-safe guard) before anything is written - both hard failures, no
flag needed. Pass --check-registry to additionally reject a literal
real name/project pulled live from `_people_registry`/`_project_registry`
(the same registry check_sensitive_data.py runs before a commit) - this
requires Drive access, so it is opt-in rather than always-on: this
script otherwise has no Google API dependency, and a missing/expired
credential shouldn't block recording routine telemetry. If the registry
can't be loaded even with the flag set, that degrades to a warning
(structural checks alone still apply) rather than a hard failure.

--from-run: deriving a task's time window from the queue
------------------------------------------------------------
--from-run <run-id> reads that queue run's Started/Completed cells
(qa_manage.py's _intake_queue sheet - naive local time, "%Y-%m-%d %H:%M",
minute precision, no finer) and converts each to a UTC ISO8601 string,
then passes them as --since/--until to extract_agent_telemetry.py's
Claude adapter instead of extracting the whole session. This is what
makes a task-outcomes.csv row's linked_session_run_id point at that
task's own usage rather than the entire multi-task session's total.
Best-effort and degrades gracefully, never blocking the recording:
  - if the queue is unreachable or the run isn't found, both bounds stay
    open (falls back to a whole-session extraction) and a warning prints;
  - if only Completed is blank (run still in progress), only `until`
    stays open;
  - an explicit --since/--until always overrides the derived value for
    that same bound, checked independently per field.
This only works for --runtime claude today - passing --from-run for any
other runtime raises the same "not yet implemented" error --since/--until
would (see extract_agent_telemetry.py's rollout notes).
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, datetime, timezone
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

import extract_agent_telemetry as extractor  # noqa: E402
from finalize_operator_run import compute_total_tokens, estimate_cost  # noqa: E402
from operator_telemetry_common import (  # noqa: E402
    AGENT_SESSION_CSV_HEADER,
    append_agent_session_row,
    diff_guard_agent_session_new_row_only,
    read_rows,
    validate_agent_session_row,
)

DEFAULT_CONFIDENCE_BY_METHOD = {
    "claude_log": "high",
    "codex_log": "high",
    "cline_history": "high",
    "antigravity_cli": "high",
    "antigravity_db": "medium",
    "manual": "manual",
}

DEFAULT_MODEL_LABELS_BY_RUNTIME = {
    "antigravity": "gemini-3.6-flash-medium",
    "claude": "claude-sonnet-5-medium",
    "claude-code": "claude-sonnet-5-medium",
    "codex": "codex-5.5-medium",
}

ACTUAL_TOKEN_FIELDS = (
    "actual_input_tokens", "actual_cache_creation_tokens", "actual_cache_read_tokens",
    "actual_output_tokens", "actual_reasoning_tokens",
)

RUNTIME_ALIASES = {
    "claude-code": "claude",
    "claudecode": "claude",
}


def canonical_runtime(runtime: str) -> str:
    """Normalize accepted CLI aliases to the single persisted runtime key
    used by agent-sessions.csv."""
    key = runtime.lower().replace(" ", "-")
    return RUNTIME_ALIASES.get(key, key)


def _default_session_run_id(runtime: str, windowed: bool = False) -> str:
    import uuid
    marker = "-task" if windowed else ""
    return f"session-{runtime}{marker}-{date.today().isoformat()}-{uuid.uuid4().hex[:8]}"


def _queue_ts_to_iso_utc(ts: str | None) -> str | None:
    """Convert a qa_manage.py `_intake_queue` timestamp ("%Y-%m-%d %H:%M",
    naive local wall-clock time, minute precision - see qa_manage.py's
    now()/parse_ts()) to the UTC ISO8601 string extract_agent_telemetry.py's
    --since/--until expect. Returns None if `ts` is blank or unparseable -
    callers treat that as "this bound is unknown," not an error. Minute
    precision only, because the source data has none finer - seconds are
    always :00, not a fabricated claim of higher precision."""
    if not ts or not ts.strip():
        return None
    try:
        naive_local = datetime.strptime(ts.strip(), "%Y-%m-%d %H:%M")
    except ValueError:
        return None
    # A naive datetime's .astimezone() is documented to assume it already
    # represents local wall-clock time and attach the system's local tzinfo
    # - exactly the assumption qa_manage.py's now()/parse_ts() make.
    aware_local = naive_local.astimezone()
    aware_utc = aware_local.astimezone(timezone.utc)
    return aware_utc.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def derive_task_window_from_run(run_id: str) -> tuple[str | None, str | None, list[str]]:
    """Best-effort derivation of one task's own [since, until] window from
    its queue run's Started/Completed timestamps. Returns (since, until,
    warnings) - never raises. Any failure (Drive/queue unreachable, run not
    found, a timestamp blank or unparseable) degrades to leaving that bound
    (or both) as None plus an explanatory warning, so --from-run falls back
    toward a whole-session extraction rather than blocking the recording."""
    try:
        from pipeline_common import get_services
        from qa_manage import find_queue, read_queue

        services = get_services()
        sheet = find_queue(services)
        if not sheet:
            return None, None, [
                f"Could not derive a task window for run {run_id!r}: intake queue sheet not found."
            ]
        rows = read_queue(services, sheet)
        row = next((r for r in rows if r.get("Run ID") == run_id), None)
        if row is None:
            return None, None, [
                f"Could not derive a task window for run {run_id!r}: no matching queue row found."
            ]

        since = _queue_ts_to_iso_utc(row.get("Started", ""))
        until = _queue_ts_to_iso_utc(row.get("Completed", ""))
        warnings: list[str] = []
        if since is None:
            warnings.append(
                f"Run {run_id!r} has no parseable Started timestamp - task window has no lower bound."
            )
        if until is None:
            warnings.append(
                f"Run {run_id!r} has no parseable Completed timestamp (run may still be in progress) "
                "- task window has no upper bound."
            )
        return since, until, warnings
    except Exception as e:  # noqa: BLE001 - deliberately broad, see docstring
        return None, None, [
            f"Could not derive a task window for run {run_id!r} ({e}) - falling back toward a "
            "whole-session extraction."
        ]


def _compute_elapsed_min(started_at: str, ended_at: str) -> str:
    if not started_at or not ended_at:
        return ""
    try:
        start = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
        end = datetime.fromisoformat(ended_at.replace("Z", "+00:00"))
    except ValueError:
        return ""
    return f"{(end - start).total_seconds() / 60:.2f}"


def load_registry_watchlist() -> tuple[set[str], list[str]]:
    """Best-effort load of the known real-name/project watch-list from
    Drive, reusing check_sensitive_data.py's own loader (see that module's
    load_watch_strings()) rather than re-fetching the registries here.
    Returns (watch, warnings) - never raises. Any failure (missing/expired
    credentials, no network, Drive API error) degrades to an empty
    watch-list plus a warning string, since this script's core job -
    recording telemetry - must not hard-depend on Drive being reachable.
    Only called when --check-registry is passed; see the module docstring."""
    try:
        import check_sensitive_data
        from pipeline_common import get_services

        services = get_services()
        watch = check_sensitive_data.load_watch_strings(services)
        return watch, []
    except Exception as e:  # noqa: BLE001 - deliberately broad, see docstring
        return set(), [
            f"Could not load the real-name/project registry watch-list ({e}) - "
            "proceeding with structural (email/ASCII-safe) checks only."
        ]


def _warn_on_unknown_linked_run_ids(linked_ids: list[str]) -> list[str]:
    """Cross-references linked_operator_run_ids against operator-runs.csv's
    actual run_ids. Returns warning strings (never raises) - see the module
    docstring for why an unknown id is a warning, not a failure."""
    if not linked_ids:
        return []
    _, rows = read_rows()
    known = {r.get("run_id") for r in rows}
    return [f"linked_operator_run_ids entry {rid!r} was not found in operator-runs.csv"
           for rid in linked_ids if rid not in known]


def build_row(args) -> tuple[dict, list[str]]:
    """Returns (row, warnings). Raises RuntimeError/ValueError on hard
    failures (extraction failure with no manual fallback, etc.)."""
    warnings: list[str] = []
    telemetry: dict = {}
    since: str | None = None
    until: str | None = None

    if args.manual:
        if not any(getattr(args, field, None) is not None for field in ACTUAL_TOKEN_FIELDS):
            raise ValueError(
                "--manual requires at least one --actual-*-tokens value; "
                "otherwise agent-sessions.csv would record a session with no token data."
            )
        for field in ACTUAL_TOKEN_FIELDS:
            val = getattr(args, field, None)
            if val is not None:
                telemetry[field] = val
        extraction_method = "manual"
    else:
        since, until = args.since, args.until
        if args.from_run and (since is None or until is None):
            derived_since, derived_until, window_warnings = derive_task_window_from_run(args.from_run)
            warnings.extend(window_warnings)
            since = since if since is not None else derived_since
            until = until if until is not None else derived_until

        try:
            telemetry = extractor.extract(args.runtime, args.session_id, since=since, until=until)
        except (FileNotFoundError, ValueError, RuntimeError) as e:
            raise RuntimeError(
                f"Automatic extraction failed for runtime={args.runtime!r} "
                f"session_id={args.session_id!r}: {e}\n"
                "Retry with --manual and explicit --actual-input-tokens/--actual-output-tokens/"
                "--actual-cache-creation-tokens/--actual-cache-read-tokens/--actual-reasoning-tokens "
                "(read from the runtime's own usage UI/CLI) instead."
            ) from e
        extraction_method = telemetry.get("extraction_method", "")
        # CLI overrides win over whatever the adapter reported, same
        # precedent as finalize_operator_run.py's --telemetry-json merge.
        for field in ACTUAL_TOKEN_FIELDS:
            val = getattr(args, field, None)
            if val is not None:
                telemetry[field] = val

    row = {k: "" for k in AGENT_SESSION_CSV_HEADER}
    row_runtime = canonical_runtime(args.runtime)
    row["session_run_id"] = args.session_run_id or _default_session_run_id(
        row_runtime, windowed=(since is not None or until is not None)
    )
    row["date"] = args.date or date.today().isoformat()
    row["runtime"] = row_runtime
    model_lbl = args.model_label or telemetry.get("model_label", "")
    if not model_lbl and extraction_method != "manual":
        model_lbl = DEFAULT_MODEL_LABELS_BY_RUNTIME.get(row_runtime, "")
    row["model_label"] = model_lbl
    row["session_id"] = args.session_id
    row["linked_operator_run_ids"] = ",".join(args.linked_operator_run_ids or [])
    row["objective"] = args.objective
    row["started_at"] = args.started_at or telemetry.get("session_started_at", "")
    row["ended_at"] = args.ended_at or telemetry.get("session_ended_at", "")
    row["elapsed_min"] = args.elapsed_min or _compute_elapsed_min(row["started_at"], row["ended_at"])
    for field in ACTUAL_TOKEN_FIELDS:
        row[field] = telemetry.get(field, "")
    row["extraction_method"] = args.extraction_method or extraction_method
    row["confidence"] = args.confidence or DEFAULT_CONFIDENCE_BY_METHOD.get(row["extraction_method"], "")
    row["notes"] = args.notes or ""

    row["total_tokens"] = compute_total_tokens(row)
    reported_cost = telemetry.get("estimated_cost_usd")
    if args.estimated_cost_usd is not None:
        row["estimated_cost_usd"] = args.estimated_cost_usd
    elif reported_cost:
        row["estimated_cost_usd"] = reported_cost
    elif row["total_tokens"]:
        cost_inputs = {k: (int(row[k]) if str(row.get(k, "")).strip() not in ("", "n/a") else 0)
                       for k in ACTUAL_TOKEN_FIELDS}
        cost = estimate_cost(row["model_label"], cost_inputs)
        if cost:
            row["estimated_cost_usd"] = cost

    warnings.extend(_warn_on_unknown_linked_run_ids(args.linked_operator_run_ids or []))
    return row, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--runtime", required=True, choices=sorted(extractor.ADAPTERS) + ["manual"])
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--session-run-id", default=None, help="Defaults to 'session-<runtime>-<date>-<short-uuid>'.")
    parser.add_argument("--date", default=None)
    parser.add_argument("--model-label", default=None)
    parser.add_argument("--objective", required=True, help="Short, redacted description of what this session did.")
    parser.add_argument("--linked-operator-run-ids", default=None,
                        help="Comma-separated operator-runs.csv run_ids measured during this session.")
    parser.add_argument("--started-at", default=None)
    parser.add_argument("--ended-at", default=None)
    parser.add_argument("--elapsed-min", default=None)
    parser.add_argument("--manual", action="store_true",
                        help="Skip automatic extraction; build the row entirely from --actual-* flags.")
    parser.add_argument("--since", default=None,
                        help="ISO8601 timestamp (inclusive). Window the extraction to usage at or "
                             "after this time. Claude only today. Overrides --from-run's derived value.")
    parser.add_argument("--until", default=None,
                        help="ISO8601 timestamp (inclusive). Window the extraction to usage at or "
                             "before this time. Claude only today. Overrides --from-run's derived value.")
    parser.add_argument("--from-run", default=None,
                        help="Derive --since/--until from this queue run_id's Started/Completed "
                             "timestamps (best-effort - see module docstring). Ignored for --manual rows.")
    for field in ACTUAL_TOKEN_FIELDS:
        parser.add_argument("--" + field.replace("_", "-"), dest=field, type=int, default=None)
    parser.add_argument("--estimated-cost-usd", dest="estimated_cost_usd", default=None,
                        help="Directly-reported cost (e.g. from the runtime's own usage UI). "
                             "If omitted, computed from model_label's pricing-table entry when possible.")
    parser.add_argument("--extraction-method", default=None,
                        help="Override the auto-detected extraction_method (rarely needed).")
    parser.add_argument("--confidence", choices=["high", "medium", "low", "manual"], default=None,
                        help="Override the extraction_method-based confidence default.")
    parser.add_argument("--notes", default=None)
    parser.add_argument("--check-registry", action="store_true",
                        help="Additionally reject a known real name/project (from _people_registry/"
                             "_project_registry) in --objective/--notes. Requires Drive access; degrades "
                             "to a warning (not a failure) if the registry can't be loaded.")
    parser.add_argument("--append-csv", action="store_true", help="Append the row to agent-sessions.csv.")
    parser.add_argument("--dry-run", action="store_true", help="Print the row; do not write the CSV.")
    args = parser.parse_args()

    args.linked_operator_run_ids = (
        [x.strip() for x in args.linked_operator_run_ids.split(",") if x.strip()]
        if args.linked_operator_run_ids else []
    )

    if not args.append_csv and not args.dry_run:
        parser.error("one of --append-csv or --dry-run is required")

    try:
        row, warnings = build_row(args)
    except (RuntimeError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    for w in warnings:
        print(f"Warning: {w}", file=sys.stderr)

    watch: set[str] = set()
    if args.check_registry:
        watch, registry_warnings = load_registry_watchlist()
        for w in registry_warnings:
            print(f"Warning: {w}", file=sys.stderr)

    errors = validate_agent_session_row(row, watch=watch)
    if errors:
        print("Error: row failed validation:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    if args.dry_run:
        import json
        print(json.dumps(row, ensure_ascii=True, indent=2))
        print("[dry-run] nothing written.")
        return 0

    append_agent_session_row(row)
    ok, violations = diff_guard_agent_session_new_row_only(row["session_run_id"])
    if not ok:
        print("Error: diff guard failed after append - see violations below.", file=sys.stderr)
        for v in violations:
            print(f" - {v}", file=sys.stderr)
        return 1

    print(f"Appended row for session_run_id={row['session_run_id']} to "
         ".agents/telemetry/agent-sessions.csv")
    print("Diff guard OK: only the new row was added. operator-runs.csv was not touched.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
