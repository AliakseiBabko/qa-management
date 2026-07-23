"""Phase 11 operator telemetry: repair migration script for agent-sessions.csv.

Consolidates duplicate rows sharing the same continuous `session_id`, unions
linked operator run IDs, re-extracts authoritative usage from local logs where
available, applies generic public-safe objectives, and normalizes legacy runtime
aliases (`claude-code` -> `claude`).

Usage:
  python .agents/scripts/repair_agent_sessions_csv.py              # dry-run (default)
  python .agents/scripts/repair_agent_sessions_csv.py --apply      # write changes to agent-sessions.csv
  python .agents/scripts/repair_agent_sessions_csv.py --apply --allow-dirty
"""

from __future__ import annotations

import argparse
import csv
import io
import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from operator_telemetry_common import (  # noqa: E402
    AGENT_SESSION_CSV_HEADER,
    AGENT_SESSION_CSV_PATH,
    read_agent_session_rows,
    validate_agent_session_row,
)
from extract_agent_telemetry import extract  # noqa: E402

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def is_git_dirty() -> bool:
    try:
        res = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, check=False,
        )
        return bool(res.stdout.strip())
    except Exception:
        return False


def _union_linked_ids(rows: list[dict]) -> str:
    linked: list[str] = []
    for r in rows:
        raw = r.get("linked_operator_run_ids", "")
        if not raw:
            continue
        for item in raw.split(","):
            item = item.strip().strip('"')
            if item and item not in linked:
                linked.append(item)
    return ",".join(linked)


