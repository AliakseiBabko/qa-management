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

  # Dry run - extract/compute and print, write nothing
  python .agents/scripts/record_agent_session.py \\
      --runtime claude --session-id <session-id> --objective "..." --dry-run

Confidence defaults (override with --confidence)
--------------------------------------------------
  claude_log, codex_log, cline_history, antigravity_cli  -> high
  antigravity_db (heuristic DB fallback)                 -> medium
  manual entry                                            -> manual

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
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, datetime
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

ACTUAL_TOKEN_FIELDS = (
    "actual_input_tokens", "actual_cache_creation_tokens", "actual_cache_read_tokens",
    "actual_output_tokens", "actual_reasoning_tokens",
)


def _default_session_run_id(runtime: str) -> str:
    import uuid
    return f"session-{runtime}-{date.today().isoformat()}-{uuid.uuid4().hex[:8]}"


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

    if args.manual:
        for field in ACTUAL_TOKEN_FIELDS:
            val = getattr(args, field, None)
            if val is not None:
                telemetry[field] = val
        extraction_method = "manual"
    else:
        try:
            telemetry = extractor.extract(args.runtime, args.session_id)
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
    row["session_run_id"] = args.session_run_id or _default_session_run_id(args.runtime)
    row["date"] = args.date or date.today().isoformat()
    row["runtime"] = args.runtime
    row["model_label"] = args.model_label or telemetry.get("model_label", "")
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
    except RuntimeError as e:
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
