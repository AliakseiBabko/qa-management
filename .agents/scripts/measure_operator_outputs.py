"""Phase 11 operator telemetry: run a read-only operator command and measure
its output footprint (bytes/chars/deterministic token estimate), without
storing any of the actual output.

Modeled on the erp-web-tests benchmark-playwright-debugging skill's
methodology (see .agents/telemetry/README.md), scaled down: there is no
fix/patch/EQA concept here, only output-size/token measurement for
dashboard/guide/classify/pack/triage/search/show_project_state versus older
full-read workflows.

Usage
-----
  # List available measurement cases
  python .agents/scripts/measure_operator_outputs.py --list

  # Dry run - print what would execute, write nothing (no subprocess call)
  python .agents/scripts/measure_operator_outputs.py --case dashboard_overview --dry-run

  # Real run against a live target (run-id/project/query), local JSON only
  python .agents/scripts/measure_operator_outputs.py --case guide_discovered \\
      --target 20260721-example-run-abc123 --runtime "Claude Code" \\
      --model-label claude-sonnet-5

  # Real run, also append a redacted row to the committed CSV
  python .agents/scripts/measure_operator_outputs.py --case dashboard_overview \\
      --append-csv

Safety
------
- Only cases in operator_telemetry_common.CASES may run; every one of them is
  read-only by construction (no qa_manage.py mutating verb), and argv is
  additionally checked against MUTATING_VERBS before exec as a defense-in-depth
  backstop.
- The resolved --target value is substituted into the argv used to actually
  run the command, but is NEVER written to disk or the CSV - only the
  original `{target}` placeholder form is persisted (command_args_redacted).
- Raw stdout/stderr are held in memory for measurement only. If --keep-raw is
  passed, the raw bytes are written under tmp/telemetry/ (gitignored) for
  local debugging - never committed, never part of the CSV row.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import uuid
from datetime import date, datetime, timezone
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPTS_DIR.parent.parent

sys.path.insert(0, str(SCRIPTS_DIR))
from operator_telemetry_common import (  # noqa: E402
    CASES,
    CSV_HEADER,
    MUTATING_VERBS,
    is_ascii_safe,
)

TMP_TELEMETRY_DIR = REPO_ROOT / "tmp" / "telemetry"


def _extract_result_count(parsed: object) -> int | None:
    if not isinstance(parsed, dict):
        return None
    data = parsed.get("data")
    if not isinstance(data, dict):
        return None
    for key in ("action_required", "items", "discovered", "matches", "commits", "candidates"):
        val = data.get(key)
        if isinstance(val, list):
            return len(val)
    docs = data.get("documents")
    if isinstance(docs, list) and docs and isinstance(docs[0], dict) and "returned_count" in docs[0]:
        return docs[0]["returned_count"]
    return None


def _extract_truncated(parsed: object) -> bool:
    if not isinstance(parsed, dict):
        return False
    data = parsed.get("data")
    if not isinstance(data, dict):
        return False
    if data.get("truncated") is True:
        return True
    docs = data.get("documents")
    if isinstance(docs, list):
        return any(isinstance(d, dict) and d.get("truncated") for d in docs)
    return False


def build_argv(case_id: str, case: dict, target: str | None) -> tuple[list[str], list[str]]:
    """Returns (redacted_argv, real_argv). redacted_argv keeps the literal
    `{target}` placeholder; real_argv substitutes the resolved target value.
    Only redacted_argv is ever written to disk."""
    template = case["argv"]
    requires_target = case.get("requires_target")
    if requires_target and not target:
        raise SystemExit(
            f"Case '{case_id}' requires --target <{requires_target}> to run for real. "
            "Use --dry-run to inspect the case without a target."
        )
    redacted = list(template)
    real = [t.replace("{target}", target) if target and "{target}" in t else t for t in template]
    return redacted, real


def assert_read_only(real_argv: list[str]) -> None:
    for token in real_argv:
        if token in MUTATING_VERBS:
            raise SystemExit(
                f"Refusing to run: argv token '{token}' matches a mutating qa_manage.py verb. "
                "measure_operator_outputs.py only runs read-only cases."
            )


def run_case(case_id: str, target: str | None, keep_raw: bool) -> dict:
    case = CASES[case_id]
    redacted_argv, real_argv = build_argv(case_id, case, target)
    assert_read_only(real_argv)

    full_argv = [sys.executable, str(SCRIPTS_DIR / real_argv[0]), *real_argv[1:]]

    start = time.perf_counter()
    proc = subprocess.run(full_argv, capture_output=True, cwd=str(REPO_ROOT))
    elapsed_ms = round((time.perf_counter() - start) * 1000)

    stdout_bytes = len(proc.stdout)
    stderr_bytes = len(proc.stderr)
    stdout_text = proc.stdout.decode("utf-8", errors="replace")
    output_chars = len(stdout_text)
    preview_chars = min(200, output_chars)

    json_mode = bool(case.get("json_mode"))
    result_count = None
    truncated = False
    status = "ok" if proc.returncode == 0 else "error"

    if json_mode and status == "ok":
        try:
            parsed = json.loads(stdout_text)
            result_count = _extract_result_count(parsed)
            truncated = _extract_truncated(parsed)
            if isinstance(parsed, dict) and parsed.get("ok") is False:
                status = "error"
        except json.JSONDecodeError:
            status = "error"

    approximate_output_tokens = output_chars // 4

    row = {
        "command_name": case["command_name"],
        "command_args_redacted": " ".join(redacted_argv),
        "json_mode": "yes" if json_mode else "no",
        "status": status,
        "elapsed_ms": elapsed_ms,
        "stdout_bytes": stdout_bytes,
        "stderr_bytes": stderr_bytes,
        "output_chars": output_chars,
        "preview_chars": preview_chars,
        "result_count": result_count if result_count is not None else "",
        "truncated": "yes" if truncated else "no",
        "approximate_input_tokens": "",
        "approximate_output_tokens": approximate_output_tokens,
        "baseline_command": (
            CASES[case["baseline_of"]]["command_name"] if case.get("baseline_of") else ""
        ),
    }

    if keep_raw:
        TMP_TELEMETRY_DIR.mkdir(parents=True, exist_ok=True)
        raw_path = TMP_TELEMETRY_DIR / f"{case_id}-{uuid.uuid4().hex[:8]}.raw.txt"
        raw_path.write_text(stdout_text, encoding="utf-8")
        print(f"(local only, gitignored) raw stdout kept at {raw_path}")

    return row


def write_run_note(run_id: str, case_id: str, row: dict) -> Path:
    TMP_TELEMETRY_DIR.mkdir(parents=True, exist_ok=True)
    note_path = TMP_TELEMETRY_DIR / f"{run_id}.md"
    lines = [
        f"# Operator telemetry run note: {run_id}",
        "",
        f"- case_id: {case_id}",
        f"- command_name: {row['command_name']}",
        f"- command_args_redacted: {row['command_args_redacted']}",
        f"- status: {row['status']}",
        f"- elapsed_ms: {row['elapsed_ms']}",
        f"- output_chars: {row['output_chars']}",
        f"- result_count: {row['result_count']}",
        f"- truncated: {row['truncated']}",
        f"- approximate_output_tokens: {row['approximate_output_tokens']}",
        "",
        "(local-only note under tmp/telemetry/ - gitignored, never committed)",
        "",
    ]
    note_path.write_text("\n".join(lines), encoding="utf-8")
    return note_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--case", choices=sorted(CASES), help="Measurement case to run.")
    parser.add_argument("--target", help="Live target value (run_id / project / query) to substitute for {target}. Never written to disk.")
    parser.add_argument("--runtime", default="manual_script", choices=["Codex", "Claude Code", "Antigravity", "manual_script"])
    parser.add_argument("--model-label", default="")
    parser.add_argument("--run-id", default=None, help="Defaults to '<case_id>-<date>-<short-uuid>'.")
    parser.add_argument("--dry-run", action="store_true", help="Print the case config; run nothing, write nothing.")
    parser.add_argument("--append-csv", action="store_true", help="Append a row to operator-runs.csv after measuring.")
    parser.add_argument("--keep-raw", action="store_true", help="Also write raw stdout to tmp/telemetry/ (gitignored, local only).")
    parser.add_argument("--list", action="store_true", help="List available case_ids and exit.")
    parser.add_argument("--json", action="store_true", help="Print the measured row as JSON to stdout.")
    args = parser.parse_args()

    if args.list:
        for cid, c in sorted(CASES.items()):
            req = f" (requires --target <{c['requires_target']}>)" if c.get("requires_target") else ""
            print(f"{cid}: {c['command_name']}{req}")
        return 0

    if not args.case:
        parser.error("--case is required (or use --list)")

    case = CASES[args.case]

    target = args.target
    telemetry_run_id = args.run_id
    if not target and args.run_id and case.get("requires_target") == "run_id":
        target = args.run_id
        telemetry_run_id = None

    if args.dry_run:
        redacted_argv, _ = build_argv(args.case, case, target or (f"<{case.get('requires_target')}>" if case.get("requires_target") else None))
        print(f"[dry-run] case={args.case}")
        print(f"[dry-run] command_name={case['command_name']}")
        print(f"[dry-run] would run: {' '.join(redacted_argv)}")
        print(f"[dry-run] json_mode={case.get('json_mode', False)}")
        print(f"[dry-run] baseline_of={case.get('baseline_of')}")
        print("[dry-run] no subprocess executed, nothing written.")
        return 0

    run_id = telemetry_run_id or f"{args.case}-{date.today().isoformat()}-{uuid.uuid4().hex[:8]}"
    row = run_case(args.case, target, args.keep_raw)

    for field in ("command_args_redacted", "notes", "notes_file"):
        val = row.get(field, "")
        if val and not is_ascii_safe(val):
            raise SystemExit(
                f"Refusing to record: field '{field}' failed the ASCII-safe redaction check "
                "(possible real-data leak). Value was not written anywhere."
            )

    full_row = {
        "case_id": args.case,
        "run_id": run_id,
        "date": date.today().isoformat(),
        "runtime": args.runtime,
        "model_label": args.model_label,
        "reduction_ratio_vs_baseline": "",
        "actual_input_tokens": "",
        "actual_cache_creation_tokens": "",
        "actual_cache_read_tokens": "",
        "actual_output_tokens": "",
        "actual_reasoning_tokens": "",
        "total_tokens": "",
        "estimated_cost_usd": "",
        "notes_file": "",
        "notes": "",
        **row,
    }

    note_path = write_run_note(run_id, args.case, row)
    full_row["notes_file"] = str(note_path.relative_to(REPO_ROOT)).replace("\\", "/")

    if args.json:
        print(json.dumps(full_row, ensure_ascii=True, indent=2))
    else:
        print(f"run_id={run_id} status={row['status']} elapsed_ms={row['elapsed_ms']} "
              f"output_chars={row['output_chars']} approx_output_tokens={row['approximate_output_tokens']} "
              f"result_count={row['result_count']} truncated={row['truncated']}")
        print(f"Run note (local, gitignored): {note_path}")

    if args.append_csv:
        from operator_telemetry_common import append_row
        append_row(full_row)
        print("Appended row to .agents/telemetry/operator-runs.csv")

    return 0 if row["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
