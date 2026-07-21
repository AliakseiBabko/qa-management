"""Shared one-line service setup for the M2/M1 Google API pipeline scripts.

Every script under .agents/scripts that talks to Drive/Sheets/Docs repeats the
same load_credentials + build_services boilerplate. This is the shared
version - new scripts should use get_services() instead of re-inlining it.
Existing scripts are not required to migrate; this just stops the pattern
from being copy-pasted again going forward.

Also holds append_doc_round() and get_last_round_status() - the m2_input
round-append logic that got hand-rolled separately for two different
projects (character-offset tracking + paragraph-style requests duplicated
each time, a real bug risk). New strategy-chat processing should call
these instead of rewriting the index math.
"""

from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path
from typing import Any

from google_api_smoke_test import build_services, load_credentials

DEFAULT_CREDENTIALS = Path(".local/google/credentials.json")
DEFAULT_TOKEN = Path(".local/google/token.json")

ANSWER_HEADING = "Ответ и общие соображения M2"

# Single merged people registry (2026-07-17) - replaces the former separate
# _m1_people_registry (10_M1_People_Management) and _m2_people_registry
# (20_M2_Project_Management), which duplicated ~10 of 13 columns between them
# and had no principled rule for which sheet owned which field - that's what
# let Name (EN) silently go missing in one sheet while other fields got filled.
# Lives in its own top-level folder (not nested under 10_ or 20_) so a repo
# clone used for only M1 or only M2 work still finds it without needing the
# other skill's folder.
PEOPLE_REGISTRY_FOLDER = "05_People_Management"
PEOPLE_REGISTRY_SHEET = "_people_registry"
PEOPLE_REGISTRY_HEADER = [
    "Name (RU)", "Name (EN)", "Email", "Side", "Worker ID", "M1",
    "Role", "Internal rank", "Project(s)", "Дата трудоустройства",
    "Дата последнего PR", "Первый коммерческий проект", "Aliases / spelling variants", "Notes",
]
# Column index constants - use these instead of magic numbers so a future
# schema change (e.g. inserting a column) doesn't silently break every
# script that indexes into a row by hand.
PR_NAME_RU, PR_NAME_EN, PR_EMAIL, PR_SIDE, PR_WORKER_ID, PR_M1, PR_ROLE, \
    PR_RANK, PR_PROJECT, PR_HIRE_DATE, PR_LAST_PR, PR_FIRST_COMMERCIAL, \
    PR_ALIASES, PR_NOTES = range(len(PEOPLE_REGISTRY_HEADER))


def get_people_registry_sheet(services):
    """Resolve the merged people registry Sheet (creating the folder if
    needed, but never the sheet itself - a missing sheet is a real problem,
    not something to silently recreate empty)."""
    from show_project_state import find_folder
    from sync_m2_source_docs_to_sheets import ROOT_FOLDER_ID, find_or_create_folder, find_sheet_in_folder

    people_root = find_or_create_folder(services["drive"], ROOT_FOLDER_ID, PEOPLE_REGISTRY_FOLDER)
    sheet = find_sheet_in_folder(services["drive"], people_root["id"], PEOPLE_REGISTRY_SHEET)
    if not sheet:
        raise SystemExit(f"{PEOPLE_REGISTRY_SHEET} not found under {PEOPLE_REGISTRY_FOLDER} - has it been created?")
    return sheet


# Workspace-wide log of which skill(s) actually got applied when processing a
# source document (2026-07-17) - separate from evidence_log (which is
# per-project and answers "which live documents changed"), this answers "what
# skill combo handled this kind of source," across both M1 and M2, so those
# patterns can eventually be analyzed instead of only living in conversation
# history. Lives at the workspace root, not nested under 10_/20_, for the
# same clone-independence reason as _people_registry.
SKILL_INVOCATIONS_SHEET = "_skill_invocations"
SKILL_INVOCATIONS_HEADER = [
    "Date", "Source", "Source type", "Project", "Person", "Skills applied", "Documents touched", "Notes",
]
# Canonical source_type values - keep in sync with google-workspace-rules.md's
# evidence_log list; extend both together rather than picking an ad hoc value
# silently at the point of use.
SKILL_INVOCATION_SOURCE_TYPES = {
    "strategy_chat", "meeting_transcript", "m1_history", "m2_conversation",
    "qa_1to1", "admin_note", "people_case_chat", "retro",
    # Pre-classification labels written by prepare_intake_review.py on
    # newly-discovered files ("pending M2 review" evidence rows). A source
    # keeps one of these only until it's classified into a type above.
    "raw_transcript", "raw_chat", "source_document",
}


