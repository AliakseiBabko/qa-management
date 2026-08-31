"""Canonical folder layout for Assessments & Interviews (60_Assessments_And_Interviews).

A per-session lane, not a per-project or per-person current-state lane: each
run is one dated feedback document about one meeting that already happened,
plus one row in a flat index. That is why the shape is
`<root>/<type folder>/<Person>/<date>_<output>` - the *type* of session owns
the rules and the output form (an internal grade assessment and an external
client interview are scored against different criteria and produce different
documents), and the person is the second level so one candidate's repeat
sessions of the same type sit together.

Contrast with the neighbouring lanes:
  10_M1_People_Management  person-first, current-state, longitudinal
  20_M2_Project_Management project-first, current-state
  40_PM_Case_Library       flat, cross-project pattern reference
  50_QA_Department_Standards flat, current-state department reference
  60_Assessments_And_Interviews  type-first, per-session, append-only

Read functions (find_*) never create anything; ensure_* functions create what
is missing. Reuses m2_workspace_layout's generic Drive helpers rather than
duplicating them, same as pm_case_workspace_layout.py and
qa_dept_standards_workspace_layout.py.
"""

from __future__ import annotations

import re
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

ASSESSMENT_ROOT_NAME = "60_Assessments_And_Interviews"

# Session type -> the folder that holds every session of that type. A type
# folder is created on the first real session of that type, never upfront.
# `other_interview` exists for a session that is genuinely neither (a mock
# interview, a screening, an internal role interview): it has no owning
# feedback skill yet, so it stores the output a skill-less pass produced
# rather than forcing it into one of the two scored forms.
TYPE_FOLDERS: dict[str, str] = {
    "internal_assessment": "internal_assessments",
    "external_interview": "external_interviews",
    "other_interview": "other_interviews",
}

# Output document role -> (filename suffix, mime type). The full document name
# is "<YYYY-MM-DD>_<suffix> - <Person>" (see session_document_name), so a
# person folder sorts chronologically and a document is identifiable out of
# context, e.g. when it is linked from Jira or a chat.
DOCUMENT_LAYOUT: dict[str, tuple[str, str]] = {
    "assessment_feedback": ("assessment_feedback", DOC_MIME),
    "interview_feedback": ("interview_feedback", DOC_MIME),
    "session_transcript": ("transcript", DOC_MIME),
}

# One row per processed session, flat at the lane root - the ground-truth
# "what was run, for whom, with what outcome" record, the same role
# pk_source_index and pm_case_index play in their own lanes.
INDEX_NAME = "_assessment_index"
INDEX_COLUMNS: tuple[str, ...] = (
    "Date",
    "Person",
    "Session Type",
    "Target Grade/Role",
    "Format",
    "Inputs",
    "Outcome",
    "Key Gap",
    "Feedback Doc",
    "Follow-up",
    "Updated",
)

_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def normalize_type(session_type: str) -> str:
    """Accept either the canonical key or its folder name."""
    if session_type in TYPE_FOLDERS:
        return session_type
    for key, folder in TYPE_FOLDERS.items():
        if session_type == folder:
            return key
    raise ValueError(
        f"Unknown session type {session_type!r} - expected one of "
        f"{sorted(TYPE_FOLDERS)}"
    )


def session_document_name(role: str, date_text: str, person: str) -> str:
    """"<date>_<suffix> - <Person>", the canonical output document name."""
    if role not in DOCUMENT_LAYOUT:
        raise ValueError(f"Unknown assessment document role: {role!r}")
    if not _DATE.fullmatch(date_text):
        raise ValueError(f"Session date must be YYYY-MM-DD, got {date_text!r}")
    person = person.strip()
    if not person:
        raise ValueError("Session document name needs a person")
    suffix, _ = DOCUMENT_LAYOUT[role]
    return f"{date_text}_{suffix} - {person}"


def find_root(drive: Any) -> dict[str, Any] | None:
    """Read-only lookup of the 60_Assessments_And_Interviews root folder."""
    return find_child_folder(drive, ROOT_FOLDER_ID, ASSESSMENT_ROOT_NAME)


def ensure_root(drive: Any) -> dict[str, Any]:
    return ensure_child_folder(drive, ROOT_FOLDER_ID, ASSESSMENT_ROOT_NAME)


def find_type_folder(drive: Any, session_type: str) -> dict[str, Any] | None:
    root = find_root(drive)
    if not root:
        return None
    return find_child_folder(drive, root["id"], TYPE_FOLDERS[normalize_type(session_type)])


def ensure_type_folder(drive: Any, session_type: str) -> dict[str, Any]:
    root = ensure_root(drive)
    return ensure_child_folder(drive, root["id"], TYPE_FOLDERS[normalize_type(session_type)])


def find_person_folder(drive: Any, session_type: str, person: str) -> dict[str, Any] | None:
    type_folder = find_type_folder(drive, session_type)
    if not type_folder:
        return None
    return find_child_folder(drive, type_folder["id"], person.strip())


def ensure_person_folder(drive: Any, session_type: str, person: str) -> dict[str, Any]:
    type_folder = ensure_type_folder(drive, session_type)
    return ensure_child_folder(drive, type_folder["id"], person.strip())


def find_session_document(drive: Any, session_type: str, person: str, role: str,
                          date_text: str) -> dict[str, Any] | None:
    """Read-only lookup of one session's output document. Returns None when
    the lane, the type folder, the person folder, or the document itself does
    not exist yet - callers create only what a real session needs, never
    speculatively."""
    person_folder = find_person_folder(drive, session_type, person)
    if not person_folder:
        return None
    name = session_document_name(role, date_text, person)
    _, mime_type = DOCUMENT_LAYOUT[role]
    matches = drive_query(
        drive,
        f"'{person_folder['id']}' in parents and name = '{q_escape(name)}' and "
        f"mimeType = '{mime_type}' and trashed = false",
    )
    if len(matches) > 1:
        raise RuntimeError(f"Duplicate {role!r} document for {name!r}")
    return matches[0] if matches else None


def find_index(drive: Any) -> dict[str, Any] | None:
    """Read-only lookup of the flat _assessment_index Sheet at the lane root."""
    root = find_root(drive)
    if not root:
        return None
    matches = drive_query(
        drive,
        f"'{root['id']}' in parents and name = '{q_escape(INDEX_NAME)}' and "
        f"mimeType = '{SHEET_MIME}' and trashed = false",
    )
    if len(matches) > 1:
        raise RuntimeError(f"Duplicate {INDEX_NAME} under {ASSESSMENT_ROOT_NAME}")
    return matches[0] if matches else None
