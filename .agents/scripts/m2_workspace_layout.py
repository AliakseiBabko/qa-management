"""Canonical visibility-based folder layout for M2 project documents.

This module is intentionally free of business data. It maps logical document
roles to Drive folder paths and provides read-compatible lookup helpers for the
pre-migration flat layout. New writes must use the canonical path; legacy
fallbacks exist only so a staged Drive migration does not break readers.
"""

from __future__ import annotations

from typing import Any, Iterable


FOLDER_MIME = "application/vnd.google-apps.folder"
SHEET_MIME = "application/vnd.google-apps.spreadsheet"
DOC_MIME = "application/vnd.google-apps.document"

PRIVATE_FOLDER = "private"
TEAM_SHARED_FOLDER = "team_shared"
PEOPLE_FOLDER = "people"
PERSON_SHARED_FOLDER = "shared"

PROJECT_PRIVATE_ROLES = {
    "project_metrics",
    "project_risk",
    "process_checklist",
    "project_development_plan",
    "evidence_log",
    "action_items",
}
PROJECT_TEAM_SHARED_ROLES = {"qa_process_metrics"}
PERSON_SHARED_ROLES = {"individual_metrics", "individual_development_plan"}
PERSON_PRIVATE_ROLES = {"individual_metrics_internal", "m2_people_1to1_file"}
FOLDER_ROLES = {"m2_input", "status_reports"}


def q_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


def drive_query(
    drive: Any,
    query: str,
    fields: str = "id,name,mimeType,parents,webViewLink,shared",
) -> list[dict[str, Any]]:
    files: list[dict[str, Any]] = []
    token: str | None = None
    while True:
        response = (
            drive.files()
            .list(
                q=query,
                fields=f"nextPageToken,files({fields})",
                pageSize=1000,
                pageToken=token,
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
            )
            .execute()
        )
        files.extend(response.get("files", []))
        token = response.get("nextPageToken")
        if not token:
            return files


def list_children(drive: Any, parent_id: str) -> list[dict[str, Any]]:
    return drive_query(
        drive,
        f"'{parent_id}' in parents and trashed = false",
    )


def find_child_folder(drive: Any, parent_id: str, name: str) -> dict[str, Any] | None:
    matches = drive_query(
        drive,
        (
            f"'{parent_id}' in parents and name = '{q_escape(name)}' and "
            f"mimeType = '{FOLDER_MIME}' and trashed = false"
        ),
    )
    if len(matches) > 1:
        raise RuntimeError(f"Duplicate Drive folders named {name!r} under parent {parent_id}")
    return matches[0] if matches else None


def ensure_child_folder(drive: Any, parent_id: str, name: str) -> dict[str, Any]:
    existing = find_child_folder(drive, parent_id, name)
    if existing:
        return existing
    return (
        drive.files()
        .create(
            body={"name": name, "mimeType": FOLDER_MIME, "parents": [parent_id]},
            fields="id,name,mimeType,parents,webViewLink,shared",
            supportsAllDrives=True,
        )
        .execute()
    )


def find_folder_path(drive: Any, parent_id: str, parts: Iterable[str]) -> dict[str, Any] | None:
    current: dict[str, Any] = {"id": parent_id}
    for part in parts:
        found = find_child_folder(drive, current["id"], part)
        if not found:
            return None
        current = found
    return current


def ensure_folder_path(drive: Any, parent_id: str, parts: Iterable[str]) -> dict[str, Any]:
    current: dict[str, Any] = {"id": parent_id}
    for part in parts:
        current = ensure_child_folder(drive, current["id"], part)
    return current


