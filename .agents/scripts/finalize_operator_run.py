"""Phase 11 operator telemetry: append one enriched row to operator-runs.csv.

The enrichment step over measure_operator_outputs.py --append-csv: this
script can merge actual token telemetry (from CLI args, a JSON file written
by extract_agent_telemetry.py, or manual entry after reading your own agent
transcript), compute total_tokens/estimated_cost_usd when possible, and
compute reduction_ratio_vs_baseline against an existing baseline row already
in the CSV. It always appends exactly one new row and never rewrites an
existing one - see operator_telemetry_common.diff_guard_new_row_only(),
run automatically after appending.

Usage
-----
  # From a measure_operator_outputs.py --json output, saved to a file
  python .agents/scripts/measure_operator_outputs.py --case dashboard_overview --json > tmp/telemetry/row.json
  python .agents/scripts/finalize_operator_run.py --from-json tmp/telemetry/row.json

  # Same, but also attach actual token telemetry measured separately
  python .agents/scripts/finalize_operator_run.py --from-json tmp/telemetry/row.json \\
      --actual-input-tokens 1200 --actual-output-tokens 340

  # Attach a baseline for reduction_ratio_vs_baseline (baseline row_id must
  # already be in the CSV)
  python .agents/scripts/finalize_operator_run.py --from-json tmp/telemetry/row.json \\
      --baseline-run-id show_project_state_full_project-2026-07-21-abcd1234

  # Fully manual row (no measure_operator_outputs.py run at all)
  python .agents/scripts/finalize_operator_run.py --manual \\
      --case-id dashboard_overview --run-id manual-001 --command-name "qa_manage.py dashboard" \\
      --command-args-redacted "qa_manage.py dashboard --json" --json-mode yes --status ok \\
      --elapsed-ms 120 --stdout-bytes 4000 --stderr-bytes 0 --output-chars 3900 --truncated no
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPTS_DIR.parent.parent

sys.path.insert(0, str(SCRIPTS_DIR))
from operator_telemetry_common import (  # noqa: E402
    CSV_HEADER,
    append_row,
    diff_guard_new_row_only,
    read_rows,
)

# Illustrative API-list pricing (USD per token), same spirit as the
# erp-web-tests benchmark skill's PRICING table: an API-equivalent cost for
# cross-platform comparability, not a claim about what any subscription user
# was actually charged. Extend as needed; unknown model_label -> blank cost.
PRICING = {
    "claude-sonnet-5": {"input": 3.00e-6, "output": 15.00e-6, "cache_creation": 3.75e-6, "cache_read": 0.30e-6},
    "claude-opus-4-8": {"input": 15.00e-6, "output": 75.00e-6, "cache_creation": 18.75e-6, "cache_read": 1.50e-6},
    "claude-haiku-4-5": {"input": 0.80e-6, "output": 4.00e-6, "cache_creation": 1.00e-6, "cache_read": 0.08e-6},
}


def estimate_cost(model_label: str, tokens: dict) -> str:
    key = (model_label or "").strip().lower()
    price = PRICING.get(key)
    if not price:
        return ""
    total = 0.0
    total += (tokens.get("actual_input_tokens") or 0) * price.get("input", 0)
    total += (tokens.get("actual_output_tokens") or 0) * price.get("output", 0)
    total += (tokens.get("actual_cache_creation_tokens") or 0) * price.get("cache_creation", 0)
    total += (tokens.get("actual_cache_read_tokens") or 0) * price.get("cache_read", 0)
    return f"{total:.6f}"


def compute_total_tokens(row: dict) -> str:
    keys = ("actual_input_tokens", "actual_cache_creation_tokens", "actual_cache_read_tokens",
            "actual_output_tokens", "actual_reasoning_tokens")
    values = [row.get(k) for k in keys]
    if all(v in (None, "", "n/a") for v in values):
        return ""
    total = 0
    for v in values:
        try:
            total += int(v)
        except (TypeError, ValueError):
            pass
    return str(total)


def compute_reduction_ratio(row: dict, baseline_run_id: str | None) -> str:
    if not baseline_run_id:
        return ""
    _, rows = read_rows()
    baseline_row = next((r for r in rows if r.get("run_id") == baseline_run_id), None)
    if not baseline_row:
        raise SystemExit(f"--baseline-run-id '{baseline_run_id}' not found in operator-runs.csv.")
    try:
        this_chars = float(row["output_chars"])
        base_chars = float(baseline_row["output_chars"])
    except (KeyError, ValueError):
        return ""
    if base_chars == 0:
        return ""
    return f"{this_chars / base_chars:.4f}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--from-json", help="Path to a JSON row emitted by measure_operator_outputs.py --json.")
    parser.add_argument("--manual", action="store_true", help="Build the row entirely from CLI flags below instead of --from-json.")
    for field in CSV_HEADER:
        flag = "--" + field.replace("_", "-")
        if flag not in ("--from-json",):
            parser.add_argument(flag, dest=field, default=None)
    parser.add_argument("--baseline-run-id", default=None, help="Existing CSV run_id to compute reduction_ratio_vs_baseline against.")
    parser.add_argument("--telemetry-json", default=None, help="JSON file with actual_* token fields (e.g. from extract_agent_telemetry.py) to merge in.")
    parser.add_argument("--dry-run", action="store_true", help="Validate and print the row; do not write the CSV.")
    args = parser.parse_args()

    if args.from_json:
        row = json.loads(Path(args.from_json).read_text(encoding="utf-8"))
    elif args.manual:
        row = {k: "" for k in CSV_HEADER}
    else:
        parser.error("one of --from-json or --manual is required")
        return 2

    for field in CSV_HEADER:
        val = getattr(args, field, None)
        if val is not None:
            row[field] = val

    row.setdefault("date", date.today().isoformat())
    row.setdefault("runtime", "manual_script")
    row.setdefault("json_mode", "no")
    row.setdefault("truncated", "no")

    if args.telemetry_json:
        telemetry = json.loads(Path(args.telemetry_json).read_text(encoding="utf-8"))
        for key in ("actual_input_tokens", "actual_cache_creation_tokens",
                    "actual_cache_read_tokens", "actual_output_tokens", "actual_reasoning_tokens"):
            if key in telemetry:
                row[key] = telemetry[key]

    row["total_tokens"] = compute_total_tokens(row)
    if row["total_tokens"] and not row.get("estimated_cost_usd"):
        cost_inputs = {k: (int(row[k]) if str(row.get(k, "")).strip() not in ("", "n/a") else 0)
                       for k in ("actual_input_tokens", "actual_output_tokens",
                                 "actual_cache_creation_tokens", "actual_cache_read_tokens")}
        cost = estimate_cost(row.get("model_label", ""), cost_inputs)
        if cost:
            row["estimated_cost_usd"] = cost

    row["reduction_ratio_vs_baseline"] = compute_reduction_ratio(row, args.baseline_run_id) or row.get("reduction_ratio_vs_baseline", "")

    missing_required = [k for k in CSV_HEADER if row.get(k, "") == "" and k in
                         ("case_id", "run_id", "date", "runtime", "command_name",
                          "command_args_redacted", "json_mode", "status", "elapsed_ms",
                          "stdout_bytes", "stderr_bytes", "output_chars", "truncated")]
    if missing_required:
        raise SystemExit(f"Missing required field(s): {missing_required}")

    if args.dry_run:
        print(json.dumps(row, ensure_ascii=True, indent=2))
        print("[dry-run] nothing written.")
        return 0

    append_row(row)
    ok, violations = diff_guard_new_row_only(row["run_id"])
    if not ok:
        print("Error: diff guard failed after append - see violations below.", file=sys.stderr)
        for v in violations:
            print(f" - {v}", file=sys.stderr)
        return 1

    print(f"Appended row for run_id={row['run_id']} to .agents/telemetry/operator-runs.csv")
    print("Diff guard OK: only the new row was added.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
