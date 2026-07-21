"""Cross-project scan for open questions and pending actions: a single place
to see everything still waiting on M2, across every project at once, instead
of opening each project's m2_input/project_risk/project_metrics separately.

Scope, deliberately stopped short of turning a raw signal into a scheduled
event (that's still a judgment call - see m2-timeline SKILL.md, "Deriving
action items from project state"):

- m2_input: any round still pending (no answer yet) -> its question text is
  itself an open item waiting on M2.
- project_risk: the latest row's "План действий" cell, if non-empty -> an
  open action with its own Owner/Следующий review already attached.
- project_metrics: any row whose value is "Неизвестно" or blank -> an open
  clarification gap (the row's Пояснение usually already says what's
  missing and from whom).

For each candidate this script proposes one action_items-shaped row
(Проект, Дата события, Тип, Что нужно сделать, Статус=Открыто, Owner,
Источник, Комментарии). It tags Источник as "scan:<kind>:<key>" and skips
any candidate whose tag already exists in that project's action_items (open
or closed) - so a rerun after M2 has processed a candidate doesn't re-surface
it. Choosing a REAL Тип (e.g. upgrading a metric-clarification candidate to
"Встреча" when it genuinely needs a live 1:1, per m2-timeline's "schedule a
1:1 to clarify" pattern) and a realistic Дата события for m2_input/metrics
candidates (their proposed date is a placeholder, not a real deadline) is
still M2's call - this script's dates/wording are a starting point, not a
finished row.

Default mode is read-only: prints candidates grouped by project and writes
a review bundle to _System/reviews/open_questions/YYYY-MM-DD.md. Pass
--write to also append new candidates into each project's action_items
Sheet (creating it if missing); run refresh_timeline_registry.py afterward
to fold them into _timeline.
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path
from typing import Any

from m2_workspace_layout import DOC_MIME, SHEET_MIME, ensure_document_folder, find_document

sys.path.insert(0, str(Path(__file__).parent))
from google_api_smoke_test import ensure_utf8_stdout
from pipeline_common import get_pending_round_questions, get_services
from sync_m2_source_docs_to_sheets import ROOT_FOLDER_ID, drive_query, find_sheet_in_folder, q_escape, read_sheet_values, upsert_sheet

FOLDER_MIME = "application/vnd.google-apps.folder"
DOC_MIME = "application/vnd.google-apps.document"
ACTION_ITEMS_HEADER = ["Проект", "Дата события", "Тип", "Что нужно сделать", "Статус", "Owner", "Источник", "Комментарии"]
DEFAULT_ROOT = Path(r"G:\My Drive\QA_Management")
REVIEW_ROOT = DEFAULT_ROOT / "_System" / "reviews" / "open_questions"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--project", help="Scan only this project; default is every active project.")
    parser.add_argument(
        "--write",
        action="store_true",
        help="Also append new candidates into each project's action_items Sheet (creating it if missing). "
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


def find_doc(services: dict[str, Any], folder_id: str, title: str) -> dict[str, Any] | None:
    matches = drive_query(
        services["drive"],
        f"'{folder_id}' in parents and name = '{q_escape(title)}' and mimeType = '{DOC_MIME}' and trashed = false",
        fields="id,name",
    )
    return matches[0] if matches else None


def scan_m2_input(services: dict[str, Any], project_folder_id: str, project: str) -> list[dict[str, str]]:
    doc = find_document(
        services["drive"], project_folder_id, "m2_input", "m2_input", DOC_MIME
    )
    if not doc:
        return []
    questions = get_pending_round_questions(services["docs"], doc["id"])
    if not questions:
        return []
    today = dt.date.today().isoformat()
    return [{
        "project": project,
        "due": today,
        "type": "Follow-up",
        "what": "Ответить на вопросы m2_input (раунд ещё не закрыт)",
        "owner": "M2",
        "source": "scan:m2_input:pending",
        "notes": questions[:300],
    }]


def scan_project_risk(services: dict[str, Any], project_folder_id: str, project: str) -> list[dict[str, str]]:
    sheet = find_document(
        services["drive"], project_folder_id, "project_risk", "project_risk", SHEET_MIME
    )
    if not sheet:
        return []
    rows = read_sheet_values(services, sheet["id"])
    if len(rows) <= 1:
        return []
    last = rows[-1]

    def cell(idx: int) -> str:
        return last[idx].strip() if len(last) > idx and last[idx] else ""

    action_plan = cell(8)
    if not action_plan:
        return []
    owner = cell(9) or "M2"
    next_review = cell(10)
    snapshot = cell(1)
    due = next_review if next_review[:4].isdigit() and len(next_review) >= 8 else ""
    notes = f"Следующий review (as written): {next_review}" if next_review and not due else ""
    return [{
        "project": project,
        "due": due or snapshot or dt.date.today().isoformat(),
        "type": "Дедлайн",
        "what": action_plan,
        "owner": owner,
        "source": f"scan:project_risk:{snapshot or 'latest'}",
        "notes": notes,
    }]


def scan_project_metrics(services: dict[str, Any], project_folder_id: str, project: str) -> list[dict[str, str]]:
    sheet = find_document(
        services["drive"], project_folder_id, "project_metrics", "project_metrics", SHEET_MIME
    )
    if not sheet:
        return []
    rows = read_sheet_values(services, sheet["id"])
    today = dt.date.today().isoformat()
    candidates = []
    for row in rows[1:]:
        if len(row) < 3:
            continue
        metric = row[2].strip() if row[2] else ""
        value = row[3].strip() if len(row) > 3 and row[3] else ""
        explanation = row[4].strip() if len(row) > 4 and row[4] else ""
        if not metric or value not in ("", "Неизвестно"):
            continue
        candidates.append({
            "project": project,
            "due": today,
            "type": "Follow-up",
            "what": f"Уточнить: {metric}",
            "owner": "M2",
            "source": f"scan:project_metrics:{metric}",
            "notes": explanation[:300],
        })
    return candidates


def existing_sources(services: dict[str, Any], project_folder_id: str) -> set[str]:
    sheet = find_document(
        services["drive"], project_folder_id, "action_items", "action_items", SHEET_MIME
    )
    if not sheet:
        return set()
    rows = read_sheet_values(services, sheet["id"])
    return {row[6].strip() for row in rows[1:] if len(row) > 6 and row[6]}


def main() -> int:
    ensure_utf8_stdout()
    args = parse_args()
    services = get_services(args.credentials, args.token)
    drive = services["drive"]

    m2_root = find_folder(drive, ROOT_FOLDER_ID, "20_M2_Project_Management")
    if not m2_root:
        print("20_M2_Project_Management folder not found under the workspace root.")
        return 1

    if args.project:
        projects = [args.project]
    else:
        projects = sorted(
            f["name"]
            for f in drive_query(
                drive,
                f"'{m2_root['id']}' in parents and mimeType = '{FOLDER_MIME}' and trashed = false",
                fields="id,name",
            )
            if not f["name"].startswith("_")
        )

    by_project: dict[str, list[dict[str, str]]] = {}
    for project in projects:
        pf = find_folder(drive, m2_root["id"], project)
        if not pf:
            print(f"{project}: folder not found, skipped")
            continue
        candidates = (
            scan_m2_input(services, pf["id"], project)
            + scan_project_risk(services, pf["id"], project)
            + scan_project_metrics(services, pf["id"], project)
        )
        already = existing_sources(services, pf["id"])
        new_candidates = [c for c in candidates if c["source"] not in already]
        if new_candidates:
            by_project[project] = new_candidates

    if not by_project:
        print("No new open questions/actions found.")
        return 0

    today = dt.date.today().isoformat()
    lines = [f"# Open questions / candidate actions — {today}", ""]
    for project, candidates in sorted(by_project.items()):
        print(f"===== {project} =====")
        lines.append(f"## {project}")
        for c in candidates:
            print(f"  [{c['type']}] {c['what']} (owner={c['owner']}, due={c['due']}) — {c['source']}")
            note = f" — {c['notes']}" if c["notes"] else ""
            lines.append(f"- [{c['type']}] **{c['what']}** (owner: {c['owner']}, предложенная дата: {c['due']}){note}")
        lines.append("")

    lines.append(
        "Next step: for each item, confirm/adjust Тип, Owner, and Дата события (these are "
        "mechanical placeholders, not real judgment — e.g. upgrade a clarification candidate to "
        "`Встреча` if it genuinely needs a scheduled 1:1), then log it via the m2-timeline skill. "
        "Pass --write to this script to append them into action_items directly instead."
    )
    REVIEW_ROOT.mkdir(parents=True, exist_ok=True)
    bundle_path = REVIEW_ROOT / f"{today}.md"
    bundle_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nReview bundle: {bundle_path}")

    if args.write:
        for project, candidates in by_project.items():
            pf = find_folder(drive, m2_root["id"], project)
            if pf is None:
                continue
            sheet = find_document(
                drive, pf["id"], "action_items", "action_items", SHEET_MIME
            )
            existing_rows = read_sheet_values(services, sheet["id"]) if sheet else [ACTION_ITEMS_HEADER]
            new_rows = [
                [c["project"], c["due"], c["type"], c["what"], "Открыто", c["owner"], c["source"], c["notes"]]
                for c in candidates
            ]
            target = ensure_document_folder(drive, pf["id"], "action_items")
            upsert_sheet(services, target["id"], "action_items", existing_rows + new_rows)
            print(f"{project}: {len(new_rows)} candidate(s) written to action_items")
        print("Run refresh_timeline_registry.py to fold these into _timeline.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