def get_skill_invocations_sheet(services):
    """Resolve the workspace-wide skill-invocations log (creating it if this
    is the first call ever - unlike the people registry, an empty log is a
    legitimate starting state, not a sign something's missing)."""
    from sync_m2_source_docs_to_sheets import ROOT_FOLDER_ID, create_sheet, find_sheet_in_folder

    sheet = find_sheet_in_folder(services["drive"], ROOT_FOLDER_ID, SKILL_INVOCATIONS_SHEET)
    if sheet:
        return sheet
    return create_sheet(services, SKILL_INVOCATIONS_SHEET, ROOT_FOLDER_ID, [SKILL_INVOCATIONS_HEADER])


def log_skill_invocation(
    services,
    *,
    date: str,
    source: str,
    source_type: str,
    skills: str,
    project: str = "",
    person: str = "",
    documents_touched: str = "",
    notes: str = "",
) -> None:
    """Append one row to _skill_invocations. `skills` and `documents_touched`
    are comma-separated strings, same convention as evidence_log's
    `routed_to` - list every skill actually applied, not just the first one
    that seems to fit. `source_type` should be one of
    SKILL_INVOCATION_SOURCE_TYPES; add a genuinely new shape to that set
    (and to google-workspace-rules.md's list) rather than inventing an ad
    hoc value here."""
    from sync_m2_source_docs_to_sheets import read_sheet_values

    if source_type not in SKILL_INVOCATION_SOURCE_TYPES:
        raise ValueError(
            f"Unrecognized source_type {source_type!r} - add it to SKILL_INVOCATION_SOURCE_TYPES "
            "(and google-workspace-rules.md) if this is a genuinely new source shape."
        )
    sheet = get_skill_invocations_sheet(services)
    rows = read_sheet_values(services, sheet["id"])
    header, body = (rows[0], rows[1:]) if rows else (SKILL_INVOCATIONS_HEADER, [])
    body.append([date, source, source_type, project, person, skills, documents_touched, notes])
    title = services["sheets"].spreadsheets().get(spreadsheetId=sheet["id"]).execute()["sheets"][0]["properties"]["title"]
    services["sheets"].spreadsheets().values().clear(spreadsheetId=sheet["id"], range=f"'{title}'").execute()
    services["sheets"].spreadsheets().values().update(
        spreadsheetId=sheet["id"], range=f"'{title}'!A1", valueInputOption="RAW",
        body={"values": [header, *body]},
    ).execute()
    reformat_sheet(services, sheet["id"], SKILL_INVOCATIONS_SHEET)


def get_services(
    credentials_path: Path | str = DEFAULT_CREDENTIALS,
    token_path: Path | str = DEFAULT_TOKEN,
) -> dict[str, Any]:
    creds = load_credentials(Path(credentials_path), Path(token_path))
    return build_services(creds)


def reformat_sheet(services: dict[str, Any], spreadsheet_id: str, name: str = "") -> None:
    """Recompute column widths/row heights for one Sheet right after writing to it.

    format_all_sheets.py's row-height heuristic is the only thing that keeps
    row height in sync with cell content - a values().update() never touches
    dimension properties, so a Sheet whose Notes column keeps growing (person
    cards, registry refreshes, etc.) silently clips visually unless something
    recomputes height after every write that changes content length. Call
    this right after such a write instead of relying on someone remembering
    to rerun format_all_sheets.py by hand later.

    Best effort - a formatting failure (e.g. a transient API timeout) must
    never make the caller think its actual data write failed too.
    """
    from format_all_sheets import format_sheet  # local import: avoid loading it for scripts that never write

    try:
        format_sheet(services["sheets"], spreadsheet_id, name or spreadsheet_id)
    except Exception as exc:  # noqa: BLE001
        print(f"WARNING: could not reformat {name or spreadsheet_id} after write: {exc}", file=sys.stderr)


