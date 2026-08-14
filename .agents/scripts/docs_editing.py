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

CLI (targeted, read-only verification)
---------------------------------------
`list_headings()`/`find_paragraph_containing()`/`document_end_index()`
are also reachable as a small CLI, so a verification pass ("did that
heading structure survive?", "did that insert land as one paragraph, not
split across two?") never needs a full-document export just to check a
few lines - a real, recurring cost on this workspace's larger Docs
(some run past 300K characters). Every subcommand calls the same single
`documents().get()` a full export would use, but prints only the small
matching slice - never the full document body.

    python docs_editing.py headings --id <doc_id> [--levels HEADING_1,HEADING_2]
    python docs_editing.py find --id <doc_id> --text "<substring>"
    python docs_editing.py end-index --id <doc_id>

For an actual full-text export/read, use `read_google_doc.py` instead -
this CLI is deliberately not a substitute for it.
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from google_api_smoke_test import ensure_utf8_stdout
from pipeline_common import get_services


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


def find_paragraph_by_prefix(docs_service: Any, doc_id: str, prefix: str) -> tuple[int, int, str]:
    """Read-only. Returns `(start_index, end_index, text)` for the ONE
    paragraph whose stripped text starts with `prefix`. Raises `ValueError`
    if zero or more than one paragraph matches - unlike
    `find_paragraph_containing()` (which happily returns the first hit),
    this is the safety-checked variant for a write that's about to REPLACE
    a paragraph in place: writing to the wrong (or an ambiguous) match is a
    real corruption risk, so ambiguity must fail loud, not silently pick
    one. Exists for the common "correct an Open Question/case paragraph
    that starts with a stable numbered/tagged prefix" edit shape - matching
    on the whole paragraph text is brittle (any later hand-edit breaks the
    match), matching on just the leading prefix survives that."""
    doc = docs_service.documents().get(documentId=doc_id).execute()
    matches: list[tuple[int, int, str]] = []
    for el in doc["body"]["content"]:
        paragraph = el.get("paragraph")
        if not paragraph:
            continue
        text = _paragraph_text(paragraph)
        if text.strip().startswith(prefix):
            matches.append((el["startIndex"], el["endIndex"], text))
    if not matches:
        raise ValueError(f"No paragraph found starting with {prefix!r}")
    if len(matches) > 1:
        locations = ", ".join(str(m[0]) for m in matches)
        raise ValueError(f"{len(matches)} paragraphs start with {prefix!r} (at indices {locations}) - ambiguous")
    return matches[0]


_HEADING_RANK = {"HEADING_1": 1, "HEADING_2": 2, "HEADING_3": 3}


def section_end_index(docs_service: Any, doc_id: str, heading_text: str) -> int:
    """Read-only. Returns the insertion index for "the end of the section
    under this heading" - the `start_index` of the next heading whose rank
    is the SAME OR BROADER than this one (e.g. an H3's section ends at the
    next H3, H2, or H1; an H2's section ends at the next H2 or H1, skipping
    over any H3 sub-headings inside it), or `document_end_index()` if this
    is the last such section in the document. This is the exact
    boundary-finding logic that previously got re-derived by hand in a
    fresh one-off script for every "add this new content to the end of an
    existing knowledge-base/case-library section" edit.

    `heading_text` is matched by exact stripped equality against
    `list_headings()`'s output and must match exactly one heading in the
    document - raises `ValueError` if it matches zero or more than one
    (ambiguous heading text, e.g. two same-named H3s in different
    sections, needs a more specific caller-side lookup instead)."""
    headings = list_headings(docs_service, doc_id)
    matches = [h for h in headings if h[3].strip() == heading_text]
    if not matches:
        raise ValueError(f"No heading found with exact text {heading_text!r}")
    if len(matches) > 1:
        locations = ", ".join(str(m[1]) for m in matches)
        raise ValueError(f"{len(matches)} headings match {heading_text!r} (at indices {locations}) - ambiguous")
    style, _start, end, _text = matches[0]
    rank = _HEADING_RANK.get(style, 0)
    for h_style, h_start, _h_end, _h_text in headings:
        if h_start <= end:
            continue
        if _HEADING_RANK.get(h_style, 0) <= rank:
            return h_start
    return document_end_index(docs_service, doc_id)


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


# ---------------------------------------------------------------------
# Tables - real Docs tables instead of inline-text data dumps
# ---------------------------------------------------------------------
#
# Why this exists: a Doc with a lot of comparable rows of data (a monthly
# trajectory, a coverage breakdown, a per-module status list) reads far
# better as a real Docs table than as a paragraph of "Area: X, Value: Y;
# Area: Z, Value: W" prose - see
# qa-management-roles/references/google-workspace/artifact-conventions.md's
# "Docs Rules" for the convention this backs. Table insertion has its own
# sharp edge, found and fixed the same way the heading-inheritance bug was:
# `insertTable` creates an EMPTY table, so filling it needs a real
# `documents().get()` round trip to learn each cell's actual insertion
# index - guessing cell indices in advance produces silent misplacement,
# not an error. One extra property makes a SECOND round trip unnecessary
# though: because every cell is a separate, non-overlapping paragraph,
# filling cells in strict descending original-index order (the same
# guarantee `build_batch_insert_requests` already provides) never disturbs
# an as-yet-unfilled cell's own original index - including the header
# row's, which is why the header-bold ranges below can be computed from
# the SAME pre-fill snapshot as the fill requests themselves, in one pass.


def find_table_at_or_after(doc: dict[str, Any], min_index: int) -> dict[str, Any]:
    """Read-only. Returns the `table`-bearing body element whose own
    `startIndex` is the smallest one >= `min_index` - i.e. "the table most
    recently inserted at/after that index". Raises if none exists."""
    candidates = [el for el in doc["body"]["content"] if "table" in el and el["startIndex"] >= min_index]
    if not candidates:
        raise ValueError(f"No table found at or after index {min_index}")
    return min(candidates, key=lambda el: el["startIndex"])


def table_cell_insertion_points(table_el: dict[str, Any]) -> list[tuple[int, int, int]]:
    """Read-only. Returns (row, col, insertion_index) for every cell in a
    table element, in reading order - each cell's first paragraph's own
    `startIndex` is where text can be inserted into that (empty) cell."""
    points: list[tuple[int, int, int]] = []
    for r, row in enumerate(table_el["table"]["tableRows"]):
        for c, cell in enumerate(row["tableCells"]):
            points.append((r, c, cell["content"][0]["startIndex"]))
    return points


def build_table_fill_requests(table_el: dict[str, Any], data: list[list[str]], bold_header: bool = True) -> list[dict[str, Any]]:
    """Pure. Given a just-inserted (still-empty) table element and `data`
    (list of rows, each a list of per-column strings; row 0 is treated as
    the header), returns the full request list to fill every cell and
    (if `bold_header`) bold the header row - all computable from this one
    snapshot, no second `get()` needed (see module note above for why that
    holds). Silently skips a cell whose data string is empty. Raises if
    `data`'s shape doesn't match the table's actual row/column count."""
    rows = table_el["table"]["tableRows"]
    if len(data) != len(rows):
        raise ValueError(f"data has {len(data)} rows, table has {len(rows)}")
    for r, row in enumerate(rows):
        if len(data[r]) != len(row["tableCells"]):
            raise ValueError(f"data row {r} has {len(data[r])} columns, table row has {len(row['tableCells'])}")

    points = table_cell_insertion_points(table_el)
    text_by_cell = {(r, c): data[r][c] for r in range(len(data)) for c in range(len(data[r]))}

    fill_requests: list[dict[str, Any]] = []
    header_ranges: list[tuple[int, int]] = []
    for r, c, idx in sorted(points, key=lambda p: p[2], reverse=True):
        text = text_by_cell.get((r, c), "")
        if text:
            fill_requests.append({"insertText": {"location": {"index": idx}, "text": text}})
        if r == 0 and text:
            header_ranges.append((idx, idx + len(text)))

    bold_requests = [
        {
            "updateTextStyle": {
                "range": {"startIndex": start, "endIndex": end},
                "textStyle": {"bold": True},
                "fields": "bold",
            }
        }
        for start, end in header_ranges
    ] if bold_header else []

    return fill_requests + bold_requests


def insert_table(docs_service: Any, doc_id: str, index: int, data: list[list[str]], bold_header: bool = True) -> None:
    """Inserts a real Docs table at `index` and fills it from `data` (list
    of rows, each a list of per-column strings; row 0 is treated as the
    header and bolded by default) - three total API calls: `insertTable`,
    one `get()` to learn real cell indices, one `batchUpdate` to fill every
    cell and bold the header, both computed from that single snapshot (see
    `build_table_fill_requests`). `index` should be a real insertion point
    (e.g. from `document_end_index()`), not a guess."""
    rows = len(data)
    cols = len(data[0]) if data else 0
    if rows == 0 or cols == 0:
        raise ValueError("data must have at least one row and one column")

    docs_service.documents().batchUpdate(
        documentId=doc_id,
        body={"requests": [{"insertTable": {"rows": rows, "columns": cols, "location": {"index": index}}}]},
    ).execute()

    doc = docs_service.documents().get(documentId=doc_id).execute()
    table_el = find_table_at_or_after(doc, index)
    requests = build_table_fill_requests(table_el, data, bold_header=bold_header)
    if requests:
        docs_service.documents().batchUpdate(documentId=doc_id, body={"requests": requests}).execute()


# ---------------------------------------------------------------------
# CLI - targeted, read-only verification (never dumps a full document)
# ---------------------------------------------------------------------

PREVIEW_LEN = 80


def preview(text: str, limit: int = PREVIEW_LEN) -> str:
    """Compact, single-line preview of a paragraph's text: collapses
    embedded whitespace/newlines and truncates to `limit` characters with
    a trailing ellipsis if longer. Exists so CLI output for even a very
    long paragraph stays a few dozen characters - the whole point of this
    CLI is never approaching full-document-dump cost."""
    collapsed = " ".join(text.split())
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[:limit].rstrip() + "…"


def _cmd_headings(docs_service: Any, args: argparse.Namespace) -> int:
    levels = tuple(args.levels.split(",")) if args.levels else ("HEADING_1", "HEADING_2", "HEADING_3")
    headings = list_headings(docs_service, args.id, levels=levels)
    if not headings:
        print("(no headings found)")
        return 0
    for style, start, end, text in headings:
        print(f"{style}\t{start}\t{end}\t{preview(text)}")
    return 0


def _cmd_find(docs_service: Any, args: argparse.Namespace) -> int:
    result = find_paragraph_containing(docs_service, args.id, args.text)
    if result is None:
        print("not found")
        return 1
    start, end, text = result
    print(f"start={start} end={end} text={preview(text)}")
    return 0


def _cmd_end_index(docs_service: Any, args: argparse.Namespace) -> int:
    print(document_end_index(docs_service, args.id))
    return 0


def _load_text_file(path: str) -> str:
    """Reads a text file for a write command and guarantees a trailing
    newline (every paragraph this module inserts must end in one - a
    caller-supplied file missing it would otherwise silently merge with
    whatever paragraph follows the insertion point)."""
    text = Path(path).read_text(encoding="utf-8")
    return text if text.endswith("\n") else text + "\n"


def _cmd_append_section(docs_service: Any, args: argparse.Namespace) -> int:
    """Insert text at the end of a named section (before the next
    same-or-broader-level heading, or at document end if it's the last
    section) - the single most common Project-Knowledge/PM-Case-Library
    edit shape: adding a new dated update to an existing heading's
    content."""
    index = section_end_index(docs_service, args.id, args.heading)
    text = _load_text_file(args.text_file)
    if args.dry_run:
        print(f"[dry-run] would insert {len(text)} chars at index {index} (end of section {args.heading!r}), style={args.style}")
        print(preview(text, limit=200))
        return 0
    safe_insert_text(docs_service, args.id, index, text, style=args.style)
    print(f"Inserted {len(text)} chars at index {index} (end of section {args.heading!r}).")
    return 0


def _cmd_replace_paragraph(docs_service: Any, args: argparse.Namespace) -> int:
    """Replace ONE paragraph, matched uniquely by its leading prefix, with
    new text - the "correct an existing Open Question/case entry in place"
    edit shape. Fails loud (via `find_paragraph_by_prefix`) if the prefix
    matches zero or more than one paragraph, rather than guessing."""
    start, end, old_text = find_paragraph_by_prefix(docs_service, args.id, args.prefix)
    new_text = _load_text_file(args.text_file)
    if args.dry_run:
        print(f"[dry-run] would replace paragraph [{start}, {end}):")
        print(f"  old: {preview(old_text)}")
        print(f"  new: {preview(new_text, limit=200)}")
        return 0
    delete_and_reinsert(
        docs_service, args.id, start, end - 1,
        reinsert=DocEdit(index=start, text=new_text, style=args.style),
    )
    print(f"Replaced paragraph at {start}.")
    return 0


def _cmd_append_end(docs_service: Any, args: argparse.Namespace) -> int:
    """Append text at the very end of the document (e.g. a new dated
    Change Log line) - before the document's own trailing empty
    paragraph."""
    index = document_end_index(docs_service, args.id)
    text = _load_text_file(args.text_file)
    if args.dry_run:
        print(f"[dry-run] would insert {len(text)} chars at document end (index {index})")
        print(preview(text, limit=200))
        return 0
    safe_insert_text(docs_service, args.id, index, text, style="NORMAL_TEXT")
    print(f"Inserted {len(text)} chars at document end (index {index}).")
    return 0


def _cmd_insert_at(docs_service: Any, args: argparse.Namespace) -> int:
    """Insert text at a caller-supplied raw index - the escape hatch for an
    insertion point `append-section`/`append-end` don't cover (e.g. right
    after one specific heading rather than at the end of its whole
    section). Still goes through `safe_insert_text`, so the inserted range
    always gets its own explicit paragraph style rather than inheriting
    from whatever sits at that index."""
    text = _load_text_file(args.text_file)
    if args.dry_run:
        print(f"[dry-run] would insert {len(text)} chars at index {args.index}, style={args.style}")
        print(preview(text, limit=200))
        return 0
    safe_insert_text(docs_service, args.id, args.index, text, style=args.style)
    print(f"Inserted {len(text)} chars at index {args.index}.")
    return 0


def build_cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Targeted Google Docs read/write helper - inspection subcommands never dump "
            "the full document body; write subcommands go through this module's safe "
            "insert/replace primitives instead of a one-off batchUpdate script. For a "
            "full-text export, use read_google_doc.py instead."
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    headings_p = sub.add_parser("headings", help="List heading paragraphs: style, start, end, short preview.")
    headings_p.add_argument("--id", required=True, help="Docs document ID.")
    headings_p.add_argument(
        "--levels",
        help="Comma-separated heading styles to include, e.g. HEADING_1,HEADING_2. "
             "Default: HEADING_1,HEADING_2,HEADING_3.",
    )
    headings_p.set_defaults(func=_cmd_headings)

    find_p = sub.add_parser("find", help="Find the first paragraph containing a substring.")
    find_p.add_argument("--id", required=True, help="Docs document ID.")
    find_p.add_argument("--text", required=True, help="Substring to search for, verbatim.")
    find_p.set_defaults(func=_cmd_find)

    end_p = sub.add_parser("end-index", help="Print the document's correct end-of-body insertion index.")
    end_p.add_argument("--id", required=True, help="Docs document ID.")
    end_p.set_defaults(func=_cmd_end_index)

    append_section_p = sub.add_parser(
        "append-section",
        help="Insert a text file's content at the end of a named section (before the next same-or-broader heading).",
    )
    append_section_p.add_argument("--id", required=True, help="Docs document ID.")
    append_section_p.add_argument("--heading", required=True, help="Exact heading text to append under (must match exactly one heading).")
    append_section_p.add_argument("--text-file", required=True, help="Path to a UTF-8 text file with the content to insert.")
    append_section_p.add_argument("--style", default="NORMAL_TEXT", help="Paragraph style for the inserted text. Default: NORMAL_TEXT.")
    append_section_p.add_argument("--dry-run", action="store_true", help="Print what would be inserted without writing.")
    append_section_p.set_defaults(func=_cmd_append_section)

    replace_p = sub.add_parser(
        "replace-paragraph",
        help="Replace the one paragraph starting with a given prefix with a text file's content.",
    )
    replace_p.add_argument("--id", required=True, help="Docs document ID.")
    replace_p.add_argument("--prefix", required=True, help="Leading text that uniquely identifies the paragraph to replace.")
    replace_p.add_argument("--text-file", required=True, help="Path to a UTF-8 text file with the replacement content.")
    replace_p.add_argument("--style", default="NORMAL_TEXT", help="Paragraph style for the replacement text. Default: NORMAL_TEXT.")
    replace_p.add_argument("--dry-run", action="store_true", help="Print what would change without writing.")
    replace_p.set_defaults(func=_cmd_replace_paragraph)

    append_end_p = sub.add_parser("append-end", help="Append a text file's content at the very end of the document.")
    append_end_p.add_argument("--id", required=True, help="Docs document ID.")
    append_end_p.add_argument("--text-file", required=True, help="Path to a UTF-8 text file with the content to insert.")
    append_end_p.add_argument("--dry-run", action="store_true", help="Print what would be inserted without writing.")
    append_end_p.set_defaults(func=_cmd_append_end)

    insert_at_p = sub.add_parser("insert-at", help="Insert a text file's content at a specific raw character index.")
    insert_at_p.add_argument("--id", required=True, help="Docs document ID.")
    insert_at_p.add_argument("--index", required=True, type=int, help="Character index to insert at (from a prior headings/find/end-index call).")
    insert_at_p.add_argument("--text-file", required=True, help="Path to a UTF-8 text file with the content to insert.")
    insert_at_p.add_argument("--style", default="NORMAL_TEXT", help="Paragraph style for the inserted text. Default: NORMAL_TEXT.")
    insert_at_p.add_argument("--dry-run", action="store_true", help="Print what would be inserted without writing.")
    insert_at_p.set_defaults(func=_cmd_insert_at)

    return parser


def main() -> int:
    ensure_utf8_stdout()
    args = build_cli_parser().parse_args()
    services = get_services()
    return args.func(services["docs"], args)


if __name__ == "__main__":
    sys.exit(main())
