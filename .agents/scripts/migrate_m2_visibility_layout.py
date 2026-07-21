"""Audit or apply the M2 visibility-folder migration in Google Drive.

The command never changes sharing permissions. It preserves Drive file IDs,
links, revisions, and existing direct permissions while moving unambiguous
canonical artifacts into private, team_shared, and per-person shared folders.
Unknown files are reported and left in place.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from google_api_smoke_test import ensure_utf8_stdout
from m2_workspace_layout import (
    DOC_MIME,
    FOLDER_MIME,
    PEOPLE_FOLDER,
    PERSON_SHARED_FOLDER,
    PRIVATE_FOLDER,
    SHEET_MIME,
    TEAM_SHARED_FOLDER,
    canonical_folder_parts,
    ensure_folder_path,
    find_child_folder,
    list_children,
    move_item,
)
from pipeline_common import get_services
from sync_m2_source_docs_to_sheets import ROOT_FOLDER_ID


M2_ROOT_NAME = "20_M2_Project_Management"
PROJECT_FILE_ROLES = {
    "project_metrics": ("project_metrics", SHEET_MIME),
    "project_risk": ("project_risk", SHEET_MIME),
    "process_checklist": ("process_checklist", SHEET_MIME),
    "project_development_plan": ("project_development_plan", DOC_MIME),
    "evidence_log": ("evidence_log", SHEET_MIME),
    "action_items": ("action_items", SHEET_MIME),
    "qa_process_metrics": ("qa_process_metrics", SHEET_MIME),
}
PERSON_FILE_ROLES = {
    "individual_metrics": ("individual_metrics", SHEET_MIME),
    "individual_development_plan": ("individual_development_plan", DOC_MIME),
    "individual_metrics_internal": ("individual_metrics_internal", SHEET_MIME),
}


@dataclass(frozen=True)
class PlannedMove:
    project: str
    role: str
    item_id: str
    item_name: str
    source_parent_id: str
    target_parts: tuple[str, ...]
    person: str = ""
    destination: str = "live"


def person_item_role(item: dict[str, Any], person: str) -> str | None:
    for role, (name, mime_type) in PERSON_FILE_ROLES.items():
        if item.get("name") == name and item.get("mimeType") == mime_type:
            return role
    if item.get("mimeType") == SHEET_MIME and item.get("name") == f"{person} 1to1":
        return "m2_people_1to1_file"
    return None


def is_predecessor(name: str, prefix: str) -> bool:
    return bool(re.fullmatch(rf"{re.escape(prefix)}_predecessor_\d{{4}}-\d{{2}}-\d{{2}}", name))


def project_item_role(item: dict[str, Any]) -> str | None:
    for role, (name, mime_type) in PROJECT_FILE_ROLES.items():
        if item.get("name") == name and item.get("mimeType") == mime_type:
            return role
    if item.get("mimeType") == FOLDER_MIME and item.get("name") in {"m2_input", "status_reports"}:
        return str(item["name"])
    return None


def plan_person_folder(
    drive: Any,
    project: dict[str, Any],
    person_folder: dict[str, Any],
) -> tuple[list[PlannedMove], list[dict[str, str]]]:
    moves: list[PlannedMove] = []
    ambiguous: list[dict[str, str]] = []
    person = str(person_folder["name"])
    for item in list_children(drive, person_folder["id"]):
        if item.get("mimeType") == FOLDER_MIME and item.get("name") == "shared":
            continue
        role = person_item_role(item, person)
        if not role:
            if is_predecessor(str(item.get("name", "")), "individual_metrics"):
                moves.append(PlannedMove(
                    project=str(project["name"]),
                    role="individual_metrics_predecessor",
                    item_id=str(item["id"]),
                    item_name=str(item["name"]),
                    source_parent_id=str(person_folder["id"]),
                    target_parts=(PEOPLE_FOLDER, person, PERSON_SHARED_FOLDER),
                    person=person,
                    destination="archive",
                ))
                continue
            ambiguous.append({
                "project": str(project["name"]),
                "person": person,
                "item": str(item.get("name", "")),
                "reason": "unrecognized person artifact",
            })
            continue
        target = canonical_folder_parts(role, person)
        moves.append(PlannedMove(
            project=str(project["name"]),
            role=role,
            item_id=str(item["id"]),
            item_name=str(item["name"]),
            source_parent_id=str(person_folder["id"]),
            target_parts=target,
            person=person,
        ))
    return moves, ambiguous


def plan_project(
    drive: Any,
    project: dict[str, Any],
) -> tuple[list[PlannedMove], list[dict[str, str]]]:
    moves: list[PlannedMove] = []
    ambiguous: list[dict[str, str]] = []
    for item in list_children(drive, project["id"]):
        if item.get("mimeType") == FOLDER_MIME and item.get("name") in {
            PRIVATE_FOLDER, TEAM_SHARED_FOLDER
        }:
            continue
        if item.get("mimeType") == FOLDER_MIME and item.get("name") == PEOPLE_FOLDER:
            for person_folder in list_children(drive, item["id"]):
                if person_folder.get("mimeType") != FOLDER_MIME:
                    ambiguous.append({
                        "project": str(project["name"]),
                        "person": "",
                        "item": str(person_folder.get("name", "")),
                        "reason": "non-folder item under people",
                    })
                    continue
                person_moves, person_ambiguous = plan_person_folder(drive, project, person_folder)
                moves.extend(person_moves)
                ambiguous.extend(person_ambiguous)
            continue
        role = project_item_role(item)
        if not role:
            item_name = str(item.get("name", ""))
            if item_name == "_PROJECT_CONTEXT.md":
                moves.append(PlannedMove(
                    project=str(project["name"]),
                    role="project_context",
                    item_id=str(item["id"]),
                    item_name=item_name,
                    source_parent_id=str(project["id"]),
                    target_parts=(PRIVATE_FOLDER,),
                ))
                continue
            if any(is_predecessor(item_name, prefix) for prefix in ("project_metrics", "project_risk")):
                moves.append(PlannedMove(
                    project=str(project["name"]),
                    role="project_predecessor",
                    item_id=str(item["id"]),
                    item_name=item_name,
                    source_parent_id=str(project["id"]),
                    target_parts=(PRIVATE_FOLDER,),
                    destination="archive",
                ))
                continue
            ambiguous.append({
                "project": str(project["name"]),
                "person": "",
                "item": str(item.get("name", "")),
                "reason": "unrecognized project artifact",
            })
            continue
        target_parts = (
            (PRIVATE_FOLDER,)
            if role in {"m2_input", "status_reports"}
            else canonical_folder_parts(role)
        )
        moves.append(PlannedMove(
            project=str(project["name"]),
            role=role,
            item_id=str(item["id"]),
            item_name=str(item["name"]),
            source_parent_id=str(project["id"]),
            target_parts=target_parts,
        ))
    return moves, ambiguous


def build_plan(drive: Any) -> tuple[dict[str, Any], list[PlannedMove], list[dict[str, str]]]:
    m2_root = find_child_folder(drive, ROOT_FOLDER_ID, M2_ROOT_NAME)
    if not m2_root:
        raise RuntimeError(f"{M2_ROOT_NAME} not found under the workspace root")
    projects = [
        item for item in list_children(drive, m2_root["id"])
        if item.get("mimeType") == FOLDER_MIME
        and not str(item.get("name", "")).startswith("_")
    ]
    moves: list[PlannedMove] = []
    ambiguous: list[dict[str, str]] = []
    for project in sorted(projects, key=lambda item: str(item["name"]).casefold()):
        project_moves, project_ambiguous = plan_project(drive, project)
        moves.extend(project_moves)
        ambiguous.extend(project_ambiguous)
    return m2_root, moves, ambiguous


def apply_plan(drive: Any, m2_root: dict[str, Any], moves: list[PlannedMove]) -> list[dict[str, str]]:
    projects = {
        str(item["name"]): item
        for item in list_children(drive, m2_root["id"])
        if item.get("mimeType") == FOLDER_MIME
    }
    archive_m2 = ensure_folder_path(
        drive, ROOT_FOLDER_ID, ("90_Storage", "Retired", M2_ROOT_NAME)
    )
    applied: list[dict[str, str]] = []
    for move in moves:
        project = projects[move.project]
        if move.destination == "archive":
            archive_project = ensure_folder_path(drive, archive_m2["id"], (move.project,))
            target = ensure_folder_path(drive, archive_project["id"], move.target_parts)
        else:
            target = ensure_folder_path(drive, project["id"], move.target_parts)
        existing = [
            item for item in list_children(drive, target["id"])
            if item.get("name") == move.item_name and item.get("id") != move.item_id
        ]
        if existing:
            raise RuntimeError(
                f"Collision in {move.project}/{'/'.join(move.target_parts)} for {move.item_name!r}"
            )
        move_item(drive, move.item_id, target["id"])
        applied.append({
            "project": move.project,
            "person": move.person,
            "role": move.role,
            "item_id": move.item_id,
            "target": "/".join(move.target_parts),
            "destination": move.destination,
        })
    return applied


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("audit", "apply"))
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--credentials", default=".local/google/credentials.json")
    parser.add_argument("--token", default=".local/google/token.json")
    return parser.parse_args()


def main() -> int:
    ensure_utf8_stdout()
    args = parse_args()
    try:
        services = get_services(Path(args.credentials), Path(args.token))
        m2_root, moves, ambiguous = build_plan(services["drive"])
        applied = apply_plan(services["drive"], m2_root, moves) if args.command == "apply" else []
        data = {
            "mode": args.command,
            "planned_count": len(moves),
            "applied_count": len(applied),
            "ambiguous_count": len(ambiguous),
            "moves": [asdict(move) for move in moves],
            "applied": applied,
            "ambiguous": ambiguous,
            "permissions_changed": False,
        }
        if args.json:
            print(json.dumps({
                "schema_version": 1,
                "ok": True,
                "command": args.command,
                "data": data,
                "warnings": ["Ambiguous items were left in place"] if ambiguous else [],
                "errors": [],
            }, ensure_ascii=False))
        else:
            print(f"Planned moves: {len(moves)}; applied: {len(applied)}; ambiguous: {len(ambiguous)}")
            for item in ambiguous:
                print(f"  AMBIGUOUS: {item['project']}/{item.get('person', '')}/{item['item']} - {item['reason']}")
        return 0
    except Exception as exc:
        if args.json:
            print(json.dumps({
                "schema_version": 1,
                "ok": False,
                "command": args.command,
                "data": {},
                "warnings": [],
                "errors": [str(exc)],
            }, ensure_ascii=False))
        else:
            print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
