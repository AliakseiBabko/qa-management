"""Parse a person card (the structured HRM-style block M2 pastes in
conversation - Job Title/M-level/Prof.Level/Mentor/DC) and apply the Person
Card Intake field mapping (see google-workspace-rules.md, Person Card
Intake) to _people_registry.

Scope, deliberately mechanical only (see m2-admin-note-intake SKILL.md):
this script does the part that's the same every time - parse fields, find
the existing row (by email), compute Role/Internal rank/Notes per the
documented mapping, and show the diff. It does NOT check for contradictions
against a project's individual_metrics/individual_development_plan (e.g.
the AQA-vs-manual-track pattern, m2-role-rules.md Вклад в проект
Calibration) - that needs reading project docs, which this script doesn't
touch. Flag those by hand after running this.

Default is a dry run (prints the parsed fields and the diff against the
existing row, writes nothing). Pass --apply to actually update the Sheet.

Usage: write the card to a UTF-8 file and pass --file <path>. Prefer this
over piping through stdin/a shell heredoc - on this Windows setup, a bash
heredoc silently drops the Cyrillic half of the name (confirmed while
building this script: --file preserved a Cyrillic full name correctly, a
heredoc with the identical text came back with an empty name_cyrillic and
no error). stdin is still accepted as a fallback, but verify the
name_cyrillic field in the printed output actually came through non-empty
before trusting the rest of a stdin-fed run.

    python apply_person_card.py --file card.txt
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))
from google_api_smoke_test import ensure_utf8_stdout
from pipeline_common import (
    PR_EMAIL,
    PR_FIRST_COMMERCIAL,
    PR_M1,
    PR_NAME_EN,
    PR_NAME_RU,
    PR_NOTES,
    PR_PROJECT,
    PR_RANK,
    PR_ROLE,
    PR_SIDE,
    PR_WORKER_ID,
    get_people_registry_sheet,
    get_services,
    reformat_sheet,
)
from show_project_state import find_doc, find_folder
from sync_m2_source_docs_to_sheets import (
    ROOT_FOLDER_ID,
    drive_query,
    find_or_create_folder,
    find_sheet_in_folder,
    read_sheet_values,
)

RECOGNIZED_M_LEVELS = {"M1", "M2", "M3", "M4"}
RECOGNIZED_RANKS = {"Junior", "Middle", "Senior", "Middle+", "Middle-", "Junior+", "Senior+"}
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
LABELS = ["Job Title", "M-level", "Prof.Level", "Mentor", "DC"]
# Optional - not every card states this, and unlike LABELS its absence is not
# an error (see newcomer-support-rules.md: ask rather than guess when a card
# doesn't say, don't treat missing as "Нет").
OPTIONAL_LABELS = ["First commercial project"]
LEVEL_KEYWORDS = ("Senior", "Middle", "Junior")

# Set this to your own company's email domain (see google-workspace-rules.md,
# _people_registry Columns, Side) - used to tell internal staff apart from
# client-side people by email domain alone.
COMPANY_EMAIL_DOMAIN = "example.com"
COMPANY_SIDE_LABEL = "Internal"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--file", help="Read the card from this file instead of stdin.")
    parser.add_argument("--apply", action="store_true", help="Write the change to _people_registry (default: dry run).")
    parser.add_argument(
        "--company-domain",
        default=COMPANY_EMAIL_DOMAIN,
        help="Override the company email domain used for the Side check, "
        "without editing this tracked file (see AGENTS.md, No Sensitive Data In This Repository).",
    )
    parser.add_argument(
        "--company-side-label",
        default=COMPANY_SIDE_LABEL,
        help="Override the Side value written for internal people, to match whatever label "
        "your own _people_registry already uses (e.g. your real company name).",
    )
    parser.add_argument("--credentials", default=".local/google/credentials.json")
    parser.add_argument("--token", default=".local/google/token.json")
    return parser.parse_args()


def parse_card(text: str) -> dict[str, str]:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    email_match = None
    email_line_idx = None
    for i, line in enumerate(lines):
        m = EMAIL_RE.search(line)
        if m:
            email_match = m.group(0)
            email_line_idx = i
            break
    if email_match is None or email_line_idx is None:
        raise ValueError("No email found in card text.")

    name_line = " ".join(lines[:email_line_idx]) if email_line_idx else ""
    latin = " ".join(re.findall(r"[A-Za-z]+", name_line))
    cyrillic = " ".join(re.findall(r"[А-Яа-яЁё]+", name_line))

    fields: dict[str, str] = {"email": email_match, "name_latin": latin, "name_cyrillic": cyrillic}
    rest = lines[email_line_idx + 1 :]
    i = 0
    while i < len(rest) - 1:
        label = rest[i]
        if label in LABELS or label in OPTIONAL_LABELS:
            fields[label] = rest[i + 1]
            i += 2
        else:
            i += 1
    missing = [l for l in LABELS if l not in fields]
    if missing:
        raise ValueError(f"Card missing expected field(s): {missing}. Parsed so far: {fields}")
    return fields


def compute_role(job_title: str, m_level: str, dc: str) -> str:
    prefixes = []
    if m_level in RECOGNIZED_M_LEVELS:
        prefixes.append(m_level)
    if dc.strip().lower() == "yes":
        prefixes.append("DC")
    return "; ".join([*prefixes, job_title]) if prefixes else job_title


def compute_internal_rank(prof_level: str) -> str:
    return prof_level if prof_level in RECOGNIZED_RANKS else ""


def compute_first_commercial_project(fields: dict[str, str]) -> str:
    """Да/Нет only when the card actually states it; blank (not "Нет") when
    the card is silent - see newcomer-support-rules.md, don't guess."""
    value = fields.get("First commercial project")
    if value is None:
        return ""
    return "Да" if value.strip().lower() == "yes" else "Нет"


