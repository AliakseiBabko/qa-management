"""Cross-team scan for upcoming/overdue M1 events: a single place to see
every Performance Review date, missing OKR, and missing monthly report
across the whole team, instead of opening each person's OKR Doc or the
monthly-report folder by hand.

Scope, deliberately stopped short of drafting the actual OKR or report
content (that's still a judgment/drafting step - see m1-timeline SKILL.md,
"Deriving events from team state"):

- OKR Doc titles: every person with a `<Person> 1to1` Sheet directly under
  10_M1_People_Management is expected to have an `OKR к Perfomance review
  DD.MM.YY` Doc in their `10_M1_People_Management\\<Person>\\` folder (see
  m1-individual-development-plan). The most recent such Doc's date is
  surfaced as a Performance Review event; a person with no OKR Doc at all
  is surfaced as its own "missing OKR" candidate.
- PR cadence cross-check: `_people_registry` (under 20_M2_Project_Management,
  see google-workspace-rules.md) holds `Дата трудоустройства` and `Дата
  последнего PR` per person. This script computes the expected next PR date
  from those two fields per the real cadence rules in
  qa-management-roles/references/performance-review-rules.md (last PR + 6
  months, or hire date + 3 months if no PR has happened yet) and cross-checks
  it against the OKR Doc title date. A mismatch, or a missing OKR Doc when a
  registry-computed date exists, is surfaced with the registry-computed date
  used as the due date - so tracking survives even before an OKR Doc exists.
- Monthly report presence: `m1_monthly_report_<Manager>_YYYY-MM` Sheets
  directly under 10_M1_People_Management are inventoried by manager; if the
  most recently completed calendar month has no report for a manager who
  has filed one before, that's surfaced as an overdue candidate.

For each candidate this script proposes one _m1_timeline-shaped row
(Сотрудник, Дата события, Тип, Что нужно сделать, Статус=Открыто, Owner,
Источник, Комментарии). It tags Источник as "scan:<kind>:<key>" and skips
any candidate whose tag already exists in _m1_timeline - so a rerun after
M1 has processed a candidate doesn't re-surface it. The proposed dates are
a starting point, not a finished row - confirming whether a PR actually
happened, or the report deadline is genuinely still open, is still M1's
call.

Default mode is read-only: prints candidates and writes a review bundle to
80_Exports/open_questions_review/YYYY-MM-DD_m1.md. Pass --write to also
append new candidates into _m1_timeline (creating it if missing); no
separate refresh step is needed since, unlike m2-timeline, this is a
single flat Sheet, not a per-project Sheet plus rollup.
"""

from __future__ import annotations

import argparse
import calendar
import datetime as dt
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))
from google_api_smoke_test import ensure_utf8_stdout
from pipeline_common import get_services
from sync_m2_source_docs_to_sheets import ROOT_FOLDER_ID, drive_query, find_sheet_in_folder, q_escape, read_sheet_values, upsert_sheet

FOLDER_MIME = "application/vnd.google-apps.folder"
DOC_MIME = "application/vnd.google-apps.document"
SHEET_MIME = "application/vnd.google-apps.spreadsheet"
TIMELINE_HEADER = ["Сотрудник", "Дата события", "Тип", "Что нужно сделать", "Статус", "Owner", "Источник", "Комментарии"]
DEFAULT_ROOT = Path(r"G:\My Drive\QA_Management")
REVIEW_ROOT = DEFAULT_ROOT / "80_Exports" / "open_questions_review"

OKR_DOC_PREFIX = "OKR к Perfomance review "
MONTHLY_REPORT_RE = re.compile(r"^m1_monthly_report_(?P<manager>.+)_(?P<month>\d{4}-\d{2})(?:_v\d+)?$")

# _people_registry column indices (see google-workspace-rules.md, _people_registry Columns):
# Name (RU), Name (EN), Email, Side, Role, Internal rank, Project(s), Notes,
# Дата трудоустройства, Дата последнего PR
REGISTRY_NAME_RU_COL = 0
REGISTRY_NAME_EN_COL = 1
REGISTRY_HIRE_DATE_COL = 8
REGISTRY_LAST_PR_COL = 9
PR_CADENCE_MONTHS = 6
PROBATION_MONTHS = 3


