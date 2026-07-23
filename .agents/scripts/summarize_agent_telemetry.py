"""Phase 11 operator telemetry: summarize agent session usage and health.

Reads .agents/telemetry/agent-sessions.csv and computes:
  1. Raw totals by runtime (input, cache creation, cache read, output, reasoning, total).
  2. Derived comparative metrics:
     - model_work_estimate = actual_input_tokens + actual_output_tokens + actual_reasoning_tokens
     - context_pressure    = actual_input_tokens + actual_cache_read_tokens
     - billing_estimate    = existing estimated_cost_usd or provider pricing when model_label is known
  3. Telemetry Health & Quality checks:
     - duplicate session_id entries
     - rows with blank token totals
     - rows using legacy runtime aliases (claude-code)
     - rows missing model_label, timestamps, or cost metadata
     - confidence breakdown (high, medium, low, manual)

Usage:
  python .agents/scripts/summarize_agent_telemetry.py
  python .agents/scripts/summarize_agent_telemetry.py --verbose
  python .agents/scripts/summarize_agent_telemetry.py --runtime claude
  python .agents/scripts/summarize_agent_telemetry.py --json
"""

from __future__ import annotations

import argparse
import io
import json
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from operator_telemetry_common import (  # noqa: E402
    read_agent_session_rows,
    AGENT_SESSION_LEGACY_RUNTIME,
)

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


KNOWN_PRICING: dict[str, dict[str, float]] = {
    # Rates per 1M tokens: input, cache_write, cache_read, output
    "claude-sonnet-5": {"input": 3.0, "cache_write": 3.75, "cache_read": 0.30, "output": 15.0},
    "claude-3-5-sonnet-20241022": {"input": 3.0, "cache_write": 3.75, "cache_read": 0.30, "output": 15.0},
    "claude-3-7-sonnet-20250219": {"input": 3.0, "cache_write": 3.75, "cache_read": 0.30, "output": 15.0},
    "claude-3-haiku-20240307": {"input": 0.25, "cache_write": 0.30, "cache_read": 0.03, "output": 1.25},
    "gpt-4o": {"input": 2.50, "cache_read": 1.25, "output": 10.00},
}


def _safe_int(val: str | None) -> int:
    if not val:
        return 0
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return 0


def _safe_float(val: str | None) -> float | None:
    if val is None or str(val).strip() == "":
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def calculate_billing_estimate(row: dict) -> float | None:
    existing_cost = _safe_float(row.get("estimated_cost_usd"))
    if existing_cost is not None:
        return existing_cost

    model_label = row.get("model_label", "").strip()
    if not model_label or model_label not in KNOWN_PRICING:
        return None

    rates = KNOWN_PRICING[model_label]
    in_tok = _safe_int(row.get("actual_input_tokens"))
    cw_tok = _safe_int(row.get("actual_cache_creation_tokens"))
    cr_tok = _safe_int(row.get("actual_cache_read_tokens"))
    out_tok = _safe_int(row.get("actual_output_tokens"))

    cost = (
        in_tok * rates.get("input", 0.0)
        + cw_tok * rates.get("cache_write", 0.0)
        + cr_tok * rates.get("cache_read", 0.0)
        + out_tok * rates.get("output", 0.0)
    ) / 1e6
    return round(cost, 6)


