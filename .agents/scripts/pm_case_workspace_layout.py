"""Canonical folder layout for the PM Case Library (40_PM_Case_Library).

Deliberately the simplest of the three layout modules (m2_workspace_layout,
project_knowledge_workspace_layout): this lane is flat and cross-project by
design - real cases from any project land in ONE shared library, organized
by theme/pattern rather than by project, so they can be compared side by
side. There is no per-project subfolder to create or resolve, unlike the
Project Knowledge lane. Personal-reference only for v1 - shared with no one
else, so there is no visibility split to model either.

Read functions (find_*) never create anything; ensure_* functions create
what's missing. Reuses m2_workspace_layout's generic Drive helpers
(drive_query, find_child_folder, ensure_child_folder, q_escape) rather than
duplicating them.
"""

from __future__ import annotations

from typing import Any

from m2_workspace_layout import (
    DOC_MIME,
    SHEET_MIME,
    drive_query,
    ensure_child_folder,
    find_child_folder,
    q_escape,
)
from sync_m2_source_docs_to_sheets import ROOT_FOLDER_ID

PM_CASE_LIBRARY_ROOT_NAME = "40_PM_Case_Library"

# Document role -> (canonical file name, mime type). Both documents live
# directly under the root folder - no subfolders, nothing per-project.
DOCUMENT_LAYOUT: dict[str, tuple[str, str]] = {
    "pm_case_index": ("pm_case_index", SHEET_MIME),
    "pm_case_library": ("pm_case_library", DOC_MIME),
}


def find_root(drive: Any) -> dict[str, Any] | None:
    """Read-only lookup of the 40_PM_Case_Library root folder."""
    return find_child_folder(drive, ROOT_FOLDER_ID, PM_CASE_LIBRARY_ROOT_NAME)


def ensure_root(drive: Any) -> dict[str, Any]:
    """Create the 40_PM_Case_Library root folder if it doesn't exist yet."""
    return ensure_child_folder(drive, ROOT_FOLDER_ID, PM_CASE_LIBRARY_ROOT_NAME)


def find_document(drive: Any, role: str) -> dict[str, Any] | None:
    """Read-only lookup of pm_case_index or pm_case_library under the root
    folder. Returns None if the root folder or the document itself doesn't
    exist yet - callers create it (via the Drive/Sheets/Docs API directly,
    same convention as project-knowledge-intake) the first time a real case
    is actually logged, never speculatively."""
    if role not in DOCUMENT_LAYOUT:
        raise ValueError(f"Unknown PM Case Library document role: {role!r}")
    name, mime_type = DOCUMENT_LAYOUT[role]
    root = find_root(drive)
    if not root:
        return None
    matches = drive_query(
        drive,
        f"'{root['id']}' in parents and name = '{q_escape(name)}' and "
        f"mimeType = '{mime_type}' and trashed = false",
    )
    if len(matches) > 1:
        raise RuntimeError(f"Duplicate {role!r} document under {PM_CASE_LIBRARY_ROOT_NAME}")
    return matches[0] if matches else None