def parse_iso_date(value: str) -> dt.date | None:
    value = (value or "").strip()
    if not value:
        return None
    try:
        return dt.date.fromisoformat(value)
    except ValueError:
        return None


def add_months(date: dt.date, months: int) -> dt.date:
    month_index = date.month - 1 + months
    year = date.year + month_index // 12
    month = month_index % 12 + 1
    day = min(date.day, calendar.monthrange(year, month)[1])
    return dt.date(year, month, day)


def expected_next_pr(hire_date: dt.date | None, last_pr_date: dt.date | None) -> tuple[dt.date | None, str]:
    """Per performance-review-rules.md, "Deriving Expected Next PR Date":
    last PR + 6 months if a PR has happened, else hire date + 3 months for
    the first (probation-closing) PR, else unknown."""
    if last_pr_date is not None:
        return add_months(last_pr_date, PR_CADENCE_MONTHS), "last_pr+6mo"
    if hire_date is not None:
        return add_months(hire_date, PROBATION_MONTHS), "hire+3mo(probation)"
    return None, "unknown"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--person", help="Scan OKR events only for this person; default is the whole team.")
    parser.add_argument(
        "--write",
        action="store_true",
        help="Also append new candidates into _m1_timeline (creating it if missing). "
        "Default is read-only (print + bundle file only).",
    )
    parser.add_argument("--credentials", default=".local/google/credentials.json")
    parser.add_argument("--token", default=".local/google/token.json")
    return parser.parse_args()


def find_folder(drive: Any, parent_id: str, name: str) -> dict[str, Any] | None:
    matches = drive_query(
        drive,
        f"'{parent_id}' in parents and name = '{q_escape(name)}' and mimeType = '{FOLDER_MIME}' and trashed = false",
        fields="id,name",
    )
    return matches[0] if matches else None


def load_people_registry(services: dict[str, Any], drive: Any) -> dict[str, dict[str, dt.date | None]]:
    """Return {normalized name -> {"hire": date|None, "last_pr": date|None}},
    keyed under both Name (RU) and Name (EN) so a lookup by whichever name
    10_M1_People_Management uses still finds the row."""
    m2_root = find_folder(drive, ROOT_FOLDER_ID, "20_M2_Project_Management")
    if not m2_root:
        print("20_M2_Project_Management folder not found — skipping PR-cadence cross-check.")
        return {}
    sheet = find_sheet_in_folder(drive, m2_root["id"], "_people_registry")
    if not sheet:
        print("_people_registry not found — skipping PR-cadence cross-check.")
        return {}

    rows = read_sheet_values(services, sheet["id"])
    lookup: dict[str, dict[str, dt.date | None]] = {}
    for row in rows[1:]:
        if not row:
            continue

        def cell(idx: int) -> str:
            return row[idx].strip() if len(row) > idx and row[idx] else ""

        record = {
            "hire": parse_iso_date(cell(REGISTRY_HIRE_DATE_COL)),
            "last_pr": parse_iso_date(cell(REGISTRY_LAST_PR_COL)),
        }
        for name in (cell(REGISTRY_NAME_RU_COL), cell(REGISTRY_NAME_EN_COL)):
            if name:
                lookup[name.strip().casefold()] = record
    return lookup


def find_person_roster(drive: Any, m1_root_id: str) -> list[str]:
    sheets = drive_query(
        drive,
        f"'{m1_root_id}' in parents and mimeType = '{SHEET_MIME}' and trashed = false and name contains ' 1to1'",
        fields="id,name",
    )
    return sorted({s["name"][: -len(" 1to1")] for s in sheets if s["name"].endswith(" 1to1")})


