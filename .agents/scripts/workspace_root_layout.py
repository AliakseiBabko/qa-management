"""Pure rules for the QA Management root-folder lifecycle."""

from __future__ import annotations

import re
from pathlib import PurePosixPath


INBOX_ROOT = "00_Inbox"
REFERENCE_ROOT = "30_Reference"
SYSTEM_ROOT = "_System"
EXPORTS_ROOT = "80_Exports"
ARCHIVE_ROOT = "90_Archive"
LEGACY_SOURCE_ROOT = "00_Source_Docs"

ACTIVE_STATUSES = {
    "discovered", "needs_scope", "ready", "processing", "blocked",
    "finalizing", "failed",
}
PROCESSED_STATUSES = {"completed", "historical"}

SYSTEM_EXPORT_FOLDERS = {
    "source_extracts": (SYSTEM_ROOT, "extracts", "source"),
    "homework_extracts": (SYSTEM_ROOT, "extracts", "homework"),
    "intake_review": (SYSTEM_ROOT, "reviews", "intake"),
    "open_questions_review": (SYSTEM_ROOT, "reviews", "open_questions"),
}

LEGACY_CATEGORY_NAMES = {
    "01_Meeting_Transcripts": "Meeting_Transcripts",
    "02_Chats_and_Emails": "Chats_and_Emails",
    "03_Source_Documents": "Source_Documents",
}


def normalize_relative_path(value: str) -> str:
    normalized = value.replace("\\", "/").strip("/")
    path = PurePosixPath(normalized)
    if not normalized or path.is_absolute() or ".." in path.parts:
        raise ValueError(f"Unsafe relative path: {value!r}")
    return path.as_posix()


def ignored_category(reason: str) -> str:
    match = re.match(r"ignored \(([^)]+)\)", reason.strip())
    return match.group(1) if match else ""


def source_disposition(row: dict) -> str:
    status = str(row.get("Status", "")).strip()
    if status in ACTIVE_STATUSES:
        return "inbox"
    if status in PROCESSED_STATUSES:
        return "archive"
    if status == "ignored":
        category = ignored_category(str(row.get("Reason", "")))
        if category in {"reference_material", "non_intake_course_material"}:
            return "reference"
        if category == "duplicate_data_quality":
            return "archive"
    return "ambiguous"


def source_destination(source: str, disposition: str) -> tuple[str, ...]:
    normalized = normalize_relative_path(source)
    parts = PurePosixPath(normalized).parts
    if not parts or parts[0] != LEGACY_SOURCE_ROOT:
        raise ValueError(f"Source is outside {LEGACY_SOURCE_ROOT}: {source!r}")
    tail = list(parts[1:])
    if not tail:
        raise ValueError("Source path names the legacy root itself")

    filename = tail[-1]
    if disposition == "inbox":
        return (INBOX_ROOT, filename)
    if disposition == "archive":
        category_tail = [LEGACY_CATEGORY_NAMES[tail[0]], *tail[1:]] if tail[0] in LEGACY_CATEGORY_NAMES else tail
        return (ARCHIVE_ROOT, "Processed_Sources", *category_tail)
    if disposition == "reference":
        category_tail = [LEGACY_CATEGORY_NAMES[tail[0]], *tail[1:]] if tail[0] in LEGACY_CATEGORY_NAMES else tail
        return (REFERENCE_ROOT, *category_tail)
    raise ValueError(f"No destination for disposition {disposition!r}")


def processed_run_destination(run_id: str, filename: str, date_text: str) -> tuple[str, ...]:
    if not run_id or "/" in run_id or "\\" in run_id:
        raise ValueError("Invalid run id for archive destination")
    if PurePosixPath(filename).name != filename:
        raise ValueError("Archive filename must not contain path components")
    match = re.fullmatch(r"(\d{4})-(\d{2})-\d{2}", date_text)
    if not match:
        raise ValueError(f"Invalid archive date: {date_text!r}")
    return (ARCHIVE_ROOT, "Processed_Sources", match.group(1), match.group(2), run_id, filename)


def latest_rows_by_source(rows: list[dict]) -> dict[str, dict]:
    result: dict[str, dict] = {}
    for row in rows:
        source = str(row.get("Source", "")).strip()
        if source:
            result[normalize_relative_path(source).casefold()] = row
    return result