def compute_repaired_rows() -> tuple[list[dict], list[str]]:
    header, original_rows = read_agent_session_rows()
    warnings: list[str] = []

    # Group rows by session_id
    grouped: dict[str, list[dict]] = {}
    for r in original_rows:
        sid = r.get("session_id", "").strip()
        grouped.setdefault(sid, []).append(r)

    repaired_rows: list[dict] = []

    for sid, group in grouped.items():
        if not sid:
            # Keep rows missing session_id (should not happen, but don't drop blindly)
            repaired_rows.extend(group)
            continue

        if len(group) == 1:
            row = dict(group[0])
            # Normalize legacy runtime alias
            if row.get("runtime") == "claude-code":
                row["runtime"] = "claude"
            repaired_rows.append(row)
            continue

        # Multiple rows for the same session_id -> Consolidation needed
        primary_runtime = group[0].get("runtime", "claude")
        if primary_runtime in ("claude", "claude-code"):
            primary_runtime = "claude"

        unioned_links = _union_linked_ids(group)

        # Attempt authoritative re-extraction from local logs first
        extracted: dict | None = None
        try:
            extracted = extract(primary_runtime, sid)
        except Exception as exc:
            warnings.append(
                f"Re-extraction for session_id {sid!r} via extract_agent_telemetry failed ({exc}); "
                "falling back to highest cumulative row metrics from CSV."
            )

        new_row = dict(group[-1])  # Start from latest row structure
        new_row["session_run_id"] = f"session-{primary_runtime}-2026-07-23-consolidated"
        new_row["date"] = "2026-07-23"
        new_row["runtime"] = primary_runtime
        new_row["linked_operator_run_ids"] = unioned_links

        # Generic public-safe objective and blank notes
        new_row["objective"] = "project knowledge intake and correction passes"
        new_row["notes"] = ""

        if extracted:
            new_row["actual_input_tokens"] = str(extracted.get("actual_input_tokens", 0))
            new_row["actual_cache_creation_tokens"] = str(extracted.get("actual_cache_creation_tokens", 0))
            new_row["actual_cache_read_tokens"] = str(extracted.get("actual_cache_read_tokens", 0))
            new_row["actual_output_tokens"] = str(extracted.get("actual_output_tokens", 0))
            new_row["actual_reasoning_tokens"] = str(extracted.get("actual_reasoning_tokens", 0))

            tot = (
                extracted.get("actual_input_tokens", 0)
                + extracted.get("actual_cache_creation_tokens", 0)
                + extracted.get("actual_cache_read_tokens", 0)
                + extracted.get("actual_output_tokens", 0)
                + extracted.get("actual_reasoning_tokens", 0)
            )
            new_row["total_tokens"] = str(tot)
            new_row["extraction_method"] = extracted.get("extraction_method", "claude_log")
            new_row["confidence"] = "high"

            if extracted.get("model_label"):
                new_row["model_label"] = extracted["model_label"]

            # Compute estimated_cost_usd for claude-sonnet-5 if model is known
            model_lbl = new_row.get("model_label", "")
            if model_lbl in ("claude-sonnet-5", "claude-3-5-sonnet-20241022", "claude-3-7-sonnet-20250219"):
                in_tok = extracted.get("actual_input_tokens", 0)
                cw_tok = extracted.get("actual_cache_creation_tokens", 0)
                cr_tok = extracted.get("actual_cache_read_tokens", 0)
                out_tok = extracted.get("actual_output_tokens", 0)
                cost = (in_tok * 3.0 + cw_tok * 3.75 + cr_tok * 0.30 + out_tok * 15.0) / 1e6
                new_row["estimated_cost_usd"] = f"{cost:.6f}"

            if extracted.get("session_started_at"):
                new_row["started_at"] = extracted["session_started_at"]
            if extracted.get("session_ended_at"):
                new_row["ended_at"] = extracted["session_ended_at"]

            if new_row.get("started_at") and new_row.get("ended_at"):
                try:
                    from datetime import datetime
                    s_dt = datetime.fromisoformat(new_row["started_at"].replace("Z", "+00:00"))
                    e_dt = datetime.fromisoformat(new_row["ended_at"].replace("Z", "+00:00"))
                    elapsed = (e_dt - s_dt).total_seconds() / 60.0
                    new_row["elapsed_min"] = f"{elapsed:.2f}"
                except Exception:
                    pass
        else:
            # Fallback: pick row with max total_tokens in group
            best = max(group, key=lambda r: float(r.get("total_tokens", 0) or 0))
            for k in (
                "actual_input_tokens", "actual_cache_creation_tokens",
                "actual_cache_read_tokens", "actual_output_tokens",
                "actual_reasoning_tokens", "total_tokens", "estimated_cost_usd",
                "started_at", "ended_at", "elapsed_min", "model_label",
                "extraction_method", "confidence",
            ):
                new_row[k] = best.get(k, "")

        repaired_rows.append(new_row)

    return repaired_rows, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Apply repair migration and rewrite CSV.")
    parser.add_argument("--allow-dirty", action="store_true", help="Allow running --apply when git status is dirty.")
    args = parser.parse_args()

    if args.apply and not args.allow_dirty and is_git_dirty():
        print(
            "Error: Working tree is dirty. Pass --allow-dirty to force repair migration on a dirty working tree.",
            file=sys.stderr,
        )
        return 1

    header, original_rows = read_agent_session_rows()
    repaired_rows, warnings = compute_repaired_rows()

    for w in warnings:
        print(f"WARN: {w}", file=sys.stderr)

    print(f"Original row count: {len(original_rows)}")
    print(f"Repaired row count: {len(repaired_rows)}")

    # Validate repaired rows
    validation_errors = []
    for i, r in enumerate(repaired_rows):
        errs = validate_agent_session_row(r)
        if errs:
            validation_errors.append(f"Row {i+1} ({r.get('session_run_id')}): {errs}")

    if validation_errors:
        print("\nValidation failures in repaired dataset:", file=sys.stderr)
        for e in validation_errors:
            print(f" - {e}", file=sys.stderr)
        return 1

    if not args.apply:
        print("\n--- Dry Run Summary ---")
        print("Consolidated session rows to be written:")
        for r in repaired_rows:
            print(
                f"  - {r['session_run_id']} | sid={r['session_id'][:8]}... | "
                f"tot={r['total_tokens']} | obj={r['objective']!r}"
            )
        print("\nRun with --apply to perform the one-time telemetry repair migration.")
        return 0

    # Write repaired CSV
    with open(AGENT_SESSION_CSV_PATH, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=AGENT_SESSION_CSV_HEADER)
        writer.writeheader()
        for r in repaired_rows:
            writer.writerow({k: r.get(k, "") for k in AGENT_SESSION_CSV_HEADER})

    print(f"\nSuccessfully wrote repaired agent-sessions.csv ({len(repaired_rows)} rows).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
