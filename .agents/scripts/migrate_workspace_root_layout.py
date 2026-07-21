"""Audit or apply the root-folder lifecycle migration in Google Drive.

The migration uses `_intake_queue` as its disposition authority. It never
changes sharing permissions, file IDs, revisions, or queue source identity.
Unknown or conflicting items remain in place and make `apply` fail closed.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from google_api_smoke_test import ensure_utf8_stdout
from m2_workspace_layout import (
    FOLDER_MIME,
    ensure_folder_path,
    find_child_folder,
    find_folder_path,
    list_children,
    move_item,
)
from pipeline_common import get_services
from qa_manage import find_queue, read_queue, write_queue
from sync_m2_source_docs_to_sheets import ROOT_FOLDER_ID
from workspace_root_layout import (
    ARCHIVE_ROOT,
    EXPORTS_ROOT,
    LEGACY_SOURCE_ROOT,
    SYSTEM_EXPORT_FOLDERS,
    latest_rows_by_source,
    normalize_relative_path,
    source_destination,
    source_disposition,
)


@dataclass(frozen=True)
class PlannedMove:
    item_id: str
    source: str
    target: tuple[str, ...]
    disposition: str
    rename_to: str = ""
    run_id: str = ""


def walk_files(drive: Any, folder_id: str, prefix: tuple[str, ...]) -> list[dict[str, str]]:
    files: list[dict[str, str]] = []
    for item in list_children(drive, folder_id):
        path = (*prefix, str(item["name"]))
        if item.get("mimeType") == FOLDER_MIME:
            files.extend(walk_files(drive, str(item["id"]), path))
        else:
            files.append({"id": str(item["id"]), "path": "/".join(path)})
    return files


def find_item_at_path(drive: Any, parts: tuple[str, ...]) -> dict[str, Any] | None:
    parent = find_folder_path(drive, ROOT_FOLDER_ID, parts[:-1])
    if not parent:
        return None
    matches = [item for item in list_children(drive, str(parent["id"])) if item.get("name") == parts[-1]]
    if len(matches) > 1:
        raise RuntimeError(f"Duplicate Drive items at {'/'.join(parts)}")
    return matches[0] if matches else None


def build_plan(
    services: dict[str, Any],
    overrides: dict[str, str] | None = None,
) -> tuple[list[PlannedMove], list[dict[str, str]]]:
    drive = services["drive"]
    queue = find_queue(services)
    if not queue:
        raise RuntimeError("_intake_queue not found")
    rows = read_queue(services, queue)
    by_source = latest_rows_by_source(rows)

    overrides = overrides or {}
    moves: list[PlannedMove] = []
    ambiguous: list[dict[str, str]] = []
    legacy = find_child_folder(drive, ROOT_FOLDER_ID, LEGACY_SOURCE_ROOT)
    if legacy:
        for item in walk_files(drive, str(legacy["id"]), (LEGACY_SOURCE_ROOT,)):
            normalized = normalize_relative_path(item["path"])
            if PurePosixPath(normalized).name == "_INBOX_STRUCTURE.md":
                continue
            row = by_source.get(normalized.casefold())
            if not row:
                disposition = overrides.get(item["id"], "")
                if disposition in {"inbox", "archive", "reference"}:
                    moves.append(PlannedMove(
                        item_id=item["id"],
                        source=normalized,
                        target=source_destination(normalized, disposition),
                        disposition=disposition,
                    ))
                    continue
                ambiguous.append({
                    "item_id": item["id"],
                    "source": normalized,
                    "reason": "no queue row",
                })
                continue
            disposition = source_disposition(row)
            if disposition == "ambiguous":
                ambiguous.append({
                    "source": normalized,
                    "reason": f"queue status {row.get('Status', '')!r} has no disposition",
                })
                continue
            moves.append(PlannedMove(
                item_id=item["id"],
                source=normalized,
                target=source_destination(normalized, disposition),
                disposition=disposition,
                run_id=str(row.get("Run ID", "")),
            ))

    # Reconcile a previous interrupted apply: queue-backed items may already
    # be at their deterministic destination while the queue still carries
    # the pre-migration schema/path. Including them makes apply idempotently
    # finish the queue update instead of losing track of those moves.
    planned_run_ids = {move.run_id for move in moves if move.run_id}
    for row in by_source.values():
        run_id = str(row.get("Run ID", ""))
        source = str(row.get("Source", ""))
        if not run_id or run_id in planned_run_ids or not source.replace("\\", "/").startswith(f"{LEGACY_SOURCE_ROOT}/"):
            continue
        disposition = source_disposition(row)
        if disposition == "ambiguous":
            continue
        target = source_destination(source, disposition)
        expected_queue_disposition = {
            "inbox": "inbox",
            "archive": "archived",
            "reference": "reference",
        }[disposition]
        current_source = str(row.get("Current source", "")).replace("\\", "/").strip("/")
        if current_source.casefold() == "/".join(target).casefold() and row.get("Source disposition") == expected_queue_disposition:
            continue
        item = find_item_at_path(drive, target)
        if item:
            moves.append(PlannedMove(
                item_id=str(item["id"]),
                source=normalize_relative_path(source),
                target=target,
                disposition=disposition,
                run_id=run_id,
            ))

    exports = find_child_folder(drive, ROOT_FOLDER_ID, EXPORTS_ROOT)
    if exports:
        for item in list_children(drive, str(exports["id"])):
            name = str(item.get("name", ""))
            target = SYSTEM_EXPORT_FOLDERS.get(name)
            if not target or item.get("mimeType") != FOLDER_MIME:
                ambiguous.append({
                    "source": f"{EXPORTS_ROOT}/{name}",
                    "reason": "not a recognized internal artifact folder",
                })
                continue
            moves.append(PlannedMove(
                item_id=str(item["id"]),
                source=f"{EXPORTS_ROOT}/{name}",
                target=target,
                disposition="system",
                rename_to=target[-1],
            ))
    vscode = find_child_folder(drive, ROOT_FOLDER_ID, ".vscode")
    if vscode:
        moves.append(PlannedMove(
            item_id=str(vscode["id"]),
            source=".vscode",
            target=(ARCHIVE_ROOT, "Retired", "VSCode_Settings_Backup", "Current"),
            disposition="system",
            rename_to="Current",
        ))
    destinations: dict[str, str] = {}
    for move in moves:
        destination = "/".join(move.target).casefold()
        previous = destinations.get(destination)
        if previous and previous != move.item_id:
            ambiguous.append({
                "source": move.source,
                "reason": f"planned destination collides with item {previous}",
            })
        destinations[destination] = move.item_id
    return moves, ambiguous


def apply_plan(services: dict[str, Any], moves: list[PlannedMove]) -> list[dict[str, str]]:
    drive = services["drive"]
    applied: list[dict[str, str]] = []
    for planned in moves:
        parent = ensure_folder_path(drive, ROOT_FOLDER_ID, planned.target[:-1])
        target_name = planned.rename_to or planned.target[-1]
        collisions = [
            item for item in list_children(drive, str(parent["id"]))
            if item.get("name") == target_name and item.get("id") != planned.item_id
        ]
        if collisions:
            raise RuntimeError(f"Destination collision at {'/'.join(planned.target)}")
        move_item(drive, planned.item_id, str(parent["id"]))
        if planned.rename_to:
            drive.files().update(
                fileId=planned.item_id,
                body={"name": planned.rename_to},
                fields="id,name,parents",
                supportsAllDrives=True,
            ).execute()
        applied.append({
            "source": planned.source,
            "target": "/".join((*planned.target[:-1], target_name)),
            "disposition": planned.disposition,
        })

    legacy = find_child_folder(drive, ROOT_FOLDER_ID, LEGACY_SOURCE_ROOT)
    if legacy:
        retired = ensure_folder_path(drive, ROOT_FOLDER_ID, (ARCHIVE_ROOT, "Retired", "Roots"))
        collision = find_child_folder(drive, str(retired["id"]), LEGACY_SOURCE_ROOT)
        if collision and collision.get("id") != legacy.get("id"):
            raise RuntimeError(f"Retired root {LEGACY_SOURCE_ROOT!r} already exists")
        move_item(drive, str(legacy["id"]), str(retired["id"]))

    exports = find_child_folder(drive, ROOT_FOLDER_ID, EXPORTS_ROOT)
    if exports:
        if list_children(drive, str(exports["id"])):
            raise RuntimeError(f"Refusing to retire non-empty {EXPORTS_ROOT}")
        retired = ensure_folder_path(drive, ROOT_FOLDER_ID, (ARCHIVE_ROOT, "Retired", "Roots"))
        move_item(drive, str(exports["id"]), str(retired["id"]))

    queue = find_queue(services)
    if not queue:
        raise RuntimeError("_intake_queue disappeared during migration")
    rows = read_queue(services, queue)
    by_run = {str(row.get("Run ID", "")): row for row in rows}
    for planned in moves:
        if not planned.run_id:
            continue
        row = by_run.get(planned.run_id)
        if not row:
            raise RuntimeError(f"Queue run {planned.run_id!r} disappeared during migration")
        row["Current source"] = "/".join(planned.target)
        row["Source disposition"] = {
            "inbox": "inbox",
            "archive": "archived",
            "reference": "reference",
        }[planned.disposition]
    write_queue(services, queue, rows)
    return applied


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("audit", "apply"))
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--credentials", default=".local/google/credentials.json")
    parser.add_argument("--token", default=".local/google/token.json")
    parser.add_argument(
        "--override",
        action="append",
        default=[],
        metavar="ITEM_ID=DISPOSITION",
        help="explicit disposition for an unqueued Drive item; disposition is inbox, archive, or reference",
    )
    return parser.parse_args()


def parse_overrides(values: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for value in values:
        item_id, separator, disposition = value.partition("=")
        if not separator or not item_id or disposition not in {"inbox", "archive", "reference"}:
            raise ValueError(f"Invalid override {value!r}; expected ITEM_ID=inbox|archive|reference")
        result[item_id] = disposition
    return result


def root_state(services: dict[str, Any]) -> dict[str, Any]:
    drive = services["drive"]
    root_children = list_children(drive, ROOT_FOLDER_ID)
    folders = sorted(
        str(item["name"]) for item in root_children if item.get("mimeType") == FOLDER_MIME
    )
    inbox = find_child_folder(drive, ROOT_FOLDER_ID, "00_Inbox")
    exports = find_child_folder(drive, ROOT_FOLDER_ID, EXPORTS_ROOT)
    return {
        "root_folders": folders,
        "legacy_source_root_present": LEGACY_SOURCE_ROOT in folders,
        "exports_root_present": EXPORTS_ROOT in folders,
        "inbox_file_count": len(walk_files(drive, str(inbox["id"]), ("00_Inbox",))) if inbox else 0,
        "exports_child_count": len(list_children(drive, str(exports["id"]))) if exports else 0,
    }


def main() -> int:
    ensure_utf8_stdout()
    args = parse_args()
    try:
        services = get_services(Path(args.credentials), Path(args.token))
        moves, ambiguous = build_plan(services, parse_overrides(args.override))
        if args.command == "apply" and ambiguous:
            raise RuntimeError(
                f"Refusing to apply while {len(ambiguous)} item(s) have no deterministic disposition"
            )
        applied = apply_plan(services, moves) if args.command == "apply" else []
        data = {
            "planned_count": len(moves),
            "applied_count": len(applied),
            "ambiguous_count": len(ambiguous),
            "by_disposition": {
                key: sum(move.disposition == key for move in moves)
                for key in ("inbox", "archive", "reference", "system")
            },
            "moves": [asdict(move) for move in moves],
            "ambiguous": ambiguous,
            "root_state": root_state(services),
        }
        envelope = {
            "schema_version": 1,
            "ok": True,
            "command": args.command,
            "data": data,
            "warnings": ["Ambiguous items remain in place"] if ambiguous else [],
            "errors": [],
        }
        print(json.dumps(envelope, ensure_ascii=False) if args.json else json.dumps(data, indent=2, ensure_ascii=False))
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