def canonical_folder_parts(role: str, person: str = "") -> tuple[str, ...]:
    if role in PROJECT_PRIVATE_ROLES:
        return (PRIVATE_FOLDER,)
    if role in PROJECT_TEAM_SHARED_ROLES:
        return (TEAM_SHARED_FOLDER,)
    if role == "m2_input":
        return (PRIVATE_FOLDER, "m2_input")
    if role == "status_reports":
        return (PRIVATE_FOLDER, "status_reports")
    if role in PERSON_SHARED_ROLES:
        if not person:
            raise ValueError(f"Role {role!r} requires a person")
        return (PEOPLE_FOLDER, person, PERSON_SHARED_FOLDER)
    if role in PERSON_PRIVATE_ROLES:
        if not person:
            raise ValueError(f"Role {role!r} requires a person")
        return (PRIVATE_FOLDER, PEOPLE_FOLDER, person)
    raise ValueError(f"Unknown M2 document role: {role}")


def legacy_folder_parts(role: str, person: str = "") -> tuple[str, ...]:
    if role in PROJECT_PRIVATE_ROLES or role in PROJECT_TEAM_SHARED_ROLES:
        return ()
    if role in FOLDER_ROLES:
        return (role,)
    if role in PERSON_SHARED_ROLES or role in PERSON_PRIVATE_ROLES:
        if not person:
            raise ValueError(f"Role {role!r} requires a person")
        return (PEOPLE_FOLDER, person)
    raise ValueError(f"Unknown M2 document role: {role}")


def document_folder_candidates(
    drive: Any,
    project_folder_id: str,
    role: str,
    person: str = "",
) -> list[dict[str, Any]]:
    """Return canonical then legacy folder candidates, deduplicated by ID."""
    candidates: list[dict[str, Any]] = []
    canonical = find_folder_path(drive, project_folder_id, canonical_folder_parts(role, person))
    if canonical:
        candidates.append(canonical)
    legacy_parts = legacy_folder_parts(role, person)
    legacy = (
        {"id": project_folder_id, "name": ""}
        if not legacy_parts
        else find_folder_path(drive, project_folder_id, legacy_parts)
    )
    if legacy and all(item["id"] != legacy["id"] for item in candidates):
        candidates.append(legacy)
    return candidates


def ensure_document_folder(
    drive: Any,
    project_folder_id: str,
    role: str,
    person: str = "",
) -> dict[str, Any]:
    return ensure_folder_path(drive, project_folder_id, canonical_folder_parts(role, person))


def list_project_people(drive: Any, project_folder_id: str) -> list[str]:
    """Return the union of employee-facing and M2-private person folders."""
    names: dict[str, str] = {}
    for parts in ((PEOPLE_FOLDER,), (PRIVATE_FOLDER, PEOPLE_FOLDER)):
        root = find_folder_path(drive, project_folder_id, parts)
        if not root:
            continue
        for item in list_children(drive, root["id"]):
            if item.get("mimeType") != FOLDER_MIME:
                continue
            name = str(item.get("name", "")).strip()
            if name and not name.startswith("_"):
                names.setdefault(name.casefold(), name)
    return sorted(names.values(), key=lambda value: (value.casefold(), value))


def find_document(
    drive: Any,
    project_folder_id: str,
    role: str,
    name: str,
    mime_type: str,
    person: str = "",
) -> dict[str, Any] | None:
    matches: list[dict[str, Any]] = []
    for folder in document_folder_candidates(drive, project_folder_id, role, person):
        matches.extend(
            drive_query(
                drive,
                (
                    f"'{folder['id']}' in parents and name = '{q_escape(name)}' and "
                    f"mimeType = '{mime_type}' and trashed = false"
                ),
            )
        )
    unique = {item["id"]: item for item in matches}
    if len(unique) > 1:
        raise RuntimeError(
            f"Duplicate canonical/legacy documents for role {role!r}, name {name!r}"
        )
    return next(iter(unique.values())) if unique else None


def move_item(drive: Any, item_id: str, target_folder_id: str) -> dict[str, Any]:
    metadata = drive.files().get(fileId=item_id, fields="id,parents").execute()
    previous = metadata.get("parents", [])
    if previous == [target_folder_id]:
        return metadata
    return (
        drive.files()
        .update(
            fileId=item_id,
            addParents=target_folder_id,
            removeParents=",".join(previous),
            fields="id,name,mimeType,parents,webViewLink,shared",
            supportsAllDrives=True,
        )
        .execute()
    )
