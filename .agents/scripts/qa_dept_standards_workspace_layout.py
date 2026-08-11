"""Canonical folder layout for QA Department Standards (50_QA_Department_Standards).

Same shape as pm_case_workspace_layout.py: flat, no per-project
subfolder, personal-reference only. Two documents live directly under the
root - qa_department_standards (current-state, topic-organized department
requirements/tools/direction) and m2_lessons_learned (append-only,
personal retrospective log). Distinct lane from both - see
qa-department-standards-roles/SKILL.md for the boundary vs
30_Project_Knowledge/40_PM_Case_Library/10_M1_People_Management.

Read functions (find_*) never create anything; ensure_* functions create
what's missing. Reuses m2_workspace_layout's generic Drive helpers
(drive_query, find_child_folder, ensure_child_folder, q_escape) rather than
duplicating them.
"""

from __future__ import annotations

from typing import Any

from m2_workspace_layout import (
    DOC_MIME,
    drive_query,
    ensure_child_folder,
    find_child_folder,
    q_escape,
)
from sync_m2_source_docs_to_sheets import ROOT_FOLDER_ID

QA_DEPT_STANDARDS_ROOT_NAME = "50_QA_Department_Standards"

# Document role -> (canonical file name, mime type). Both documents live
# directly under the root folder - no subfolders, nothing per-project.
DOCUMENT_LAYOUT: dict[str, tuple[str, str]] = {
    "qa_department_standards": ("qa_department_standards", DOC_MIME),
    "m2_lessons_learned": ("m2_lessons_learned", DOC_MIME),
}


def find_root(drive: Any) -> dict[str, Any] | None:
    """Read-only lookup of the 50_QA_Department_Standards root folder."""
    return find_child_folder(drive, ROOT_FOLDER_ID, QA_DEPT_STANDARDS_ROOT_NAME)


def ensure_root(drive: Any) -> dict[str, Any]:
    """Create the 50_QA_Department_Standards root folder if it doesn't exist yet."""
    return ensure_child_folder(drive, ROOT_FOLDER_ID, QA_DEPT_STANDARDS_ROOT_NAME)


def find_document(drive: Any, role: str) -> dict[str, Any] | None:
    """Read-only lookup of qa_department_standards or m2_lessons_learned
    under the root folder. Returns None if the root folder or the document
    itself doesn't exist yet - callers create it (via the Drive/Docs API
    directly, same convention as project-knowledge-intake) the first time a
    real entry is actually logged, never speculatively."""
    if role not in DOCUMENT_LAYOUT:
        raise ValueError(f"Unknown QA Department Standards document role: {role!r}")
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
        raise RuntimeError(f"Duplicate {role!r} document under {QA_DEPT_STANDARDS_ROOT_NAME}")
    return matches[0] if matches else None
