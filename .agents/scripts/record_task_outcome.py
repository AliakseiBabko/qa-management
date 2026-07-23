#!/usr/bin/env python3
"""Phase 11 operator telemetry: record one task-outcome workload/closure row.

Companion to operator-runs.csv (command footprints) and agent-sessions.csv
(LLM session tokens): task-outcomes.csv records derived pass closure facts
and business deliverables.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
import uuid
from pathlib import Path
from types import SimpleNamespace

SCRIPTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPTS_DIR.parent.parent

sys.path.insert(0, str(SCRIPTS_DIR))
from operator_telemetry_common import (  # noqa: E402
    TASK_OUTCOME_CSV_HEADER,
    append_task_outcome_row,
    diff_guard_task_outcome_new_row_only,
    validate_task_outcome_row,
)


def _resolve_source_blob(run_id: str) -> tuple[str, str, str]:
    """Look up _source_text_manifest.json for key '<run_id>:v1'.
    Returns (source_blob_present, source_chars, source_estimated_tokens).
    Degrades gracefully with a warning to stderr if missing or unreadable."""
    mirror_roots = [
        Path.home() / "Documents" / "qa-drive-mirror",
        Path.home() / ".qa-drive-mirror",
    ]
    for root in mirror_roots:
        manifest_path = root / "_source_text_manifest.json"
        if not manifest_path.exists():
            continue
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            blob_key = f"{run_id}:v1"
            if blob_key in manifest:
                rel_blob = manifest[blob_key].get("text_path", "")
                blob_file = root / rel_blob
                if blob_file.exists():
                    text = blob_file.read_text(encoding="utf-8", errors="replace")
                    chars = len(text)
                    tokens = chars // 4
                    return "yes", str(chars), str(tokens)
        except Exception as exc:
            sys.stderr.write(f"Warning: error reading source text manifest at {manifest_path}: {exc}\n")

    sys.stderr.write(f"Warning: source text blob for {run_id}:v1 not found in private mirror.\n")
    return "no", "", ""


def _tally_closure_outcomes(outcomes: list[dict]) -> tuple[int, int, int, int]:
    """Pure tally over closure_outcomes.fetch_outcomes()-shaped rows (keyed
    by closure_outcomes.HEADER - "Outcome" with a capital O, matching the
    real _closure_outcomes Sheet header, not a lowercase "outcome" key).
    Split out from _derive_closure_counts so it is unit-testable against
    real-shaped fixture data with no Google API/network dependency."""
    count = updated = no_change = gated = 0
    for rec in outcomes:
        count += 1
        outcome = rec.get("Outcome", "")
        if outcome == "updated":
            updated += 1
        elif outcome == "no_change":
            no_change += 1
        elif outcome in ("gated", "regenerated"):
            gated += 1
    return count, updated, no_change, gated


def _derive_closure_counts(run_id: str) -> tuple[int, int, int, int, str]:
    """Fetch this run's _closure_outcomes rows (all scopes - this is a
    reporting tally over what was already recorded, not the strict
    per-scope closure check check_cascade_closure.py/complete perform) and
    tally them by outcome.

    Returns (count, updated, no_change, gated, status) where status is:
      "ok"          - the fetch itself succeeded. 0 rows is a legitimate,
                      real outcome for a route with no cascade edges, not
                      a failure - it is NOT conflated with a derivation
                      problem below.
      "unavailable" - could not obtain Google API services (e.g. no
                      credentials/network) - the zero counts returned here
                      are NOT a real measurement, just unmeasured.
      "error"       - fetch_outcomes itself raised (e.g. an import/attribute
                      error, a malformed sheet) - same caveat as above.

    Never silently swallows a derivation exception into an indistinguishable
    false zero (the original bug: importing a nonexistent
    closure_outcomes.read_closure_outcomes, caught by a bare `except
    Exception: pass`) - the caller decides what a non-"ok" status means for
    the row's own `status` field."""
    try:
        from qa_manage import get_services_cached
        services = get_services_cached()
    except Exception as exc:
        sys.stderr.write(
            f"Warning: could not obtain Google API services for closure-outcome "
            f"derivation on run {run_id}: {exc}\n"
        )
        return 0, 0, 0, 0, "unavailable"

    try:
        from closure_outcomes import fetch_outcomes
        outcomes = fetch_outcomes(services, run_id, all_scopes=True)
    except Exception as exc:
        sys.stderr.write(
            f"ERROR: closure-outcome derivation failed for run {run_id}: {exc}\n"
        )
        return 0, 0, 0, 0, "error"

    count, updated, no_change, gated = _tally_closure_outcomes(outcomes)
    return count, updated, no_change, gated, "ok"


