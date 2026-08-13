"""Safe Google Docs batchUpdate primitives - inspection helpers plus a
descending-index-ordering guarantee for multi-edit inserts.

Why this exists
----------------
Every skill that edits a Google Doc via the raw Docs API has to solve the
same two problems by hand, and one of them has a real, sharp failure mode:

1. **Heading-inheritance on insert.** `insertText` at a location that sits
   exactly at a heading paragraph's own `startIndex` (the common "insert
   new content right before this section's heading" move, e.g. appending
   to the end of the preceding section) makes the newly-inserted text
   silently inherit that heading's style - it becomes a run of fake
   `HEADING_2`/`HEADING_3` paragraphs, not the `NORMAL_TEXT` intended,
   unless an explicit `updateParagraphStyle` is applied over the inserted
   range in the same call. `pipeline_common._insert_blocks` already
   handles this for its own callers; this module generalizes the same
   fix for everything else.
2. **Multi-edit ordering.** When one `batchUpdate` call contains more than
   one `insertText` (or a mix of insert/delete) computed against indices
   from a single earlier `documents().get()` snapshot, the requests must
   be ordered so a lower-index edit is applied AFTER a higher-index one -
   otherwise the higher-index edit's own precomputed index (still
   expressed in the ORIGINAL, pre-edit document) gets silently
   invalidated by the lower one shifting content forward first. This
   produced a real, in-production corruption incident: two edits for one
   document (an end-of-document append and a mid-document insert) were
   listed in ascending index order in one `batchUpdate` call. The
   lower-index insert ran first, shifting the document forward by its own
   length; the higher-index append's precomputed index no longer pointed
   where it was meant to, and its text landed mid-word inside content the
   first edit had just inserted, splitting a word in two and merging two
   paragraphs. Repaired by hand afterward via `deleteContentRange` +
   re-insert at the correct (re-fetched) position - see
   `delete_and_reinsert()` below for that exact repair shape, generalized.

`safe_batch_insert_text()` (and the pure `build_batch_insert_requests()`
it wraps) makes ordering a non-issue: pass edits in any order, indexed
against one shared "before" snapshot of the document, and it sorts them
descending before building requests - callers never reason about ordering
themselves again.

Nothing in this module knows about any specific document, project, or
piece of business content - every example in this docstring and in the
module's tests uses synthetic placeholder text only.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DocEdit:
    """One text insertion to make into a Doc.

    `index` must be expressed in the ORIGINAL (pre-edit) document's own
    coordinate space - typically read once via `list_headings()`/
    `find_paragraph_containing()`/`document_end_index()` before any edit
    in the same batch is applied. Multiple `DocEdit`s passed together to
    `safe_batch_insert_text()`/`build_batch_insert_requests()` are always
    reordered internally (descending by `index`) before use, so the
    caller-supplied order never matters.

    `style` is applied to the ENTIRE inserted range via an explicit
    `updateParagraphStyle` - always, never left to inherit from whatever
    paragraph happens to sit at `index` (see module docstring, point 1).
    Use `"NORMAL_TEXT"` (the default) for ordinary prose, or a heading
    style (`"HEADING_1"`/`"HEADING_2"`/`"HEADING_3"`) when the inserted
    text is itself a new heading.
    """
    index: int
    text: str
    style: str = "NORMAL_TEXT"


# ---------------------------------------------------------------------
# Read-only inspection helpers
# ---------------------------------------------------------------------

def _paragraph_text(paragraph: dict[str, Any]) -> str:
    return "".join(r.get("textRun", {}).get("content", "") for r in paragraph.get("elements", []))


def list_headings(
    docs_service: Any,
    doc_id: str,
    levels: tuple[str, ...] = ("HEADING_1", "HEADING_2", "HEADING_3"),
) -> list[tuple[str, int, int, str]]:
    """Read-only. Returns `(style, start_index, end_index, text)` for
    every heading-styled paragraph in the doc, in document order -
    exactly the shape needed to find a section's boundaries before
    computing an insertion index (e.g. "the end of section X" is the
    `start_index` of the heading that comes right after it)."""
    doc = docs_service.documents().get(documentId=doc_id).execute()
    out: list[tuple[str, int, int, str]] = []
    for el in doc["body"]["content"]:
        paragraph = el.get("paragraph")
        if not paragraph:
            continue
        style = paragraph.get("paragraphStyle", {}).get("namedStyleType", "")
        if style in levels:
            out.append((style, el["startIndex"], el["endIndex"], _paragraph_text(paragraph)))
    return out


def find_paragraph_containing(docs_service: Any, doc_id: str, needle: str) -> tuple[int, int, str] | None:
    """Read-only. Returns `(start_index, end_index, text)` for the first
    paragraph whose text contains `needle` verbatim, or `None` if no
    paragraph matches. Useful for locating a specific already-written
    passage to correct in place, or to verify an edit landed as one
    paragraph (not split across two - the corruption shape this module
    exists to prevent)."""
    doc = docs_service.documents().get(documentId=doc_id).execute()
    for el in doc["body"]["content"]:
        paragraph = el.get("paragraph")
        if not paragraph:
            continue
        text = _paragraph_text(paragraph)
        if needle in text:
            return el["startIndex"], el["endIndex"], text
    return None


def document_end_index(docs_service: Any, doc_id: str) -> int:
    """Read-only. Returns the correct insertion index for "append at the
    very end of the document" (e.g. a Change Log's last line) - one
    before the document body's own final (always-empty) trailing
    paragraph, never that paragraph's own `endIndex` itself (which would
    insert past the end of the body and fail)."""
    doc = docs_service.documents().get(documentId=doc_id).execute()
    return doc["body"]["content"][-1]["endIndex"] - 1


# ---------------------------------------------------------------------
# Safe multi-edit insert
# ---------------------------------------------------------------------

def build_batch_insert_requests(edits: list[DocEdit]) -> list[dict[str, Any]]:
    """Pure computation, no API calls. Given `edits` in ANY order, returns
    the `batchUpdate` `requests` list that performs all of them safely -
    sorted descending by `index` first (see module docstring, point 2),
    with an explicit `updateParagraphStyle` over each inserted range
    (module docstring, point 1). Exposed separately from
    `safe_batch_insert_text()` so the ordering/request-shape logic is
    testable with zero Google API mocking."""
    ordered = sorted(edits, key=lambda edit: edit.index, reverse=True)
    requests: list[dict[str, Any]] = []
    for edit in ordered:
        end = edit.index + len(edit.text)
        requests.append({"insertText": {"location": {"index": edit.index}, "text": edit.text}})
        requests.append({
            "updateParagraphStyle": {
                "range": {"startIndex": edit.index, "endIndex": end},
                "paragraphStyle": {"namedStyleType": edit.style},
                "fields": "namedStyleType",
            }
        })
    return requests


def safe_batch_insert_text(docs_service: Any, doc_id: str, edits: list[DocEdit]) -> None:
    """Apply one or more text insertions to a Doc in a single `batchUpdate`
    call, safely regardless of the order `edits` was given in - see
    `build_batch_insert_requests()`. No-op if `edits` is empty (never
    issues a call with zero requests)."""
    if not edits:
        return
    requests = build_batch_insert_requests(edits)
    docs_service.documents().batchUpdate(documentId=doc_id, body={"requests": requests}).execute()


def safe_insert_text(docs_service: Any, doc_id: str, index: int, text: str, style: str = "NORMAL_TEXT") -> None:
    """Convenience wrapper for a single insertion. Prefer
    `safe_batch_insert_text()` directly when making more than one edit to
    the same document in one pass, so they land in one `batchUpdate` call
    instead of several round trips."""
    safe_batch_insert_text(docs_service, doc_id, [DocEdit(index=index, text=text, style=style)])


# ---------------------------------------------------------------------
# Repair primitive
# ---------------------------------------------------------------------

def build_delete_and_reinsert_requests(
    delete_start: int,
    delete_end: int,
    reinsert: DocEdit | None = None,
) -> list[dict[str, Any]]:
    """Pure computation, no API calls. Builds a `deleteContentRange` for
    `[delete_start, delete_end)`, optionally combined with re-inserting
    `reinsert` elsewhere in the SAME document, ordered correctly so
    neither operation invalidates the other's original-coordinate index -
    the exact repair shape a real corruption incident needed by hand (see
    module docstring): delete a misplaced insertion found via
    `find_paragraph_containing()`, and re-insert the same or corrected
    text at the actually-intended position (often `document_end_index()`).

    Raises `ValueError` if `reinsert.index` falls strictly inside the
    range being deleted - that position won't exist anymore after the
    delete, so there is no single well-defined coordinate space for it."""
    if reinsert is not None and delete_start < reinsert.index < delete_end:
        raise ValueError(
            f"reinsert.index ({reinsert.index}) falls inside the deleted range "
            f"[{delete_start}, {delete_end}) - not a valid combined edit."
        )

    delete_request = {"deleteContentRange": {"range": {"startIndex": delete_start, "endIndex": delete_end}}}
    insert_requests: list[dict[str, Any]] = []
    if reinsert is not None:
        end = reinsert.index + len(reinsert.text)
        insert_requests = [
            {"insertText": {"location": {"index": reinsert.index}, "text": reinsert.text}},
            {
                "updateParagraphStyle": {
                    "range": {"startIndex": reinsert.index, "endIndex": end},
                    "paragraphStyle": {"namedStyleType": reinsert.style},
                    "fields": "namedStyleType",
                }
            },
        ]

    if reinsert is not None and reinsert.index > delete_start:
        # The reinsertion point sits after the deleted range - apply it
        # first (higher index), same descending-order rule as
        # build_batch_insert_requests().
        return insert_requests + [delete_request]
    return [delete_request] + insert_requests


def delete_and_reinsert(
    docs_service: Any,
    doc_id: str,
    delete_start: int,
    delete_end: int,
    reinsert: DocEdit | None = None,
) -> None:
    """Executes `build_delete_and_reinsert_requests()`'s result in one
    `batchUpdate` call - see that function for the request shape and
    ordering guarantee."""
    requests = build_delete_and_reinsert_requests(delete_start, delete_end, reinsert)
    docs_service.documents().batchUpdate(documentId=doc_id, body={"requests": requests}).execute()