def parse_okr_date(title: str) -> dt.date | None:
    if not title.startswith(OKR_DOC_PREFIX):
        return None
    date_str = title[len(OKR_DOC_PREFIX) :].strip()
    try:
        return dt.datetime.strptime(date_str, "%d.%m.%y").date()
    except ValueError:
        return None


def scan_person_okr(
    drive: Any, m1_root_id: str, person: str, registry: dict[str, dict[str, dt.date | None]]
) -> list[dict[str, str]]:
    person_folder = find_folder(drive, m1_root_id, person)
    docs: list[dict[str, Any]] = []
    if person_folder:
        docs = drive_query(
            drive,
            f"'{person_folder['id']}' in parents and mimeType = '{DOC_MIME}' and trashed = false "
            f"and name contains '{q_escape(OKR_DOC_PREFIX.strip())}'",
            fields="id,name",
        )

    dated = [(parse_okr_date(d["name"]), d["name"]) for d in docs]
    dated = [(date, name) for date, name in dated if date is not None]
    doc_date, doc_name = max(dated, key=lambda pair: pair[0]) if dated else (None, None)

    record = registry.get(person.strip().casefold(), {})
    expected_date, basis = expected_next_pr(record.get("hire"), record.get("last_pr"))

    if doc_date is None and expected_date is None:
        return [{
            "person": person,
            "due": dt.date.today().isoformat(),
            "type": "OKR",
            "what": f"Составить OKR для {person} — текущий OKR Doc не найден, и в _people_registry "
            "нет ни «Дата трудоустройства», ни «Дата последнего PR» для расчёта ожидаемой даты PR",
            "owner": "M1",
            "source": f"scan:okr:{person}:missing",
            "notes": "",
        }]

    if doc_date is None:
        # No OKR Doc yet, but the registry lets us compute an expected PR date anyway.
        return [{
            "person": person,
            "due": expected_date.isoformat(),
            "type": "OKR",
            "what": f"Составить OKR для {person} — OKR Doc не найден; ожидаемый Performance Review "
            f"~{expected_date.isoformat()} (расчёт: {basis})",
            "owner": "M1",
            "source": f"scan:okr:{person}:missing",
            "notes": f"Расчёт из _people_registry ({basis})",
        }]

    mismatch = (
        expected_date is not None and abs((expected_date - doc_date).days) > 14
    )
    due = doc_date
    overdue = doc_date < dt.date.today()
    what = (
        f"Performance Review для {person} прошёл ({doc_date.isoformat()}) — подтвердить, что PR "
        "проведён и OKR закрыт (у каждого KR проставлен статус/результат), затем открыть новый цикл "
        "и обновить «Дата последнего PR» в _people_registry"
        if overdue
        else f"Проверить готовность OKR к Performance Review {person} — все KR должны быть закрыты "
        "(статус/результат) до этой даты"
    )
    notes = f"Doc: {doc_name}"
    if mismatch:
        notes += (
            f"; расхождение с расчётом из _people_registry: ожидалось ~{expected_date.isoformat()} "
            f"({basis}), в Doc указано {doc_date.isoformat()} — свериться, какая дата верна"
        )
    return [{
        "person": person,
        "due": due.isoformat(),
        "type": "Performance Review",
        "what": what,
        "owner": "M1",
        "source": f"scan:okr:{person}:{doc_date.isoformat()}",
        "notes": notes,
    }]


def previous_reporting_month(today: dt.date) -> str:
    first_of_this_month = today.replace(day=1)
    last_month_end = first_of_this_month - dt.timedelta(days=1)
    return f"{last_month_end.year:04d}-{last_month_end.month:02d}"


