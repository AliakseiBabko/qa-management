"""Phase 11 operator telemetry: validate .agents/telemetry/operator-runs.csv.

Checks header match, required fields, numeric fields, enum values, no
malformed rows, and a best-effort leak guard (ASCII-only redacted-args/notes
fields - see operator_telemetry_common.is_ascii_safe). Modeled on the
erp-web-tests benchmark skill's check_csv.py, scaled to this CSV's simpler
append-only (no in-place row update) model.

Usage
-----
  python .agents/scripts/check_operator_csv.py
  python .agents/scripts/check_operator_csv.py --diff-guard --run-id <run_id>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))
from operator_telemetry_common import (  # noqa: E402
    CSV_HEADER,
    CSV_PATH,
    diff_guard_new_row_only,
    read_rows,
    validate_row,
)


def validate_csv() -> bool:
    if not CSV_PATH.exists():
        print(f"Error: CSV not found: {CSV_PATH}", file=sys.stderr)
        return False

    raw = CSV_PATH.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        print("Error: CSV contains a UTF-8 BOM. Use plain UTF-8.", file=sys.stderr)
        return False
    try:
        raw.decode("utf-8")
    except UnicodeDecodeError as e:
        print(f"Error: CSV is not valid UTF-8: {e}", file=sys.stderr)
        return False

    header, rows = read_rows()
    if header != CSV_HEADER:
        print("Error: CSV schema drift detected.", file=sys.stderr)
        missing = set(CSV_HEADER) - set(header)
        extra = set(header) - set(CSV_HEADER)
        if missing:
            print(f"  Missing columns: {sorted(missing)}", file=sys.stderr)
        if extra:
            print(f"  Extra columns: {sorted(extra)}", file=sys.stderr)
        return False

    print(f"CSV header ({len(CSV_HEADER)} columns) matches canonical schema.")

    errors = []
    seen_run_ids: dict[str, int] = {}
    for i, row in enumerate(rows):
        line_num = i + 2  # +1 header, +1 to 1-index
        run_id = row.get("run_id")
        if not run_id:
            errors.append(f"Line {line_num}: missing run_id.")
        elif run_id in seen_run_ids:
            errors.append(f"Line {line_num}: duplicate run_id '{run_id}' (first seen at line {seen_run_ids[run_id]}).")
        else:
            seen_run_ids[run_id] = line_num

        row_errors = validate_row(row)
        for err in row_errors:
            errors.append(f"Line {line_num} ({run_id or '<missing>'}): {err}")

    if errors:
        print("\n--- CSV validation errors ---", file=sys.stderr)
        for e in errors:
            print(f" - {e}", file=sys.stderr)
        print(f"\nTotal errors: {len(errors)}", file=sys.stderr)
        return False

    print(f"Success: {len(rows)} row(s), no errors found.")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--diff-guard", action="store_true", help="Assert the working CSV only added --run-id's row vs --ref.")
    parser.add_argument("--run-id", help="Target run_id (required with --diff-guard).")
    parser.add_argument("--ref", default="HEAD", help="Git ref to compare against (default: HEAD).")
    args = parser.parse_args()

    if args.diff_guard:
        if not args.run_id:
            parser.error("--diff-guard requires --run-id")
        ok, violations = diff_guard_new_row_only(args.run_id, args.ref)
        if not ok:
            print(f"\n--- Diff guard FAILED (ref={args.ref}, target run_id={args.run_id}) ---", file=sys.stderr)
            for v in violations:
                print(f" - {v}", file=sys.stderr)
            return 1
        print(f"Diff guard OK: only '{args.run_id}' changed vs {args.ref}.")
        return 0

    return 0 if validate_csv() else 1


if __name__ == "__main__":
    sys.exit(main())