def extract_from_run(run_id: str) -> dict:
    from qa_manage import cmd_review

    res = cmd_review(SimpleNamespace(run_id=run_id, json=True, min_age_days=0))
    if not res.ok:
        raise SystemExit(f"qa_manage.py review failed for run {run_id}: {res.human_lines}")

    data = res.data
    # cmd_review's actual output (qa_manage.py's CommandResult.data) has no
    # "lane" or "source_type" key at all - those describe the queue row's
    # routing, not review's own return schema. Left blank rather than
    # guessed; add real fields to cmd_review's output later if this is
    # needed, instead of reading keys that don't exist.
    lane = ""
    source_type = ""
    run_status = data.get("status", "")
    unresolved_edges = data.get("unresolved_edges", [])

    if run_status in ("completed", "ready"):
        status = "gated" if unresolved_edges else "ok"
    elif run_status == "blocked":
        status = "gated"
    else:
        status = "error"

    # entries is {scope_key: {doc_name: [outcome, reason]}} - see
    # qa_manage.py's parse_entries_cell() - one level deeper than a flat
    # {doc_name: [outcome, reason]} dict.
    entries = data.get("entries", {})
    record_apply_updated = 0
    record_apply_no_change = 0
    record_apply_not_applicable = 0
    if isinstance(entries, dict):
        for scope_key, docs in entries.items():
            if not isinstance(docs, dict):
                continue
            for doc_name, item in docs.items():
                if isinstance(item, list) and len(item) > 0:
                    outcome = item[0]
                    if outcome == "updated":
                        record_apply_updated += 1
                    elif outcome == "no_change":
                        record_apply_no_change += 1
                    elif outcome == "not_applicable":
                        record_apply_not_applicable += 1

    closure_count, closure_updated, closure_no_change, closure_gated, closure_derivation_status = (
        _derive_closure_counts(run_id)
    )

    sys.stderr.write(
        "Warning: lane/source_type are not derivable from qa_manage.py review --json - "
        "leaving both blank. Pass --lane/--source-type explicitly, or add those fields "
        "to cmd_review's output if this becomes a recurring need.\n"
    )

    blob_present, source_chars, source_tokens = _resolve_source_blob(run_id)
    queue_run_hash = hashlib.sha256(run_id.encode("utf-8")).hexdigest()[:16]

    return {
        "queue_run_hash": queue_run_hash,
        "lane": lane,
        "source_type": source_type,
        "source_count": 1,
        "source_blob_present": blob_present,
        "source_chars": source_chars,
        "source_estimated_tokens": source_tokens,
        "record_apply_updated_count": record_apply_updated,
        "record_apply_no_change_count": record_apply_no_change,
        "record_apply_not_applicable_count": record_apply_not_applicable,
        "closure_edges_count": closure_count,
        "closure_edges_updated_count": closure_updated,
        "closure_edges_no_change_count": closure_no_change,
        "closure_edges_gated_count": closure_gated,
        "closure_derivation_status": closure_derivation_status,
        "status": status,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-run", help="Auto-extract closure facts from a completed queue run_id")
    parser.add_argument("--task-type", default="intake_run",
                        choices=["intake_run", "repo_maintenance", "retro_pass", "admin_pass", "quality_audit", "cleanup_pass"])
    parser.add_argument("--runtime", default="antigravity",
                        choices=["antigravity", "claude", "codex", "cline", "manual"])
    parser.add_argument("--linked-session-run-id", default="")
    parser.add_argument("--lane", default="")
    parser.add_argument("--source-type", default="")
    parser.add_argument("--source-count", default=None, type=int)
    parser.add_argument("--source-chars", default=None, type=int)
    parser.add_argument("--record-apply-updated-count", default=None, type=int)
    parser.add_argument("--record-apply-no-change-count", default=None, type=int)
    parser.add_argument("--record-apply-not-applicable-count", default=None, type=int)
    parser.add_argument("--closure-edges-count", default=None, type=int)
    parser.add_argument("--closure-edges-updated-count", default=None, type=int)
    parser.add_argument("--closure-edges-no-change-count", default=None, type=int)
    parser.add_argument("--closure-edges-gated-count", default=None, type=int)
    parser.add_argument("--mirror-export-mode", default="", choices=["full", "scoped", "none", ""])
    parser.add_argument("--status", default="ok", choices=["ok", "error", "gated"])
    parser.add_argument("--notes", default="")
    parser.add_argument("--check-registry", action="store_true")
    parser.add_argument("--append-csv", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    today_iso = dt.date.today().isoformat()
    prefix = args.task_type.replace("_", "-")
    if prefix == "intake-run":
        prefix = "intake"
    task_outcome_id = f"outcome-{prefix}-{today_iso}-{uuid.uuid4().hex[:8]}"

    extracted = {}
    if args.from_run:
        extracted = extract_from_run(args.from_run)

    row = dict.fromkeys(TASK_OUTCOME_CSV_HEADER, "")
    row.update({
        "task_outcome_id": task_outcome_id,
        "date": today_iso,
        "task_type": args.task_type,
        "runtime": args.runtime,
        "linked_session_run_id": args.linked_session_run_id,
        "lane": args.lane or extracted.get("lane", ""),
        "source_type": args.source_type or extracted.get("source_type", ""),
        "source_count": str(args.source_count if args.source_count is not None else extracted.get("source_count", 0)),
        "source_blob_present": extracted.get("source_blob_present", "no" if args.source_chars is None else "yes"),
        "source_chars": str(args.source_chars) if args.source_chars is not None else str(extracted.get("source_chars", "")),
        "source_estimated_tokens": str(args.source_chars // 4) if args.source_chars is not None else str(extracted.get("source_estimated_tokens", "")),
        "record_apply_updated_count": str(args.record_apply_updated_count if args.record_apply_updated_count is not None else extracted.get("record_apply_updated_count", 0)),
        "record_apply_no_change_count": str(args.record_apply_no_change_count if args.record_apply_no_change_count is not None else extracted.get("record_apply_no_change_count", 0)),
        "record_apply_not_applicable_count": str(args.record_apply_not_applicable_count if args.record_apply_not_applicable_count is not None else extracted.get("record_apply_not_applicable_count", 0)),
        "closure_edges_count": str(args.closure_edges_count if args.closure_edges_count is not None else extracted.get("closure_edges_count", 0)),
        "closure_edges_updated_count": str(args.closure_edges_updated_count if args.closure_edges_updated_count is not None else extracted.get("closure_edges_updated_count", 0)),
        "closure_edges_no_change_count": str(args.closure_edges_no_change_count if args.closure_edges_no_change_count is not None else extracted.get("closure_edges_no_change_count", 0)),
        "closure_edges_gated_count": str(args.closure_edges_gated_count if args.closure_edges_gated_count is not None else extracted.get("closure_edges_gated_count", 0)),
        "queue_run_hash": extracted.get("queue_run_hash", ""),
        "mirror_export_mode": args.mirror_export_mode,
        "status": extracted.get("status", args.status),
        "notes": args.notes,
    })

    # If closure-outcome derivation itself failed/was unavailable (see
    # _derive_closure_counts), the closure_edges_* counts above are NOT a
    # real zero - do not let the row silently claim "ok" with unmeasured
    # counts. An explicit --closure-edges-* override means the caller
    # already supplied ground truth, so it is trusted and no escalation
    # applies. Otherwise, escalate loudly: to "error" for a run whose other
    # signals already looked clean (closure data should have been
    # measurable), to "gated" when the row's status already reflected some
    # other problem (already surfaced, don't downgrade it back to a milder
    # label than an unrelated existing issue implies... this only ever
    # raises severity, never lowers it).
    explicit_closure_override = any(
        v is not None for v in (
            args.closure_edges_count, args.closure_edges_updated_count,
            args.closure_edges_no_change_count, args.closure_edges_gated_count,
        )
    )
    closure_derivation_status = extracted.get("closure_derivation_status", "ok")
    if not explicit_closure_override and closure_derivation_status != "ok":
        prior_status = row["status"]
        escalated_status = "error" if prior_status == "ok" else prior_status
        if escalated_status != prior_status:
            sys.stderr.write(
                f"Warning: closure-outcome derivation status={closure_derivation_status!r} - "
                f"row status escalated from {prior_status!r} to {escalated_status!r} "
                "(closure_edges_* counts are unmeasured, not a real zero). "
                "Pass --closure-edges-* explicitly to override.\n"
            )
            row["status"] = escalated_status

    watch = None
    if args.check_registry:
        try:
            from check_sensitive_data import load_watch_strings
            from pipeline_common import get_services
            watch = load_watch_strings(get_services())
        except Exception as exc:
            sys.stderr.write(f"Warning: could not load watch strings: {exc}\n")

    errors = validate_task_outcome_row(row, watch=watch)
    if errors:
        sys.stderr.write("Validation failed:\n  " + "\n  ".join(errors) + "\n")
        return 1

    if args.dry_run or not args.append_csv:
        if args.json:
            print(json.dumps(row, indent=2))
        else:
            print(json.dumps(row, indent=2))
            print("[dry-run] nothing written.")
        return 0

    append_task_outcome_row(row)
    ok, violations = diff_guard_task_outcome_new_row_only(task_outcome_id, repo_root=REPO_ROOT)
    if not ok:
        sys.stderr.write("Diff guard VIOLATION:\n  " + "\n  ".join(violations) + "\n")
        return 1

    print(f"Appended row for task_outcome_id={task_outcome_id} to {TASK_OUTCOME_CSV_HEADER}")
    print("Diff guard OK: only the new task-outcome row was added.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