def get_project_person_folder(services: dict[str, Any], project: str, person: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Resolve (project_folder, person_folder) under
    20_M2_Project_Management/<project>/people/<person>/shared - the canonical
    employee-visible folder used by individual_metrics and
    individual_development_plan. This replaces the repeated
    m2_root -> project -> people -> person lookup that was hand-rolled at
    the top of apply-1to1-findings-style scripts (a
    copy-paste source of at least one real IndexError). Uses
    canonical folder helpers, so it's safe to call for a person who doesn't
    have a shared folder yet. It
    does not create the project folder itself if missing; that's still a
    deliberate step, not something to paper over silently."""
    from sync_m2_source_docs_to_sheets import ROOT_FOLDER_ID, find_or_create_folder

    drive = services["drive"]
    m2_root = find_or_create_folder(drive, ROOT_FOLDER_ID, "20_M2_Project_Management")
    project_folder = find_or_create_folder(drive, m2_root["id"], project)
    from m2_workspace_layout import ensure_document_folder

    person_folder = ensure_document_folder(
        drive, project_folder["id"], "individual_metrics", person
    )
    return project_folder, person_folder


def _insert_blocks(docs_service: Any, doc_id: str, insert_at: int, blocks: list[tuple[str, str]]) -> None:
    """Shared insert logic: build insertText + paragraph-style requests for
    a (kind, text) block list starting at a given index, and apply them.

    Inserted text inherits the paragraph style of whatever's AT the
    insertion point (e.g. an empty "Ответ и общие соображения M2" HEADING_2
    paragraph) until explicitly overridden. Every block's range is
    therefore explicitly (re)set to NORMAL_TEXT first, then HEADING_2 is
    applied on top for heading2-kind blocks - never rely on inheritance
    defaulting to normal text (it doesn't when the insertion point happens
    to be a heading, which is exactly the append_to_pending_round case)."""
    text_parts: list[str] = []
    heading2: list[tuple[int, int]] = []
    bullets: list[tuple[int, int]] = []
    cursor = insert_at
    for kind, text in blocks:
        content = text + "\n"
        start = cursor
        end = start + len(content)
        if kind == "heading2":
            heading2.append((start, end))
        elif kind == "bullet":
            bullets.append((start, end))
        text_parts.append(content)
        cursor = end
    inserted_end = cursor

    requests: list[dict[str, Any]] = [
        {"insertText": {"location": {"index": insert_at}, "text": "".join(text_parts)}},
        {
            "updateParagraphStyle": {
                "range": {"startIndex": insert_at, "endIndex": inserted_end},
                "paragraphStyle": {"namedStyleType": "NORMAL_TEXT"},
                "fields": "namedStyleType",
            }
        },
    ]
    for start, end in heading2:
        requests.append({
            "updateParagraphStyle": {
                "range": {"startIndex": start, "endIndex": end},
                "paragraphStyle": {"namedStyleType": "HEADING_2"},
                "fields": "namedStyleType",
            }
        })
    for start, end in bullets:
        requests.append({
            "createParagraphBullets": {
                "range": {"startIndex": start, "endIndex": end},
                "bulletPreset": "BULLET_DISC_CIRCLE_SQUARE",
            }
        })
    docs_service.documents().batchUpdate(documentId=doc_id, body={"requests": requests}).execute()


def _find_answer_heading_start(docs_service: Any, doc_id: str) -> tuple[dict[str, Any], int | None]:
    """Locate the start index of the CURRENT round's answer heading - the
    LAST "Ответ и общие соображения M2" heading in the doc, mirroring
    get_last_round_status's own last-match logic. A doc with more than one
    round (an earlier answered one plus a later pending one) has more than
    one such heading; returning the first one instead of the last means an
    addendum meant for the pending round lands in the wrong, already-
    answered round instead (this happened once on a real project; see that
    project's own m2_input history/evidence_log for the fix)."""
    doc = docs_service.documents().get(documentId=doc_id).execute()
    answer_start = None
    for element in doc["body"]["content"]:
        if "paragraph" not in element:
            continue
        text = "".join(run.get("textRun", {}).get("content", "") for run in element["paragraph"]["elements"])
        if text.strip() == ANSWER_HEADING:
            answer_start = element["startIndex"]
    return doc, answer_start


def append_doc_round(docs_service: Any, doc_id: str, blocks: list[tuple[str, str]]) -> None:
    """Append a brand-new dated round to the end of a Doc (e.g. m2_input).

    blocks is a list of (kind, text) pairs, kind one of "heading2", "bullet",
    "normal". Inserts before the Doc's trailing empty paragraph so a blank
    line is preserved at the very end, matching the existing m2_input
    convention of one dated section per round.

    Use this only to open a NEW round. To add content to an ALREADY-pending
    round (see get_last_round_status), use append_to_pending_round instead -
    appending here would land after the empty "Ответ и общие соображения M2"
    heading and make get_last_round_status wrongly read the round as
    answered (this happened once on a real project; see the project's own
    m2_input history/evidence_log for the fix).
    """
    doc = docs_service.documents().get(documentId=doc_id).execute()
    end_index = doc["body"]["content"][-1]["endIndex"]
    _insert_blocks(docs_service, doc_id, end_index - 1, blocks)


def append_to_pending_round(docs_service: Any, doc_id: str, blocks: list[tuple[str, str]]) -> None:
    """Add an addendum to the CURRENT round while it's still pending, by
    inserting right before the "Ответ и общие соображения M2" heading -
    keeping that heading's answer section genuinely empty so
    get_last_round_status still reads the round as pending.

    Raises ValueError if the doc has no answer heading (call
    get_last_round_status first and use append_doc_round instead if the doc
    doesn't have the expected shape, or the round is already answered and a
    new one should be opened).
    """
    doc, answer_start = _find_answer_heading_start(docs_service, doc_id)
    if answer_start is None:
        raise ValueError(
            f"No '{ANSWER_HEADING}' heading found in doc {doc_id} - can't locate the pending round to "
            "extend. Use append_doc_round to open a new round instead."
        )
    _insert_blocks(docs_service, doc_id, answer_start, blocks)


def add_questions(
    docs_service: Any,
    doc_id: str,
    blocks: list[tuple[str, str]],
    round_date: str | None = None,
) -> dict[str, Any]:
    """Add new question/context content to an m2_input Doc - the entry point
    to use instead of picking between append_doc_round and
    append_to_pending_round yourself (that choice was made wrong once on a
    real project; see that project's own m2_input history/evidence_log).

    Auto-routes on the doc's current state (via get_last_round_status):
    - a round is pending -> appended as an addendum before the answer
      heading (append_to_pending_round), so the round stays correctly
      pending.
    - no round is pending (answered, or the doc has no round yet) -> a
      fresh round is opened with today's date (or round_date if given),
      wrapping `blocks` in the full heading scaffold, via append_doc_round.

    blocks is just the question/context content itself - (kind, text)
    pairs, kind one of "heading2" (for a labeled sub-section within the
    round), "bullet", "normal". Do not include the "Раунд:"/"Вопросы от
    предварительного анализа"/answer headings yourself; they're added
    automatically when a new round needs to be opened.

    Returns the status dict (see get_last_round_status) after the write.
    """
    status = get_last_round_status(docs_service, doc_id)
    if status["pending"]:
        append_to_pending_round(docs_service, doc_id, blocks)
    else:
        date = round_date or dt.date.today().isoformat()
        scaffold: list[tuple[str, str]] = [
            ("heading2", f"Раунд: {date}"),
            ("heading2", "Вопросы от предварительного анализа"),
            *blocks,
            ("heading2", ANSWER_HEADING),
            ("normal", ""),
        ]
        append_doc_round(docs_service, doc_id, scaffold)
    return get_last_round_status(docs_service, doc_id)


def add_answer(docs_service: Any, doc_id: str, blocks: list[tuple[str, str]]) -> dict[str, Any]:
    """Write answer content into the CURRENT pending round of an m2_input
    Doc. Requires a round to actually be pending - raises ValueError
    otherwise, since answering a round that's already answered (or doesn't
    exist) is not a valid action; open one with add_questions first.

    blocks is the answer content - (kind, text) pairs. Inserted at the
    Doc's end, which lands right after the empty answer heading, filling it
    in and making the round read as answered afterward.

    Returns the status dict (see get_last_round_status) after the write.
    """
    status = get_last_round_status(docs_service, doc_id)
    if not status["pending"]:
        raise ValueError(
            f"No pending round in doc {doc_id} to answer (status={status}). "
            "Use add_questions to open a new round first."
        )
    append_doc_round(docs_service, doc_id, blocks)
    return get_last_round_status(docs_service, doc_id)


QUESTIONS_HEADING = "Вопросы от предварительного анализа"


def get_pending_round_questions(docs_service: Any, doc_id: str) -> str:
    """Return the question text of the CURRENT pending round (everything
    between the last 'Вопросы от предварительного анализа' heading and the
    last 'Ответ и общие соображения M2' heading), or "" if no round is
    pending or the doc has no round yet.

    Used by scan_open_questions.py to surface what's still waiting on an M2
    answer without requiring a full doc dump - a pending round with no
    answer is itself an open item.
    """
    doc = docs_service.documents().get(documentId=doc_id).execute()
    paragraphs: list[tuple[str, str]] = []
    for element in doc["body"]["content"]:
        if "paragraph" not in element:
            continue
        style = element["paragraph"].get("paragraphStyle", {}).get("namedStyleType", "NORMAL_TEXT")
        text = "".join(run.get("textRun", {}).get("content", "") for run in element["paragraph"]["elements"])
        paragraphs.append((style, text))

    questions_idx = answer_idx = None
    for i, (style, text) in enumerate(paragraphs):
        if style != "HEADING_2":
            continue
        stripped = text.strip()
        if stripped == QUESTIONS_HEADING:
            questions_idx = i
        elif stripped == ANSWER_HEADING:
            answer_idx = i

    if questions_idx is None or answer_idx is None or answer_idx <= questions_idx:
        return ""
    after_answer = "".join(text for _, text in paragraphs[answer_idx + 1 :]).strip()
    if after_answer:
        return ""  # round already answered, nothing pending
    return "".join(text for _, text in paragraphs[questions_idx + 1 : answer_idx]).strip()


def get_pending_round_summary(docs_service: Any, doc_id: str) -> dict[str, Any]:
    """Content-free summary of the CURRENT pending round, for `qa_manage.py
    gates` (Phase 12): never returns the actual question/addendum text,
    only counts and the first addendum heading label (itself just a dated
    section title, not question content) - safe to print/log without
    leaking business content.

    Returns {"round_date": str | None, "pending": bool | None,
    "addenda_count": int, "block_chars": int, "first_heading": str | None}.
    addenda_count/block_chars/first_heading are 0/0/None when no round is
    pending (mirrors get_last_round_status's None-means-no-signal
    convention)."""
    doc = docs_service.documents().get(documentId=doc_id).execute()
    paragraphs: list[tuple[str, str]] = []
    for element in doc["body"]["content"]:
        if "paragraph" not in element:
            continue
        style = element["paragraph"].get("paragraphStyle", {}).get("namedStyleType", "NORMAL_TEXT")
        text = "".join(run.get("textRun", {}).get("content", "") for run in element["paragraph"]["elements"])
        paragraphs.append((style, text))

    round_date = None
    questions_idx = answer_idx = None
    for i, (style, text) in enumerate(paragraphs):
        stripped = text.strip()
        if style == "HEADING_2" and stripped.startswith("Раунд:"):
            round_date = stripped.split(":", 1)[1].strip()
        if style == "HEADING_2" and stripped == QUESTIONS_HEADING:
            questions_idx = i
        elif style == "HEADING_2" and stripped == ANSWER_HEADING:
            answer_idx = i

    if answer_idx is None:
        return {"round_date": round_date, "pending": None, "addenda_count": 0,
                "block_chars": 0, "first_heading": None}

    after_answer = "".join(text for _, text in paragraphs[answer_idx + 1:]).strip()
    if after_answer or questions_idx is None or answer_idx <= questions_idx:
        return {"round_date": round_date, "pending": False, "addenda_count": 0,
                "block_chars": 0, "first_heading": None}

    window = paragraphs[questions_idx + 1: answer_idx]
    block_chars = len("".join(text for _, text in window).strip())
    addenda_headings = [text.strip() for style, text in window
                         if style == "HEADING_2" and text.strip().startswith("Дополнение (")]
    return {
        "round_date": round_date,
        "pending": True,
        "addenda_count": len(addenda_headings),
        "block_chars": block_chars,
        "first_heading": addenda_headings[0] if addenda_headings else None,
    }


def get_last_round_status(docs_service: Any, doc_id: str) -> dict[str, Any]:
    """Read an m2_input Doc and report the most recent round's date and
    whether it's still waiting on an answer (the text after the last
    "Ответ и общие соображения M2" heading is empty).

    Returns {"round_date": str | None, "pending": bool | None} - pending is
    None if the doc has no answer-section heading at all (unexpected/older
    format), so a caller can distinguish "no signal" from "answered".
    """
    doc = docs_service.documents().get(documentId=doc_id).execute()
    paragraphs: list[tuple[str, str]] = []
    for element in doc["body"]["content"]:
        if "paragraph" not in element:
            continue
        style = element["paragraph"].get("paragraphStyle", {}).get("namedStyleType", "NORMAL_TEXT")
        text = "".join(run.get("textRun", {}).get("content", "") for run in element["paragraph"]["elements"])
        paragraphs.append((style, text))

    round_date = None
    for style, text in paragraphs:
        stripped = text.strip()
        if style == "HEADING_2" and stripped.startswith("Раунд:"):
            round_date = stripped.split(":", 1)[1].strip()

    answer_idx = None
    for i, (style, text) in enumerate(paragraphs):
        if style == "HEADING_2" and text.strip() == ANSWER_HEADING:
            answer_idx = i

    if answer_idx is None:
        return {"round_date": round_date, "pending": None}

    after = "".join(text for _, text in paragraphs[answer_idx + 1 :]).strip()
    return {"round_date": round_date, "pending": not bool(after)}
