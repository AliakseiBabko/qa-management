"""Update or add one person's row in the living `Светофор рисков` Sheet
(10_M1_People_Management), per m1-people-risk-report's file-contract.

Светофор рисков is a living document - one row per employee, updated in
place, no dated snapshots (see google-workspace-rules.md, M1 Person-Based
Layout, and m1-people-risk-report/references/file-contract.md). This
script is the mechanical write path for that skill, the same role
apply_person_card.py plays for _people_registry: it does not decide risk
levels or write narrative - it takes already-decided field values and
applies them safely (existing-row lookup, in-place update vs. new row,
Дата обновления bookkeeping, risk-scale validation).

Input is a small labeled text block (file or stdin), one label per line,
value continues until the next recognized label:

    Сотрудник: Имя Фамилия
    Риск с нашей стороны: Средний, стабильный. ...
    Риск со стороны сотрудника: Низкий, снижение. ...
    Комментарии: ...
    План действий: ...

Only include the fields you're actually changing when updating an
existing row - omitted fields are left untouched. All four content fields
are required when adding a brand-new row (Комментарии/План действий may
be explicitly empty, but must be present as a label so it's clear that's
intentional, not an oversight).

Default is a dry run (prints the parsed fields and the diff against the
existing row, writes nothing). Pass --apply to actually update the Sheet.

    python update_m1_risk_row.py --file update.txt
    python update_m1_risk_row.py --file update.txt --apply
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))
from google_api_smoke_test import ensure_utf8_stdout
from pipeline_common import get_services
from show_project_state import find_folder
from sync_m2_source_docs_to_sheets import ROOT_FOLDER_ID, find_sheet_in_folder, first_sheet_range, read_sheet_values

M1_FOLDER_NAME = "10_M1_People_Management"
SHEET_TITLE = "Светофор рисков"
HEADER = [
    "Сотрудник",
    "Дата обновления",
    "Риски с нашей стороны (мы недовольны)",
    "Риски со стороны сотрудника (он недоволен)",
    "Комментарии",
    "План действий",
]
VALID_LEVELS = ("Низкий", "Средний", "Высокий")

LABELS = {
    "Сотрудник": "person",
    "Риск с нашей стороны": "our_risk",
    "Риск со стороны сотрудника": "their_risk",
    "Комментарии": "comments",
    "План действий": "action_plan",
    "Дата обновления": "updated_date",
}


def parse_update(text: str) -> dict[str, str]:
    lines = text.splitlines()
    fields: dict[str, str] = {}
    current_key: str | None = None
    buffer: list[str] = []

    def flush() -> None:
        if current_key is not None:
            fields[current_key] = "\n".join(buffer).strip()

    for line in lines:
        matched = None
        for label, key in LABELS.items():
            prefix = f"{label}:"
            if line.strip().startswith(prefix):
                matched = (key, line.strip()[len(prefix) :].strip())
                break
        if matched:
            flush()
            current_key, first_value = matched
            buffer = [first_value] if first_value else []
        elif current_key is not None:
            buffer.append(line)
    flush()

    if "person" not in fields or not fields["person"]:
        raise ValueError("Update text must include a 'Сотрудник:' line naming who this row is for.")
    return fields


def validate_level(field_name: str, value: str) -> None:
    if not value:
        return
    level = value.split(",", 1)[0].strip()
    if level not in VALID_LEVELS:
        raise ValueError(
            f"{field_name} starts with '{level}', not one of {VALID_LEVELS}. "
            f"Светофор рисков uses a 3-level scale, no 'Критический' — see "
            f"m1-people-risk-report/references/file-contract.md, Risk Level Scale. "
            f"Remap the level (an acute/materialized situation is still Высокий) "
            f"rather than writing a 4th level."
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--file", help="Read the update block from this file instead of stdin.")
    parser.add_argument("--apply", action="store_true", help="Write the change to Светофор рисков (default: dry run).")
    parser.add_argument("--credentials", default=".local/google/credentials.json")
    parser.add_argument("--token", default=".local/google/token.json")
    return parser.parse_args()


def main() -> int:
    ensure_utf8_stdout()
    args = parse_args()
    raw = Path(args.file).read_text(encoding="utf-8") if args.file else sys.stdin.read()
    fields = parse_update(raw)

    for field_name, key in (("Риск с нашей стороны", "our_risk"), ("Риск со стороны сотрудника", "their_risk")):
        if key in fields:
            validate_level(field_name, fields[key])

    services = get_services(args.credentials, args.token)
    drive = services["drive"]
    sheets = services["sheets"]

    m1_root = find_folder(drive, ROOT_FOLDER_ID, M1_FOLDER_NAME)
    if not m1_root:
        print(f"{M1_FOLDER_NAME} folder not found under the workspace root.")
        return 1
    sheet = find_sheet_in_folder(drive, m1_root["id"], SHEET_TITLE)
    if not sheet:
        print(f"'{SHEET_TITLE}' Sheet not found under {M1_FOLDER_NAME} — create it from Templates\\светофор_рисков.csv first.")
        return 1

    rows = read_sheet_values(services, sheet["id"])
    if not rows or rows[0] != HEADER:
        print("WARNING: Sheet header doesn't match the expected schema. Found:", rows[0] if rows else None)
        print("Expected:", HEADER)
        return 1

    person = fields["person"]
    row_idx = next((i for i, r in enumerate(rows) if r and r[0] == person), None)
    today = dt.date.today().isoformat()

    if row_idx is None:
        missing = [f for f in ("our_risk", "their_risk", "comments", "action_plan") if f not in fields]
        if missing:
            print(f"No existing row for '{person}' — this is a new person, so all fields are required.")
            print(f"Missing: {missing}. Add explicit labels (empty value is fine) for each.")
            return 1
        new_row = [
            person,
            fields.get("updated_date", today),
            fields["our_risk"],
            fields["their_risk"],
            fields["comments"],
            fields["action_plan"],
        ]
        print("No existing row found — would add:")
        print(" ", new_row)
        if args.apply:
            sheet_title, _ = first_sheet_range(sheets, sheet["id"])
            sheets.spreadsheets().values().update(
                spreadsheetId=sheet["id"],
                range=f"'{sheet_title}'!A{len(rows) + 1}",
                valueInputOption="RAW",
                body={"values": [new_row]},
            ).execute()
            print("Applied: added new row.")
        else:
            print("Dry run — nothing written. Re-run with --apply to add this row.")
        return 0

    existing = rows[row_idx]
    while len(existing) < len(HEADER):
        existing.append("")
    updated = list(existing)
    changed = False
    for key, col in (("our_risk", 2), ("their_risk", 3), ("comments", 4), ("action_plan", 5)):
        if key in fields and fields[key] != existing[col]:
            updated[col] = fields[key]
            changed = True
    if changed:
        updated[1] = fields.get("updated_date", today)

    print("Before:", existing)
    print("After: ", updated)
    if not changed:
        print("No content fields differ from the existing row — nothing to update.")
        return 0

    if args.apply:
        sheet_title, _ = first_sheet_range(sheets, sheet["id"])
        sheets.spreadsheets().values().update(
            spreadsheetId=sheet["id"],
            range=f"'{sheet_title}'!A{row_idx + 1}",
            valueInputOption="RAW",
            body={"values": [updated]},
        ).execute()
        print("Applied: updated row in place.")
    else:
        print("Dry run — nothing written. Re-run with --apply to write this update.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
