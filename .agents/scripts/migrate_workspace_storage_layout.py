"""Audit or apply consolidation into the user-facing 90_Storage root.

The migration renames 90_Archive in place, moves 30_Reference and _System
under it, groups legacy material under Retired, and updates only the queue's
mutable Current source path. Drive IDs, revisions, permissions, and immutable
queue Source identities are preserved.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from google_api_smoke_test import ensure_utf8_stdout
from m2_workspace_layout import FOLDER_MIME, ensure_child_folder, find_child_folder, list_children, move_item
from pipeline_common import get_services
from qa_manage import find_queue, read_queue, write_queue
from sync_m2_source_docs_to_sheets import ROOT_FOLDER_ID
from workspace_root_layout import (
    BACKUPS_FOLDER,
    PROCESSED_FOLDER,
    REFERENCE_FOLDER,
    RETIRED_FOLDER,
    STORAGE_ROOT,
    SYSTEM_FOLDER,
    migrate_current_source_path,
)


LEGACY_ARCHIVE_ROOT = "90_Archive"
LEGACY_REFERENCE_ROOT = "30_Reference"
LEGACY_SYSTEM_ROOT = "_System"
LEGACY_BACKUPS_FOLDER = "_git_mirror_backups"


@dataclass(frozen=True)
class PlannedAction:
    action: str
    source: str
    target: str


def child_folders(drive: Any, parent_id: str) -> dict[str, dict[str, Any]]:
    return {
        str(item["name"]): item
        for item in list_children(drive, parent_id)
        if item.get("mimeType") == FOLDER_MIME
    }


def build_plan(services: dict[str, Any]) -> tuple[list[PlannedAction], list[str]]:
    drive = services["drive"]
    root = child_folders(drive, ROOT_FOLDER_ID)
    actions: list[PlannedAction] = []
    errors: list[str] = []

    archive = root.get(LEGACY_ARCHIVE_ROOT)
    storage = root.get(STORAGE_ROOT)
    if archive and storage and archive["id"] != storage["id"]:
        errors.append("Both 90_Archive and 90_Storage exist")
        return actions, errors
    if archive:
        actions.append(PlannedAction("rename", LEGACY_ARCHIVE_ROOT, STORAGE_ROOT))

    effective = archive or storage
    if not effective:
        errors.append("Neither 90_Archive nor 90_Storage exists")
        return actions, errors

    children = child_folders(drive, str(effective["id"]))
    reference = root.get(LEGACY_REFERENCE_ROOT)
    if reference:
        if REFERENCE_FOLDER in children:
            errors.append("Reference destination already exists")
        else:
            actions.append(PlannedAction("move_rename", LEGACY_REFERENCE_ROOT, f"{STORAGE_ROOT}/{REFERENCE_FOLDER}"))
    system = root.get(LEGACY_SYSTEM_ROOT)
    if system:
        if SYSTEM_FOLDER in children:
            errors.append("_System destination already exists")
        else:
            actions.append(PlannedAction("move", LEGACY_SYSTEM_ROOT, f"{STORAGE_ROOT}/{SYSTEM_FOLDER}"))

    if LEGACY_BACKUPS_FOLDER in children:
        if BACKUPS_FOLDER in children:
            errors.append("Both legacy and canonical backup folders exist")
        else:
            actions.append(PlannedAction("rename", f"{STORAGE_ROOT}/{LEGACY_BACKUPS_FOLDER}", f"{STORAGE_ROOT}/{BACKUPS_FOLDER}"))

    allowed = {PROCESSED_FOLDER, BACKUPS_FOLDER, LEGACY_BACKUPS_FOLDER, REFERENCE_FOLDER, SYSTEM_FOLDER, RETIRED_FOLDER}
    for name in sorted(children, key=lambda value: (value.casefold(), value)):
        if name not in allowed:
            target_name = "Roots" if name == "Retired_Roots" else name
            actions.append(PlannedAction("move_rename", f"{STORAGE_ROOT}/{name}", f"{STORAGE_ROOT}/{RETIRED_FOLDER}/{target_name}"))
    return actions, errors


def rename_item(drive: Any, item_id: str, name: str) -> None:
    drive.files().update(
        fileId=item_id,
        body={"name": name},
        fields="id,name,parents",
        supportsAllDrives=True,
    ).execute()


def apply_plan(services: dict[str, Any]) -> tuple[list[PlannedAction], int]:
    drive = services["drive"]
    root = child_folders(drive, ROOT_FOLDER_ID)
    archive = root.get(LEGACY_ARCHIVE_ROOT)
    storage = root.get(STORAGE_ROOT)
    if archive and storage and archive["id"] != storage["id"]:
        raise RuntimeError("Both 90_Archive and 90_Storage exist")
    applied: list[PlannedAction] = []
    if archive:
        rename_item(drive, str(archive["id"]), STORAGE_ROOT)
        storage = dict(archive, name=STORAGE_ROOT)
        applied.append(PlannedAction("rename", LEGACY_ARCHIVE_ROOT, STORAGE_ROOT))
    if not storage:
        raise RuntimeError("Storage root is missing")

    storage_id = str(storage["id"])
    storage_children = child_folders(drive, storage_id)

    reference = root.get(LEGACY_REFERENCE_ROOT)
    if reference:
        if REFERENCE_FOLDER in storage_children:
            raise RuntimeError("Reference destination already exists")
        move_item(drive, str(reference["id"]), storage_id)
        rename_item(drive, str(reference["id"]), REFERENCE_FOLDER)
        applied.append(PlannedAction("move_rename", LEGACY_REFERENCE_ROOT, f"{STORAGE_ROOT}/{REFERENCE_FOLDER}"))

    system = root.get(LEGACY_SYSTEM_ROOT)
    if system:
        if SYSTEM_FOLDER in storage_children:
            raise RuntimeError("_System destination already exists")
        move_item(drive, str(system["id"]), storage_id)
        applied.append(PlannedAction("move", LEGACY_SYSTEM_ROOT, f"{STORAGE_ROOT}/{SYSTEM_FOLDER}"))

    storage_children = child_folders(drive, storage_id)
    legacy_backups = storage_children.get(LEGACY_BACKUPS_FOLDER)
    if legacy_backups:
        if BACKUPS_FOLDER in storage_children:
            raise RuntimeError("Both legacy and canonical backup folders exist")
        rename_item(drive, str(legacy_backups["id"]), BACKUPS_FOLDER)
        applied.append(PlannedAction("rename", f"{STORAGE_ROOT}/{LEGACY_BACKUPS_FOLDER}", f"{STORAGE_ROOT}/{BACKUPS_FOLDER}"))

    retired = ensure_child_folder(drive, storage_id, RETIRED_FOLDER)
    storage_children = child_folders(drive, storage_id)
    allowed = {PROCESSED_FOLDER, BACKUPS_FOLDER, REFERENCE_FOLDER, SYSTEM_FOLDER, RETIRED_FOLDER}
    retired_children = child_folders(drive, str(retired["id"]))
    for name, item in sorted(storage_children.items(), key=lambda pair: (pair[0].casefold(), pair[0])):
        if name in allowed:
            continue
        target_name = "Roots" if name == "Retired_Roots" else name
        if target_name in retired_children:
            raise RuntimeError(f"Retired destination {target_name!r} already exists")
        move_item(drive, str(item["id"]), str(retired["id"]))
        if target_name != name:
            rename_item(drive, str(item["id"]), target_name)
        applied.append(PlannedAction("move_rename", f"{STORAGE_ROOT}/{name}", f"{STORAGE_ROOT}/{RETIRED_FOLDER}/{target_name}"))

    queue = find_queue(services)
    if not queue:
        raise RuntimeError("_intake_queue not found")
    rows = read_queue(services, queue)
    changed = 0
    for row in rows:
        current = str(row.get("Current source", "")).strip()
        if not current:
            continue
        migrated = migrate_current_source_path(current)
        if migrated != current.replace("\\", "/"):
            row["Current source"] = migrated
            changed += 1
    if changed:
        write_queue(services, queue, rows)
    return applied, changed


def storage_state(services: dict[str, Any]) -> dict[str, Any]:
    drive = services["drive"]
    root = child_folders(drive, ROOT_FOLDER_ID)
    storage = root.get(STORAGE_ROOT)
    return {
        "root_folders": sorted(root, key=lambda value: (value.casefold(), value)),
        "storage_children": sorted(child_folders(drive, str(storage["id"]))) if storage else [],
        "legacy_roots_present": [name for name in (LEGACY_ARCHIVE_ROOT, LEGACY_REFERENCE_ROOT, LEGACY_SYSTEM_ROOT) if name in root],
    }


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
        plan, errors = build_plan(services)
        if errors:
            raise RuntimeError("; ".join(errors))
        applied, queue_rows_changed = apply_plan(services) if args.command == "apply" else ([], 0)
        data = {
            "planned_count": len(plan),
            "applied_count": len(applied),
            "queue_rows_changed": queue_rows_changed,
            "plan": [asdict(item) for item in plan],
            "state": storage_state(services),
        }
        envelope = {"schema_version": 1, "ok": True, "command": args.command, "data": data, "warnings": [], "errors": []}
        print(json.dumps(envelope, ensure_ascii=False) if args.json else json.dumps(data, indent=2, ensure_ascii=False))
        return 0
    except Exception as exc:
        envelope = {"schema_version": 1, "ok": False, "command": args.command, "data": {}, "warnings": [], "errors": [str(exc)]}
        if args.json:
            print(json.dumps(envelope, ensure_ascii=False))
        else:
            print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