def summarize_telemetry(runtime_filter: str | None = None) -> dict:
    _, rows = read_agent_session_rows()

    if runtime_filter:
        flt = runtime_filter.lower().strip()
        rows = [r for r in rows if r.get("runtime", "").lower().strip() == flt]

    health_warnings: list[str] = []
    seen_session_ids: dict[str, list[str]] = {}

    runtimes: dict[str, dict] = {}
    confidence_counts: dict[str, int] = {}
    missing_model_count = 0
    missing_cost_count = 0
    missing_timestamps_count = 0
    blank_tokens_count = 0
    legacy_runtime_count = 0

    for r in rows:
        rt = r.get("runtime", "unknown")
        if rt in AGENT_SESSION_LEGACY_RUNTIME:
            legacy_runtime_count += 1
            health_warnings.append(f"Row '{r.get('session_run_id')}' uses legacy runtime alias {rt!r}.")

        sid = r.get("session_id", "").strip()
        if sid:
            seen_session_ids.setdefault(sid, []).append(r.get("session_run_id", ""))

        conf = r.get("confidence", "unknown")
        confidence_counts[conf] = confidence_counts.get(conf, 0) + 1

        in_tok = _safe_int(r.get("actual_input_tokens"))
        cw_tok = _safe_int(r.get("actual_cache_creation_tokens"))
        cr_tok = _safe_int(r.get("actual_cache_read_tokens"))
        out_tok = _safe_int(r.get("actual_output_tokens"))
        rs_tok = _safe_int(r.get("actual_reasoning_tokens"))
        tot_tok = _safe_int(r.get("total_tokens"))

        if tot_tok == 0 and (in_tok + out_tok) == 0:
            blank_tokens_count += 1
            health_warnings.append(f"Row '{r.get('session_run_id')}' has blank/zero token totals.")

        model_lbl = r.get("model_label", "").strip()
        if not model_lbl:
            missing_model_count += 1

        if not r.get("started_at") or not r.get("ended_at"):
            missing_timestamps_count += 1

        cost = calculate_billing_estimate(r)
        if cost is None:
            missing_cost_count += 1

        # Initialize runtime summary if new
        if rt not in runtimes:
            runtimes[rt] = {
                "session_count": 0,
                "raw_input_tokens": 0,
                "raw_cache_creation_tokens": 0,
                "raw_cache_read_tokens": 0,
                "raw_output_tokens": 0,
                "raw_reasoning_tokens": 0,
                "raw_total_tokens": 0,
                "model_work_estimate": 0,
                "context_pressure": 0,
                "billing_estimate_usd": 0.0,
                "has_unknown_cost": False,
            }

        rt_summary = runtimes[rt]
        rt_summary["session_count"] += 1
        rt_summary["raw_input_tokens"] += in_tok
        rt_summary["raw_cache_creation_tokens"] += cw_tok
        rt_summary["raw_cache_read_tokens"] += cr_tok
        rt_summary["raw_output_tokens"] += out_tok
        rt_summary["raw_reasoning_tokens"] += rs_tok
        rt_summary["raw_total_tokens"] += tot_tok

        # Derived metrics
        rt_summary["model_work_estimate"] += (in_tok + out_tok + rs_tok)
        rt_summary["context_pressure"] += (in_tok + cr_tok)

        if cost is not None:
            rt_summary["billing_estimate_usd"] += cost
        else:
            rt_summary["has_unknown_cost"] = True

    # Check for duplicate session_ids
    duplicate_sessions = {sid: sids for sid, sids in seen_session_ids.items() if len(sids) > 1}
    for sid, sids in duplicate_sessions.items():
        health_warnings.append(
            f"Duplicate session_id {sid!r} found across {len(sids)} rows: {sids}"
        )

    # Format runtime costs cleanly
    for rt, stats in runtimes.items():
        if stats["has_unknown_cost"] and stats["billing_estimate_usd"] == 0.0:
            stats["billing_estimate_formatted"] = "N/A (model/pricing unknown)"
        elif stats["has_unknown_cost"]:
            stats["billing_estimate_formatted"] = f"${stats['billing_estimate_usd']:.2f}+ (partial)"
        else:
            stats["billing_estimate_formatted"] = f"${stats['billing_estimate_usd']:.2f}"

    summary = {
        "total_sessions": len(rows),
        "runtimes": runtimes,
        "health": {
            "duplicate_session_ids_count": len(duplicate_sessions),
            "duplicate_session_details": duplicate_sessions,
            "blank_tokens_count": blank_tokens_count,
            "legacy_runtime_alias_count": legacy_runtime_count,
            "missing_model_label_count": missing_model_count,
            "missing_timestamps_count": missing_timestamps_count,
            "missing_cost_count": missing_cost_count,
            "confidence_breakdown": confidence_counts,
            "warnings": health_warnings,
        },
    }
    return summary


def print_text_report(summary: dict, verbose: bool = False) -> None:
    print("=" * 70)
    print("OPERATOR TELEMETRY SESSION SUMMARY")
    print("=" * 70)
    print(f"Total sessions recorded: {summary['total_sessions']}\n")

    print("PER-RUNTIME SUMMARY")
    print("-" * 70)
    for rt, stats in summary["runtimes"].items():
        print(f"Runtime: {rt} ({stats['session_count']} session(s))")
        print(f"  Raw Total Tokens:        {stats['raw_total_tokens']:,}")
        print(f"  Model Work Estimate:     {stats['model_work_estimate']:,} (input + output + reasoning)")
        print(f"  Context Pressure:        {stats['context_pressure']:,} (input + cache_read)")
        print(f"  Billing Estimate:        {stats['billing_estimate_formatted']}")
        print(f"  Breakdown:")
        print(f"    - Input Tokens:        {stats['raw_input_tokens']:,}")
        print(f"    - Cache Read Tokens:   {stats['raw_cache_read_tokens']:,}")
        print(f"    - Cache Creation:      {stats['raw_cache_creation_tokens']:,}")
        print(f"    - Output Tokens:       {stats['raw_output_tokens']:,}")
        print(f"    - Reasoning Tokens:    {stats['raw_reasoning_tokens']:,}")
        print("-" * 70)

    print("\nHEALTH & QUALITY REPORT")
    print("-" * 70)
    health = summary["health"]
    print(f"  Duplicate session_ids:    {health['duplicate_session_ids_count']}")
    print(f"  Blank token rows:         {health['blank_tokens_count']}")
    print(f"  Legacy runtime aliases:   {health['legacy_runtime_alias_count']}")
    print(f"  Missing model labels:     {health['missing_model_label_count']}")
    print(f"  Missing timestamps:       {health['missing_timestamps_count']}")
    print(f"  Missing costs:            {health['missing_cost_count']}")
    print("  Confidence Breakdown:")
    for conf, cnt in sorted(health["confidence_breakdown"].items()):
        print(f"    - {conf}: {cnt}")

    if health["warnings"]:
        print("\nHealth Warnings:")
        for w in health["warnings"]:
            print(f"  ! {w}")
    else:
        print("\nAll health checks passed (zero duplicate session IDs or hygiene issues).")
    print("=" * 70)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Output summary in strict JSON format.")
    parser.add_argument("--runtime", help="Filter summary for a specific runtime.")
    parser.add_argument("--verbose", action="store_true", help="Print extra details.")
    args = parser.parse_args()

    summary = summarize_telemetry(runtime_filter=args.runtime)

    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print_text_report(summary, verbose=args.verbose)

    return 0


if __name__ == "__main__":
    sys.exit(main())