def compute_notes(fields: dict[str, str], today: str) -> str:
    parts = [f"Подтверждено карточкой M2 ({today}): Job Title {fields['Job Title']}"]
    if fields["M-level"] not in RECOGNIZED_M_LEVELS:
        parts.append(f"M-level {fields['M-level']} (значение не подтверждено)")
    parts.append(f"Prof.Level {fields['Prof.Level']}" + (
        " (нестандартное значение шкалы)" if fields["Prof.Level"] not in RECOGNIZED_RANKS else ""
    ))
    parts.append(f"Mentor: {'Да' if fields['Mentor'].lower() == 'yes' else 'Нет'}")
    parts.append(f"DC: {'Да' if fields['DC'].lower() == 'yes' else 'Нет'}")
    first_commercial = compute_first_commercial_project(fields)
    if first_commercial:
        parts.append(f"Первый коммерческий проект: {first_commercial}")
    return ", ".join(parts) + "."


def find_row_by_email(body: list[list[str]], email: str, email_col: int = PR_EMAIL) -> list[str] | None:
    for row in body:
        if len(row) > email_col and row[email_col].strip().lower() == email.strip().lower():
            return row
    return None


def scan_track_level_mismatch(
    services: Any,
    m2_root_id: str,
    projects: list[str],
    name_ru: str,
    name_en: str,
    confirmed_job_title: str,
    confirmed_rank: str,
) -> list[str]:
    """Heads-up only, not a resolution: grep a person's individual_metrics/
    individual_development_plan (across their confirmed Project(s)) for
    seniority/track language that doesn't match the card, the way several
    real track/level mismatches were each found by hand before this script
    existed (see m2-role-rules.md, Вклад в проект Calibration). Does not
    fetch anything if projects is empty - there's nowhere to look.

    Known limitation (confirmed while building this): only scans the
    Project(s) currently listed on the registry row. A person moved off a
    project (Project(s) updated to reflect that) leaves their mismatch
    evidence behind in the old project's docs, invisible to this scan -
    confirmed by testing against a real case where a mismatch lived on a
    project the person had since moved off; the scan came back clean,
    which was wrong for their actual history. Don't treat a clean scan as
    proof there's no mismatch for someone who's changed projects recently
    - check their prior project(s) by hand if that applies.
    """
    drive = services["drive"]
    wanted_tokens = set(re.findall(r"[A-Za-zА-Яа-яЁё]+", f"{name_ru} {name_en}".casefold()))
    flags: list[str] = []
    for project in projects:
        project_folder = find_folder(drive, m2_root_id, project)
        if not project_folder:
            continue
        people_folder = find_folder(drive, project_folder["id"], "people")
        if not people_folder:
            continue
        for person_folder in drive_query(
            drive,
            f"'{people_folder['id']}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false",
            fields="id,name",
        ):
            folder_tokens = set(re.findall(r"[A-Za-zА-Яа-яЁё]+", person_folder["name"].casefold()))
            if not (folder_tokens & wanted_tokens):
                continue

            blob_parts: list[str] = []
            im_sheet = find_sheet_in_folder(drive, person_folder["id"], "individual_metrics")
            if im_sheet:
                rows = read_sheet_values(services, im_sheet["id"])
                blob_parts.append(" ".join(" ".join(r) for r in rows))
            idp = find_doc(services, person_folder["id"], "individual_development_plan")
            if idp:
                doc = services["docs"].documents().get(documentId=idp["id"]).execute()
                blob_parts.append("".join(
                    run.get("textRun", {}).get("content", "")
                    for el in doc["body"]["content"]
                    if "paragraph" in el
                    for run in el["paragraph"]["elements"]
                ))
            blob = " ".join(blob_parts)

            for level_kw in LEVEL_KEYWORDS:
                if level_kw in blob and not confirmed_rank.startswith(level_kw):
                    flags.append(
                        f"{project}/{person_folder['name']}: mentions '{level_kw}' but confirmed "
                        f"Prof.Level is '{confirmed_rank or '(none)'}'."
                    )
            if "MQA" in blob and "aqa" in confirmed_job_title.casefold():
                flags.append(
                    f"{project}/{person_folder['name']}: mentions 'MQA' track but confirmed Job Title "
                    f"is '{confirmed_job_title}'."
                )
            if "QA Lead" in blob and "lead" not in confirmed_job_title.casefold():
                flags.append(
                    f"{project}/{person_folder['name']}: mentions 'QA Lead' expectations but confirmed "
                    f"Job Title is '{confirmed_job_title}' (no Lead)."
                )
    return flags


