"""Canonical folder layout for the Project Knowledge lane (30_Project_Knowledge).

This module is intentionally free of business data - same spirit as
m2_workspace_layout.py, but deliberately simpler: this lane has no
private/team_shared/people visibility split. Everything lives directly
under the project folder, private by default via the 30_Project_Knowledge
root's own restricted sharing. Sharing an individual Doc is a deliberate,
one-off action taken outside this layout (a manual Drive permission
change), not a folder move this module performs.

Read functions (find_*) never create anything; ensure_* functions create
what's missing. Reuses m2_workspace_layout's generic Drive helpers
(drive_query, find_child_folder, ensure_child_folder, q_escape) rather than
duplicating them - those are already parent_id-generic, not M2-specific.
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

PROJECT_KNOWLEDGE_ROOT_NAME = "30_Project_Knowledge"

# Document role -> (subfolder parts relative to the project folder,
# canonical file name - "{project}" is substituted if present, mime type).
# pk_summary is intentionally absent here: it is one document per source
# (named "<source-slug>_summary"), not a single fixed-name document like
# the rest - see find_summary_document()/summary_document_name().
DOCUMENT_LAYOUT: dict[str, tuple[tuple[str, ...], str, str]] = {
    "pk_source_index": ((), "source_index", SHEET_MIME),
    "pk_knowledge_base": (("knowledge_base",), "{project}_knowledge_base", DOC_MIME),
    "pk_performance_test_plan": (("qa_docs",), "performance_test_plan", DOC_MIME),
    "pk_test_plan": (("qa_docs",), "test_plan", DOC_MIME),
    "pk_test_strategy": (("qa_docs",), "test_strategy", DOC_MIME),
}

SUMMARY_FOLDER_PARTS: tuple[str, ...] = ("summaries",)
PROJECT_SUBFOLDERS: tuple[str, ...] = ("knowledge_base", "summaries", "qa_docs")


def summary_document_name(source_slug: str) -> str:
    return f"{source_slug}_summary"


def find_root(drive: Any) -> dict[str, Any] | None:
    """Read-only lookup of the 30_Project_Knowledge root folder."""
    return find_child_folder(drive, ROOT_FOLDER_ID, PROJECT_KNOWLEDGE_ROOT_NAME)


def ensure_root(drive: Any) -> dict[str, Any]:
    """Create the 30_Project_Knowledge root folder if it doesn't exist yet."""
    return ensure_child_folder(drive, ROOT_FOLDER_ID, PROJECT_KNOWLEDGE_ROOT_NAME)


def find_project_folder(drive: Any, project: str) -> dict[str, Any] | None:
    """Read-only lookup of one project's folder under 30_Project_Knowledge."""
    root = find_root(drive)
    if not root:
        return None
    return find_child_folder(drive, root["id"], project)


def ensure_project_folder(drive: Any, project: str) -> dict[str, Any]:
    """Create 30_Project_Knowledge/<project>/ and its knowledge_base/,
    summaries/, qa_docs/ subfolders if missing. Never called automatically
    by classify/guide/pack/show_project_state - a project folder is only
    created when a source is actually being processed into it."""
    root = ensure_root(drive)
    project_folder = ensure_child_folder(drive, root["id"], project)
    for subfolder in PROJECT_SUBFOLDERS:
        ensure_child_folder(drive, project_folder["id"], subfolder)
    return project_folder


def _find_subfolder(drive: Any, parent_id: str, parts: tuple[str, ...]) -> dict[str, Any] | None:
    current_id = parent_id
    for part in parts:
        found = find_child_folder(drive, current_id, part)
        if not found:
            return None
        current_id = found["id"]
    return {"id": current_id}


def find_document_folder(drive: Any, project_folder_id: str, role: str) -> dict[str, Any] | None:
    """Read-only lookup of the subfolder a document role lives in (the
    project folder itself if the role has no subfolder of its own)."""
    parts, _name, _mime = DOCUMENT_LAYOUT[role]
    return _find_subfolder(drive, project_folder_id, parts)


def find_document(drive: Any, project_folder_id: str, role: str, project: str = "") -> dict[str, Any] | None:
    """Read-only lookup of one of this lane's fixed-name documents
    (pk_source_index, pk_knowledge_base, pk_performance_test_plan,
    pk_test_plan, pk_test_strategy). Use find_summary_document for
    pk_summary, which is per-source, not fixed-name."""
    if role not in DOCUMENT_LAYOUT:
        raise ValueError(f"Unknown Project Knowledge document role: {role!r}")
    parts, name_template, mime_type = DOCUMENT_LAYOUT[role]
    name = name_template.format(project=project) if "{project}" in name_template else name_template
    folder = _find_subfolder(drive, project_folder_id, parts)
    if not folder:
        return None
    matches = drive_query(
        drive,
        f"'{folder['id']}' in parents and name = '{q_escape(name)}' and "
        f"mimeType = '{mime_type}' and trashed = false",
    )
    if len(matches) > 1:
        raise RuntimeError(f"Duplicate {role!r} document under project folder {project_folder_id!r}")
    return matches[0] if matches else None


def find_summary_document(drive: Any, project_folder_id: str, source_slug: str) -> dict[str, Any] | None:
    """Read-only lookup of one source's pk_summary document, under
    summaries/, named "<source-slug>_summary"."""
    folder = _find_subfolder(drive, project_folder_id, SUMMARY_FOLDER_PARTS)
    if not folder:
        return None
    name = summary_document_name(source_slug)
    matches = drive_query(
        drive,
        f"'{folder['id']}' in parents and name = '{q_escape(name)}' and "
        f"mimeType = '{DOC_MIME}' and trashed = false",
    )
    if len(matches) > 1:
        raise RuntimeError(f"Duplicate summary document for slug {source_slug!r}")
    return matches[0] if matches else None