def scan_monthly_reports(drive: Any, m1_root_id: str) -> list[dict[str, str]]:
    sheets = drive_query(
        drive,
        f"'{m1_root_id}' in parents and mimeType = '{SHEET_MIME}' and trashed = false "
        "and name contains 'm1_monthly_report_'",
        fields="id,name",
    )
    by_manager: dict[str, set[str]] = {}
    for s in sheets:
        match = MONTHLY_REPORT_RE.match(s["name"])
        if not match:
            continue
        by_manager.setdefault(match.group("manager"), set()).add(match.group("month"))

    if not by_manager:
        return []

    target_month = previous_reporting_month(dt.date.today())
    candidates = []
    for manager, months in sorted(by_manager.items()):
        if target_month in months:
            continue
        candidates.append({
            "person": f"M1: {manager}",
            "due": dt.date.today().isoformat(),
            "type": "Monthly report",
            "what": f"Заполнить m1_monthly_report за {target_month} для {manager} "
            "(включая пункт «Работа с ОКР» — нужны реальные подтверждения OKR-активности за месяц)",
            "owner": manager,
            "source": f"scan:monthly_report:{manager}:{target_month}",
            "notes": f"Известные отчёты: {', '.join(sorted(months)) or 'нет'}",
        })
    return candidates


def existing_sources(drive: Any, services: dict[str, Any], m1_root_id: str) -> set[str]:
    sheet = find_sheet_in_folder(drive, m1_root_id, "_m1_timeline")
    if not sheet:
        return set()
    rows = read_sheet_values(services, sheet["id"])
    return {row[6].strip() for row in rows[1:] if len(row) > 6 and row[6]}


def main() -> int:
    ensure_utf8_stdout()
    args = parse_args()
    services = get_services(args.credentials, args.token)
    drive = services["drive"]

    m1_root = find_folder(drive, ROOT_FOLDER_ID, "10_M1_People_Management")
    if not m1_root:
        print("10_M1_People_Management folder not found under the workspace root.")
        return 1

    if args.person:
        roster = [args.person]
    else:
        roster = find_person_roster(drive, m1_root["id"])
        if not roster:
            print("No '<Person> 1to1' Sheets found directly under 10_M1_People_Management — nothing to scan.")

    registry = load_people_registry(services, drive)

    candidates: list[dict[str, str]] = []
    for person in roster:
        candidates.extend(scan_person_okr(drive, m1_root["id"], person, registry))
    if not args.person:
        candidates.extend(scan_monthly_reports(drive, m1_root["id"]))

    already = existing_sources(drive, services, m1_root["id"])
    new_candidates = [c for c in candidates if c["source"] not in already]

    if not new_candidates:
        print("No new M1 events found.")
        return 0

    today = dt.date.today().isoformat()
    lines = [f"# M1 upcoming/overdue events — {today}", ""]
    for c in new_candidates:
        print(f"[{c['type']}] {c['person']}: {c['what']} (owner={c['owner']}, due={c['due']}) — {c['source']}")
        note = f" — {c['notes']}" if c["notes"] else ""
        lines.append(f"- [{c['type']}] **{c['person']}** — {c['what']} (owner: {c['owner']}, дата: {c['due']}){note}")

    lines.append(
        ""
        "Next step: confirm each candidate against the actual OKR Doc/monthly report state "
        "(these dates are a starting point, not a finished row — see m1-timeline SKILL.md, "
        "\"Deriving events from team state\"), then log it via the m1-timeline skill. "
        "Pass --write to this script to append them into _m1_timeline directly instead."
    )
    REVIEW_ROOT.mkdir(parents=True, exist_ok=True)
    bundle_path = REVIEW_ROOT / f"{today}_m1.md"
    bundle_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nReview bundle: {bundle_path}")

    if args.write:
        existing_sheet = find_sheet_in_folder(drive, m1_root["id"], "_m1_timeline")
        existing_rows = read_sheet_values(services, existing_sheet["id"]) if existing_sheet else [TIMELINE_HEADER]
        new_rows = [
            [c["person"], c["due"], c["type"], c["what"], "Открыто", c["owner"], c["source"], c["notes"]]
            for c in new_candidates
        ]
        upsert_sheet(services, m1_root["id"], "_m1_timeline", existing_rows + new_rows)
        print(f"_m1_timeline: {len(new_rows)} candidate(s) written")

    return 0


if __name__ == "__main__":
    sys.exit(main())
