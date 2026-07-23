"""Phase 11 operator telemetry: authoritative summarize agent session usage and health.

Reads .agents/telemetry/agent-sessions.csv and computes:
  1. Common Ground Comparison (default cross-runtime comparison layer):
     - work_done_tokens        = actual_input_tokens + actual_output_tokens + actual_reasoning_tokens
                                 (excludes cache-read multiplication)
     - context_pressure_tokens = actual_input_tokens + actual_cache_read_tokens
                                 (reflects total context window accumulation)
     - billable_estimate_usd   = existing estimated_cost_usd or provider pricing when model_label is known
  2. Provider-Native Totals (preserved raw evidence, labeled provider-native):
     - provider_native_latest_snapshot_totals (default) or provider_native_all_snapshot_totals (--include-snapshots)
     - input, cache creation, cache read, output, reasoning, total tokens
  3. Telemetry Health & Quality checks:
     - cumulative snapshot detection (duplicate session_id rows)
     - rows with blank token totals
     - rows using legacy runtime aliases (claude-code)
     - rows missing model_label, timestamps, or cost metadata
     - row_confidence_breakdown (raw CSV rows) vs session_confidence_breakdown (aggregated session units)

Usage:
  python .agents/scripts/summarize_agent_telemetry.py
  python .agents/scripts/summarize_agent_telemetry.py --include-snapshots
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
    "claude-sonnet-5-medium": {"input": 3.0, "cache_write": 3.75, "cache_read": 0.30, "output": 15.0},
    "claude-3-5-sonnet-20241022": {"input": 3.0, "cache_write": 3.75, "cache_read": 0.30, "output": 15.0},
    "claude-3-7-sonnet-20250219": {"input": 3.0, "cache_write": 3.75, "cache_read": 0.30, "output": 15.0},
    "claude-3-haiku-20240307": {"input": 0.25, "cache_write": 0.30, "cache_read": 0.03, "output": 1.25},
    "gemini-3.6-flash-medium": {"input": 0.15, "cache_write": 0.15, "cache_read": 0.0375, "output": 0.60},
    "codex-5.5-medium": {"input": 2.50, "cache_read": 1.25, "output": 10.00},
    "gpt-4o": {"input": 2.50, "cache_read": 1.25, "output": 10.00},
}

DEFAULT_MODEL_LABELS_BY_RUNTIME = {
    "antigravity": "gemini-3.6-flash-medium",
    "claude": "claude-sonnet-5-medium",
    "claude-code": "claude-sonnet-5-medium",
    "codex": "codex-5.5-medium",
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
    if not model_label:
        rt = row.get("runtime", "").lower().strip()
        model_label = DEFAULT_MODEL_LABELS_BY_RUNTIME.get(rt, "")

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


def summarize_telemetry(runtime_filter: str | None = None, include_snapshots: bool = False, verbose: bool = False) -> dict:
    _, all_rows = read_agent_session_rows()

    if runtime_filter:
        flt = runtime_filter.lower().strip()
        all_rows = [r for r in all_rows if r.get("runtime", "").lower().strip() == flt]

    health_warnings: list[str] = []
    seen_session_ids: dict[str, list[dict]] = {}

    for r in all_rows:
        sid = r.get("session_id", "").strip()
        if sid:
            seen_session_ids.setdefault(sid, []).append(r)

    duplicate_session_groups = {sid: rows for sid, rows in seen_session_ids.items() if len(rows) > 1}
    if duplicate_session_groups:
        total_snapshot_rows = sum(len(rows) for rows in duplicate_session_groups.values())
        health_warnings.append(
            f"Detected {len(duplicate_session_groups)} session_id group(s) with {total_snapshot_rows} cumulative snapshot rows. "
            + ("Totals include all snapshot rows (--include-snapshots passed; overcount warning)."
               if include_snapshots else
               "Default mode: using latest snapshot per session_id to prevent cumulative overcounting.")
        )

    # Determine aggregated targets: deduplicated vs all snapshot rows
    if include_snapshots:
        target_rows = all_rows
    else:
        deduped: dict[tuple[str, str], dict] = {}
        for r in all_rows:
            rt = r.get("runtime", "unknown")
            sid = r.get("session_id", "").strip()
            key = (rt, sid if sid else r.get("session_run_id", ""))
            deduped[key] = r
        target_rows = list(deduped.values())

    runtimes_cg: dict[str, dict] = {}
    runtimes_raw: dict[str, dict] = {}
    row_confidence_breakdown: dict[str, int] = {}
    session_unit_confidence_breakdown: dict[str, int] = {}

    missing_model_count = 0
    missing_cost_count = 0
    missing_timestamps_count = 0
    blank_tokens_count = 0
    legacy_runtime_count = 0

    # Inspect all CSV rows for health metadata
    for r in all_rows:
        rt = r.get("runtime", "unknown")
        if rt in AGENT_SESSION_LEGACY_RUNTIME:
            legacy_runtime_count += 1

        conf = r.get("confidence", "unknown")
        row_confidence_breakdown[conf] = row_confidence_breakdown.get(conf, 0) + 1

        model_lbl = r.get("model_label", "").strip()
        if not model_lbl:
            missing_model_count += 1

        if not r.get("started_at") or not r.get("ended_at"):
            missing_timestamps_count += 1

        cost = calculate_billing_estimate(r)
        if cost is None:
            missing_cost_count += 1

        in_tok = _safe_int(r.get("actual_input_tokens"))
        out_tok = _safe_int(r.get("actual_output_tokens"))
        tot_tok = _safe_int(r.get("total_tokens"))
        if tot_tok == 0 and (in_tok + out_tok) == 0:
            blank_tokens_count += 1

    # Aggregations for common_ground and provider_native totals (session unit level)
    overall_work_done = 0
    overall_context_pressure = 0
    overall_billable_cost = 0.0
    overall_has_unknown_cost = False

    for r in target_rows:
        rt = r.get("runtime", "unknown")
        conf = r.get("confidence", "unknown")

        session_unit_confidence_breakdown[conf] = session_unit_confidence_breakdown.get(conf, 0) + 1

        in_tok = _safe_int(r.get("actual_input_tokens"))
        cw_tok = _safe_int(r.get("actual_cache_creation_tokens"))
        cr_tok = _safe_int(r.get("actual_cache_read_tokens"))
        out_tok = _safe_int(r.get("actual_output_tokens"))
        rs_tok = _safe_int(r.get("actual_reasoning_tokens"))
        tot_tok = _safe_int(r.get("total_tokens"))
        cost = calculate_billing_estimate(r)

        work_done = in_tok + out_tok + rs_tok
        context_pressure = in_tok + cr_tok

        # Common ground by runtime
        if rt not in runtimes_cg:
            runtimes_cg[rt] = {
                "session_count": 0,
                "row_count": 0,
                "work_done_tokens": 0,
                "context_pressure_tokens": 0,
                "billable_estimate_usd": 0.0,
                "has_unknown_cost": False,
                "confidence_breakdown": {},
            }
        cg = runtimes_cg[rt]
        cg["session_count"] += 1
        cg["work_done_tokens"] += work_done
        cg["context_pressure_tokens"] += context_pressure
        cg["confidence_breakdown"][conf] = cg["confidence_breakdown"].get(conf, 0) + 1

        if cost is not None:
            cg["billable_estimate_usd"] += cost
        else:
            cg["has_unknown_cost"] = True

        # Overall common ground
        overall_work_done += work_done
        overall_context_pressure += context_pressure
        if cost is not None:
            overall_billable_cost += cost
        else:
            overall_has_unknown_cost = True

        # Raw totals by runtime (for target snapshot set)
        if rt not in runtimes_raw:
            runtimes_raw[rt] = {
                "raw_input_tokens": 0,
                "raw_cache_creation_tokens": 0,
                "raw_cache_read_tokens": 0,
                "raw_output_tokens": 0,
                "raw_reasoning_tokens": 0,
                "raw_total_tokens": 0,
            }
        raw = runtimes_raw[rt]
        raw["raw_input_tokens"] += in_tok
        raw["raw_cache_creation_tokens"] += cw_tok
        raw["raw_cache_read_tokens"] += cr_tok
        raw["raw_output_tokens"] += out_tok
        raw["raw_reasoning_tokens"] += rs_tok
        raw["raw_total_tokens"] += tot_tok

    # Count total rows matching each runtime
    for r in all_rows:
        rt = r.get("runtime", "unknown")
        if rt in runtimes_cg:
            runtimes_cg[rt]["row_count"] += 1

    # Format billing estimates
    for rt, cg in runtimes_cg.items():
        if cg["has_unknown_cost"] and cg["billable_estimate_usd"] == 0.0:
            cg["billable_estimate_usd"] = None
            cg["billable_estimate_formatted"] = "N/A (model/pricing unknown)"
            health_warnings.append(f"Runtime '{rt}' includes sessions with unknown model pricing.")
        elif cg["has_unknown_cost"]:
            cg["billable_estimate_usd"] = round(cg["billable_estimate_usd"], 6)
            cg["billable_estimate_formatted"] = f"${cg['billable_estimate_usd']:.2f}+ (partial)"
        else:
            cg["billable_estimate_usd"] = round(cg["billable_estimate_usd"], 6)
            cg["billable_estimate_formatted"] = f"${cg['billable_estimate_usd']:.2f}"

    if overall_has_unknown_cost and overall_billable_cost == 0.0:
        overall_billable_val = None
        overall_billable_fmt = "N/A (model/pricing unknown)"
    elif overall_has_unknown_cost:
        overall_billable_val = round(overall_billable_cost, 6)
        overall_billable_fmt = f"${overall_billable_cost:.2f}+ (partial)"
    else:
        overall_billable_val = round(overall_billable_cost, 6)
        overall_billable_fmt = f"${overall_billable_cost:.2f}"

    # Task outcomes reading & summary
    outcomes_payload = {"total_outcomes_count": 0, "by_runtime": {}}
    try:
        from operator_telemetry_common import TASK_OUTCOME_CSV_PATH, read_task_outcome_rows
        if TASK_OUTCOME_CSV_PATH.exists():
            _out_header, out_rows = read_task_outcome_rows()
            outcomes_payload["total_outcomes_count"] = len(out_rows)
            for orow in out_rows:
                ort = orow.get("runtime", "unknown")
                if ort not in outcomes_payload["by_runtime"]:
                    outcomes_payload["by_runtime"][ort] = {
                        "outcome_count": 0,
                        "source_chars": 0,
                        "record_apply_updated_count": 0,
                        "closure_edges_updated_count": 0,
                    }
                op = outcomes_payload["by_runtime"][ort]
                op["outcome_count"] += 1
                op["source_chars"] += _safe_int(orow.get("source_chars"))
                op["record_apply_updated_count"] += _safe_int(orow.get("record_apply_updated_count"))
                op["closure_edges_updated_count"] += _safe_int(orow.get("closure_edges_updated_count"))
    except Exception:
        pass

    raw_totals_key = "provider_native_all_snapshot_totals" if include_snapshots else "provider_native_latest_snapshot_totals"

    data_payload = {
        "aggregation_mode": "include_snapshots" if include_snapshots else "deduplicated_latest",
        "common_ground": {
            "overall": {
                "session_count": len(target_rows),
                "row_count": len(all_rows),
                "work_done_tokens": overall_work_done,
                "context_pressure_tokens": overall_context_pressure,
                "billable_estimate_usd": overall_billable_val,
                "billable_estimate_formatted": overall_billable_fmt,
                "confidence_breakdown": session_unit_confidence_breakdown,
            },
            "by_runtime": runtimes_cg,
        },
        "task_outcomes": outcomes_payload,
        raw_totals_key: {
            "by_runtime": runtimes_raw,
        },
        "health": {
            "duplicate_session_ids_count": len(duplicate_session_groups),
            "cumulative_snapshot_rows_count": sum(len(v) for v in duplicate_session_groups.values()),
            "blank_tokens_count": blank_tokens_count,
            "legacy_runtime_alias_count": legacy_runtime_count,
            "missing_model_label_count": missing_model_count,
            "missing_timestamps_count": missing_timestamps_count,
            "missing_cost_count": missing_cost_count,
            "session_confidence_breakdown": session_unit_confidence_breakdown,
            "row_confidence_breakdown": row_confidence_breakdown,
        },
    }

    if verbose:
        data_payload["runtime_details"] = target_rows

    envelope = {
        "schema_version": 1,
        "ok": True,
        "command": "summarize_agent_telemetry.py",
        "data": data_payload,
        "warnings": health_warnings,
        "errors": [],
    }
    return envelope


def print_text_report(envelope: dict, verbose: bool = False) -> None:
    data = envelope["data"]
    cg_overall = data["common_ground"]["overall"]
    cg_runtimes = data["common_ground"]["by_runtime"]
    raw_totals_key = "provider_native_all_snapshot_totals" if "provider_native_all_snapshot_totals" in data else "provider_native_latest_snapshot_totals"
    raw_runtimes = data[raw_totals_key]["by_runtime"]
    health = data["health"]

    print("=" * 78)
    print("OPERATOR TELEMETRY SESSION SUMMARY — AUTHORITATIVE COMMON GROUND")
    print("=" * 78)
    print(f"Total rows in CSV: {cg_overall['row_count']}")
    print(f"Aggregated session units: {cg_overall['session_count']}")
    print(f"Aggregation mode: {data['aggregation_mode']}")
    if data['aggregation_mode'] == 'include_snapshots':
        print("WARNING: Aggregating all snapshot rows includes cumulative token counts.")
    print("")

    print("1. COMMON GROUND COMPARISON (DEFAULT CROSS-RUNTIME PRODUCTIVITY METRICS)")
    print("-" * 78)
    print(f"{'Runtime':<12} | {'Work Done (In+Out+Think)':<25} | {'Context Pressure (In+CacheRead)':<30} | {'Billing Est.':<12}")
    print("-" * 78)
    for rt, cg in cg_runtimes.items():
        work_str = f"{cg['work_done_tokens']:,}"
        ctx_str = f"{cg['context_pressure_tokens']:,}"
        cost_str = cg['billable_estimate_formatted']
        print(f"{rt:<12} | {work_str:<25} | {ctx_str:<30} | {cost_str:<12}")
    print("-" * 78)
    work_ov = f"{cg_overall['work_done_tokens']:,}"
    ctx_ov = f"{cg_overall['context_pressure_tokens']:,}"
    cost_ov = cg_overall['billable_estimate_formatted']
    print(f"{'OVERALL':<12} | {work_ov:<25} | {ctx_ov:<30} | {cost_ov:<12}")
    print("-" * 78)
    print("  * Work Done = Fresh Input + Output + Reasoning (excludes cache-read multiplication).")
    print("  * Context Pressure = Fresh Input + Cache Reads (measures multi-turn context accumulation).")
    print("")

    header_mode_label = "ALL SNAPSHOT ROWS" if data['aggregation_mode'] == 'include_snapshots' else "LATEST SNAPSHOT PER SESSION"
    print(f"2. PROVIDER-NATIVE TOTALS (PRESERVED EVIDENCE — {header_mode_label})")
    print("-" * 78)
    for rt, raw in raw_runtimes.items():
        cg = cg_runtimes.get(rt, {})
        print(f"Runtime: {rt} ({cg.get('session_count', 0)} session unit(s), {cg.get('row_count', 0)} row(s))")
        print(f"  Raw Total Tokens:        {raw['raw_total_tokens']:,}")
        print(f"  Breakdown:")
        print(f"    - Input Tokens:        {raw['raw_input_tokens']:,}")
        print(f"    - Cache Read Tokens:   {raw['raw_cache_read_tokens']:,}")
        print(f"    - Cache Creation:      {raw['raw_cache_creation_tokens']:,}")
        print(f"    - Output Tokens:       {raw['raw_output_tokens']:,}")
        print(f"    - Reasoning Tokens:    {raw['raw_reasoning_tokens']:,}")
        print("-" * 78)

    print("\n3. TELEMETRY HEALTH & QUALITY REPORT")
    print("-" * 78)
    print(f"  Duplicate session_id groups: {health['duplicate_session_ids_count']} ({health['cumulative_snapshot_rows_count']} rows)")
    print(f"  Blank token rows:            {health['blank_tokens_count']}")
    print(f"  Legacy runtime aliases:      {health['legacy_runtime_alias_count']}")
    print(f"  Missing model labels:        {health['missing_model_label_count']}")
    print(f"  Missing timestamps:          {health['missing_timestamps_count']}")
    print(f"  Missing costs:               {health['missing_cost_count']}")
    print("  Session Confidence Breakdown (Aggregated Session Units):")
    for conf, cnt in sorted(health["session_confidence_breakdown"].items()):
        print(f"    - {conf}: {cnt}")
    print("  Row Confidence Breakdown (Raw CSV Rows):")
    for conf, cnt in sorted(health["row_confidence_breakdown"].items()):
        print(f"    - {conf}: {cnt}")

    if envelope["warnings"]:
        print("\nHealth & Operational Warnings:")
        for w in envelope["warnings"]:
            print(f"  * {w}")
    else:
        print("\nAll health checks passed cleanly.")
    print("=" * 78)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Output summary in strict JSON format.")
    parser.add_argument("--runtime", help="Filter summary for a specific runtime.")
    parser.add_argument("--include-snapshots", "--all-rows", dest="include_snapshots", action="store_true",
                        help="Include all cumulative snapshot rows in totals (overcount warning).")
    parser.add_argument("--verbose", action="store_true", help="Print extra details.")
    args = parser.parse_args()

    envelope = summarize_telemetry(
        runtime_filter=args.runtime,
        include_snapshots=args.include_snapshots,
        verbose=args.verbose,
    )

    if args.json:
        print(json.dumps(envelope, indent=2))
    else:
        print_text_report(envelope, verbose=args.verbose)

    return 0


if __name__ == "__main__":
    sys.exit(main())
