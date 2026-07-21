"""Detect new project-level M2 "_strategy" chat exports, parse Google Chat
message timestamps, log them to evidence_log, and write a review bundle for
M2 to read.

Scope, deliberately stopped at the same judgment boundary as
prepare_intake_review.py (see m2-role-rules.md, Project-Level Rollups and
Pipeline Architecture):

- scans 00_Inbox recursively for files matching
  "<project>_strategy*.txt" (case-insensitive) not already logged in that
  project's evidence_log by filename
- classifies the project by the literal prefix before "_strategy" in the
  filename, matched against _project_registry; ambiguous/unmatched files are
  left UNCLASSIFIED, not guessed
- parses Google Chat's copy-paste message-header format
  ("[N unread, ]Name, Month Day, H:MM AM/PM[, Edited]" for older messages, or
  "[N unread, ]Name, Weekday H:MM AM/PM[, Edited]" - no comma before the
  time - for recent ones) to resolve the date range of messages in the file.
  Google Chat headers carry no year and use relative weekday-only
  timestamps for recent messages, so this resolves dates against the
  file's local mtime as an anchor (assumes messages are never dated after
  the file was saved) - a heuristic, not a guarantee; a file edited long
  after the messages were sent will resolve wrong.
- appends one evidence_log row per new file per project
  (source_type=strategy_chat, routed_to="pending M2 review", notes carry the
  resolved date range and any unresolved header lines)
- writes a review bundle markdown summarizing what's new

It does NOT extract facts, apply corrections, or touch m2_input/
project_risk/project_development_plan/_people_registry - by design, this
repo keeps judgment-level updates conversational (see README, "Current
pipeline scripts"). Read the review bundle, then run the
m2-strategy-chat-analysis skill's conversational workflow for anything worth
acting on.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))
from google_api_smoke_test import build_services, ensure_utf8_stdout, load_credentials
from pipeline_common import reformat_sheet
from prepare_intake_review import already_logged_sources, source_tail
from sync_m2_source_docs_to_sheets import (
    ROOT_FOLDER_ID,
    find_or_create_folder,
    find_sheet_in_folder,
    merge_evidence,
    read_sheet_values,
)

DEFAULT_ROOT = Path(r"G:\My Drive\QA_Management")
INBOX_ROOT = "00_Inbox"
REVIEW_ROOT = DEFAULT_ROOT / "_System" / "reviews" / "intake"

STRATEGY_FILE_RE = re.compile(r"^(?P<project>.+)_strategy(?:_.*)?\.txt$", re.IGNORECASE)

WEEKDAYS = {
    "mon": 0, "monday": 0, "tue": 1, "tues": 1, "tuesday": 1, "wed": 2, "weds": 2, "wednesday": 2,
    "thu": 3, "thur": 3, "thurs": 3, "thursday": 3, "fri": 4, "friday": 4,
    "sat": 5, "saturday": 5, "sun": 6, "sunday": 6,
}
MONTHS = {
    m.lower(): i
    for i, m in enumerate(
        ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], start=1
    )
}

# Google Chat's copy-paste headers use two structurally different forms:
# absolute dates are comma-separated from the time ("Feb 5, 3:13 PM"), but
# recent/relative weekday-only headers have no comma before the time at all
# ("Fri 11:58 AM") - a single regex with an optional day-number can't cover
# both, since without the comma there's no way to tell where the date part
# ends and the time begins except by trying each shape.
ABS_HEADER_RE = re.compile(
    r"^(?:\d+\s+unread,\s*)?"
    r"(?P<name>[^,]+),\s*"
    r"(?P<month>[A-Za-z]{3,9})\s+(?P<day>\d{1,2}),\s*"
    r"(?P<time>\d{1,2}:\d{2}\s*[AP]M)"
    r"(?:,\s*Edited)?\s*$"
)
REL_HEADER_RE = re.compile(
    r"^(?:\d+\s+unread,\s*)?"
    r"(?P<name>[^,]+),\s*"
    r"(?P<weekday>[A-Za-z]{3,9})\s+"
    r"(?P<time>\d{1,2}:\d{2}\s*[AP]M)"
    r"(?:,\s*Edited)?\s*$"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(DEFAULT_ROOT))
    parser.add_argument("--credentials", default=".local/google/credentials.json")
    parser.add_argument("--token", default=".local/google/token.json")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Scan and classify only; do not write evidence_log or the review bundle.",
    )
    return parser.parse_args()


def load_project_names(services: dict[str, Any]) -> list[str]:
    drive = services["drive"]
    m2_root = find_or_create_folder(drive, ROOT_FOLDER_ID, "20_M2_Project_Management")
    return [
        f["name"]
        for f in drive.files()
        .list(
            q=f"'{m2_root['id']}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false",
            fields="files(name)",
        )
        .execute()
        .get("files", [])
        if not f["name"].startswith("_")
    ]


def classify_project(filename: str, projects: list[str]) -> tuple[str, str]:
    match = STRATEGY_FILE_RE.match(filename)
    if not match:
        return "", "filename does not match '<project>_strategy[...].txt'"
    prefix = match.group("project").casefold()
    for project in projects:
        if project.casefold() == prefix:
            return project, f"filename prefix matches project '{project}' exactly"
    for project in projects:
        if project.casefold() in prefix or prefix in project.casefold():
            return project, f"filename prefix '{match.group('project')}' loosely matches project '{project}'"
    return "", f"filename prefix '{match.group('project')}' does not match any known project"


def resolve_weekday(weekday_name: str, anchor: dt.date) -> dt.date | None:
    target = WEEKDAYS.get(weekday_name.casefold())
    if target is None:
        return None
    for back in range(0, 7):
        candidate = anchor - dt.timedelta(days=back)
        if candidate.weekday() == target:
            return candidate
    return None  # pragma: no cover - unreachable, all 7 weekdays covered above


def resolve_month_day(month_name: str, day: int, anchor: dt.date) -> dt.date | None:
    month = MONTHS.get(month_name.casefold()[:3])
    if month is None:
        return None
    for year in (anchor.year, anchor.year - 1):
        try:
            candidate = dt.date(year, month, day)
        except ValueError:
            continue
        if candidate <= anchor:
            return candidate
    # Both candidate years land after the anchor (e.g. a file saved right at
    # a year boundary) - return the anchor year's date anyway rather than
    # silently dropping the message.
    try:
        return dt.date(anchor.year, month, day)
    except ValueError:
        return None


def is_header_line(line: str) -> bool:
    stripped = line.strip()
    return bool(ABS_HEADER_RE.match(stripped) or REL_HEADER_RE.match(stripped))


def parse_header(line: str, anchor: dt.date) -> dt.date | None:
    stripped = line.strip()
    abs_match = ABS_HEADER_RE.match(stripped)
    if abs_match:
        return resolve_month_day(abs_match.group("month"), int(abs_match.group("day")), anchor)
    rel_match = REL_HEADER_RE.match(stripped)
    if rel_match:
        return resolve_weekday(rel_match.group("weekday"), anchor)
    return None


def scan_file(path: Path) -> dict[str, Any]:
    anchor = dt.date.fromtimestamp(path.stat().st_mtime)
    dates: list[dt.date] = []
    unresolved: list[str] = []
    message_count = 0
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line or not is_header_line(line):
            continue
        message_count += 1
        resolved = parse_header(line, anchor)
        if resolved is None:
            unresolved.append(line)
        else:
            dates.append(resolved)
    return {
        "anchor": anchor,
        "message_count": message_count,
        "min_date": min(dates) if dates else None,
        "max_date": max(dates) if dates else None,
        "unresolved": unresolved,
    }


def main() -> int:
    ensure_utf8_stdout()
    args = parse_args()
    root = Path(args.root)
    today = dt.date.today().isoformat()

    inbox_path = root / INBOX_ROOT
    if not inbox_path.exists():
        print(f"No such folder: {inbox_path}")
        return 0

    strategy_files = [
        path for path in sorted(inbox_path.rglob("*.txt")) if STRATEGY_FILE_RE.match(path.name)
    ]
    if not strategy_files:
        print("No '_strategy' chat files found.")
        return 0

    creds = load_credentials(Path(args.credentials), Path(args.token))
    services = build_services(creds)
    drive = services["drive"]

    projects = load_project_names(services)
    m2_root = find_or_create_folder(drive, ROOT_FOLDER_ID, "20_M2_Project_Management")

    evidence_by_project: dict[str, list[list[str]]] = {}
    projects_with_new_rows: set[str] = set()
    found: list[dict[str, Any]] = []

    for path in strategy_files:
        project, reason = classify_project(path.name, projects)
        relative = path.relative_to(root)

        if project:
            if project not in evidence_by_project:
                pf = find_or_create_folder(drive, m2_root["id"], project)
                sheet = find_sheet_in_folder(drive, pf["id"], "evidence_log")
                evidence_by_project[project] = (
                    read_sheet_values(services, sheet["id"])
                    if sheet
                    else [["date", "source", "source_type", "project", "routed_to", "notes"]]
                )
            if source_tail(str(relative)) in already_logged_sources(evidence_by_project[project]):
                continue
        elif source_tail(str(relative)) in already_logged_sources(
            evidence_by_project.setdefault(
                "_unclassified", [["date", "source", "source_type", "project", "routed_to", "notes"]]
            )
        ):
            continue

        scan = scan_file(path)
        found.append({"path": str(relative), "project": project, "reason": reason, **scan})

    if not found:
        print("No new '_strategy' chat files found.")
        return 0

    print(f"Found {len(found)} new '_strategy' file(s).")
    if args.dry_run:
        for item in found:
            date_range = (
                f"{item['min_date']} .. {item['max_date']}" if item["min_date"] else "no dates resolved"
            )
            print(f"  [{item['project'] or 'UNCLASSIFIED'}] {item['path']} — {date_range} ({item['reason']})")
        return 0

    for item in found:
        date_range = f"{item['min_date']} .. {item['max_date']}" if item["min_date"] else "no dates resolved"
        notes = (
            f"Detected by detect_strategy_chats.py. {item['message_count']} message(s), date range "
            f"{date_range} (resolved against file mtime {item['anchor']} as anchor - heuristic, verify if "
            f"the file was edited well after the messages were sent)."
        )
        if item["unresolved"]:
            notes += f" {len(item['unresolved'])} header line(s) could not be date-parsed."
        row = [today, item["path"], "strategy_chat", item["project"] or "UNCLASSIFIED", "pending M2 review", notes]
        key = item["project"] or "_unclassified"
        evidence_by_project[key] = merge_evidence(evidence_by_project.get(key, []), [row])
        projects_with_new_rows.add(key)

    logged_projects: list[str] = []
    for project in projects:
        if project not in projects_with_new_rows:
            continue
        pf = find_or_create_folder(drive, m2_root["id"], project)
        sheet = find_sheet_in_folder(drive, pf["id"], "evidence_log")
        if sheet:
            services["sheets"].spreadsheets().values().clear(spreadsheetId=sheet["id"], range="A1:F5000").execute()
            services["sheets"].spreadsheets().values().update(
                spreadsheetId=sheet["id"],
                range="A1",
                valueInputOption="RAW",
                body={"values": evidence_by_project[project]},
            ).execute()
            reformat_sheet(services, sheet["id"], "evidence_log")
            logged_projects.append(project)

    REVIEW_ROOT.mkdir(parents=True, exist_ok=True)
    bundle_path = REVIEW_ROOT / f"strategy_chats_{today}.md"
    lines = [f"# Strategy-chat intake review — {today}", ""]
    by_project: dict[str, list[dict[str, Any]]] = {}
    for item in found:
        by_project.setdefault(item["project"] or "UNCLASSIFIED", []).append(item)
    for project, items in sorted(by_project.items()):
        lines.append(f"## {project}")
        for item in items:
            date_range = (
                f"{item['min_date']} .. {item['max_date']}" if item["min_date"] else "no dates resolved"
            )
            lines.append(f"- `{item['path']}` — {item['message_count']} message(s), {date_range} ({item['reason']})")
            if item["unresolved"]:
                lines.append(f"  - {len(item['unresolved'])} unparsed header line(s), e.g. `{item['unresolved'][0]}`")
        lines.append("")
    lines.append(
        "Next step: read the flagged file(s) above using the `m2-strategy-chat-analysis` skill. This script "
        "only detects, date-ranges, and logs new files to evidence_log; it does not extract facts or update "
        "_people_registry/project_risk/project_development_plan/m2_input. UNCLASSIFIED items need manual "
        "routing (confirm the project and rename the file to `<Project>_strategy...txt` if needed)."
    )
    bundle_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Review bundle: {bundle_path}")
    if logged_projects:
        print(f"evidence_log updated for: {', '.join(sorted(logged_projects))}")
    if "UNCLASSIFIED" in by_project:
        print(f"{len(by_project['UNCLASSIFIED'])} file(s) UNCLASSIFIED — needs manual routing.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
