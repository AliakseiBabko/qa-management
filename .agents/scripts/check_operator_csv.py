"""Phase 11 operator telemetry: validate .agents/telemetry/operator-runs.csv
(and, with --sessions, .agents/telemetry/agent-sessions.csv).

Checks header match, required fields, numeric fields, enum values, no
malformed rows, and a best-effort leak guard (ASCII-only redacted-args/notes
fields - see operator_telemetry_common.is_ascii_safe). Modeled on the
erp-web-tests benchmark skill's check_csv.py, scaled to this CSV's simpler
append-only (no in-place row update) model.

Usage
-----
  python .agents/scripts/check_operator_csv.py
  python .agents/scripts/check_operator_csv.py --diff-guard --run-id <run_id>

  python .agents/scripts/check_operator_csv.py --sessions
  python .agents/scripts/check_operator_csv.py --sessions --diff-guard --session-run-id <session_run_id>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))
from operator_telemetry_common import (  # noqa: E402
    AGENT_SESSION_CSV_HEADER,
    AGENT_SESSION_CSV_PATH,
    CSV_HEADER,
    CSV_PATH,
    diff_guard_agent_session_new_row_only,
    diff_guard_new_row_only,
    read_agent_session_rows,
    read_rows,
    validate_agent_session_row,
    validate_row,
)


def _validate_csv(csv_path: Path, canonical_header: list[str], read_fn, validate_fn,
                  id_field: str, label: str) -> bool:
    if not csv_path.exists():
        print(f"Error: CSV not found: {csv_path}", file=sys.stderr)
        return False

    raw = csv_path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        print("Error: CSV contains a UTF-8 BOM. Use plain UTF-8.", file=sys.stderr)
        return False
    try:
        raw.decode("utf-8")
    except UnicodeDecodeError as e:
        print(f"Error: CSV is not valid UTF-8: {e}", file=sys.stderr)
        return False

    header, rows = read_fn()
    if header != canonical_header:
        print(f"Error: {label} CSV schema drift detected.", file=sys.stderr)
        missing = set(canonical_header) - set(header)
        extra = set(header) - set(canonical_header)
        if missing:
            print(f"  Missing columns: {sorted(missing)}", file=sys.stderr)
        if extra:
            print(f"  Extra columns: {sorted(extra)}", file=sys.stderr)
        return False

    print(f"{label} CSV header ({len(canonical_header)} columns) matches canonical schema.")

    errors = []
    seen_ids: dict[str, int] = {}
    for i, row in enumerate(rows):
        line_num = i + 2  # +1 header, +1 to 1-index
        row_id = row.get(id_field)
        if not row_id:
            errors.append(f"Line {line_num}: missing {id_field}.")
        elif row_id in seen_ids:
            errors.append(f"Line {line_num}: duplicate {id_field} '{row_id}' (first seen at line {seen_ids[row_id]}).")
        else:
            seen_ids[row_id] = line_num

        for err in validate_fn(row):
            errors.append(f"Line {line_num} ({row_id or '<missing>'}): {err}")

    if errors:
        print(f"\n--- {label} CSV validation errors ---", file=sys.stderr)
        for e in errors:
            print(f" - {e}", file=sys.stderr)
        print(f"\nTotal errors: {len(errors)}", file=sys.stderr)
        return False

    print(f"Success: {len(rows)} row(s), no errors found.")
    return True


def validate_csv() -> bool:
    return _validate_csv(CSV_PATH, CSV_HEADER, read_rows, validate_row, "run_id", "operator-runs")


def validate_agent_sessions_csv() -> bool:
    return _validate_csv(AGENT_SESSION_CSV_PATH, AGENT_SESSION_CSV_HEADER, read_agent_session_rows,
                         validate_agent_session_row, "session_run_id", "agent-sessions")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--sessions", action="store_true",
                        help="Validate agent-sessions.csv instead of operator-runs.csv.")
    parser.add_argument("--diff-guard", action="store_true",
                        help="Assert the working CSV only added the target row vs --ref.")
    parser.add_argument("--run-id", help="Target run_id (operator-runs.csv --diff-guard).")
    parser.add_argument("--session-run-id", help="Target session_run_id (agent-sessions.csv --diff-guard).")
    parser.add_argument("--ref", default="HEAD", help="Git ref to compare against (default: HEAD).")
    args = parser.parse_args()

    if args.diff_guard:
        if args.sessions:
            if not args.session_run_id:
                parser.error("--sessions --diff-guard requires --session-run-id")
            ok, violations = diff_guard_agent_session_new_row_only(args.session_run_id, args.ref)
            target = args.session_run_id
        else:
            if not args.run_id:
                parser.error("--diff-guard requires --run-id")
            ok, violations = diff_guard_new_row_only(args.run_id, args.ref)
            target = args.run_id
        if not ok:
            print(f"\n--- Diff guard FAILED (ref={args.ref}, target={target}) ---", file=sys.stderr)
            for v in violations:
                print(f" - {v}", file=sys.stderr)
            return 1
        print(f"Diff guard OK: only '{target}' changed vs {args.ref}.")
        return 0

    if args.sessions:
        return 0 if validate_agent_sessions_csv() else 1
    return 0 if validate_csv() else 1


if __name__ == "__main__":
    sys.exit(main())
