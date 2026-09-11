"""Canonical folder layout for AI Adoption (55_AI_Adoption).

Same shape as qa_dept_standards_workspace_layout.py / pm_case_workspace_layout.py,
with one addition: a `reviews` subfolder, because this lane has both a small
fixed set of workspace-level documents and an open-ended, per-project,
per-session document family.

Four documents live directly under the root - the tiered knowledge base, plus
a Russian generic rules digest derived from its top tier:

  ai_adoption_source_notes    tier 1, append-only, one section per source
  ai_adoption_knowledge_store tier 2, topic-organized, upsert in place
  ai_in_qa_best_practices     tier 3, synthesized readable wiki
  ai_in_qa_best_practices_ru  Russian generic rules digest derived from tier 3

Per-project scored reviews live under `reviews/` and are named
`<Project>_ai_adoption_review_<YYYY-MM-DD>` - one document per session, never
rewritten; a re-review is a new dated document. See
ai-adoption-review/references/knowledge-base-contract.md for the tiering rules
and ai-adoption-review/SKILL.md for the lane boundary vs 30_Project_Knowledge,
40_PM_Case_Library and 50_QA_Department_Standards.

Read functions (find_*) never create anything; ensure_* functions create what's
missing. Reuses m2_workspace_layout's generic Drive helpers rather than
duplicating them.
"""

from __future__ import annotations

import re
from typing import Any

from m2_workspace_layout import (
    DOC_MIME,
    drive_query,
    ensure_child_folder,
    find_child_folder,
    q_escape,
)
from sync_m2_source_docs_to_sheets import ROOT_FOLDER_ID

AI_ADOPTION_ROOT_NAME = "55_AI_Adoption"
REVIEWS_FOLDER_NAME = "reviews"

# Document role -> (canonical file name, mime type). All of these live directly
# under the root folder; per-project reviews live under REVIEWS_FOLDER_NAME.
DOCUMENT_LAYOUT: dict[str, tuple[str, str]] = {
    "ai_adoption_source_notes": ("ai_adoption_source_notes", DOC_MIME),
    "ai_adoption_knowledge_store": ("ai_adoption_knowledge_store", DOC_MIME),
    "ai_in_qa_best_practices": ("ai_in_qa_best_practices", DOC_MIME),
    # Russian-language generic rules digest derived from the tier-3 wiki. NOT a
    # translation: it deliberately drops all project/session/person references
    # and states only rules, so its content differs from its source by design
    # (see knowledge-base-contract.md, "Derived language editions").
    "ai_in_qa_best_practices_ru": ("ai_in_qa_best_practices_ru", DOC_MIME),
}

# Derived edition -> the document it is derived from. A change to the source
# leaves every derived edition stale; regenerate it rather than patching both,
# and never treat these as line-for-line translations.
DERIVED_EDITIONS: dict[str, str] = {
    "ai_in_qa_best_practices_ru": "ai_in_qa_best_practices",
}

REVIEW_NAME_RE = re.compile(
    r"^(?P<project>.+)_ai_adoption_review_(?P<date>\d{4}-\d{2}-\d{2})$"
)


def find_root(drive: Any) -> dict[str, Any] | None:
    """Read-only lookup of the 55_AI_Adoption root folder."""
    return find_child_folder(drive, ROOT_FOLDER_ID, AI_ADOPTION_ROOT_NAME)


def ensure_root(drive: Any) -> dict[str, Any]:
    """Create the 55_AI_Adoption root folder if it doesn't exist yet."""
    return ensure_child_folder(drive, ROOT_FOLDER_ID, AI_ADOPTION_ROOT_NAME)


def find_reviews_folder(drive: Any) -> dict[str, Any] | None:
    """Read-only lookup of the reviews subfolder. None if either it or the
    root folder doesn't exist yet."""
    root = find_root(drive)
    if not root:
        return None
    return find_child_folder(drive, root["id"], REVIEWS_FOLDER_NAME)


def ensure_reviews_folder(drive: Any) -> dict[str, Any]:
    """Create the reviews subfolder (and the root, if needed)."""
    root = ensure_root(drive)
    return ensure_child_folder(drive, root["id"], REVIEWS_FOLDER_NAME)


def find_document(drive: Any, role: str) -> dict[str, Any] | None:
    """Read-only lookup of one of the workspace-level knowledge base documents
    under the root folder. Returns None if the root folder or the document itself doesn't
    exist yet - callers create it the first time a real source is actually
    processed, never speculatively."""
    if role not in DOCUMENT_LAYOUT:
        raise ValueError(f"Unknown AI Adoption document role: {role!r}")
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
        raise RuntimeError(f"Duplicate {role!r} document under {AI_ADOPTION_ROOT_NAME}")
    return matches[0] if matches else None


def review_document_name(project: str, review_date: str) -> str:
    """Canonical review document name. `review_date` is ISO YYYY-MM-DD."""
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", review_date):
        raise ValueError(f"review_date must be ISO YYYY-MM-DD, got {review_date!r}")
    project = project.strip()
    if not project:
        raise ValueError("project must not be empty")
    return f"{project}_ai_adoption_review_{review_date}"


def parse_review_document_name(name: str) -> tuple[str, str] | None:
    """Inverse of review_document_name. None if `name` isn't a review document."""
    match = REVIEW_NAME_RE.match(name.strip())
    if not match:
        return None
    return match.group("project"), match.group("date")


def find_reviews(drive: Any, project: str | None = None) -> list[dict[str, Any]]:
    """Read-only listing of review documents, newest first. With `project`,
    only that project's reviews - which is how a review pass finds the previous
    one it has to cite."""
    folder = find_reviews_folder(drive)
    if not folder:
        return []
    matches = drive_query(
        drive,
        f"'{folder['id']}' in parents and mimeType = '{DOC_MIME}' and trashed = false",
    )
    parsed: list[tuple[str, dict[str, Any]]] = []
    for item in matches:
        fields = parse_review_document_name(item.get("name", ""))
        if not fields:
            continue
        item_project, item_date = fields
        if project is not None and item_project != project.strip():
            continue
        parsed.append((item_date, item))
    parsed.sort(key=lambda pair: pair[0], reverse=True)
    return [item for _, item in parsed]