def main() -> int:
    ensure_utf8_stdout()
    args = parse_args()
    raw = Path(args.file).read_text(encoding="utf-8") if args.file else sys.stdin.read()
    fields = parse_card(raw)
    today = dt.date.today().isoformat()

    side = (
        args.company_side_label
        if fields["email"].lower().endswith(f"@{args.company_domain}")
        else f"ASK - not an @{args.company_domain} address"
    )
    role = compute_role(fields["Job Title"], fields["M-level"], fields["DC"])
    internal_rank = compute_internal_rank(fields["Prof.Level"])
    notes = compute_notes(fields, today)
    first_commercial = compute_first_commercial_project(fields)

    print("Parsed card:")
    for key in ("name_latin", "name_cyrillic", "email", *LABELS):
        print(f"  {key}: {fields[key]!r}")
    for key in OPTIONAL_LABELS:
        if key in fields:
            print(f"  {key}: {fields[key]!r}")
    print()
    print("Computed registry fields:")
    print(f"  Side:          {side}")
    print(f"  Role:          {role}")
    print(f"  Internal rank: {internal_rank!r} {'(non-standard Prof.Level, kept out of this column)' if not internal_rank and fields['Prof.Level'] else ''}")
    print(f"  Notes:         {notes}")
    print(f"  Первый коммерческий проект: {first_commercial!r} "
          f"{'(not stated on card - ask rather than leave silently blank once staffed)' if not first_commercial else ''}")
    print()

    services = get_services(args.credentials, args.token)
    drive = services["drive"]
    m2_root = find_or_create_folder(drive, ROOT_FOLDER_ID, "20_M2_Project_Management")
    people_sheet = get_people_registry_sheet(services)
    rows = read_sheet_values(services, people_sheet["id"])
    header, body = rows[0], rows[1:]

    existing = find_row_by_email(body, fields["email"])
    if existing:
        print(f"Existing row found (matched by email): {existing}")
        print()
        print("This script does not auto-write over an existing row's Name/Project(s) - those need human")
        print("judgment (see Person Card Intake, and the Project(s) rule in google-workspace-rules.md).")
        print("Review the computed Role/Internal rank/Notes above against the existing row and edit by hand,")
        print("or extend this script's --apply path if this becomes a common enough case to automate safely.")
        print()
        projects = [p.strip() for p in existing[PR_PROJECT].split(",")] if len(existing) > PR_PROJECT and existing[PR_PROJECT] else []
        if not projects:
            print("Project(s) is blank on the existing row - skipping track/level mismatch scan (nowhere to look).")
        else:
            print(f"Scanning {', '.join(projects)} individual_metrics/individual_development_plan for mismatches...")
            flags = scan_track_level_mismatch(
                services, m2_root["id"], projects, existing[PR_NAME_RU], existing[PR_NAME_EN], fields["Job Title"], fields["Prof.Level"]
            )
            if flags:
                print("HEADS UP - possible track/level mismatch worth checking by hand (not auto-resolved):")
                for flag in flags:
                    print(f"  - {flag}")
            else:
                print("No obvious track/level mismatch found in that person's project documents.")
    else:
        print("No existing row found for this email - this looks like a new person.")
        new_row = [""] * len(header)
        new_row[PR_NAME_RU] = fields["name_cyrillic"]
        new_row[PR_NAME_EN] = fields["name_latin"]
        new_row[PR_EMAIL] = fields["email"]
        new_row[PR_SIDE] = side
        new_row[PR_ROLE] = role
        new_row[PR_RANK] = internal_rank
        new_row[PR_NOTES] = notes
        new_row[PR_FIRST_COMMERCIAL] = first_commercial
        print(f"Would add row: {new_row}")
        if args.apply:
            body.append(new_row)
            title = services["sheets"].spreadsheets().get(spreadsheetId=people_sheet["id"]).execute()["sheets"][0]["properties"]["title"]
            services["sheets"].spreadsheets().values().clear(spreadsheetId=people_sheet["id"], range=f"'{title}'").execute()
            services["sheets"].spreadsheets().values().update(
                spreadsheetId=people_sheet["id"], range=f"'{title}'!A1", valueInputOption="RAW",
                body={"values": [header, *body]},
            ).execute()
            reformat_sheet(services, people_sheet["id"], "_people_registry")
            print("Applied: added new row to _people_registry.")
        else:
            print("Dry run - nothing written. Re-run with --apply to add this row.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
